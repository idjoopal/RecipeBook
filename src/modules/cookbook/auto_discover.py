"""
Auto-discover tool manuals from registered FastMCP tools.

부팅 시 같은 MCP 서버에 등록된 도구들을 introspection 으로 수집해
``tool_manual`` 골격 Recipe 를 생성한다 (설계서 §4.2).
"""
from __future__ import annotations

from typing import Any

from src.utils.logger import get_logger

from .schema import Param, Recipe

logger = get_logger("cookbook")

# cookbook 자체 도구는 자기 자신을 manual 로 만들지 않음 (cookbook_search/get).
# (직접 manual 을 작성한 경우 static merge 단계에서 골격을 대체함)
_COOKBOOK_TOOL_NAMES = {"cookbook_search", "cookbook_get"}


def _summary_from_description(description: str | None) -> str:
    if not description:
        return ""
    first = description.strip().splitlines()[0] if description.strip() else ""
    return first.strip()


def _params_from_input_schema(input_schema: Any) -> list[Param]:
    if not isinstance(input_schema, dict):
        return []
    props = input_schema.get("properties") or {}
    required = set(input_schema.get("required") or [])
    out: list[Param] = []
    for name, spec in props.items():
        if not isinstance(spec, dict):
            continue
        semantics = spec.get("description") or spec.get("title") or ""
        type_str = spec.get("type") or ""
        req_str = "required" if name in required else "optional"
        valid_range = type_str + (f", {req_str}" if type_str else req_str)
        out.append(Param(name=name, semantics=str(semantics), valid_range=valid_range))
    return out


async def _list_tools(mcp: Any) -> list[Any]:
    """FastMCP 2.14 의 ``list_tools()`` 로 등록된 도구를 조회."""
    list_tools = getattr(mcp, "list_tools", None)
    if callable(list_tools):
        result = list_tools()
        if hasattr(result, "__await__"):
            result = await result  # type: ignore[assignment]
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return list(result.values())
    logger.warning("[cookbook.auto_discover] mcp.list_tools() not available")
    return []


async def build_skeletons(mcp: Any) -> dict[str, Recipe]:
    """등록된 MCP 도구별로 ``tool_manual`` 골격 Recipe 를 생성."""
    skeletons: dict[str, Recipe] = {}
    for tool in await _list_tools(mcp):
        name = getattr(tool, "name", None) or getattr(tool, "key", None)
        if not name or name in _COOKBOOK_TOOL_NAMES:
            continue
        description = getattr(tool, "description", "") or ""
        # FastMCP 2.14: FunctionTool.parameters 는 JSON Schema dict
        input_schema = (
            getattr(tool, "parameters", None)
            or getattr(tool, "input_schema", None)
            or getattr(tool, "inputSchema", None)
            or {}
        )
        recipe = Recipe(
            id=f"tool_manual.{name}",
            kind="tool_manual",
            title=f"{name} — MCP tool manual (auto)",
            tags=[name, "tool_manual", "auto"],
            summary=_summary_from_description(description),
            body=description,
            tool_name=name,
            params=_params_from_input_schema(input_schema),
        )
        skeletons[recipe.id] = recipe
    logger.info("[cookbook.auto_discover] skeletons built: count=%d", len(skeletons))
    return skeletons
