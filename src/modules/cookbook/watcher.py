"""
Hot reload (설계서 §4.2).

기본: watchdog (inotify on Linux). 변경 감지 후 1초 debounce 로 reload 콜백 호출.
폴백: ``COOKBOOK_WATCH_MODE=poll`` 환경변수일 때 5초 mtime polling.
"""
from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger("cookbook")


class _Stoppable:
    """start/stop 가능한 watcher 의 공통 인터페이스."""

    def stop(self) -> None:  # pragma: no cover - default noop
        pass


class _PollingWatcher(_Stoppable):
    def __init__(self, root: Path, on_change: Callable[[], None], interval: float = 5.0):
        self._root = root
        self._on_change = on_change
        self._interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="cookbook-poll", daemon=True)
        self._last_sig: tuple = ()

    def start(self) -> None:
        self._last_sig = self._signature()
        self._thread.start()
        logger.info("[cookbook.watcher] polling started: root=%s interval=%.1fs",
                    self._root, self._interval)

    def stop(self) -> None:
        self._stop.set()

    def _signature(self) -> tuple:
        if not self._root.exists():
            return ()
        try:
            return tuple(sorted(
                (str(p), p.stat().st_mtime_ns, p.stat().st_size)
                for p in self._root.rglob("*.md") if p.is_file()
            ))
        except OSError:
            return ()

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            sig = self._signature()
            if sig != self._last_sig:
                self._last_sig = sig
                try:
                    self._on_change()
                except Exception as e:  # noqa: BLE001
                    logger.warning("[cookbook.watcher] reload callback failed: %s", e)


def _build_inotify_watcher(root: Path, on_change: Callable[[], None]) -> _Stoppable | None:
    try:
        from watchdog.events import FileSystemEventHandler  # type: ignore[import-not-found]
        from watchdog.observers import Observer  # type: ignore[import-not-found]
    except ImportError:
        return None

    debounce_lock = threading.Lock()
    pending = {"t": None}  # type: ignore[var-annotated]

    def _trigger() -> None:
        try:
            on_change()
        except Exception as e:  # noqa: BLE001
            logger.warning("[cookbook.watcher] reload callback failed: %s", e)

    def _schedule() -> None:
        with debounce_lock:
            t = pending.get("t")
            if t is not None:
                t.cancel()
            timer = threading.Timer(1.0, _trigger)
            timer.daemon = True
            pending["t"] = timer
            timer.start()

    class _Handler(FileSystemEventHandler):
        def on_any_event(self, event):  # noqa: D401, ANN001
            if getattr(event, "is_directory", False):
                return
            src = getattr(event, "src_path", "") or ""
            if src.endswith(".md"):
                _schedule()

    observer = Observer()
    observer.schedule(_Handler(), str(root), recursive=True)

    class _ObserverHandle(_Stoppable):
        def __init__(self) -> None:
            self._obs = observer

        def start(self) -> None:
            self._obs.start()
            logger.info("[cookbook.watcher] inotify started: root=%s", root)

        def stop(self) -> None:
            self._obs.stop()
            self._obs.join(timeout=2.0)

    return _ObserverHandle()


def start_watcher(root: Path, on_change: Callable[[], None]) -> _Stoppable:
    """root 디렉토리 변경 감시 시작. 핸들을 리턴 (.stop() 으로 종료)."""
    mode = os.getenv("COOKBOOK_WATCH_MODE", "auto").lower()
    if mode != "poll":
        handle = _build_inotify_watcher(root, on_change)
        if handle is not None:
            handle.start()  # type: ignore[attr-defined]
            return handle
        logger.info("[cookbook.watcher] watchdog unavailable, falling back to polling")
    poll = _PollingWatcher(root, on_change)
    poll.start()
    return poll
