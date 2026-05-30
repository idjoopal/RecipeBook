"""
My Agent Router

REST API 엔드포인트가 여러 개일 때 APIRouter로 분리하는 패턴 예시입니다.
실제 Agent 추가 시 이 파일을 복사해 {name}.py로 수정하세요.

실제 로직은 모두 src/agents/my_agent.py에 위임합니다.

등록: main.py에서 app.include_router(my_agent_router, prefix="/api")
접속: /api/my-agent/...
"""
from fastapi import APIRouter
from pydantic import BaseModel

from src.agents.my_agent import my_agent

router = APIRouter(prefix="/my-agent", tags=["My Agent"])


# =============================================================================
# Request / Response 스키마
# =============================================================================
class InvokeRequest(BaseModel):
    input: str


class InvokeResponse(BaseModel):
    result: str


class DetailResponse(BaseModel):
    id: str
    detail: str


class ListResponse(BaseModel):
    items: list[str]


class StatusResponse(BaseModel):
    status: str
    message: str


# =============================================================================
# 엔드포인트
# =============================================================================
@router.post(
    "/invoke",
    response_model=InvokeResponse,
    summary="Agent 실행",
    description="입력을 받아 Agent를 실행하고 결과를 반환합니다.",
)
async def invoke(req: InvokeRequest):
    result = await my_agent(input=req.input, mode="default")
    return InvokeResponse(**result)


@router.get(
    "/items",
    response_model=ListResponse,
    summary="목록 조회",
    description="처리 가능한 항목 목록을 반환합니다.",
)
async def list_items():
    result = await my_agent(input="", mode="list")
    return ListResponse(**result)


@router.get(
    "/items/{item_id}",
    response_model=DetailResponse,
    summary="항목 상세 조회",
    description="특정 항목의 상세 정보를 반환합니다.",
)
async def get_detail(item_id: str):
    result = await my_agent(input="", mode="detail", item_id=item_id)
    return DetailResponse(**result)


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Agent 상태 조회",
    description="Agent의 현재 상태를 반환합니다.",
)
async def status():
    result = await my_agent(input="", mode="status")
    return StatusResponse(**result)
