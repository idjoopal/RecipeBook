"""
Layer 1 catalog text builder.

설계서 §9.2 — cookbook_search 의 description 끝에 부착될 카탈로그 텍스트.
부팅 시 + reload 시 새로 생성된다. 1500 token 예산을 넘지 않도록 잘라낸다.
"""
from __future__ import annotations

from collections.abc import Iterable

from .schema import Kind, Recipe

# kind 출력 순서
_KIND_ORDER: tuple[Kind, ...] = ("skill", "workflow", "tool_manual")
_KIND_LABEL: dict[Kind, str] = {
    "skill": "skill",
    "workflow": "workflow",
    "tool_manual": "tool_manual",
}

# 항목 1줄당 약 30 token 가정 → 50개로 제한해 1500 token 이내 유지.
_MAX_ITEMS_DEFAULT = 50


def build_catalog_text(
    recipes: Iterable[Recipe],
    max_items: int = _MAX_ITEMS_DEFAULT,
) -> str:
    """카탈로그 섹션 텍스트를 반환. recipe 가 없으면 빈 문자열."""
    by_kind: dict[Kind, list[Recipe]] = {k: [] for k in _KIND_ORDER}
    for r in recipes:
        if r.kind in by_kind:
            by_kind[r.kind].append(r)
    total = sum(len(v) for v in by_kind.values())
    if total == 0:
        return ""

    lines: list[str] = ["== Available recipes =="]
    shown = 0
    for kind in _KIND_ORDER:
        items = by_kind[kind]
        if not items:
            continue
        lines.append("")
        lines.append(f"[{_KIND_LABEL[kind]}]")
        # title 기준 정렬 (안정적 표시)
        for r in sorted(items, key=lambda x: x.id):
            if shown >= max_items:
                break
            summary = r.summary.splitlines()[0] if r.summary else r.title
            lines.append(f"  {r.id} — {summary}")
            shown += 1
        if shown >= max_items:
            break

    remaining = total - shown
    if remaining > 0:
        lines.append("")
        lines.append(f"... and {remaining} more. Use cookbook_search(query=...) to find them.")

    return "\n".join(lines)
