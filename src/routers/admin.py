"""
Admin Router - 환경변수 관리 + 서버 재기동
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.utils.log_stream import read_logs

router = APIRouter(prefix="/admin", tags=["Admin"])


def _parse_prefixes(prefixes: str | None) -> list[str]:
    if not prefixes:
        return []
    return [p.strip() for p in prefixes.split(",") if p.strip()]

_ROOT_DIR = Path(__file__).parent.parent.parent
_AGENT_ENV_DIR = Path(__file__).parent.parent / "agents" / "agent_env"

_SENSITIVE_KEYWORDS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "PASSWD", "CREDENTIAL")


def _is_sensitive(key: str) -> bool:
    k = key.upper()
    return any(kw in k for kw in _SENSITIVE_KEYWORDS)


def _parse_env_file(path: Path) -> dict[str, str]:
    if path.exists():
        return {k: v for k, v in dotenv_values(path).items() if v is not None}
    example = path.with_suffix(path.suffix + ".example")
    if example.exists():
        return {k: v for k, v in dotenv_values(example).items() if v is not None}
    return {}


def _write_env_file(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for k, v in data.items():
        if "\n" in v or " " in v or "=" in v or "#" in v or '"' in v:
            v_escaped = v.replace('"', '\\"')
            lines.append(f'{k}="{v_escaped}"')
        else:
            lines.append(f"{k}={v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _list_env_files() -> list[dict[str, Any]]:
    files = []

    root_env = _ROOT_DIR / ".env"
    files.append({
        "id": "root",
        "label": "Root .env",
        "path": str(root_env),
        "exists": root_env.exists(),
        "entries": [
            {"key": k, "value": v, "sensitive": _is_sensitive(k)}
            for k, v in _parse_env_file(root_env).items()
        ],
    })

    if _AGENT_ENV_DIR.exists():
        for example in sorted(_AGENT_ENV_DIR.glob("*.env.example")):
            agent_name = example.name.replace(".env.example", "")
            actual = _AGENT_ENV_DIR / f"{agent_name}.env"
            files.append({
                "id": f"agent_{agent_name}",
                "label": f"{agent_name}.env",
                "path": str(actual),
                "exists": actual.exists(),
                "entries": [
                    {"key": k, "value": v, "sensitive": _is_sensitive(k)}
                    for k, v in _parse_env_file(actual).items()
                ],
            })

    return files


@router.get("/env")
async def get_env_files():
    return {"files": _list_env_files()}


class EnvSaveRequest(BaseModel):
    file_id: str
    entries: list[dict[str, str]]  # [{key, value}, ...]


@router.put("/env")
async def save_env_file(body: EnvSaveRequest):
    files = _list_env_files()
    target = next((f for f in files if f["id"] == body.file_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Unknown env file id: {body.file_id}")

    data = {e["key"]: e["value"] for e in body.entries if e.get("key")}
    _write_env_file(Path(target["path"]), data)
    return {"status": "saved", "file_id": body.file_id}


@router.post("/restart")
async def restart_server():
    async def _do_restart():
        await asyncio.sleep(0.6)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    asyncio.create_task(_do_restart())
    return {"status": "restarting"}


# =============================================================================
# 로그 — 에이전트별 실시간 로그 (logger 이름 prefix 필터)
# =============================================================================
@router.get("/logs")
async def get_logs(prefixes: str | None = None, after: int = 0, limit: int = 300):
    """최근 로그를 prefix 필터로 조회. prefixes=쉼표구분 (예: 'sql_explorer,nl2sql')."""
    return read_logs(_parse_prefixes(prefixes), after_seq=after, limit=limit)


@router.get("/logs/stream")
async def stream_logs(prefixes: str | None = None, after: int = 0):
    """로그 실시간 스트리밍 (SSE). 버퍼를 ~1s 폴링해 새 라인만 전송."""
    pfx = _parse_prefixes(prefixes)

    async def _sse():
        last = after
        # 초기 백필(최근 200) — 연결 직후 현재 맥락 제공
        init = read_logs(pfx, after_seq=last, limit=200)
        for e in init["entries"]:
            yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
        last = init["last_seq"]
        idle = 0
        while True:
            await asyncio.sleep(1.0)
            res = read_logs(pfx, after_seq=last, limit=500)
            entries = res["entries"]
            if entries:
                for e in entries:
                    yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
                last = res["last_seq"]
                idle = 0
            else:
                idle += 1
                if idle >= 15:  # ~15s마다 keepalive
                    idle = 0
                    yield ": keepalive\n\n"

    return StreamingResponse(
        _sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
