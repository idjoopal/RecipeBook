"""
Cookbook Agent

설계서 §1~§7 의 ``cookbook_search`` / ``cookbook_get`` 두 도구를 노출.

REQUIRED MODULES
- src/modules/cookbook : service / indexer / loader / referral / watcher

description 은 doc/agent-tool-writing-guide.md 의 8섹션 규칙을 따른다.
실제 카탈로그 섹션은 부팅 시 ``build_search_description()`` 으로 동적 주입된다.

환경 설정: agents/agent_env/cookbook.env
"""
from __future__ import annotations

import time
from typing import Any

from src.modules.cookbook import service
from src.utils.logger import get_logger

logger = get_logger("cookbook")


# =============================================================================
# MCP Tool descriptions  —  8 sections (agent-tool-writing-guide.md §2)
# =============================================================================

COOKBOOK_SEARCH_DESCRIPTION_STATIC = """\
Search the cookbook: a library of skills, workflows, and tool manuals for this MCP server.

■ Parameters
- query (string, required): 자연어 검색어. 한국어/영어 모두 지원. 빈 문자열이면 빈 결과 반환.
- kind (string, optional): "skill" | "workflow" | "tool_manual" 중 하나로 필터. 미지정 시 전체 검색.
- tags (list[string], optional): 태그 교집합 필터. 미지정 시 태그 무시.
- top_k (int, optional, default=5): 반환 결과 개수 (1~20 권장).

■ Returns
- type: list of objects (메타데이터만; 본문은 cookbook_get 으로 후속 조회)
- shape: [{"id": "...", "kind": "...", "title": "...", "summary": "...", "tags": [...], "score": 0.0}, ...]
- example:
  [{"id": "wf.report_pipeline", "kind": "workflow",
    "title": "NL질의 → SQL → Chart → 보고서 풀파이프",
    "summary": "자연어 질의를 받아 ...", "tags": ["report","nl2sql"], "score": 4.12}]

■ When to USE
- 다단계 복합 질의에서 어떤 도구를 어떤 순서로 호출해야 할지 모를 때 (workflow 탐색).
- 이 서버의 낯선 도구를 만났을 때 그 사용법 매뉴얼을 찾고 싶을 때 (tool_manual 탐색).
- 도메인 스킬(예: 모호 질의 재질의 절차) 등 skills.md 가 없는 환경에서 절차를 찾을 때.

■ When NOT to use
- 외부 웹/일반 지식 검색이 필요한 경우 — web 도구를 사용. cookbook 은 이 서버 내 콘텐츠만 검색함.
- 이미 id 를 알고 있는 경우 — search 단계 건너뛰고 cookbook_get(id="...") 직접 호출.
- description 말미의 "== Available recipes ==" 카탈로그에서 원하는 id 가 보이면 search 없이 바로 cookbook_get 호출 가능.

■ Input example
- cookbook_search(query="자연어로 차트 만들기", kind="workflow", top_k=3)

■ Post-call behavior
- 결과는 메타데이터일 뿐. 본문이 필요하면 반환된 id 로 cookbook_get 을 후속 호출.
- 결과 0건이면 쿼리를 일반화(주요 명사만 추출 등)해서 1회 재시도. 그래도 없으면 사용자에게 보고.

■ Error handling
- 인덱스 미초기화 시: 빈 리스트 반환 (서버 startup 중일 수 있음 — 사용자에게 보고하고 잠시 후 재시도).
- query 가 빈 문자열이거나 토큰 0개로 분해되면 빈 리스트 반환.
- 내부 BM25 예외 발생 시: 예외 전파 (자동 재시도 금지).
"""


COOKBOOK_GET_DESCRIPTION = """\
Fetch a single recipe (skill / workflow / tool_manual) by its id.

■ Parameters
- id (string, required): "skill.X" / "wf.X" / "tool_manual.X" 형식의 안정적 식별자.

■ Returns
- type: object — Recipe 전체 본문 + kind 별 확장 필드 + 자율호출 메타필드.
- shape: 공통 코어 {id, kind, title, tags, summary, body, trigger_patterns, related_ids}
  + kind 별 확장: workflow→steps[], tool_manual→{tool_name, params[], examples[], output_format, chain_with[]}, skill→{prerequisites, when_to_use}
- example:
  {"id": "wf.report_pipeline", "kind": "workflow",
   "title": "...", "steps": [{"tool": "nl2sql", "input_hint": "...",
   "output_use": "...", "next_steps": ["tool_manual.nl2chart"]}],
   "chain_with": ["tool_manual.nl2chart"]}

■ When to USE
- cookbook_search 로 받은 결과의 본문이 필요할 때.
- cookbook_search.description 의 카탈로그 섹션에서 id 를 식별했을 때.
- 도구를 호출하기 직전 그 도구의 tool_manual 을 참조하고 싶을 때 (특히 description 에 "MUST consult cookbook_get(...)" 가 명시된 경우).

■ When NOT to use
- id 를 모를 때 — 먼저 cookbook_search 로 검색.
- 단순히 카탈로그 목록만 필요할 때 — cookbook_search 의 description 에 카탈로그가 이미 있음.

■ Input example
- cookbook_get(id="tool_manual.nl2sql")

■ Post-call behavior
- 반환된 ``chain_with`` 또는 ``steps[].next_steps`` 필드를 보고 다음 호출 후보를 자동 식별 (Layer 3).
- tool_manual 의 ``params`` / ``examples`` / ``output_format`` 를 도구 호출 직전 학습 자료로 사용.

■ Error handling
- 존재하지 않는 id: KeyError 전파 (자동 재시도 금지, 사용자에게 보고).
- 인덱스 미초기화 시: KeyError (서버 startup 중일 수 있음).
"""


# =============================================================================
# Agent functions  —  Module 조합 + I/O 변환 + 로깅
# =============================================================================


async def cookbook_search_agent(
    query: str,
    kind: str | None = None,
    tags: list[str] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Module 조합 호출 + JSON 직렬화."""
    start = time.time()
    logger.info(
        "[REQUEST] cookbook_search, query=%r, kind=%s, tags=%s, top_k=%s",
        query, kind, tags, top_k,
    )
    try:
        # cast: 잘못된 kind 가 들어오면 BM25 필터에서 매칭이 0건이 되어 빈 결과 반환
        results = await service.search(query=query, kind=kind, tags=tags, top_k=top_k)  # type: ignore[arg-type]
        out = [r.model_dump() for r in results]
        elapsed = round((time.time() - start) * 1000, 2)
        logger.info(
            "[RESPONSE] cookbook_search status=success, hits=%d, elapsed_time_ms=%s",
            len(out), elapsed,
        )
        return out
    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 2)
        logger.error(
            "[RESPONSE] cookbook_search status=error, elapsed_time_ms=%s, error=%s",
            elapsed, str(e),
        )
        raise


async def cookbook_get_agent(id: str) -> dict[str, Any]:  # noqa: A002 (shadow builtin OK for MCP arg name)
    """단일 Recipe 본문 반환 (chain_with / next_steps 포함 → Layer 3)."""
    start = time.time()
    logger.info("[REQUEST] cookbook_get, id=%s", id)
    try:
        recipe = await service.get(id_=id)
        out = recipe.model_dump()
        elapsed = round((time.time() - start) * 1000, 2)
        logger.info(
            "[RESPONSE] cookbook_get status=success, kind=%s, elapsed_time_ms=%s",
            out.get("kind"), elapsed,
        )
        return out
    except KeyError as e:
        elapsed = round((time.time() - start) * 1000, 2)
        logger.warning(
            "[RESPONSE] cookbook_get status=not_found, id=%s, elapsed_time_ms=%s",
            id, elapsed,
        )
        raise KeyError(f"recipe not found: {id}") from e
    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 2)
        logger.error(
            "[RESPONSE] cookbook_get status=error, id=%s, elapsed_time_ms=%s, error=%s",
            id, elapsed, str(e),
        )
        raise


# =============================================================================
# Layer 1 — dynamic description builder
# =============================================================================


def build_search_description() -> str:
    """cookbook_search 의 최종 description = 정적 안내 + 동적 카탈로그 (설계서 §9)."""
    catalog = service.catalog_text()
    if not catalog:
        return COOKBOOK_SEARCH_DESCRIPTION_STATIC
    return COOKBOOK_SEARCH_DESCRIPTION_STATIC + "\n\n" + catalog
