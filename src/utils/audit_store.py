"""Append-only 감사 이벤트 저장소 (§9.3).

Phase 1~3: SQLite (aiosqlite).
Phase 4: PostgreSQL 옵션 추가 예정 (backend 추상화 준비).
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import aiosqlite

from src.utils.logger import get_logger

logger = get_logger("audit_store")


class AuditStore:
    """SQLite 기반 append-only 감사 로그 저장소."""

    def __init__(self, db_path: str = ".sql_explorer/audit.db"):
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(str(path))
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id    TEXT PRIMARY KEY,
                query_id    TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                stage       TEXT NOT NULL,
                inputs      TEXT NOT NULL,
                outputs     TEXT NOT NULL,
                duration_ms REAL,
                tokens_used INTEGER,
                cost_usd    REAL,
                parent_event TEXT
            )
        """)
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_query_id ON audit_events(query_id)"
        )
        await self._db.commit()
        logger.info("[AuditStore] SQLite 연결 완료: %s", self._db_path)

    async def disconnect(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def connected(self) -> bool:
        return self._db is not None

    async def append(self, event: Any) -> None:
        """AuditEvent를 저장한다 (append-only)."""
        if not self._db:
            raise RuntimeError("AuditStore에 연결되어 있지 않습니다.")

        await self._db.execute(
            """
            INSERT OR IGNORE INTO audit_events
              (event_id, query_id, timestamp, stage, inputs, outputs,
               duration_ms, tokens_used, cost_usd, parent_event)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event.event_id),
                str(event.query_id),
                event.timestamp.isoformat(),
                event.stage,
                json.dumps(event.inputs, ensure_ascii=False, default=str),
                json.dumps(event.outputs, ensure_ascii=False, default=str),
                event.duration_ms,
                event.tokens_used,
                event.cost_usd,
                str(event.parent_event) if event.parent_event else None,
            ),
        )
        await self._db.commit()

    async def get_by_query(self, query_id: str) -> list[dict]:
        """특정 query_id의 모든 이벤트를 시간순으로 반환한다."""
        if not self._db:
            raise RuntimeError("AuditStore에 연결되어 있지 않습니다.")

        cursor = await self._db.execute(
            "SELECT * FROM audit_events WHERE query_id = ? ORDER BY timestamp ASC",
            (query_id,),
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in rows]

    async def health(self) -> dict:
        """연결 상태를 반환한다."""
        if not self._db:
            return {"status": "error", "message": "연결되지 않음"}
        try:
            await self._db.execute("SELECT 1")
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
