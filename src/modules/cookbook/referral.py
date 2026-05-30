"""
Layer 2 referral phrase + tool description annotator (설계서 §7, §8).

각 도구의 tool_manual 에 명시된 ``dom`` (D, O, M) 합산값에 따라
description 말미에 cookbook_get 참조 문구를 자동 부착한다.

| D+O+M | 강도 | 문구 |
|-------|-----|------|
| 0~2   | 없음 | 부착 안 함 |
| 3~4   | recommended | "For detailed usage, see cookbook_get('tool_manual.X')" |
| 5~9   | MUST | "You MUST consult cookbook_get('tool_manual.X') before calling this tool" |
"""
from __future__ import annotations

from typing import Any

from src.utils.logger import get_logger

from .schema import Recipe

logger = get_logger("cookbook")

_MARKER = "\n\n<!-- cookbook-referral -->\n"


def referral_phrase(tool_name: str, dom: list[int] | None) -> str:
    """D/O/M 합산에 따라 referral 문구 반환. dom 미지정 시 빈 문자열."""
    if not dom or len(dom) != 3:
        return ""
    s = sum(int(x) for x in dom)
    body = ""
    if s <= 2:
        return ""
    if s <= 4:
        body = (
            f"For detailed usage, see cookbook_get(id='tool_manual.{tool_name}')."
        )
    else:
        body = (
            f"You MUST consult cookbook_get(id='tool_manual.{tool_name}') "
            "before calling this tool."
        )
    return _MARKER + body


def _strip_previous_referral(description: str) -> str:
    """기존에 부착한 referral 섹션을 제거 (재실행/reload 대비)."""
    if not description:
        return ""
    idx = description.find(_MARKER)
    if idx == -1:
        return description
    return description[:idx]


async def _list_tools(mcp: Any) -> list[Any]:
    list_tools = getattr(mcp, "list_tools", None)
    if callable(list_tools):
        result = list_tools()
        if hasattr(result, "__await__"):
            result = await result  # type: ignore[assignment]
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return list(result.values())
    return []


async def annotate_tools(mcp: Any, recipes_by_tool: dict[str, Recipe]) -> int:
    """등록된 도구에 D/O/M referral 문구를 부착. 부착된 도구 수 반환."""
    count = 0
    for tool in await _list_tools(mcp):
        name = getattr(tool, "name", None) or getattr(tool, "key", None)
        if not name:
            continue
        recipe = recipes_by_tool.get(name)
        if recipe is None:
            continue
        phrase = referral_phrase(name, recipe.dom)
        if not phrase:
            continue
        current = getattr(tool, "description", "") or ""
        base = _strip_previous_referral(current)
        try:
            tool.description = base + phrase
            count += 1
        except (AttributeError, TypeError) as e:
            logger.warning(
                "[cookbook.referral] failed to set description: tool=%s err=%s", name, e
            )
    logger.info("[cookbook.referral] annotated tools: count=%d", count)
    return count
