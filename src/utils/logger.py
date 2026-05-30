"""
MCP Server Logger

stdout으로 JSON 형식의 로그를 출력하는 로거를 제공합니다.

APP_ENV=dev  → indent=2  (사람이 읽기 편한 멀티라인)
그 외 (운영)  → indent=None (로그 수집기 호환, 한 줄)
"""
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional


def _resolve_indent() -> Optional[int]:
    """APP_ENV 값에 따라 JSON indent를 결정합니다."""
    return 2 if os.getenv("APP_ENV", "dev").lower() == "dev" else None


class JsonFormatter(logging.Formatter):
    """로그를 JSON 형식으로 포맷팅하는 Formatter"""

    def __init__(self, indent: Optional[int] = None):
        super().__init__()
        self.indent = indent

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "levelno": record.levelno,
            "name": record.name,
            "message": record.getMessage(),
            "source": {
                "function": record.funcName,
                "line": record.lineno,
                "pathname": record.pathname,
            },
        }
        return json.dumps(log_data, ensure_ascii=False, indent=self.indent)


def get_logger(name: str = "mcp_server") -> logging.Logger:
    """
    stdout으로 JSON 형식의 로그를 출력하는 로거를 반환합니다.

    Example:
        >>> from src.utils.logger import get_logger
        >>> logger = get_logger("my_module")
        >>> logger.info("Hello, World!")
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(JsonFormatter(indent=_resolve_indent()))

    logger.addHandler(handler)

    return logger
