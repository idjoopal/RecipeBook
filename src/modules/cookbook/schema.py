"""
Cookbook Pydantic schemas.

설계서 §3 (Schema) 를 그대로 코드화. 공통 코어 필드 + kind별 확장 필드.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["skill", "workflow", "tool_manual"]


class Param(BaseModel):
    """tool_manual 의 파라미터 1개."""
    name: str
    semantics: str = ""
    valid_range: str | None = None
    gotcha: str | None = None


class Step(BaseModel):
    """workflow 의 단일 step. 설계서 §3.2 workflow 참조."""
    tool: str
    input_hint: str = ""
    output_use: str = ""
    next_steps: list[str] = Field(default_factory=list)


class Recipe(BaseModel):
    """모든 kind 의 통합 표현."""

    # 공통 코어
    id: str
    kind: Kind
    title: str
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    body: str = ""
    trigger_patterns: list[str] = Field(default_factory=list)
    related_ids: list[str] = Field(default_factory=list)

    # skill 확장
    prerequisites: str | None = None
    when_to_use: str | None = None

    # workflow 확장
    steps: list[Step] = Field(default_factory=list)

    # tool_manual 확장
    tool_name: str | None = None
    params: list[Param] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    output_format: str | None = None
    chain_with: list[str] = Field(default_factory=list)

    # D/O/M referral 차등 (설계서 §8). [D, O, M] 각 0~3.
    dom: list[int] | None = None


class SearchResult(BaseModel):
    """검색 메타데이터만 반환 (설계서 §3 API 표면)."""
    id: str
    kind: Kind
    title: str
    summary: str
    tags: list[str]
    score: float
