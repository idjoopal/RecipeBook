"""OpenSearch 클라이언트 — 범용 벡터 인프라.

AsyncOpenSearch 래퍼. knn 인덱스 관리 + upsert + knn_search.
SQL_EXPLORER_OS_ENABLED=false이면 connect()가 no-op으로 동작한다.
"""
from __future__ import annotations

from typing import Any

from src.utils.logger import get_logger

logger = get_logger("opensearch_client")


class OpenSearchClient:
    """AsyncOpenSearch 래퍼 — knn 인덱스 upsert/search."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9200,
        user: str = "",
        password: str = "",
        use_ssl: bool = False,
    ) -> None:
        # host 정규화: 스킴(http/https)이 포함되어 있으면 분리하고 use_ssl을 자동 보정.
        # opensearch-py의 AsyncOpenSearch는 host에 스킴을 받지 않으므로 미리 제거 필요.
        host = (host or "").strip()
        if host.startswith("https://"):
            host = host[len("https://"):]
            use_ssl = True
        elif host.startswith("http://"):
            host = host[len("http://"):]
            use_ssl = False
        host = host.rstrip("/")

        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._use_ssl = use_ssl
        self._client = None
        self._connected = False

    async def connect(self) -> None:
        from opensearchpy import AsyncOpenSearch

        kwargs: dict[str, Any] = {
            "hosts": [{"host": self._host, "port": self._port}],
            "use_ssl": self._use_ssl,
            "verify_certs": False,
            "ssl_show_warn": False,
        }
        if self._user and self._password:
            kwargs["http_auth"] = (self._user, self._password)

        self._client = AsyncOpenSearch(**kwargs)
        # 연결 확인
        await self._client.info()
        self._connected = True
        logger.info("[OpenSearch] 연결 완료: %s:%d", self._host, self._port)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def ensure_index(self, index_name: str, dims: int) -> None:
        """knn 인덱스가 없으면 생성한다."""
        if not self._client:
            raise RuntimeError("OpenSearch에 연결되어 있지 않습니다.")
        exists = await self._client.indices.exists(index=index_name)
        if exists:
            return
        body = {
            "settings": {"index.knn": True},
            "mappings": {
                "properties": {
                    "doc_id": {"type": "keyword"},
                    "subject": {"type": "keyword"},
                    "content": {"type": "text"},
                    "provenance": {"type": "keyword"},
                    "confidence": {"type": "float"},
                    "vector": {"type": "knn_vector", "dimension": dims},
                    "expires_at": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                    "schema_version": {"type": "keyword"},
                }
            },
        }
        await self._client.indices.create(index=index_name, body=body)
        logger.info("[OpenSearch] 인덱스 생성: %s (dims=%d)", index_name, dims)

    async def upsert(self, index_name: str, doc_id: str, vector: list[float], metadata: dict) -> None:
        """문서를 upsert한다."""
        if not self._client:
            raise RuntimeError("OpenSearch에 연결되어 있지 않습니다.")
        doc = {"doc_id": doc_id, "vector": vector, **metadata}
        await self._client.index(index=index_name, id=doc_id, body=doc)

    async def knn_search(
        self,
        index_name: str,
        vector: list[float],
        k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict]:
        """knn 검색. score >= min_score인 결과만 반환한다."""
        if not self._client:
            raise RuntimeError("OpenSearch에 연결되어 있지 않습니다.")
        body = {
            "size": k,
            "query": {"knn": {"vector": {"vector": vector, "k": k}}},
        }
        resp = await self._client.search(index=index_name, body=body)
        hits = resp.get("hits", {}).get("hits", [])
        return [
            {"score": h["_score"], "id": h["_id"], **h["_source"]}
            for h in hits
            if h["_score"] >= min_score
        ]

    async def health(self) -> dict:
        if not self._client:
            return {"status": "error", "message": "OpenSearch 미연결"}
        try:
            info = await self._client.cluster.health()
            status = info.get("status", "unknown")
            return {"status": "ok" if status in ("green", "yellow") else "error", "cluster_status": status}
        except Exception as e:
            return {"status": "error", "message": str(e)}
