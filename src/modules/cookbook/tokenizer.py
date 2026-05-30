"""
Tokenizer with optional Korean morphological analyzer.

기본은 whitespace + lowercase 폴백.
COOKBOOK_TOKENIZER=kiwi 로 설정하면 kiwipiepy 형태소 분석기 사용 (선택 의존성).
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable

_TOKEN_RE = re.compile(r"[a-zA-Z0-9가-힣]+")


def _fallback_tokenize(s: str) -> list[str]:
    return _TOKEN_RE.findall(s.lower())


def _kiwi_tokenize_factory() -> Callable[[str], list[str]] | None:
    try:
        from kiwipiepy import Kiwi  # type: ignore[import-not-found]
    except ImportError:
        return None

    kiwi = Kiwi()
    # 명사/동사/형용사/외래어/일반 위주만 유지
    keep_tags = {"N", "V", "M", "S", "L"}

    def tokenize(s: str) -> list[str]:
        return [
            t.form.lower()
            for t in kiwi.tokenize(s)
            if t.tag and t.tag[0] in keep_tags
        ]

    return tokenize


def get_tokenizer() -> Callable[[str], list[str]]:
    """환경변수에 따라 토크나이저 선택. 매 호출마다 새로 만들지 않게 lru_cache 처리."""
    return _CACHED


def _build() -> Callable[[str], list[str]]:
    mode = os.getenv("COOKBOOK_TOKENIZER", "fallback").lower()
    if mode == "kiwi":
        kiwi = _kiwi_tokenize_factory()
        if kiwi is not None:
            return kiwi
    return _fallback_tokenize


_CACHED = _build()
