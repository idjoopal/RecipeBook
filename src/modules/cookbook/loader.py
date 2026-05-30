"""
Content loader.

cookbook/{skills,workflows,tool_manuals}/*.md 파일을 재귀 스캔해 Recipe 로 파싱.
YAML front matter + markdown 본문 (설계서 §4.3).
"""
from __future__ import annotations

from pathlib import Path

import frontmatter

from src.utils.logger import get_logger

from .schema import Param, Recipe, Step

logger = get_logger("cookbook")


def _coerce_steps(raw: object) -> list[Step]:
    if not isinstance(raw, list):
        return []
    out: list[Step] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(Step(**{k: v for k, v in item.items() if v is not None}))
    return out


def _coerce_params(raw: object) -> list[Param]:
    if not isinstance(raw, list):
        return []
    out: list[Param] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(Param(**{k: v for k, v in item.items() if v is not None}))
    return out


def _coerce_dom(raw: object) -> list[int] | None:
    if not isinstance(raw, list) or len(raw) != 3:
        return None
    try:
        return [int(raw[0]), int(raw[1]), int(raw[2])]
    except (TypeError, ValueError):
        return None


def parse_file(path: Path) -> Recipe | None:
    """단일 .md 파일을 Recipe 로 파싱. 실패 시 None 리턴 + 경고 로그."""
    try:
        post = frontmatter.load(path)
    except Exception as e:  # noqa: BLE001
        logger.warning("[cookbook.loader] parse failed: path=%s err=%s", path, e)
        return None

    meta = post.metadata or {}
    rid = meta.get("id")
    kind = meta.get("kind")
    title = meta.get("title")
    if not rid or kind not in ("skill", "workflow", "tool_manual") or not title:
        logger.warning(
            "[cookbook.loader] missing required front matter (id/kind/title): path=%s", path
        )
        return None

    return Recipe(
        id=rid,
        kind=kind,
        title=title,
        tags=list(meta.get("tags") or []),
        summary=str(meta.get("summary") or "").strip(),
        body=post.content,
        trigger_patterns=list(meta.get("trigger_patterns") or []),
        related_ids=list(meta.get("related_ids") or []),
        # skill
        prerequisites=meta.get("prerequisites"),
        when_to_use=meta.get("when_to_use"),
        # workflow
        steps=_coerce_steps(meta.get("steps")),
        # tool_manual
        tool_name=meta.get("tool_name"),
        params=_coerce_params(meta.get("params")),
        examples=list(meta.get("examples") or []),
        output_format=meta.get("output_format"),
        chain_with=list(meta.get("chain_with") or []),
        # referral
        dom=_coerce_dom(meta.get("dom")),
    )


def load_dir(root: Path) -> list[Recipe]:
    """root 디렉토리 (cookbook/) 의 *.md 파일을 모두 파싱."""
    if not root.exists():
        logger.info("[cookbook.loader] content root not found: %s", root)
        return []
    recipes: list[Recipe] = []
    for path in sorted(root.rglob("*.md")):
        recipe = parse_file(path)
        if recipe is not None:
            recipes.append(recipe)
    logger.info("[cookbook.loader] loaded recipes: count=%d root=%s", len(recipes), root)
    return recipes
