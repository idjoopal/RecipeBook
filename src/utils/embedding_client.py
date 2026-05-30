"""임베딩 클라이언트 — LLMManager.aembed 위 얇은 shim.

배치 처리 + 차원 검증. 다른 에이전트도 재사용 가능한 범용 유틸.
"""
from __future__ import annotations

from src.utils.logger import get_logger

logger = get_logger("embedding_client")


class Embedder:
    """LLMManager.aembed 위 배치 shim."""

    def __init__(self, llm_manager: any, expected_dims: int | None = None) -> None:
        self._llm = llm_manager
        self._dims = expected_dims

    async def aembed_one(self, text: str) -> list[float]:
        results = await self._llm.aembed([text])
        vec = results[0]
        self._check_dims(vec)
        return vec

    async def aembed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results = await self._llm.aembed(texts)
        for vec in results:
            self._check_dims(vec)
        return results

    def _check_dims(self, vec: list[float]) -> None:
        if self._dims and len(vec) != self._dims:
            raise ValueError(f"임베딩 차원 불일치: 기대={self._dims}, 실제={len(vec)}")
