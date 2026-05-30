# Prebuilt MCP - 개발자 사용 가이드

> 이 가이드를 참고해 새로운 Agent / Module을 동일한 패턴으로 추가하세요.

---

## 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [레이어별 역할과 규칙](#2-레이어별-역할과-규칙)
3. [환경변수 설정 구조](#3-환경변수-설정-구조)
4. [공통 유틸리티](#4-공통-유틸리티)
5. [새 Agent / Module 추가하기](#5-새-agent--module-추가하기)
6. [서버 실행](#6-서버-실행)
7. [프론트엔드 (UI)](#7-프론트엔드-ui)

> **Tool Description / System Prompt 작성 기준:** [`doc/agent-tool-writing-guide.md`](doc/agent-tool-writing-guide.md) — 새 Agent/Tool 추가 시 description 작성 필독.

---

## 1. 아키텍처 개요

```
[MCP Client]      [REST Client]      [Browser → /ui]
     │                 │                    │
     ▼                 ▼                    ▼
[main.py]  ← FastAPI + FastMCP 서버. MCP Tool 등록 + REST 라우터 마운트 + 프론트엔드 정적 서빙
     │       /mcp → FastMCP  |  /api/* → FastAPI Routers  |  /ui → frontend/dist  |  /health, /docs
     │
     ├──▶ [routers/]   ← Agent의 REST API 엔드포인트 (APIRouter)
     │
     ├──▶ [frontend/]  ← Vite + React UI (빌드 산출물을 /ui로 서빙). 자세한 내용은 frontend/README.md
     │
     ▼
[agents/]  ← 역할(role) 단위. Module을 조합하고 I/O를 변환. MCP + REST 양쪽 진입점
            (MCP 부적합 역할은 REST 전용 — @mcp.tool 미등록)
     │
     ▼
[modules/] ← 비즈니스 로직. 직속은 "하나의 MCP 역할 도메인" 단위(예: modules/ppt/),
            복잡한 도메인은 그 안에서 sub-module로 분할
     │
     ▼
[utils/]   ← LLM/DB 연결, 설정 로드, 로깅, Health Check — 공통 인프라
```

### 레이어 간 의존 방향

```
main.py  →  routers  →  agents  →  modules  →  utils
```

- 역방향 의존 금지: `modules`는 `agents`를 모르고, `utils`는 `modules`를 모릅니다.
- `agents`끼리 서로를 직접 호출하지 않습니다.
- `modules`끼리 서로를 직접 호출하지 않습니다. 조합은 `agents`에서 수행합니다.
- `routers`는 `agents`만 호출합니다. `modules`를 직접 호출하지 않습니다.

---

## 2. 레이어별 역할과 규칙

### 2-1. `main.py` — 서버 진입점 + MCP Tool 등록

**역할:** FastAPI + FastMCP 서버를 구성하고, Agent를 MCP Tool로 등록하며, REST 라우터를 마운트합니다.

```python
from contextlib import asynccontextmanager
from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastmcp import FastMCP

from src.health import LivenessResponse, ReadinessResponse, run_checks
from src.routers.my_agent import router as my_agent_router
from src.utils.config_loader import load_root_env

load_root_env()

mcp = FastMCP("Prebuilt MCP Server")
mcp_app = mcp.http_app(path="/")

# 서버 종료 시 실행할 cleanup 훅
_cleanup_fns: list[Callable[[], Awaitable[None]]] = []

def register_cleanup(fn: Callable[[], Awaitable[None]]) -> None:
    _cleanup_fns.append(fn)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.lifespan(app):
        yield
    for fn in _cleanup_fns:
        await fn()

app = FastAPI(lifespan=lifespan)
app.mount("/mcp", mcp_app)
app.include_router(my_agent_router, prefix="/api")   # REST 라우터 등록

# Health Probe (서버 공통 엔드포인트는 main.py에 직접 정의)
@app.get("/health/live", response_model=LivenessResponse, tags=["Monitoring"])
async def health_live():
    return LivenessResponse()

@app.get("/health/ready", response_model=ReadinessResponse, tags=["Monitoring"])
async def health_ready():
    result = await run_checks()
    return JSONResponse(content=result.model_dump(), status_code=200 if result.status == "ok" else 503)

# MCP Tool 등록
from src.agents.my_agent import my_agent

@mcp.tool(name="test_myagent", description="...")
async def my_agent_tool(input: str) -> str:
    result = await my_agent(input=input, mode="default")
    return result["result"]
```

**규칙:**
- MCP Tool로 등록하는 대상은 **Agent**입니다. Module을 직접 등록하지 않습니다.
- Tool 함수 본체는 **Agent 호출 + 결과 변환**만 합니다. 비즈니스 로직을 두지 않습니다.
- REST API는 **항상 `src/routers/{이름}.py`로 분리**하고 `app.include_router(router, prefix="/api")`로 등록합니다.
- `/health/live`, `/health/ready` 같은 서버 공통 엔드포인트만 `main.py`에 직접 정의합니다.
- `load_root_env()`는 반드시 `main.py` 최상단에서 호출합니다.
- `register_cleanup(fn)`: 서버 종료 시 실행할 cleanup 함수를 등록합니다 (DB 커넥션 반환 등).

---

### 2-2. `agents/` — MCP + REST 공통 진입점

**역할:** 하나 이상의 Module을 조합하고, 호출 모드에 맞게 Input/Output을 변환합니다.
Agent 함수는 **MCP Tool과 REST API 양쪽에서 호출**되는 공통 진입점입니다.

**파일 위치:** `src/agents/{이름}.py`

```python
# src/agents/my_agent.py
import time
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("my_agent")


async def my_agent(input: str, mode: str = "default", **kwargs: Any) -> dict[str, Any]:
    """
    My Agent — 요청을 처리하고 결과를 반환합니다.

    Args:
        input:  사용자 입력 (MCP 및 REST API 공통)
        mode:   동작 모드 ("default" | "detail" | "list" | "status")
        **kwargs: 모드별 추가 인자
    """
    start_time = time.time()
    logger.info("[REQUEST] my_agent, mode=%s, input=%s", mode, input)

    try:
        # TODO: my_module_service.execute(...)로 교체
        result = _execute(mode=mode, input=input, **kwargs)

        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info("[RESPONSE] status=success, elapsed_time_ms=%s", elapsed)
        return result

    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed, str(e))
        raise
```

**Agent가 해야 할 일:**

| 단계 | 내용 |
|------|------|
| 1. 로깅 | `[REQUEST]` 로그 — 입력값/모드 기록 |
| 2. Input 변환 | 호출자(MCP/REST) 입력 → 각 Module의 `execute()`가 받는 형태로 변환 |
| 3. Module 조합 호출 | `module_a_service.execute(...)`, `module_b_service.execute(...)` 순서대로 호출 |
| 4. Output 변환 | Module 결과 → 공통 dict 형태로 반환 (router/tool이 각각의 응답 모델로 가공) |
| 5. 에러 처리 | 예외 발생 시 로깅 후 `raise` (응답 변환은 호출자가 담당) |
| 6. 로깅 | `[RESPONSE]` 로그 — elapsed_time_ms 기록 |

**`mode` 패턴:**
- 같은 Agent를 여러 REST 엔드포인트(invoke/list/detail/status)와 MCP Tool에서 공유합니다.
- `mode` 인자로 동작을 분기하면 라우터/툴 쪽 코드가 얇아집니다.

**규칙:**
- Agent는 **MCP Tool과 REST API 양쪽에서 호출**되는 공통 함수입니다.
- Module은 MCP/REST에 직접 노출하지 않습니다.
- Module 간 직접 호출은 금지. 조합은 Agent에서 수행합니다.
- LLM 호출이나 DB 접속이 필요하면 `utils/llm_manager`, `utils/db_manager`를 사용합니다.
- 반환 타입은 `dict[str, Any]`로 통일하고, 응답 스키마 매핑은 호출자(라우터/툴)가 수행합니다.

---

### 2-3. `routers/` — REST API 엔드포인트

**역할:** Agent의 REST API 엔드포인트를 `APIRouter`로 분리합니다.

**언제 사용:**
- Agent에 REST 엔드포인트가 필요하면 **항상** `src/routers/{이름}.py`를 만듭니다.
- 엔드포인트 개수와 무관하게 일관성을 위해 분리합니다.

**파일 위치:** `src/routers/{이름}.py`

```python
# src/routers/my_agent.py
from fastapi import APIRouter
from pydantic import BaseModel

from src.agents.my_agent import my_agent

router = APIRouter(prefix="/my-agent", tags=["My Agent"])


# Request / Response 스키마
class InvokeRequest(BaseModel):
    input: str

class InvokeResponse(BaseModel):
    result: str

class StatusResponse(BaseModel):
    status: str
    message: str


# 엔드포인트
@router.post("/invoke", response_model=InvokeResponse, summary="Agent 실행")
async def invoke(req: InvokeRequest):
    result = await my_agent(input=req.input, mode="default")
    return InvokeResponse(**result)

@router.get("/status", response_model=StatusResponse, summary="Agent 상태 조회")
async def status():
    result = await my_agent(input="", mode="status")
    return StatusResponse(**result)
```

**`main.py`에 등록:**

```python
from src.routers.my_agent import router as my_agent_router
app.include_router(my_agent_router, prefix="/api")
# → /api/my-agent/invoke, /api/my-agent/status
```

**규칙:**
- Router는 Pydantic `BaseModel`로 Request/Response 스키마를 정의해 Swagger에 자동 노출되게 합니다.
- 라우터 함수 본체는 **Agent 호출 + 응답 모델 매핑**만 합니다. 비즈니스 로직 금지.
- `tags=["..."]`을 지정해 Swagger에서 그룹화합니다.
- prefix는 라우터(`/my-agent`) + main.py 등록 시(`/api`) 두 단계로 구성됩니다.

---

### 2-4. `modules/` — 비즈니스 로직 (MCP 역할 도메인 단위)

**역할:** `modules/` 의 **직속 자식은 "하나의 MCP 역할 도메인"** 단위여야 합니다(세부 기능이
직속에 흩어지면 안 됨). 단순 도메인은 `modules/{도메인}/` 안에서 완결되고, 복잡한 도메인은
그 안에서 다시 sub-module로 나눕니다.

> 예: PPT 도메인은 `modules/ppt/` 하나로 묶고, 그 안에 `pptx_parser/`, `content_filler/`,
> `template_store/` … sub-module을 둡니다. 두 역할(저작 `ppt_template_generator`, 채우기 `ppt_report_generator`)이
> 이 sub-module들을 조합합니다.

**디렉토리 구조** (단순 도메인 기준; 복잡하면 `{도메인}/{sub-module}/` 로 한 단계 더 중첩):
```
src/modules/{도메인}/
├── __init__.py          # service 싱글톤 인스턴스를 외부에 export
├── service.py           # 핵심 로직 + 외부 진입점: execute()
├── types.py             # Pydantic 모델, 타입 정의
├── constants.py         # 상수
├── exceptions.py        # 커스텀 예외
├── prompts.py           # LLM 프롬프트 (있을 경우)
├── config/
│   ├── __init__.py
│   ├── config.py        # 환경변수 로드 + 설정값 관리
│   └── *.yaml           # 서비스별 설정 파일 (있을 경우)
└── providers/           # 외부 서비스 구현체 (있을 경우)
    ├── __init__.py
    ├── base.py           # 추상 베이스 클래스
    └── {provider}.py     # 구현체
```

**`service.py`의 핵심 패턴 — `execute()`가 유일한 진입점:**

```python
class MyModuleService:
    async def execute(self, query: str) -> str:
        """
        Agent에서 호출하는 유일한 진입점.
        이 메서드 하나로 해당 모듈의 기능 전체를 사용할 수 있어야 합니다.
        """
        ...

# 싱글톤 인스턴스 — __init__.py에서 이것만 export
my_module_service = MyModuleService()
```

**`__init__.py` — 외부에 service 인스턴스만 노출:**

```python
# src/modules/my_module/__init__.py
from .service import my_module_service

__all__ = ["my_module_service"]
```

**규칙:**
- 해당 기능의 로직은 **Module 디렉토리 안에 전부** 있어야 합니다.
- Agent에서는 `execute()` 하나만 호출합니다. 내부 메서드를 직접 호출하지 않습니다.
- Module은 `agents/`, `routers/`, `main.py`를 import하지 않습니다.
- LLM 호출이 필요하면 `utils/llm_manager`를, DB 접속이 필요하면 `utils/db_manager`를 사용합니다.

**Provider 패턴 — 외부 API 구현체가 여럿일 때:**

```python
# providers/base.py — 공통 인터페이스 정의
class BaseSearchService(ABC):
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[SearchResult]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

새 Provider 추가 시 `service.py`의 레지스트리에 1줄만 추가하면 됩니다:

```python
_SERVICE_REGISTRY: Dict[str, Type[BaseSearchService]] = {
    "tavily":     TavilySearchService,
    "perplexity": PerplexitySearchService,
    "my_new":     MyNewSearchService,   # ← 이 줄만 추가
}
```

---

### 2-5. `utils/` — 공통 인프라

**역할:** 여러 Module이 공통으로 사용하는 연결/설정/로깅 기능을 제공합니다.

| 파일 | 역할 |
|------|------|
| `llm_manager.py` | **LLM 연결** — Cohere / OpenAI 라우팅 클라이언트 |
| `db_manager.py` | **DB 연결** — PostgreSQL / MariaDB 연결 관리 |
| `config_loader.py` | `.env` 파일 로드 + 환경변수 조회 헬퍼 |
| `logger.py` | JSON 형식 stdout 로거 (`APP_ENV=dev`일 때 indent=2) |

> Health Check 프레임워크(`src/health.py`)는 utils와 별도 모듈로 위치합니다. [4-5절](#4-5-health-check-프레임워크-srchealthpy) 참고.

**규칙:**
- LLM을 호출해야 할 때는 반드시 `utils/llm_manager`를 사용합니다. 직접 LLM SDK를 import하지 않습니다.
- DB에 접속해야 할 때는 반드시 `utils/db_manager`를 사용합니다. 직접 DB 드라이버를 연결하지 않습니다.
- `utils`에는 특정 Module에 종속된 로직을 두지 않습니다. 범용적인 기능만 위치합니다.
- 해당 기능이 수정되면 모든 Prebuilt 프로젝트에 영향이 있습니다. 반드시 입고시 확인 절차가 요구됩니다.

---

## 3. 환경변수 설정 구조

```
[루트 .env]                              ← 서버 전체 공통 (LLM API 키, APP_ENV 등)
[src/agents/agent_env/{이름}.env]        ← Agent별 독립 설정 (DB 접속, 검색 API 키 등)
```

### 루트 `.env` 주요 항목

```bash
cp .env.example .env
```

```ini
APP_ENV=dev
SERVER_HOST=0.0.0.0
SERVER_PORT=9101

# Cohere (기본 LLM)
CLIENT_NAME=prebuilt-mcp
API_KEY=your-cohere-api-key
BASE_URL=http://your-cohere-endpoint
MODEL=command
TEMPERATURE=0.0
TIMEOUT=120
MAX_TOKENS=2048

# OpenAI (선택)
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### Agent별 `.env` (예: `my_agent.env`)

```bash
cp src/agents/agent_env/my_agent.env.example src/agents/agent_env/my_agent.env
```

```ini
MY_AGENT_MODEL=command-r-plus
MY_AGENT_API_KEY=
```

### Module의 `config.py`에서 환경변수 로드

```python
# src/modules/my_module/config/config.py
from src.utils.config_loader import load_root_env, load_agent_env, get_env

# 모듈 import 시 1회 실행
load_root_env()              # 루트 .env
load_agent_env("my_module")  # src/agents/agent_env/my_module.env

MY_API_KEY = get_env("MY_API_KEY", "")
```

> `.env.example` 파일은 Git에 포함, 실제 `.env` 파일은 `.gitignore`에 의해 제외됩니다.

---

## 4. 공통 유틸리티

### 4-1. `llm_manager` — LLM 연결 (Cohere / OpenAI)

LLM을 호출해야 하는 모든 곳에서 직접 SDK를 사용하지 않고 `LLMManager`를 사용합니다.

```python
from src.utils.llm_manager import LLMManager

llm = LLMManager()

# 모델명으로 Provider 자동 선택
result = await llm.ainvoke(prompt, model_name="command-r-plus")  # → Cohere
result = await llm.ainvoke(prompt, model_name="gpt-4o-mini")     # → OpenAI
result = await llm.ainvoke(prompt, model_name="openai:gpt-4o")   # → OpenAI (명시적)
result = await llm.ainvoke(prompt, model_name="openai")          # → OPENAI_MODEL env 사용

# 반환값
content = result["content"]  # str
usage   = result["usage"]    # {"input_tokens": ..., "output_tokens": ..., "elapsed_time": ...}
```

**모델명 라우팅 규칙:**

| 입력 | Provider | 사용 모델 |
|------|----------|-----------|
| `"command-r-plus"` | Cohere | 입력값 그대로 |
| `"gpt-4o-mini"` | OpenAI | 입력값 그대로 |
| `"openai"` | OpenAI | `OPENAI_MODEL` env 값 |
| `"cohere"` | Cohere | `COHERE_MODEL` env 값 |
| `"openai:gpt-4o"` | OpenAI | `gpt-4o` |
| `"cohere:command-r"` | Cohere | `command-r` |

### 4-2. `db_manager` — DB 연결 (PostgreSQL / MariaDB)

DB에 접속해야 하는 모든 곳에서 직접 드라이버를 연결하지 않고 `db_manager`를 사용합니다.

```python
from src.utils.db_manager import DBManager

db = DBManager()
rows = await db.execute_query("SELECT * FROM my_table WHERE id = $1", [id])
```

DB 접속 정보는 해당 Agent의 `.env`에 설정합니다.

### 4-3. `config_loader` — 환경변수 로드 & 조회

```python
from src.utils.config_loader import (
    load_root_env,
    load_agent_env,
    get_env,
    get_env_int,
    get_env_float,
    get_env_bool,
)

load_root_env()
load_agent_env("my_module")

api_key = get_env("MY_API_KEY", default="")
timeout  = get_env_int("TIMEOUT", default=30)
ratio    = get_env_float("RATIO", default=0.5)
debug    = get_env_bool("DEBUG", default=False)
```

### 4-4. `get_logger` — JSON 구조화 로그

```python
from src.utils.logger import get_logger

logger = get_logger("my_agent")
```

출력 형식 (JSON, stdout). `APP_ENV=dev`일 때만 `indent=2`로 들여쓰기, 운영에서는 한 줄 로그:

```json
{
  "timestamp": "2026-03-25T10:00:00.000000",
  "level": "INFO",
  "name": "my_agent",
  "message": "[REQUEST] input=hello",
  "source": { "function": "my_agent", "line": 42, "pathname": "..." }
}
```

**로그 컨벤션:**

```python
# 요청 시작 (Agent 진입)
logger.info("[REQUEST] {operation}, {key}={value}, ...")

# 성공 응답
logger.info("[RESPONSE] status=success, elapsed_time_ms=%s, ...", elapsed_ms)

# 에러 응답
logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed_ms, str(e))
```

### 4-5. Health Check 프레임워크 (`src/health.py`)

Agent/Module이 의존하는 외부 서비스(LLM, DB, OpenSearch 등)의 상태를 `register_health_check(name, fn)`으로 등록하면 `/health/ready`에서 자동으로 집계됩니다.

```python
from src.health import register_health_check, ComponentStatus

async def _check_my_service() -> ComponentStatus:
    try:
        await my_client.ping()
        return ComponentStatus(status="ok")
    except Exception as e:
        return ComponentStatus(status="error", message=str(e))

# Module의 service.py 모듈 로드 시점에 1회 호출
register_health_check("my_service", _check_my_service)
```

**엔드포인트:**

| 경로 | 설명 | 응답 |
|------|------|------|
| `/health/live` | Liveness — 프로세스 생존만 확인 | 항상 200 `{"status": "ok"}` |
| `/health/ready` | Readiness — 등록된 모든 check 실행 | 하나라도 실패 시 503 |

- `latency_ms`는 자동으로 측정되어 응답에 포함됩니다.
- 등록된 check가 없으면 `{"status": "ok", "components": {}}` 반환.

---

## 5. 새 Agent / Module 추가하기

이 절은 에이전트 추가에 필요한 **모든 것의 단일 기준**이다(네이밍·백엔드·프론트·완전
호환 계약·표준 이탈). Description(도구 설명문) 작성의 심화 기준만 별도 문서
[`doc/agent-tool-writing-guide.md`](doc/agent-tool-writing-guide.md)를 따른다.

### Step 0. 에이전트 3계층 명명 규칙 (먼저 이름부터 확정)

하나의 에이전트는 계층마다 다른 이름으로 불린다. **에이전트당 3개의 공식 이름**을 먼저
정하고, 나머지 식별자는 모두 여기서 파생한다.

| 이름 | 역할 | 규칙 |
|---|---|---|
| ① **MCP 도구명** (tool_name) | 외부 LLM 오케스트레이터·프론트가 호출하는 **외부 계약** | 동사구 snake_case (예: `query_internal_db`). 함부로 바꾸지 않는다. |
| ② **코드 슬러그** (내부 식별자) | 백엔드 구현 식별자 | 도메인 슬러그 snake_case (예: `nl2sql`). 아래 파생 규칙의 기준. |
| ③ **UI label** | 콘솔 화면 표시 명칭 | 에이전트별 정식 명칭 (예: `NL2SQL Agent`). |

**② 코드 슬러그에서 파생:**
- BE 에이전트 함수: `{슬러그}_agent` (예: `nl2sql_agent`)
- BE 서비스 클래스: `{Pascal}Service` (예: `NL2SQLService`) — 약어는 대문자(`SQL`) 유지
- description 상수: `{대문자슬러그}_DESCRIPTION` (예: `NL2SQL_DESCRIPTION`)
- env 파일: `src/agents/agent_env/{슬러그}.env` / admin id `agent_{슬러그}` / 프론트 manifest `envFiles: ['agent_{슬러그}']`
- 로그 prefix: `{슬러그}` / health 컴포넌트명: `{슬러그}_*`

**① MCP 도구명에서 파생:**
- 프론트 에이전트 폴더: `frontend/src/agents/{도구명}/` (manifest `toolName` = ① 도구명, 백엔드와 1:1 일치 필수)

**확정 스펙 표 (현행 에이전트 정본):**

| 논리 에이전트 | ① MCP 도구명 | ② 코드 슬러그 | BE 서비스 클래스 | description 상수 | ③ UI label |
|---|---|---|---|---|---|
| NL2SQL | query_internal_db | nl2sql | NL2SQLService | NL2SQL_DESCRIPTION | NL2SQL Agent |
| SQL Explorer | explore_internal_db | sql_explorer | SQLExplorerService | SQL_EXPLORER_DESCRIPTION | SQL Explorer Agent |
| Web Search | search_web | web_search | WebSearchService | WEB_SEARCH_DESCRIPTION | Web Search Agent |
| Web Fetch | fetch_web | web_fetch | WebFetchService | WEB_FETCH_DESCRIPTION | Web Fetch Tool |
| Dart Search | search_dart | dart_search | DartSearchService | DART_SEARCH_DESCRIPTION | Dart Search Agent |
| Analysis Completion | complete_analysis | analysis_completion | AnalysisCompletionService | ANALYSIS_COMPLETION_DESCRIPTION | Analysis Completion |
| Task Decomposer | decompose_task | task_decomposer | TaskDecomposerService | TASK_DECOMPOSER_DESCRIPTION | Task Decomposer |
| Chart Generator | generate_chart | chart_generator | ChartGeneratorService | CHART_GENERATOR_DESCRIPTION | NL2Chart Agent |
| PPT Report Generator | generate_ppt_report | ppt_report_generator | (ppt 복합 모듈) | PPT_REPORT_GENERATOR_DESCRIPTION | Report Generator (PPTX) |
| PPT Template Generator | — (REST 전용, MCP 미등록) | ppt_template_generator | (ppt 복합 모듈) | PPT_TEMPLATE_GENERATOR_DESCRIPTION | (내부/미노출) |
| My Agent | test_myagent | my_agent | (전용 모듈 없음) | MY_AGENT_DESCRIPTION | My Agent |

> **혼동 주의(의도적으로 다르게/그대로 둠):**
> - **① 도구명 ≠ ② 슬러그 ≠ ③ UI명**: 세 계층은 역할이 달라 의도적으로 다르다
>   (예: `query_internal_db` / `nl2sql` / `NL2SQL Agent`). 비정상이 아니라 본 규칙이다.
> - **env `agent_` 접두사**: admin API가 `agent_{슬러그}` id를 만들고 프론트가 동일 참조 → 유지.
> - **프론트 폴더명 = ① 도구명**: `toolName` 바인딩 때문(유지).

---

아래 순서대로 파일을 만들고 내용을 채웁니다.

### Step 1. Module 디렉토리 생성

```bash
mkdir -p src/modules/my_module/config
touch src/modules/my_module/__init__.py
touch src/modules/my_module/service.py
touch src/modules/my_module/config/__init__.py
touch src/modules/my_module/config/config.py
```

### Step 2. `config/config.py` 작성 — 환경변수 로드

```python
# src/modules/my_module/config/config.py
from src.utils.config_loader import load_root_env, load_agent_env, get_env

load_root_env()
load_agent_env("my_module")   # src/agents/agent_env/my_module.env 로드

MY_API_KEY = get_env("MY_API_KEY", "")
```

### Step 3. `service.py` 작성 — 기능의 모든 비즈니스 로직

```python
# src/modules/my_module/service.py
from src.utils.llm_manager import LLMManager
from .config.config import MY_API_KEY


class MyModuleService:
    def __init__(self):
        self.llm = LLMManager()

    async def execute(self, query: str) -> str:
        """Agent에서 호출하는 유일한 진입점."""
        result = await self.llm.ainvoke(query)
        return result["content"]


my_module_service = MyModuleService()
```

(선택) Health Check 등록:

```python
from src.health import register_health_check, ComponentStatus

async def _check() -> ComponentStatus:
    try:
        await my_module_service.llm.ainvoke("ping")
        return ComponentStatus(status="ok")
    except Exception as e:
        return ComponentStatus(status="error", message=str(e))

register_health_check("my_module", _check)
```

### Step 4. `__init__.py` 작성 — service 인스턴스 export

```python
# src/modules/my_module/__init__.py
from .service import my_module_service

__all__ = ["my_module_service"]
```

### Step 5. Agent 파일 생성

```bash
touch src/agents/my_module.py
touch src/agents/agent_env/my_module.env.example
```

### Step 6. `src/agents/my_module.py` 작성 — Module 조합 + I/O 변환

```python
"""
My Module Agent

MCP Tool과 REST API 양쪽에서 호출되는 공통 함수입니다.
mode 인자로 동작을 분기합니다.
"""
import time
from typing import Any

from src.modules.my_module import my_module_service
from src.utils.logger import get_logger

logger = get_logger("my_module")


# =============================================================================
# MCP Tool description — main.py에서 import해 @mcp.tool(description=...)에 사용
# =============================================================================
# 작성 기준: doc/agent-tool-writing-guide.md(2장)의 8개 필수 항목을 모두 채웁니다.
# (Purpose / Parameters / Returns / When to USE 2+ / When NOT to use 1+ /
#  Input example / Post-call behavior / Error handling)
# src/agents/my_agent.py의 MY_AGENT_DESCRIPTION이 가이드 준수 예시입니다.
MY_MODULE_DESCRIPTION = """\
<동사로 시작하는 한 줄 정의 — 이 도구가 무엇을 하는지>

[작성 기준: doc/agent-tool-writing-guide.md 2장. 아래 8개 항목을 모두 채우세요.]

■ Parameters
- input (string, required): <설명 / 제약 / 기본값>

■ Returns
- type: <string|object|array> — <한 줄 설명>
- shape: <간략 스키마>
- example: <실제 예시 한 개>

■ When to USE
- <긍정 예시 1>
- <긍정 예시 2 (2개 이상 필수)>

■ When NOT to use
- <부정 예시 1 (1개 이상 필수, 유사 도구와의 경계 포함)>

■ Input example
- my_module_tool(input="<예시 입력>")

■ Post-call behavior
- <호출 직후 에이전트 행동 규칙>

■ Error handling
- <실패 종류 → 대응 방향. 재시도 정책 포함>
"""


async def my_module(input: str, mode: str = "default", **kwargs: Any) -> dict[str, Any]:
    start_time = time.time()
    logger.info("[REQUEST] my_module, mode=%s, input=%s", mode, input)

    try:
        if mode == "default":
            content = await my_module_service.execute(query=input)
            result = {"result": content}
        elif mode == "status":
            result = {"status": "ok", "message": "정상 동작 중"}
        else:
            raise ValueError(f"지원하지 않는 mode: {mode}")

        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info("[RESPONSE] status=success, elapsed_time_ms=%s", elapsed)
        return result

    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed, str(e))
        raise
```

### Step 7. REST 라우터 생성 — `src/routers/my_module.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

from src.agents.my_module import my_module

router = APIRouter(prefix="/my-module", tags=["My Module"])


class InvokeRequest(BaseModel):
    input: str

class InvokeResponse(BaseModel):
    result: str

class StatusResponse(BaseModel):
    status: str
    message: str


@router.post("/invoke", response_model=InvokeResponse, summary="Agent 실행")
async def invoke(req: InvokeRequest):
    result = await my_module(input=req.input, mode="default")
    return InvokeResponse(**result)


@router.get("/status", response_model=StatusResponse, summary="Agent 상태 조회")
async def status():
    result = await my_module(input="", mode="status")
    return StatusResponse(**result)
```

### Step 8. `main.py`에 등록

REST 라우터 + MCP Tool 두 가지를 모두 등록합니다.

```python
# (상단) 라우터 등록
from src.routers.my_module import router as my_module_router
app.include_router(my_module_router, prefix="/api")
# → /api/my-module/invoke, /api/my-module/status


# (Tool 등록 영역) MCP Tool 등록
# description은 agent 모듈(Step 6)에서 정의하고 여기서는 import만 합니다.
from src.agents.my_module import my_module, MY_MODULE_DESCRIPTION

# name=은 ① MCP 도구명(동사구 snake_case, Step 0 규칙) — 프론트 manifest.toolName과 1:1 일치해야 함
@mcp.tool(name="query_my_module", description=MY_MODULE_DESCRIPTION)
async def my_module_tool(input: str) -> str:
    result = await my_module(input=input, mode="default")
    return result["result"]
```

### Step 9. `.env.example` 작성

```ini
# src/agents/agent_env/my_module.env.example
MY_API_KEY=your-api-key-here
```

### Step 10. 프론트 매니페스트 — `frontend/src/agents/{① 도구명}/manifest.js`

콘솔(사이드바·Overview·`/agents/{도구명}` 상세)에 노출하려면 프론트 폴더 하나를 만든다.
폴더명은 **① MCP 도구명**과 일치해야 한다(코드 슬러그 아님 — Step 0). 중앙 로더
[`frontend/src/lib/agentRegistry.js`](frontend/src/lib/agentRegistry.js)가 Vite의
`import.meta.glob`로 모든 `manifest.js`를 빌드 시 자동 수집하므로 **App.jsx·라우터 무수정**.

```js
// frontend/src/agents/query_my_module/manifest.js  (폴더명 = ① 도구명)
export default {
  toolName: 'query_my_module', // 필수. 백엔드 @mcp.tool(name=...)과 1:1 일치
  label: 'My Module',          // 필수. 사이드바/카드 표시 이름(③ UI label)
  icon: '🧩',                  // 필수
  blurb: '한 줄 설명.',         // 필수
  test: 'text',                // 필수. 'text'(질의 테스트) | 'workspace'(풀스크린)
  // --- 이하 선택 ---
  sampleQueries: ['예시 질의'],  // Test 탭 샘플
  envFiles: ['agent_my_module'], // = src/agents/agent_env/{슬러그}.env (admin env 편집기 매칭)
  logPrefixes: ['my_module'],    // = get_logger("{슬러그}") (Logs 탭 필터)
  healthPrefixes: ['my_module'], // = register_health_check("{슬러그}_*") (Overview 상태 매칭)
}
```

> 실제 카드가 뜨려면 백엔드 `main.py`에 동일 `toolName`의 MCP 도구가 등록되어 있어야 한다
> (Step 8). 프론트 폴더는 표시 메타·워크스페이스 화면만 공급한다.

### Step 11. (선택) 워크스페이스 + API 래퍼 — 풀스크린 화면이 필요할 때

풀스크린 화면이 필요하면 같은 폴더에 워크스페이스 컴포넌트와 REST 래퍼를 두고
manifest에 `workspace`를 추가한다(사이드바 Workspaces 그룹·`/workspaces/{id}` 라우트
자동 생성, App.jsx 무수정).

```js
import MyWorkspace from './MyWorkspace.jsx'

export default {
  toolName: 'query_my_module',
  label: 'My Module',
  icon: '🧩',
  blurb: '...',
  test: 'workspace',
  workspace: {
    id: 'mine',
    label: 'My Workspace',
    icon: '🗂️',
    route: '/workspaces/mine',
    component: MyWorkspace,
  },
}
```

API 래퍼(`{domain}Api.js`)는 베이스 경로 상수 + fetch 헬퍼 패턴을 따른다.
실시간 스트리밍은 `EventSource`(SSE)를 사용한다.

```js
// myModuleApi.js
const B = '/api/my-module'
async function get(url)  { const r = await fetch(url); if (!r.ok) throw new Error(r.statusText); return r.json() }
async function post(url, body) {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error(r.statusText); return r.json()
}
export const getStatus = () => get(`${B}/status`)
export const invoke    = (input) => post(`${B}/invoke`, { input })
// SSE: const es = new EventSource(`${B}/watch`); es.onmessage = e => {...}; // 소비자가 .close()
```

> 참고 예시: `explore_internal_db`(SqlExplorerWorkspace, SSE 스트리밍),
> `generate_ppt_report`(다단계 위저드).

### 완전 호환 계약 (계층 간 반드시 일치)

신규 에이전트가 모듈에 빠짐없이 끼워지려면 아래 값들이 **양쪽에서 정확히 일치**해야 한다.
하나라도 어긋나면 카드 미표시·env 편집기 누락·로그/상태 필터 실패가 발생한다.

| 항목 | 일치시킬 두(세) 지점 |
|---|---|
| MCP 도구명 | 프론트 `manifest.toolName` ↔ `main.py` `@mcp.tool(name=...)` |
| 프론트 폴더명 | `frontend/src/agents/{도구명}/` ↔ ① MCP 도구명 |
| env 파일 | `manifest.envFiles: ['agent_{슬러그}']` ↔ `src/agents/agent_env/{슬러그}.env(.example)` ↔ 모듈 `load_agent_env("{슬러그}")` |
| 로그/health prefix | `manifest.logPrefixes`/`healthPrefixes` ↔ `get_logger("{슬러그}")` / `register_health_check("{슬러그}_*")` |
| description | `{대문자슬러그}_DESCRIPTION` 상수 ↔ 8항목 충족([`doc/agent-tool-writing-guide.md`](doc/agent-tool-writing-guide.md) 2장) |

### 체크리스트

```
[ ] src/modules/my_module/config/config.py        — load_root_env() + load_agent_env() 호출
[ ] src/modules/my_module/service.py              — execute() 구현, 기능 전체가 여기에
[ ] src/modules/my_module/__init__.py             — service 인스턴스 export
[ ] src/agents/my_module.py                       — Module 조합 + I/O 변환 + 로깅 + mode 분기 + {NAME}_DESCRIPTION 상수
[ ] src/routers/my_module.py                      — APIRouter + Pydantic 스키마 + 엔드포인트
[ ] src/agents/agent_env/my_module.env.example    — 환경변수 예시
[ ] src/agents/agent_env/my_module.env            — 실제 값 입력 (gitignore됨)
[ ] main.py                                       — include_router + agent 모듈에서 description import + @mcp.tool() 등록 (description 별도 정의 금지)
[ ] (선택) register_health_check()                — 외부 의존성이 있을 경우
[ ] frontend/src/agents/{도구명}/manifest.js      — 폴더명=① 도구명, toolName=백엔드 @mcp.tool name과 1:1, envFiles/logPrefixes=슬러그
[ ] (선택) {Domain}Workspace.jsx + {domain}Api.js + manifest.workspace  — 풀스크린 화면이 필요할 때
[ ] @mcp.tool description     — Purpose 한 줄, 동사로 시작
[ ] @mcp.tool description     — 모든 파라미터에 type / required / 제약 / 기본값 명시
[ ] @mcp.tool description     — Returns 형식 + 예시 1개
[ ] @mcp.tool description     — When to USE 2개 이상
[ ] @mcp.tool description     — When NOT to use 1개 이상 (유사 도구 경계 포함)
[ ] @mcp.tool description     — Post-call behavior 명시
[ ] @mcp.tool description     — Error handling(재시도 정책 포함) 명시
[ ] @mcp.tool description     — 도구 간 우선순위/페르소나가 description에 섞이지 않음
```

### 표준에서 벗어난 에이전트 (템플릿으로 복붙 금지)

신규 에이전트는 위 표준만 따른다. 아래 에이전트들은 특수 사정으로 표준과 다르므로
**복사 출발점으로 삼지 말 것**. 표준 골격이 필요하면 `my_agent`(BE) /
`test_myagent`(FE)를 베이스로 한다.

- **의도적 예외(도메인 특성상 불가피):**
  - `chart_generator` — 라우터에 `prefix` 없이 절대경로 라우트(`/charts/{id}`,
    `/chart/{id}`)로 파일 산출물(HTML/PNG)을 서빙. 일반 에이전트는 `prefix="/api"` 사용.
  - `os_index_admin` — **레지스트리 기반 공용 OpenSearch 인덱스 관리** 모듈(REST 전용, MCP 미등록).
    특정 에이전트에 결합되지 않으며, 각 에이전트가 `register_index_group()`으로 자신의 큐레이션
    인덱스 그룹을 등록한다(의존성 역전). UI는 독립 페이지 `/os-index-admin`. 에이전트가 아니므로
    위 표준(에이전트 추가)의 대상이 아니다.
  - `ppt` 도메인 — **2개 에이전트가 단일 복합 모듈 `modules/ppt/`를 공유**.
    `ppt_template_generator`는 REST 전용으로 MCP 도구·프론트 폴더가 없다.
  - `sql_explorer` — `event_bus`/`progress` 기반 SSE 스트리밍, 정적 `monitor.html`
    서빙(`/api/sql-explorer/monitor`), 평가용 모드(eval 등) 다수.

---

## 6. 서버 실행

### 의존성 설치

```bash
uv sync
```

### 환경변수 설정

```bash
cp .env.example .env
# .env 편집 후 LLM API 키, endpoint 입력

# Agent별 env 파일도 동일하게 준비 (필요 시)
cp src/agents/agent_env/{agent_name}.env.example src/agents/agent_env/{agent_name}.env
```

### 개발 모드 (Hot Reload)

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 9101 --reload
```

### 운영 모드 (Gunicorn)

```bash
uv run gunicorn -b 0.0.0.0:9101 -k uvicorn.workers.UvicornWorker main:app
```

### 접속 경로

| 경로 | 설명 |
|------|------|
| `http://0.0.0.0:9101/mcp` | MCP 클라이언트 연결 (FastMCP Streamable HTTP) |
| `http://0.0.0.0:9101/api/*` | Agent REST API (라우터별 prefix) |
| `http://0.0.0.0:9101/api/admin/*` | 환경변수 관리 + 서버 재기동 (Admin API) |
| `http://0.0.0.0:9101/ui/` | 프론트엔드 UI — `frontend/dist`가 있을 때만 활성화 |
| `http://0.0.0.0:9101/health/live` | Liveness probe |
| `http://0.0.0.0:9101/health/ready` | Readiness probe |
| `http://0.0.0.0:9101/docs` | Swagger UI |

---

## 7. 프론트엔드 (UI)

`frontend/`는 Vite + React 기반의 MCP 테스트용 UI입니다. 등록된 MCP 도구를 조회하고 채팅 형태로 호출해볼 수 있고, 사이드바에서 도구별로 토글하거나 description / inputSchema를 펼쳐볼 수 있습니다.

### 빌드 산출물 위치

| 항목 | 경로 |
|------|------|
| 소스 | `frontend/src/` |
| 빌드 결과 | `frontend/dist/` |
| 정적 서빙 경로 | `/ui/` (main.py가 `frontend/dist` 존재 여부를 확인해 자동 마운트) |

> `frontend/dist`가 없으면 `/ui` 엔드포인트는 마운트되지 않습니다. 빌드를 먼저 수행하세요.

### 빠른 실행

```bash
# 의존성 설치 (frontend 디렉토리 안에서)
cd frontend
npm install

# 운영용 빌드 — 끝나면 frontend/dist/ 생성, 백엔드의 /ui/ 가 자동 활성화
npm run build

# 개발용 (Hot Reload, Vite dev server)
npm run dev
```

빌드를 마쳤다면 백엔드 서버를 띄우고 브라우저에서 `http://<host>:9101/ui/` 접속.

### 더 자세한 내용

프론트엔드 디렉토리 구조, MCP 클라이언트 구현(`src/mcp/client.js`), 도구 토글 동작, Vite dev proxy 설정 등 상세 사항은 [`frontend/README.md`](frontend/README.md) 참고.
