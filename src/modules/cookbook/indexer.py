"""
BM25 in-memory index (설계서 §5).

검색 알고리즘:
  1) kind / tags 필터로 후보 좁힘 (옵셔널)
  2) rank_bm25 로 (title + tags + summary + body) 토큰화 → 랭킹
  3) top_k 메타데이터만 SearchResult 로 반환
"""
from __future__ import annotations

from collections.abc import Iterable

from rank_bm25 import BM25Okapi  # type: ignore[import-not-found]

from src.utils.logger import get_logger

from .schema import Kind, Recipe, SearchResult
from .tokenizer import get_tokenizer

logger = get_logger("cookbook")


def _doc_text(r: Recipe) -> str:
    return " ".join(
        [
            r.title or "",
            " ".join(r.tags or []),
            r.summary or "",
            r.body or "",
        ]
    )


class CookbookIndex:
    """Recipe 리스트로부터 BM25 인덱스를 빌드하고 검색/조회를 제공."""

    def __init__(self) -> None:
        self._recipes: dict[str, Recipe] = {}
        self._order: list[str] = []
        self._bm25: BM25Okapi | None = None

    def rebuild(self, recipes: Iterable[Recipe]) -> None:
        tokenize = get_tokenizer()
        self._recipes = {}
        self._order = []
        tokenized: list[list[str]] = []
        for r in recipes:
            self._recipes[r.id] = r
            self._order.append(r.id)
            tokenized.append(tokenize(_doc_text(r)))
        self._bm25 = BM25Okapi(tokenized) if tokenized else None
        logger.info("[cookbook.indexer] rebuilt: docs=%d", len(self._order))

    # --------------------------------------------------------------- query

    def search(
        self,
        query: str,
        kind: Kind | None = None,
        tags: list[str] | None = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        if self._bm25 is None or not self._order:
            return []
        tokenize = get_tokenizer()
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        scores = self._bm25.get_scores(q_tokens)
        tag_set = set(tags or [])

        # 필터 후보 idx
        candidates: list[int] = []
        for i, rid in enumerate(self._order):
            r = self._recipes[rid]
            if kind is not None and r.kind != kind:
                continue
            if tag_set and not tag_set.intersection(r.tags):
                continue
            candidates.append(i)

        candidates.sort(key=lambda i: scores[i], reverse=True)
        out: list[SearchResult] = []
        for i in candidates[:top_k]:
            r = self._recipes[self._order[i]]
            out.append(
                SearchResult(
                    id=r.id,
                    kind=r.kind,
                    title=r.title,
                    summary=r.summary,
                    tags=r.tags,
                    score=float(scores[i]),
                )
            )
        return out

    # --------------------------------------------------------------- accessors

    def get(self, id_: str) -> Recipe:
        if id_ not in self._recipes:
            raise KeyError(f"recipe not found: {id_}")
        return self._recipes[id_]

    def has(self, id_: str) -> bool:
        return id_ in self._recipes

    def iter(self) -> list[Recipe]:
        return [self._recipes[i] for i in self._order]

    def by_tool(self) -> dict[str, Recipe]:
        """tool_name 으로 인덱싱한 tool_manual 매핑 (L2 referral 에 사용)."""
        out: dict[str, Recipe] = {}
        for r in self._recipes.values():
            if r.kind == "tool_manual" and r.tool_name:
                out[r.tool_name] = r
        return out
