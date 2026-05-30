"""
Health Check 프레임워크

등록 기반 구조로, Agent/Module이 register_health_check()로 의존성을 등록합니다.
run_checks()가 등록된 모든 check 함수를 실행하고 결과를 반환합니다.

사용 예시 (module의 service.py 등에서):
    from src.health import register_health_check, ComponentStatus

    async def _check_my_service() -> ComponentStatus:
        try:
            await my_client.ping()
            return ComponentStatus(status="ok")
        except Exception as e:
            return ComponentStatus(status="error", message=str(e))

    register_health_check("my_service", _check_my_service)
"""
import time
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel


class ComponentStatus(BaseModel):
    status: Literal["ok", "error"]
    message: str | None = None
    latency_ms: float | None = None
    # 외부 리소스(DB·OpenSearch·객체저장소 등) 연결 체크면 True.
    # 프로세스 내부 단계는 False(기본) — UI는 external=True만 노출.
    external: bool = False


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    status: Literal["ok", "error"]
    components: dict[str, ComponentStatus]


_health_checks: dict[str, Callable[[], Awaitable[ComponentStatus]]] = {}
_external_flags: dict[str, bool] = {}


def register_health_check(
    name: str,
    check_fn: Callable[[], Awaitable[ComponentStatus]],
    external: bool = False,
) -> None:
    """
    health check 함수를 등록합니다.

    Args:
        name: 컴포넌트 이름 (예: "llm", "db", "opensearch")
        check_fn: 인자 없이 호출되어 ComponentStatus를 반환하는 async 함수
        external: 외부 리소스(DB·OpenSearch 등) 연결 체크면 True. 내부 단계는 False(기본).
                  UI(콘솔)는 external=True 컴포넌트만 표시한다.
    """
    _health_checks[name] = check_fn
    _external_flags[name] = external


async def run_checks() -> ReadinessResponse:
    """등록된 모든 check 함수를 실행하고 종합 결과를 반환합니다."""
    if not _health_checks:
        return ReadinessResponse(status="ok", components={})

    results: dict[str, ComponentStatus] = {}
    for name, fn in _health_checks.items():
        start = time.perf_counter()
        external = _external_flags.get(name, False)
        try:
            result = await fn()
            result.latency_ms = round((time.perf_counter() - start) * 1000, 2)
            result.external = external
            results[name] = result
        except Exception as e:
            results[name] = ComponentStatus(
                status="error",
                message=str(e),
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
                external=external,
            )

    overall: Literal["ok", "error"] = (
        "error" if any(v.status == "error" for v in results.values()) else "ok"
    )
    return ReadinessResponse(status=overall, components=results)
