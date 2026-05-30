"""
Merge auto-discovered skeleton with static override (설계서 §4.2).

override 의 비어있지 않은 필드만 골격에 덮어쓰고,
list 형 필드(tags/examples/chain_with/...)는 합집합을 취한다.
"""
from __future__ import annotations

from .schema import Recipe

_LIST_UNION_FIELDS = (
    "tags",
    "trigger_patterns",
    "related_ids",
    "examples",
    "chain_with",
)
_LIST_OVERRIDE_FIELDS = ("steps", "params")
_OPTIONAL_FIELDS = (
    "summary",
    "body",
    "title",
    "prerequisites",
    "when_to_use",
    "tool_name",
    "output_format",
    "dom",
)


def _union_preserve_order(a: list, b: list) -> list:
    seen: set = set()
    out: list = []
    for x in [*a, *b]:
        key = x if isinstance(x, (str, int, float, bool, tuple)) else id(x)
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def merge(skeleton: Recipe, override: Recipe) -> Recipe:
    """skeleton 위에 override 의 비어있지 않은 필드를 얹는다."""
    base = skeleton.model_dump()
    over = override.model_dump()

    # 옵셔널/스칼라: override 가 비어있지 않으면 대체
    for field in _OPTIONAL_FIELDS:
        v = over.get(field)
        if isinstance(v, str) and v.strip():
            base[field] = v
        elif v not in (None, [], "", 0):
            base[field] = v

    # 리스트(합집합)
    for field in _LIST_UNION_FIELDS:
        base[field] = _union_preserve_order(base.get(field) or [], over.get(field) or [])

    # 리스트(override 가 있으면 통째로 대체)
    for field in _LIST_OVERRIDE_FIELDS:
        if over.get(field):
            base[field] = over[field]

    # id/kind 는 항상 skeleton 의 것을 유지 (계약상 변경 금지)
    base["id"] = skeleton.id
    base["kind"] = skeleton.kind

    return Recipe(**base)
