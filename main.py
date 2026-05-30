"""
Prebuilt MCP Server

아키텍처:
1. main.py   - FastAPI + FastMCP 서버. Agent를 MCP Tool로 등록하는 유일한 진입점
2. agents/   - Modules를 불러오고 input/output 변환만 수행 (한 도메인이 여러 역할이면
              역할별 agent로 분리. MCP 텍스트 대화에 부적합한 역할은 REST 전용으로 두고
              @mcp.tool 등록을 생략한다 — 예: ppt_template_generator=REST 전용, ppt_report_generator=MCP+REST)
3. modules/  - 비즈니스 로직. modules/ 직속은 "하나의 MCP 역할 도메인" 단위로 묶고
              복잡한 도메인은 그 안에서 sub-module로 분할한다 (예: modules/ppt/<sub>)
4. utils/    - LLM/DB 연결, 설정 로드, 로깅 — 공통 인프라

엔드포인트:
  /mcp           → FastMCP Streamable HTTP (MCP 클라이언트 연결)
  /health/live   → Liveness probe
  /health/ready  → Readiness probe (등록된 의존성 체크)
  /docs          → Swagger UI
  /ui            → 프론트엔드 (빌드 후 제공)
  /api/admin/*   → 환경변수 관리 + 서버 재기동
"""
import os
from contextlib import asynccontextmanager
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastmcp import FastMCP

from src.health import LivenessResponse, ReadinessResponse, run_checks
from src.routers.my_agent import router as my_agent_router
from src.routers.admin import router as admin_router
from src.routers.cookbook import router as cookbook_router
from src.utils.config_loader import get_env, get_env_int, load_agent_env, load_root_env
from src.utils.logger import get_logger

# =============================================================================
# 환경변수 로드
# =============================================================================
load_root_env()

# 에이전트별 실시간 로그용: root logger에 인메모리 캡처 핸들러 부착(/api/admin/logs*)
from src.utils.log_stream import install_log_capture
install_log_capture()

logger = get_logger("mcp-server")

# =============================================================================
# FastMCP 인스턴스
# =============================================================================
mcp = FastMCP("Prebuilt MCP Server")
mcp_app = mcp.http_app(path="/")


# =============================================================================
# Cleanup 훅
# =============================================================================
_cleanup_fns: list[Callable[[], Awaitable[None]]] = []


def register_cleanup(fn: Callable[[], Awaitable[None]]) -> None:
    """서버 종료 시 실행할 cleanup 함수를 등록합니다."""
    _cleanup_fns.append(fn)


# =============================================================================
# Lifespan
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Prebuilt MCP Server Starting ===")
    async with mcp_app.lifespan(app):
        # cookbook MCP: 모든 @mcp.tool 등록 완료 후 자율호출 3-Layer 와이어링
        # (설계서 §7: L1 카탈로그 / L2 referral / L3 chain_with)
        import asyncio as _asyncio

        from src.agents.cookbook_agent import build_search_description
        from src.modules.cookbook import service as cookbook_service
        from src.modules.cookbook.referral import annotate_tools

        # cookbook 전용 env 로드 (COOKBOOK_CONTENT_DIR / TOKENIZER / WATCH_MODE)
        load_agent_env("cookbook")
        content_root = Path(__file__).parent / get_env("COOKBOOK_CONTENT_DIR", "cookbook")
        await cookbook_service.init(mcp, content_root=content_root)

        async def _apply_l1_l2_async() -> None:
            # L1: cookbook_search.description 끝에 카탈로그 동적 주입
            tool = await mcp.get_tool("cookbook_search")
            tool.description = build_search_description()
            # L2: 동료 도구 description 끝에 D/O/M referral 부착
            await annotate_tools(mcp, cookbook_service.recipes_by_tool())

        await _apply_l1_l2_async()

        # reload 콜백은 동기 컨텍스트에서 호출되므로 새 이벤트 루프로 감싼다.
        def _apply_l1_l2_sync() -> None:
            try:
                _asyncio.run(_apply_l1_l2_async())
            except RuntimeError:
                loop = _asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_apply_l1_l2_async())
                finally:
                    loop.close()

        cookbook_service.register_on_reload(_apply_l1_l2_sync)

        # 종료 시 watcher 정리
        register_cleanup(cookbook_service.cleanup)

        yield
    for fn in _cleanup_fns:
        await fn()
    logger.info("=== Prebuilt MCP Server Shutting Down ===")


# =============================================================================
# FastAPI App
# =============================================================================
_DESCRIPTION = """
FastAPI + FastMCP 기반 MCP 서버입니다.

## 엔드포인트

| 경로 | 설명 |
|------|------|
| `/mcp` | FastMCP Streamable HTTP — MCP 클라이언트 연결 |
| `/health/live` | Liveness probe — 프로세스 생존 확인 |
| `/health/ready` | Readiness probe — 등록된 의존성 체크 |
| `/docs` | Swagger UI |
| `/ui` | 프론트엔드 UI (빌드 후 제공) |
| `/api/admin/*` | 환경변수 관리 + 서버 재기동 |
"""

app = FastAPI(
    title="Prebuilt MCP Server",
    description=_DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.mount("/mcp", mcp_app)
app.include_router(my_agent_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(cookbook_router, prefix="/api")

_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_FRONTEND_DIST):
    app.mount("/ui", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")


# FastMCP의 _current_http_request ContextVar는 /mcp ASGI 진입 시에만 세팅된다.
# REST/UI 경로에서도 chart 응답 URL이 요청 호스트를 따라가도록, 모든 HTTP 요청을 감싸
# 같은 ContextVar에 set/reset 한다. FastMCP가 자체 set 한 경우엔 내부 nesting으로 안전.
from fastmcp.server.http import set_http_request as _set_http_request  # noqa: E402


@app.middleware("http")
async def _propagate_http_request(request, call_next):
    with _set_http_request(request):
        return await call_next(request)


# =============================================================================
# Monitoring
# =============================================================================
@app.get(
    "/health/live",
    response_model=LivenessResponse,
    tags=["Monitoring"],
    summary="Liveness probe",
    description="프로세스가 살아있으면 200을 반환합니다.",
)
async def health_live():
    return LivenessResponse()


@app.get(
    "/health/ready",
    response_model=ReadinessResponse,
    tags=["Monitoring"],
    summary="Readiness probe",
    description="등록된 모든 의존성 체크를 실행합니다. 하나라도 실패하면 503을 반환합니다.",
)
async def health_ready():
    result = await run_checks()
    status_code = 200 if result.status == "ok" else 503
    return JSONResponse(content=result.model_dump(), status_code=status_code)


# =============================================================================
# Tool 등록 영역
# =============================================================================
# 새 Agent는 아래 패턴으로 추가합니다.
#
# from src.agents.{name}_agent import {name}_agent, {NAME}_AGENT_DESCRIPTION
#
# @mcp.tool(name="...", description={NAME}_AGENT_DESCRIPTION)
# async def {name}_tool(input: str) -> str:
#     return await {name}_agent(input=input)
#
# ⚠ description은 각 agent 모듈에서 정의하고 여기서는 import만 합니다.
#   작성 기준: doc/agent-tool-writing-guide.md(2장) 필수 8항목
#   (Purpose / Parameters / Returns / When to USE 2+ / When NOT to use 1+ /
#    Input example / Post-call behavior / Error handling).
#   src/agents/my_agent.py의 MY_AGENT_DESCRIPTION이 가이드 준수 예시(exemplar)입니다.

# -----------------------------------------------------------------------------
# My Agent
# REST API: /api/my-agent/* (src/routers/my_agent.py)
# -----------------------------------------------------------------------------
from src.agents.my_agent import my_agent, MY_AGENT_DESCRIPTION

@mcp.tool(name="test_myagent", description=MY_AGENT_DESCRIPTION)
async def my_agent_tool(input: str) -> str:
    result = await my_agent(input=input, mode="default")
    return result["result"]


# -----------------------------------------------------------------------------
# Cookbook (설계서 doc/cookbook-design.md)
# REST API: /api/cookbook/* (src/routers/cookbook.py)
# Layer 1 카탈로그는 lifespan startup hook 에서 동적으로 주입됨.
# -----------------------------------------------------------------------------
from src.agents.cookbook_agent import (
    COOKBOOK_GET_DESCRIPTION,
    COOKBOOK_SEARCH_DESCRIPTION_STATIC,
    cookbook_get_agent,
    cookbook_search_agent,
)


@mcp.tool(name="cookbook_search", description=COOKBOOK_SEARCH_DESCRIPTION_STATIC)
async def cookbook_search_tool(
    query: str,
    kind: Optional[str] = None,
    tags: Optional[list[str]] = None,
    top_k: int = 5,
) -> list[dict]:
    return await cookbook_search_agent(query=query, kind=kind, tags=tags, top_k=top_k)


@mcp.tool(name="cookbook_get", description=COOKBOOK_GET_DESCRIPTION)
async def cookbook_get_tool(id: str) -> dict:
    return await cookbook_get_agent(id=id)


# =============================================================================
# Entrypoint
# =============================================================================
# `.env`의 SERVER_HOST / SERVER_PORT를 읽어 uvicorn으로 실행합니다.
# 사용: `uv run python main.py` (또는 `python main.py`)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=get_env("SERVER_HOST", "0.0.0.0"),
        port=get_env_int("SERVER_PORT", 9101),
        reload=get_env("APP_ENV", "dev") == "dev",
    )
