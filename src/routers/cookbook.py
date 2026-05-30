"""
Cookbook REST Router

엔드포인트:
  POST /api/cookbook/search              — Recipe 검색 (메타데이터)
  GET  /api/cookbook/recipes/{id}        — Recipe 본문 조회
  POST /api/cookbook/reload              — admin/debug 용 수동 reload

실제 로직은 src/modules/cookbook/service.py 에 위임.
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agents.cookbook_agent import cookbook_get_agent, cookbook_search_agent
from src.modules.cookbook import service as cookbook_service

router = APIRouter(prefix="/cookbook", tags=["Cookbook"])


# =============================================================================
# Request / Response 스키마
# =============================================================================


class SearchRequest(BaseModel):
    query: str = Field(..., description="자연어 검색어")
    kind: Literal["skill", "workflow", "tool_manual"] | None = Field(
        default=None, description="kind 필터"
    )
    tags: list[str] | None = Field(default=None, description="태그 교집합 필터")
    top_k: int = Field(default=5, ge=1, le=50, description="반환 결과 개수")


class ReloadResponse(BaseModel):
    status: str
    docs: int


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/search",
    response_model=list[dict[str, Any]],
    summary="Recipe 검색",
    description="자연어 쿼리로 cookbook 색인을 BM25 검색한 결과 메타데이터를 반환합니다.",
)
async def search(req: SearchRequest) -> list[dict[str, Any]]:
    return await cookbook_search_agent(
        query=req.query, kind=req.kind, tags=req.tags, top_k=req.top_k,
    )


@router.get(
    "/recipes/{id}",
    response_model=dict[str, Any],
    summary="Recipe 본문 조회",
    description="안정 식별자(id)로 Recipe 본문을 조회합니다. 미존재 시 404.",
)
async def get_recipe(id: str) -> dict[str, Any]:  # noqa: A002
    try:
        return await cookbook_get_agent(id=id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/reload",
    response_model=ReloadResponse,
    summary="cookbook 인덱스 수동 reload",
    description="콘텐츠 디렉토리를 다시 스캔하고 인덱스/카탈로그/L2 referral 을 재빌드합니다.",
)
async def reload() -> ReloadResponse:
    # service._reload_sync_blocking 은 동기 함수지만 이미 lifespan 외부 호출 안전.
    cookbook_service._reload_sync_blocking()
    return ReloadResponse(status="ok", docs=len(cookbook_service.iter_recipes()))
