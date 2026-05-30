"""인메모리 로그 캡처 + 조회.

root logger에 핸들러 하나를 붙여 모든 named logger의 레코드를 링버퍼에 모은다
(named logger는 propagate=True라 root로 전파됨). REST/SSE 엔드포인트가 logger 이름
prefix로 필터해 에이전트별 실시간 로그를 노출한다.

cross-thread asyncio 큐 문제를 피하려 push가 아닌 "버퍼 + seq 폴링" 방식을 쓴다.
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime
from typing import Any

# 전역 링버퍼 (최근 N개). 각 항목: {seq, ts, level, name, message}
_MAXLEN = 3000
_buffer: deque[dict[str, Any]] = deque(maxlen=_MAXLEN)
_lock = threading.Lock()
_seq = 0
_installed = False


class LogBufferHandler(logging.Handler):
    """로그 레코드를 링버퍼에 적재하는 핸들러 (원문 메시지 보존)."""

    def emit(self, record: logging.LogRecord) -> None:
        global _seq
        try:
            message = record.getMessage()
        except Exception:
            message = str(getattr(record, "msg", ""))
        with _lock:
            _seq += 1
            _buffer.append({
                "seq": _seq,
                "ts": datetime.now().isoformat(timespec="milliseconds"),
                "level": record.levelname,
                "name": record.name,
                "message": message,
            })


def install_log_capture(level: int = logging.INFO) -> None:
    """root logger에 캡처 핸들러를 1회만 부착한다.

    root level은 변경하지 않는다 — 명시적으로 INFO인 에이전트 logger의 레코드만
    전파되어 잡히고, 레벨 미설정 서드파티 logger의 verbose는 차단된다.
    """
    global _installed
    if _installed:
        return
    handler = LogBufferHandler()
    handler.setLevel(level)
    logging.getLogger().addHandler(handler)  # root
    _installed = True


def _matches(name: str, prefixes: list[str]) -> bool:
    if not prefixes:
        return True
    return any(name.startswith(p) for p in prefixes)


def read_logs(prefixes: list[str] | None = None, after_seq: int = 0, limit: int = 300) -> dict[str, Any]:
    """seq>after_seq 이고 name이 prefixes 중 하나로 시작하는 로그를 최신순 limit개 반환.

    Returns: {"entries": [...오름차순...], "last_seq": <버퍼 최신 seq>}
    """
    prefixes = prefixes or []
    with _lock:
        snapshot = list(_buffer)
    matched = [e for e in snapshot if e["seq"] > after_seq and _matches(e["name"], prefixes)]
    # 최신 limit개만 유지하되 표시 순서는 오름차순(시간순)
    if limit and len(matched) > limit:
        matched = matched[-limit:]
    last_seq = snapshot[-1]["seq"] if snapshot else after_seq
    return {"entries": matched, "last_seq": last_seq}
