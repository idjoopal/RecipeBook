#!/usr/bin/env python3
"""
LLM Manager Module
LLM 매니저 모듈

환경변수와 모델명을 기준으로 LLM 백엔드(Cohere/OpenAI)를 선택해 호출합니다.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Literal

import cohere
import httpx

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - optional dependency fallback
    AsyncOpenAI = None  # type: ignore[assignment]

from src.utils.config_loader import (
    get_env,
    get_env_bool,
    get_env_float,
    get_env_int,
    load_root_env,
)

# .env 파일 로드 (모듈 import 시 1회 실행)
load_root_env()

# 네트워크 관련 예외 (공통)
NETWORK_EXCEPTIONS = (
    httpx.ReadError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.NetworkError,
    httpx.TimeoutException,
    ConnectionError,
    TimeoutError,
)

logger = logging.getLogger(__name__)
LLMProvider = Literal["cohere", "openai"]

# Cohere 엔드포인트 별칭 레지스트리 prefix.
# 예) COHERE_ENDPOINT_NORTH_LARGE=http://172.20.22.199 → 별칭 'north-large'
_COHERE_ENDPOINT_PREFIX = "COHERE_ENDPOINT_"

# OpenAI reasoning_effort 허용 값.
_OPENAI_REASONING_EFFORTS = {"minimal", "low", "medium", "high"}


def _load_cohere_endpoints() -> dict[str, str]:
    """env의 COHERE_ENDPOINT_<ALIAS>=<base_url> 를 {별칭: base_url} 로 수집.

    별칭 정규화: prefix 제거 → 소문자 → '_'를 '-'로 치환.
    (load_root_env()가 import 시 실행되어 os.environ에 이미 로드됨.)
    """
    registry: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith(_COHERE_ENDPOINT_PREFIX):
            continue
        url = (value or "").strip()
        if not url:
            continue
        alias = key[len(_COHERE_ENDPOINT_PREFIX):].strip().lower().replace("_", "-")
        if alias:
            registry[alias] = url
    return registry


class LLMManager:
    """Cohere/OpenAI 백엔드를 모델명으로 라우팅하는 LLM 매니저."""

    # 공통 설정 (기존 환경변수 호환)
    BASE_URL: str = get_env("BASE_URL", "https://api.cohere.ai")
    CLIENT_NAME: str = get_env("CLIENT_NAME", "prebuilt-mcp")
    API_KEY: str = get_env("API_KEY", "")
    TIMEOUT: float = get_env_float("TIMEOUT", 120.0)
    MODEL: str = get_env("MODEL", "command-r-plus")
    TEMPERATURE: float = get_env_float("TEMPERATURE", 0.3)
    TOP_K: int = get_env_int("TOP_K", 0)
    MAX_TOKENS: int = get_env_int("MAX_TOKENS", 4096)
    THINKING: bool = get_env_bool("THINKING", False)

    # Cohere 전용 설정
    COHERE_BASE_URL: str = get_env("COHERE_BASE_URL", BASE_URL)
    COHERE_CLIENT_NAME: str = get_env("COHERE_CLIENT_NAME", CLIENT_NAME)
    COHERE_API_KEY: str = get_env("COHERE_API_KEY", API_KEY)
    COHERE_MODEL: str = get_env("COHERE_MODEL", MODEL)

    # OpenAI 전용 설정
    OPENAI_BASE_URL: str = get_env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_API_KEY: str = get_env("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = get_env("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_TIMEOUT: float = get_env_float("OPENAI_TIMEOUT", TIMEOUT)

    # 임베딩 전용 설정 (OpenAI text-embedding-*; aembed에서 사용)
    EMBEDDING_MODEL: str = get_env("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMS: int = get_env_int("EMBEDDING_DIMS", 1536)

    # 추론(thinking/reasoning) 기본값 — 둘 다 기본 OFF, 원할 때만 켠다.
    THINKING_DEFAULT: bool = get_env_bool("THINKING", False)
    OPENAI_REASONING_EFFORT: str = get_env("OPENAI_REASONING_EFFORT", "").strip().lower()

    # Cohere 엔드포인트 별칭 레지스트리 ({별칭: base_url})
    COHERE_ENDPOINTS: dict[str, str] = _load_cohere_endpoints()

    def __init__(self, base_url: str | None = None):
        """
        Args:
            base_url: Cohere base URL override (지정 시 별칭 레지스트리보다 우선되는 폴백).
        """
        self.cohere_base_url_override: str = (base_url or self.COHERE_BASE_URL or "").strip()
        # base_url별 Cohere 클라이언트 (여러 내부 엔드포인트 동시 사용 지원)
        self._cohere_clients: dict[str, cohere.AsyncClientV2] = {}
        self.openai_client: Any = None
        self._initialized_providers: set[LLMProvider] = set()

    @property
    def initialized(self) -> bool:
        """기존 코드 호환용 속성."""
        return self.is_initialized()

    def _resolve_provider_and_model(self, model_name: str | None) -> tuple[LLMProvider, str]:
        raw_model = (model_name or "").strip()

        if not raw_model:
            raw_model = (self.COHERE_MODEL or self.OPENAI_MODEL).strip()

        # Provider만 지정된 경우 → 전체 env에서 정의한 모델 사용
        # (예: agent env에서 NL2SQL_MODEL_ID=openai → OPENAI_MODEL 값 자동 사용)
        lowered = raw_model.lower()
        if lowered == "openai":
            return "openai", self.OPENAI_MODEL
        if lowered == "cohere":
            return "cohere", self.COHERE_MODEL

        # 명시적 접두사 지원: openai:gpt-4o-mini / cohere:command-r-plus
        for separator in (":", "/"):
            if separator in raw_model:
                provider_prefix, model_part = raw_model.split(separator, 1)
                provider_prefix = provider_prefix.strip().lower()
                model_part = model_part.strip()
                if provider_prefix in {"cohere", "openai"} and model_part:
                    return provider_prefix, model_part

        if lowered.startswith(("gpt-", "o1", "o3", "o4", "chatgpt")):
            provider: LLMProvider = "openai"
        else:
            provider = "cohere"

        final_model = raw_model.strip()
        if not final_model:
            final_model = self.OPENAI_MODEL if provider == "openai" else self.COHERE_MODEL

        if not final_model:
            raise ValueError("모델명이 비어 있습니다. MODEL 또는 모델 인자를 설정하세요.")

        return provider, final_model

    def _cohere_base_url_for(self, model: str) -> str:
        """Cohere 모델(별칭)에 대응하는 base_url을 결정합니다.

        우선순위: 별칭 레지스트리(COHERE_ENDPOINT_*) → base_url override/COHERE_BASE_URL
        → 레지스트리 단일 항목. 모두 없으면 명확한 에러.
        """
        alias = (model or "").strip().lower()
        url = self.COHERE_ENDPOINTS.get(alias)
        if url:
            return url
        if self.cohere_base_url_override:
            return self.cohere_base_url_override
        if self.COHERE_ENDPOINTS:
            return next(iter(self.COHERE_ENDPOINTS.values()))
        raise ValueError(
            f"Cohere 엔드포인트를 찾을 수 없습니다 (model='{model}'). "
            f".env에 COHERE_ENDPOINT_<별칭>=<base_url> 을 정의하고 "
            f"model_id를 cohere:<별칭> 으로 지정하세요."
        )

    async def _get_cohere_client(self, base_url: str) -> cohere.AsyncClientV2:
        """base_url별 Cohere 클라이언트를 lazy 생성/재사용합니다 (API 키 불필요)."""
        client = self._cohere_clients.get(base_url)
        if client is not None:
            return client

        kwargs: dict[str, Any] = {
            "base_url": base_url,
            # 내부 엔드포인트는 키 불필요 — SDK 요구에 맞춰 placeholder 전달
            "api_key": self.COHERE_API_KEY or self.API_KEY or "none",
            "timeout": self.TIMEOUT,
        }
        client_name = (self.COHERE_CLIENT_NAME or "").strip()
        if client_name:
            kwargs["client_name"] = client_name

        client = cohere.AsyncClientV2(**kwargs)
        self._cohere_clients[base_url] = client
        self._initialized_providers.add("cohere")
        return client

    async def initialize(self, model_name: str | None = None) -> None:
        """모델명 기준으로 필요한 provider 클라이언트를 초기화합니다."""
        provider, resolved_model = self._resolve_provider_and_model(model_name)

        try:
            if provider == "cohere":
                await self._get_cohere_client(self._cohere_base_url_for(resolved_model))
            else:
                if "openai" not in self._initialized_providers:
                    await self._initialize_openai()
                    self._initialized_providers.add("openai")
            logger.debug("LLM Manager initialized (provider=%s, model=%s)", provider, resolved_model)
        except NETWORK_EXCEPTIONS as e:
            error_msg = f"LLM 연결 실패 ({type(e).__name__}): {e or 'Connection failed'}"
            logger.error("[LLM] %s", error_msg)
            raise ConnectionError(error_msg) from e
        except Exception:
            logger.exception("Failed to initialize LLM Manager (provider=%s)", provider)
            raise

    async def _initialize_openai(self) -> None:
        if AsyncOpenAI is None:
            raise ImportError("openai 패키지가 설치되지 않았습니다. `uv sync` 또는 `pip install openai`를 실행하세요.")

        if not self.OPENAI_API_KEY:
            raise ConnectionError("OPENAI_API_KEY가 설정되지 않았습니다.")

        self.openai_client = AsyncOpenAI(
            api_key=self.OPENAI_API_KEY,
            base_url=self.OPENAI_BASE_URL,
            timeout=self.OPENAI_TIMEOUT,
        )

    async def ainvoke(
        self,
        msg: str,
        model_name: str | None = None,
        *,
        thinking: bool | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        """
        모델명을 기준으로 provider를 선택해 LLM을 호출합니다.

        Args:
            msg: 사용자 입력 프롬프트
            model_name: 모델명 (예: openai:gpt-4o-mini, cohere:north-large)
            thinking: (Cohere) 사고(thinking) 모드 강제. 기본 None → env THINKING(기본 OFF).
            reasoning_effort: (OpenAI) reasoning 모델의 추론 강도(minimal|low|medium|high).
                기본 None → env OPENAI_REASONING_EFFORT(기본 OFF). 둘 다 없으면 미적용.
        """
        provider, resolved_model = self._resolve_provider_and_model(model_name)

        try:
            if provider == "cohere":
                return await self._ainvoke_cohere(msg, resolved_model, thinking=thinking)
            return await self._ainvoke_openai(msg, resolved_model, reasoning_effort=reasoning_effort)
        except NETWORK_EXCEPTIONS as e:
            error_msg = (
                f"LLM API network error ({provider}, {type(e).__name__}): "
                f"{e or 'Connection failed'}"
            )
            logger.error("[LLM] %s", error_msg)
            raise RuntimeError(error_msg) from e
        except Exception:
            logger.exception("[LLM] Error (provider=%s, model=%s)", provider, resolved_model)
            raise

    async def ainvoke_json(
        self,
        msg: str,
        model_name: str | None = None,
        schema: dict | None = None,
    ) -> dict[str, Any]:
        """JSON 출력을 강제하는 LLM 호출.

        Returns:
            {"content": <parsed dict>, "usage": ..., "raw": ...}

        방어적 파싱: ``` 펜스 제거 → json.loads → 실패 시 1회 repair 재시도 → raise.
        """
        provider, resolved_model = self._resolve_provider_and_model(model_name)
        if provider not in self._initialized_providers:
            await self.initialize(model_name=resolved_model)

        try:
            if provider == "openai":
                raw_result = await self._ainvoke_openai_json(msg, resolved_model, schema)
            else:
                raw_result = await self._ainvoke_cohere(msg, resolved_model)
        except NETWORK_EXCEPTIONS as e:
            error_msg = f"LLM JSON API network error ({provider}): {e or 'Connection failed'}"
            logger.error("[LLM] %s", error_msg)
            raise RuntimeError(error_msg) from e
        except Exception:
            logger.exception("[LLM] ainvoke_json error (provider=%s)", provider)
            raise

        text = raw_result["content"]
        parsed = self._parse_json_robust(text)
        return {
            "content": parsed,
            "usage": raw_result.get("usage", {}),
            "raw": raw_result.get("raw"),
        }

    def _parse_json_robust(self, text: str) -> dict:
        """JSON 파싱. ``` 펜스 제거 후 시도, 실패 시 1회 repair."""
        # 코드 펜스 제거 (```json ... ``` 또는 ``` ... ```)
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Repair: 첫 { 부터 마지막 } 까지 추출
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다. 내용: {text[:300]!r}")

    async def _ainvoke_openai_json(
        self, msg: str, model_name: str, schema: dict | None = None
    ) -> dict[str, Any]:
        """OpenAI JSON mode를 이용한 호출."""
        if self.openai_client is None:
            raise RuntimeError("OpenAI client is None after initialization")

        lowered_model = model_name.lower()
        use_max_completion_tokens = lowered_model.startswith(("gpt-5", "o1", "o3", "o4"))

        # OpenAI json_object 모드는 메시지에 'json' 단어가 반드시 포함돼야 한다(400 방지).
        content = msg if "json" in msg.lower() else (msg + "\n\n(Return the answer as valid JSON.)")
        request_kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_object"},
        }
        if use_max_completion_tokens:
            request_kwargs["max_completion_tokens"] = self.MAX_TOKENS
        else:
            request_kwargs["max_tokens"] = self.MAX_TOKENS

        if (lowered_model.startswith("gpt-") or lowered_model.startswith("chatgpt")) and not use_max_completion_tokens:
            request_kwargs["temperature"] = self.TEMPERATURE

        start_time = time.perf_counter()
        response = await self.openai_client.chat.completions.create(**request_kwargs)
        elapsed_time = time.perf_counter() - start_time

        return {
            "content": self._extract_openai_text(response),
            "usage": self._extract_openai_usage(response, elapsed_time),
            "raw": response,
        }

    async def aembed(
        self, texts: list[str], model_name: str | None = None
    ) -> list[list[float]]:
        """텍스트 목록의 임베딩 벡터를 반환한다.

        OpenAI text-embedding-* 모델을 사용한다. OPENAI_API_KEY 필요.

        Returns:
            각 입력 텍스트에 대한 float 벡터 리스트.
        """
        embed_model = model_name or self.EMBEDDING_MODEL
        if "openai" not in self._initialized_providers:
            await self._initialize_openai()
            self._initialized_providers.add("openai")

        if self.openai_client is None:
            raise RuntimeError("OpenAI client is None after initialization")

        try:
            start_time = time.perf_counter()
            response = await self.openai_client.embeddings.create(
                model=embed_model,
                input=texts,
            )
            elapsed_time = time.perf_counter() - start_time

            vectors = [item.embedding for item in response.data]

            # 차원 검증
            if vectors and len(vectors[0]) != self.EMBEDDING_DIMS:
                logger.warning(
                    "[LLM] 임베딩 차원 불일치: 예상=%d, 실제=%d",
                    self.EMBEDDING_DIMS,
                    len(vectors[0]),
                )

            logger.debug(
                "[LLM] aembed: %d texts, elapsed=%.2fs", len(texts), elapsed_time
            )
            return vectors

        except NETWORK_EXCEPTIONS as e:
            raise RuntimeError(f"임베딩 API network error: {e}") from e
        except Exception:
            logger.exception("[LLM] aembed error")
            raise

    async def _ainvoke_cohere(
        self, msg: str, model_name: str, *, thinking: bool | None = None
    ) -> dict[str, Any]:
        client = await self._get_cohere_client(self._cohere_base_url_for(model_name))

        chat_kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": msg}],
            "temperature": self.TEMPERATURE,
            "k": self.TOP_K,
            "max_tokens": self.MAX_TOKENS,
        }
        # thinking: 인자 우선, 미지정 시 env 기본값(기본 OFF). True일 때만 활성.
        use_thinking = self.THINKING_DEFAULT if thinking is None else thinking
        if use_thinking:
            chat_kwargs["thinking"] = {"type": "enabled"}

        start_time = time.perf_counter()
        response = await client.chat(**chat_kwargs)
        elapsed_time = time.perf_counter() - start_time

        return {
            "content": self._extract_cohere_text(response),
            "usage": self._extract_cohere_usage(response, elapsed_time),
            "raw": response,
        }

    def _resolve_reasoning_effort(self, reasoning_effort: str | None) -> str:
        """reasoning_effort 인자/​env 를 정규화합니다. 기본 OFF(빈 문자열)."""
        raw = reasoning_effort if reasoning_effort is not None else self.OPENAI_REASONING_EFFORT
        effort = (raw or "").strip().lower()
        if not effort:
            return ""
        if effort not in _OPENAI_REASONING_EFFORTS:
            logger.warning(
                "[LLM] 잘못된 reasoning_effort='%s' (허용: %s) — 미적용",
                effort, ", ".join(sorted(_OPENAI_REASONING_EFFORTS)),
            )
            return ""
        return effort

    async def _ainvoke_openai(
        self, msg: str, model_name: str, *, reasoning_effort: str | None = None
    ) -> dict[str, Any]:
        if self.openai_client is None:
            await self._initialize_openai()
            self._initialized_providers.add("openai")

        lowered_model = model_name.lower()
        use_max_completion_tokens = lowered_model.startswith(("gpt-5", "o1", "o3", "o4"))

        request_kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": msg}],
        }

        # gpt-5/o-series는 max_completion_tokens만 허용
        if use_max_completion_tokens:
            request_kwargs["max_completion_tokens"] = self.MAX_TOKENS
        else:
            request_kwargs["max_tokens"] = self.MAX_TOKENS

        # 일부 최신 모델(gpt-5/o-series)은 temperature 미지원일 수 있어 제외
        if (lowered_model.startswith("gpt-") or lowered_model.startswith("chatgpt")) and not use_max_completion_tokens:
            request_kwargs["temperature"] = self.TEMPERATURE

        # reasoning_effort: 명시될 때만, 그리고 reasoning 계열 모델에서만 적용 (기본 OFF)
        effort = self._resolve_reasoning_effort(reasoning_effort)
        if effort and use_max_completion_tokens:
            request_kwargs["reasoning_effort"] = effort

        start_time = time.perf_counter()
        response = await self.openai_client.chat.completions.create(**request_kwargs)
        elapsed_time = time.perf_counter() - start_time

        return {
            "content": self._extract_openai_text(response),
            "usage": self._extract_openai_usage(response, elapsed_time),
            "raw": response,
        }

    def _extract_cohere_usage(self, response: Any, elapsed_time: float) -> dict[str, Any]:
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                tokens = getattr(usage, "tokens", None)
                if tokens is not None:
                    input_tokens = getattr(tokens, "input_tokens", None)
                    output_tokens = getattr(tokens, "output_tokens", None)
                    if input_tokens is not None:
                        input_tokens = int(input_tokens)
                    if output_tokens is not None:
                        output_tokens = int(output_tokens)
                    return {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "elapsed_time": elapsed_time,
                    }
        except Exception as e:
            logger.warning("Failed to extract usage from Cohere response: %s", e)

        return {
            "input_tokens": None,
            "output_tokens": None,
            "elapsed_time": elapsed_time,
        }

    def _extract_openai_usage(self, response: Any, elapsed_time: float) -> dict[str, Any]:
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                return {
                    "input_tokens": getattr(usage, "prompt_tokens", None),
                    "output_tokens": getattr(usage, "completion_tokens", None),
                    "elapsed_time": elapsed_time,
                }
        except Exception as e:
            logger.warning("Failed to extract usage from OpenAI response: %s", e)

        return {
            "input_tokens": None,
            "output_tokens": None,
            "elapsed_time": elapsed_time,
        }

    def _extract_cohere_text(self, response: Any) -> str:
        try:
            content = response.message.content
            if isinstance(content, list) and content:
                # thinking 등 비-텍스트 블록을 건너뛰고 type=='text' 블록을 우선 추출
                for item in content:
                    if getattr(item, "type", None) == "text" and getattr(item, "text", None):
                        return str(item.text)
                # type 미지정이라도 text 속성이 있으면 사용
                for item in content:
                    text = getattr(item, "text", None)
                    if text:
                        return str(text)
                return str(content[0])
            return str(content)
        except Exception as e:
            logger.warning("Failed to extract text from Cohere response: %s", e)
            return f"Error: {e}"

    def _extract_openai_text(self, response: Any) -> str:
        try:
            choices = getattr(response, "choices", None)
            if not choices:
                return ""
            message = getattr(choices[0], "message", None)
            if message is None:
                return ""
            content = getattr(message, "content", "")
            if content is None:
                return ""
            return content if isinstance(content, str) else str(content)
        except Exception as e:
            logger.warning("Failed to extract text from OpenAI response: %s", e)
            return f"Error: {e}"

    def is_initialized(self, model_name: str | None = None) -> bool:
        """초기화 여부를 반환합니다."""
        if model_name is None:
            return bool(self._initialized_providers)

        provider, _ = self._resolve_provider_and_model(model_name)
        return provider in self._initialized_providers

    async def cleanup(self) -> None:
        """HTTP 클라이언트 리소스를 정리합니다."""
        for base_url, client in list(self._cohere_clients.items()):
            try:
                if hasattr(client, "_client") and client._client is not None:
                    await client._client.aclose()
                    logger.debug("Cohere HTTP client closed (base_url=%s)", base_url)
            except Exception as e:
                logger.warning("Error closing Cohere HTTP client (%s): %s", base_url, e)
        self._cohere_clients.clear()

        if self.openai_client is not None:
            try:
                await self.openai_client.close()
                logger.debug("OpenAI HTTP client closed successfully")
            except Exception as e:
                logger.warning("Error closing OpenAI HTTP client: %s", e)
            finally:
                self.openai_client = None

        self._initialized_providers.clear()
