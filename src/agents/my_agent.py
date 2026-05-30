"""
My Agent

MCP Tool 및 REST API 양쪽에서 호출되는 Agent 예시입니다.
실제 Agent 추가 시 이 파일을 복사해 {name}_agent.py로 수정하세요.
MCP Tool description은 doc/agent-tool-writing-guide.md(2장)를 따라 작성합니다.

================================================================================
REQUIRED MODULES (필수 의존성)
================================================================================
1. modules/my_module/
   - service.py : 핵심 비즈니스 로직

환경 설정: agents/agent_env/my_agent.env
================================================================================
"""
import time
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("my_agent")


# =============================================================================
# MCP Tool description
# =============================================================================
# main.py에서 import해 @mcp.tool(description=...)에 사용합니다.
# doc/agent-tool-writing-guide.md(2장)를 따른 예시(exemplar)이니, 실제 Agent
# 추가 시 이 상수를 그대로 복사해 8개 항목을 본인 도구에 맞게 교체하세요.
MY_AGENT_DESCRIPTION = """\
입력 텍스트를 받아 처리하고 결과 문자열을 반환합니다.

[이 설명은 작성 가이드(doc/agent-tool-writing-guide.md)를 따른 예시(exemplar)입니다.
 실제 Agent를 추가할 때 이 구조를 그대로 복사해 각 항목을 본인 도구에 맞게 교체하세요.
 현재 MyAgent는 stub이므로 아래 동작/예시는 템플릿 형태입니다.]

■ Parameters
- input (string, required): 처리할 사용자 입력 텍스트. 빈 문자열도 허용되나 의미 있는 결과를 보장하지 않음. 기본값 없음.

■ Returns
- type: string — 처리 결과 텍스트 한 개.
- shape: "<처리 결과 문자열>"
- example: "[stub] input=안녕 처리 완료"

■ When to USE
- 단일 텍스트 입력을 받아 가공된 텍스트 결과 하나가 필요할 때.
- 이 도구의 처리 규칙이 사용자 요청에 정확히 해당할 때 (실제 Agent 구현 시 도메인 조건으로 구체화).

■ When NOT to use
- 구조화된 데이터(목록/상세/상태 등)가 필요한 경우 — 해당 전용 REST 엔드포인트(/api/my-agent/*)를 사용.
- 입력이 비어 있거나 처리 대상이 불명확한 경우 — 추측 호출 대신 사용자에게 명확화 요청.
- 다른 도구가 더 적합한 작업으로 명시된 경우 — 그 도구를 사용 (도구 간 우선순위는 이 설명이 아니라 System Prompt에서 관리).

■ Input example
- my_agent_tool(input="처리할 텍스트")

■ Post-call behavior
- 결과 문자열을 그대로 사용자에게 전달. 추가 도구 호출 없이 한 번의 호출로 응답을 종료.
- 결과가 비어 있거나 의미 없으면 입력을 재확인하도록 사용자에게 안내(자동 재호출 금지).

■ Error handling
- 처리 실패(예외) 시: 도구는 예외를 전파함. 동일 입력으로의 무한 재시도 금지, 원인과 함께 사용자에게 보고.
- 미지원 동작 요청 시: 재시도하지 말고 지원 범위를 사용자에게 안내.
"""


async def my_agent(input: str, mode: str = "default", **kwargs: Any) -> dict[str, Any]:
    """
    My Agent — 요청을 처리하고 결과를 반환합니다.

    Args:
        input:  사용자 입력 (MCP 및 REST API 공통)
        mode:   동작 모드 ("default" | "detail" | "list" | "status")
        **kwargs: 모드별 추가 인자

    Returns:
        모드별 결과 딕셔너리
    """
    start_time = time.time()
    logger.info("[REQUEST] my_agent, mode=%s, input=%s", mode, input)

    try:
        # TODO: my_module_service.execute(...)로 교체
        result = _stub_execute(mode=mode, input=input, **kwargs)

        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info("[RESPONSE] status=success, elapsed_time_ms=%s", elapsed)
        return result

    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed, str(e))
        raise


def _stub_execute(mode: str, input: str, **kwargs: Any) -> dict[str, Any]:
    """TODO: modules/my_module로 교체 예정인 stub 구현."""
    if mode == "default":
        return {"result": f"[stub] input={input} 처리 완료"}
    if mode == "detail":
        item_id = kwargs.get("item_id", "")
        return {"id": item_id, "detail": f"[stub] {item_id} 상세 정보"}
    if mode == "list":
        return {"items": ["item_1", "item_2", "item_3"]}
    if mode == "status":
        return {"status": "ok", "message": "[stub] 정상 동작 중"}
    raise ValueError(f"지원하지 않는 mode: {mode}")
