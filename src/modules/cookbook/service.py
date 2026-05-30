"""
Cookbook service — 외부 진입점.

설계서 §1~§7 의 모든 책임을 모은 facade.

- ``init(mcp, content_root)`` : 부팅 시 1회. auto-discover + static merge + BM25 build + watcher 시작.
- ``search/get`` : MCP tool 및 REST API 에서 호출되는 검색/조회.
- ``catalog_text()`` : Layer 1 카탈로그 텍스트 (cookbook_search.description 에 주입).
- ``recipes_by_tool()`` : Layer 2 referral 부착에 사용.
- ``reload()`` : watcher 또는 admin 트리거. 인덱스 재빌드 + 콜백 호출.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

from . import auto_discover, loader
from .catalog import build_catalog_text
from .indexer import CookbookIndex
from .merge import merge
from .schema import Kind, Recipe, SearchResult
from .watcher import start_watcher, _Stoppable

logger = get_logger("cookbook")

# 모듈 레벨 싱글톤 (FastAPI lifespan 에서 1회 init).
_index = CookbookIndex()
_lock = threading.RLock()
_state: dict[str, Any] = {
    "mcp": None,
    "content_root": None,
    "skeletons": {},          # auto_discover 캐시 (재사용)
    "watcher": None,          # _Stoppable
    "on_reload": [],          # list[Callable[[], None]]
    "initialized": False,
}


# ---------------------------------------------------------------- internal


async def _rebuild_index() -> None:
    content_root: Path = _state["content_root"]
    skeletons: dict[str, Recipe] = _state["skeletons"]
    statics = {r.id: r for r in loader.load_dir(content_root)}

    recipes: dict[str, Recipe] = {}
    # 1) skeleton 위에 static override 머지
    for sid, sk in skeletons.items():
        ov = statics.get(sid)
        recipes[sid] = merge(sk, ov) if ov is not None else sk
    # 2) skeleton 에 없는 static (skill / workflow / 신규 tool_manual) 추가
    for sid, r in statics.items():
        if sid not in recipes:
            recipes[sid] = r

    _index.rebuild(recipes.values())


def _run_on_reload_callbacks() -> None:
    for cb in list(_state["on_reload"]):
        try:
            cb()
        except Exception as e:  # noqa: BLE001
            logger.warning("[cookbook.service] on_reload callback failed: %s", e)


def _reload_sync_blocking() -> None:
    """watcher 가 콜하는 동기 진입점. async 인덱싱은 새 이벤트루프 없이 처리."""
    import asyncio
    with _lock:
        # auto_discover 결과는 mcp 도구 자체가 바뀌지 않는 한 재사용
        # (런타임에 도구가 추가/삭제되지 않는다는 가정)
        try:
            asyncio.run(_rebuild_index())
        except RuntimeError:
            # 이미 이벤트 루프가 있는 경우 — 새 스레드에서 실행
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_rebuild_index())
            finally:
                loop.close()
        _run_on_reload_callbacks()
        logger.info("[cookbook.service] reloaded")


# ---------------------------------------------------------------- public


async def init(mcp: Any, content_root: Path) -> None:
    """부팅 시 1회 호출. 모든 @mcp.tool 등록이 완료된 lifespan startup 시점."""
    with _lock:
        _state["mcp"] = mcp
        _state["content_root"] = content_root
        _state["skeletons"] = await auto_discover.build_skeletons(mcp)
        await _rebuild_index()

        # watcher 시작
        if _state["watcher"] is None and content_root.exists():
            _state["watcher"] = start_watcher(content_root, _reload_sync_blocking)
        _state["initialized"] = True
        logger.info(
            "[cookbook.service] init done: docs=%d content_root=%s",
            len(_index.iter()), content_root,
        )


def register_on_reload(cb: Callable[[], None]) -> None:
    """reload 직후 실행할 콜백 등록. L1/L2 갱신용."""
    _state["on_reload"].append(cb)


async def search(
    query: str,
    kind: Kind | None = None,
    tags: list[str] | None = None,
    top_k: int = 5,
) -> list[SearchResult]:
    return _index.search(query=query, kind=kind, tags=tags, top_k=top_k)


async def get(id_: str) -> Recipe:
    return _index.get(id_)


def is_initialized() -> bool:
    return bool(_state["initialized"])


def catalog_text() -> str:
    return build_catalog_text(_index.iter())


def recipes_by_tool() -> dict[str, Recipe]:
    return _index.by_tool()


def iter_recipes() -> list[Recipe]:
    return _index.iter()


async def cleanup() -> None:
    """서버 종료 시 호출 (register_cleanup 으로 등록)."""
    watcher: _Stoppable | None = _state.get("watcher")
    if watcher is not None:
        try:
            watcher.stop()
        except Exception as e:  # noqa: BLE001
            logger.warning("[cookbook.service] watcher stop failed: %s", e)
        _state["watcher"] = None
    logger.info("[cookbook.service] cleanup done")
