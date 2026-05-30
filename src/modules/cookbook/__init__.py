"""
Cookbook MCP Module

복잡한 질의 앞에서 LLM이 가장 먼저 펼쳐보는 색인.
Skill 카탈로그 · Tool Manual · Workflow Recipe 를 단일 진입점으로 제공.

설계서: doc/cookbook-design.md

외부 진입점은 ``service`` 모듈을 사용합니다.

>>> from src.modules.cookbook import service
>>> service.init(mcp, content_root=Path("cookbook"))
>>> await service.search(query="...", top_k=5)
>>> await service.get(id_="wf.report_pipeline")
"""

from . import service  # re-export 진입점

__all__ = ["service"]
