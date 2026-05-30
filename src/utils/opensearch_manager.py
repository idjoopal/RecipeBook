"""
OpenSearch Manager

NL2SQL 지식 인덱스(pb_table, pb_column, pb_query_sql_pairs, pb_business_terms,
pb_metric_formulas, pb_reference_knowledge)에 대한 BM25 + kNN 하이브리드 검색을
제공합니다. 결과는 RRF(Reciprocal Rank Fusion)로 병합합니다.

임베딩(텍스트 → 벡터 변환)은 본 매니저 내부에서 수행합니다. 생성자에 embedding_*
인자를 전달하면 search_hybrid 호출 시 query_text를 자동으로 벡터화합니다 (OpenAI /
Cohere 지원).

검색 모드:
    1) 클라이언트 측 임베딩 (기본):
       embedding_provider/model/api_key를 생성자에 주입하면 자동 처리.
       호출 시 query_vector를 직접 넘기면 임베딩 단계 우회.
    2) 서버 측 임베딩 (Neural Search):
       OpenSearch ML Commons + Ingest pipeline이 사전 구성된 환경에서
       search_hybrid_neural()로 model_id만 넘기면 됨. 임베딩 설정 불필요.

사용법:
    manager = OpenSearchManager(
        host="localhost", port=9200,
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        embedding_api_key="sk-...",
    )
    await manager.connect()
    hits = await manager.search_hybrid("pb_table", "월별 매출 조회", top_k=5)
    await manager.disconnect()
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.utils.logger import get_logger

logger = get_logger("opensearch_manager")


class OpenSearchManager:
    """OpenSearch 연결 + 하이브리드 검색 + 임베딩 매니저"""

    DEFAULT_TEXT_FIELD = "content"
    DEFAULT_VECTOR_FIELD = "vector"
    DEFAULT_RRF_K = 60
    SUPPORTED_EMBEDDING_PROVIDERS = ("openai", "cohere")

    def __init__(
        self,
        host: str,
        port: int,
        use_ssl: bool = False,
        verify_certs: bool = False,
        user: str = "",
        password: str = "",
        embedding_provider: str = "",
        embedding_model: str = "",
        embedding_api_key: str = "",
        embedding_base_url: str = "",
    ):
        """
        Args:
            host: OpenSearch 호스트
            port: OpenSearch 포트
            use_ssl: HTTPS 사용 여부
            verify_certs: 인증서 검증 여부 (자체 서명 시 False)
            user: basic auth 사용자 (선택)
            password: basic auth 비밀번호 (선택)
            embedding_provider: 임베딩 백엔드 ("openai" | "cohere"). 빈 문자열이면 임베딩 비활성.
            embedding_model: 임베딩 모델 ID (예: "text-embedding-3-small", "embed-multilingual-v3.0")
            embedding_api_key: 임베딩 API 키
            embedding_base_url: 임베딩 API base URL (선택)
        """
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

        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.verify_certs = verify_certs
        self.user = user
        self.password = password

        self.embedding_provider = (embedding_provider or "").strip().lower()
        self.embedding_model = (embedding_model or "").strip()
        self.embedding_api_key = embedding_api_key or ""
        self.embedding_base_url = (embedding_base_url or "").strip()

        if self.embedding_provider and self.embedding_provider not in self.SUPPORTED_EMBEDDING_PROVIDERS:
            raise ValueError(
                f"지원하지 않는 임베딩 provider: {self.embedding_provider}. "
                f"지원 목록: {self.SUPPORTED_EMBEDDING_PROVIDERS}"
            )

        self._client = None              # AsyncOpenSearch
        self._embedding_client: Any = None

    @property
    def connected(self) -> bool:
        """OpenSearch 연결 상태"""
        return self._client is not None

    # ──────────────────────────────────────────────
    # 연결 / 해제
    # ──────────────────────────────────────────────
    async def connect(self) -> None:
        """OpenSearch에 연결합니다."""
        if self.connected:
            logger.info("[OS] 이미 연결되어 있습니다.")
            return

        from opensearchpy import AsyncOpenSearch

        logger.info(
            f"[OS] OpenSearch 연결 시작 — {self.host}:{self.port} (ssl={self.use_ssl})"
        )

        http_auth = (self.user, self.password) if self.user else None
        self._client = AsyncOpenSearch(
            hosts=[{"host": self.host, "port": self.port}],
            http_auth=http_auth,
            use_ssl=self.use_ssl,
            verify_certs=self.verify_certs,
            ssl_show_warn=False,
        )

        info = await self._client.info()
        version = info.get("version", {}).get("number", "?")
        logger.info(f"[OS] 연결 완료 (cluster_version={version})")

    async def disconnect(self) -> None:
        """OpenSearch 및 임베딩 클라이언트 연결을 종료합니다."""
        if self.connected:
            logger.info("[OS] 연결 종료")
            await self._client.close()
            self._client = None

        if self._embedding_client is not None:
            close_coro = getattr(self._embedding_client, "close", None)
            if callable(close_coro):
                try:
                    result = close_coro()
                    if hasattr(result, "__await__"):
                        await result
                except Exception:
                    logger.exception("[OS] 임베딩 클라이언트 종료 중 오류")
            self._embedding_client = None

    # ──────────────────────────────────────────────
    # 임베딩 (텍스트 → 벡터)
    # ──────────────────────────────────────────────
    @property
    def embedding_enabled(self) -> bool:
        """임베딩 사용 가능 여부 (provider/model/api_key 모두 설정됨).

        api_key가 비어있으면 _initialize_embedding_client에서 RuntimeError가 나서
        하이브리드 검색이 통째로 실패하므로, 여기서 미리 비활성으로 판정해 BM25-only로
        흘러가도록 한다.
        """
        return (
            bool(self.embedding_provider)
            and bool(self.embedding_model)
            and bool(self.embedding_api_key)
        )

    async def embed(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환합니다.

        Returns:
            임베딩 벡터 (List[float])

        Raises:
            RuntimeError: 임베딩 설정이 없거나 클라이언트 초기화 실패
        """
        if not self.embedding_enabled:
            raise RuntimeError(
                "임베딩이 비활성화되어 있습니다. 생성자에 embedding_provider/model을 지정하세요."
            )

        if self._embedding_client is None:
            await self._initialize_embedding_client()

        if self.embedding_provider == "openai":
            return await self._embed_openai(text)
        elif self.embedding_provider == "cohere":
            return await self._embed_cohere(text)
        raise ValueError(f"지원하지 않는 임베딩 provider: {self.embedding_provider}")

    async def _initialize_embedding_client(self) -> None:
        """임베딩 클라이언트를 lazy 초기화합니다."""
        if not self.embedding_api_key:
            raise RuntimeError(
                f"임베딩 API 키가 설정되지 않았습니다 (provider={self.embedding_provider})."
            )

        logger.info(
            "[OS] 임베딩 클라이언트 초기화 (provider=%s, model=%s)",
            self.embedding_provider, self.embedding_model,
        )

        if self.embedding_provider == "openai":
            from openai import AsyncOpenAI
            self._embedding_client = AsyncOpenAI(
                api_key=self.embedding_api_key,
                base_url=self.embedding_base_url or None,
            )
        elif self.embedding_provider == "cohere":
            import cohere
            self._embedding_client = cohere.AsyncClientV2(
                api_key=self.embedding_api_key,
                base_url=self.embedding_base_url or None,
            )

    async def _embed_openai(self, text: str) -> List[float]:
        response = await self._embedding_client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return list(response.data[0].embedding)

    async def _embed_cohere(self, text: str) -> List[float]:
        # Cohere v3 embed: 검색 질의용은 input_type="search_query"
        response = await self._embedding_client.embed(
            texts=[text],
            model=self.embedding_model,
            input_type="search_query",
            embedding_types=["float"],
        )
        return list(response.embeddings.float[0])

    # ──────────────────────────────────────────────
    # BM25 검색
    # ──────────────────────────────────────────────
    async def search_bm25(
        self,
        index: str,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        text_field: str = DEFAULT_TEXT_FIELD,
        source: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """BM25(text) 매칭 검색."""
        body: Dict[str, Any] = {
            "size": top_k,
            "query": self._build_bool_query(
                must=[{"match": {text_field: query_text}}],
                filter_=self._filters_to_clauses(filters),
            ),
        }
        if source is not None:
            body["_source"] = source
        return await self._search(index, body)

    # ──────────────────────────────────────────────
    # kNN 검색 (사전 임베딩된 vector 사용)
    # ──────────────────────────────────────────────
    async def search_knn(
        self,
        index: str,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        vector_field: str = DEFAULT_VECTOR_FIELD,
        source: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """kNN(dense_vector) 검색 — 호출자가 사전 임베딩한 vector 사용."""
        knn_body: Dict[str, Any] = {
            "vector": query_vector,
            "k": top_k,
        }
        filter_clauses = self._filters_to_clauses(filters)
        if filter_clauses:
            # OpenSearch knn은 단일 filter 구조를 요구
            knn_body["filter"] = self._build_bool_query(filter_=filter_clauses)

        body: Dict[str, Any] = {
            "size": top_k,
            "query": {"knn": {vector_field: knn_body}},
        }
        if source is not None:
            body["_source"] = source
        return await self._search(index, body)

    # ──────────────────────────────────────────────
    # 하이브리드 (BM25 + kNN, RRF 병합)
    # ──────────────────────────────────────────────
    async def search_hybrid(
        self,
        index: str,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        query_vector: Optional[List[float]] = None,
        rrf_k: int = DEFAULT_RRF_K,
        candidate_size: Optional[int] = None,
        text_field: str = DEFAULT_TEXT_FIELD,
        vector_field: str = DEFAULT_VECTOR_FIELD,
        source: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """BM25 + kNN 결과를 RRF로 병합한 하이브리드 검색.

        query_vector가 None이면 내부 self.embed()로 query_text를 벡터화한다.
        임베딩이 비활성이면 BM25-only로 fallback (경고 로그).
        """
        if query_vector is None and self.embedding_enabled:
            query_vector = await self.embed(query_text)

        candidate_size = candidate_size or max(top_k * 4, 50)

        bm25_hits = await self.search_bm25(
            index, query_text,
            top_k=candidate_size, filters=filters,
            text_field=text_field, source=source,
        )

        if query_vector is None:
            logger.warning(
                "[OS] 임베딩 비활성/query_vector 없음 — BM25-only fallback (index=%s)", index
            )
            return bm25_hits[:top_k]

        knn_hits = await self.search_knn(
            index, query_vector,
            top_k=candidate_size, filters=filters,
            vector_field=vector_field, source=source,
        )

        merged = self._rrf_merge([bm25_hits, knn_hits], k=rrf_k)
        return merged[:top_k]

    # ──────────────────────────────────────────────
    # 하이브리드 (BM25 + Neural Search, RRF 병합)
    # ──────────────────────────────────────────────
    async def search_hybrid_neural(
        self,
        index: str,
        query_text: str,
        model_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        rrf_k: int = DEFAULT_RRF_K,
        candidate_size: Optional[int] = None,
        text_field: str = DEFAULT_TEXT_FIELD,
        vector_field: str = DEFAULT_VECTOR_FIELD,
        source: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """OpenSearch Neural Search(ML Commons)을 사용한 하이브리드 검색.

        클라이언트 임베딩 없이 model_id만으로 동작. 사전에 OpenSearch 측에 모델 배포 +
        ingest pipeline 구성이 되어 있어야 한다.
        """
        candidate_size = candidate_size or max(top_k * 4, 50)

        bm25_hits = await self.search_bm25(
            index, query_text,
            top_k=candidate_size, filters=filters,
            text_field=text_field, source=source,
        )

        neural_body: Dict[str, Any] = {
            "size": candidate_size,
            "query": self._build_bool_query(
                must=[{
                    "neural": {
                        vector_field: {
                            "query_text": query_text,
                            "model_id": model_id,
                            "k": candidate_size,
                        }
                    }
                }],
                filter_=self._filters_to_clauses(filters),
            ),
        }
        if source is not None:
            neural_body["_source"] = source
        neural_hits = await self._search(index, neural_body)

        merged = self._rrf_merge([bm25_hits, neural_hits], k=rrf_k)
        return merged[:top_k]

    # ──────────────────────────────────────────────
    # 문서 조회/수정 (지식 워크스페이스용 — pb_* 인덱스 큐레이션)
    # ──────────────────────────────────────────────
    async def count_docs(self, index: str) -> int:
        """인덱스 문서 수. 인덱스 없거나 오류 시 -1."""
        if not self.connected:
            raise ConnectionError("OpenSearch에 연결되어 있지 않습니다.")
        try:
            resp = await self._client.count(index=index)
            return int(resp.get("count", 0))
        except Exception as e:
            logger.debug("[OS] count 실패 (index=%s): %s", index, e)
            return -1

    async def list_docs(
        self,
        index: str,
        from_: int = 0,
        size: int = 50,
        query_text: Optional[str] = None,
        exclude_vector: bool = True,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """인덱스 문서를 페이징 조회. (docs, total) 반환. vector 필드는 기본 제외."""
        if not self.connected:
            raise ConnectionError("OpenSearch에 연결되어 있지 않습니다.")
        query = (
            {"match": {self.DEFAULT_TEXT_FIELD: query_text}}
            if query_text else {"match_all": {}}
        )
        body: Dict[str, Any] = {
            "from": from_,
            "size": size,
            "track_total_hits": True,
            "query": query,
        }
        if exclude_vector:
            body["_source"] = {"excludes": [self.DEFAULT_VECTOR_FIELD]}
        response = await self._client.search(index=index, body=body)
        hits = response.get("hits", {})
        docs = [
            {**(h.get("_source") or {}), "_id": h.get("_id")}
            for h in hits.get("hits", [])
        ]
        total = hits.get("total", {})
        total_n = total.get("value", 0) if isinstance(total, dict) else int(total or 0)
        return docs, total_n

    async def get_doc(
        self, index: str, doc_id: str, exclude_vector: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """단일 문서 조회. 없으면 None. vector 기본 제외."""
        if not self.connected:
            raise ConnectionError("OpenSearch에 연결되어 있지 않습니다.")
        try:
            params = {"_source_excludes": self.DEFAULT_VECTOR_FIELD} if exclude_vector else {}
            resp = await self._client.get(index=index, id=doc_id, params=params)
        except Exception as e:
            logger.debug("[OS] get_doc 실패 (index=%s id=%s): %s", index, doc_id, e)
            return None
        if not resp.get("found"):
            return None
        return {**(resp.get("_source") or {}), "_id": resp.get("_id")}

    async def index_doc(
        self, index: str, doc_id: str, body: Dict[str, Any], refresh: bool = True,
    ) -> None:
        """문서 업서트(기존 _id 덮어쓰기). body는 _id를 포함하지 않은 _source."""
        if not self.connected:
            raise ConnectionError("OpenSearch에 연결되어 있지 않습니다.")
        await self._client.index(index=index, id=doc_id, body=body, refresh=refresh)
        logger.info("[OS] index_doc 완료 (index=%s id=%s)", index, doc_id)

    # ──────────────────────────────────────────────
    # 내부 헬퍼
    # ──────────────────────────────────────────────
    async def get_vector_field_dim(
        self, index: str, vector_field: str = DEFAULT_VECTOR_FIELD,
    ) -> Optional[int]:
        """인덱스 매핑에서 knn_vector 필드의 차원(dimension)을 반환합니다.

        인덱스가 없거나 필드 미존재 시 None 반환.
        """
        if not self.connected:
            return None
        try:
            mapping = await self._client.indices.get_mapping(index=index)
            props = (
                mapping.get(index, {})
                .get("mappings", {})
                .get("properties", {})
            )
            dim = props.get(vector_field, {}).get("dimension")
            return int(dim) if dim is not None else None
        except Exception as e:
            logger.debug("[OS] 인덱스 매핑 조회 실패 (index=%s): %s", index, e)
            return None

    async def _search(self, index: str, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """저수준 _search 호출 + hits 평탄화."""
        if not self.connected:
            raise ConnectionError(
                "OpenSearch에 연결되어 있지 않습니다. connect()를 먼저 호출하세요."
            )

        logger.debug("[OS] _search index=%s body=%s", index, body)
        response = await self._client.search(index=index, body=body)
        hits = response.get("hits", {}).get("hits", [])
        logger.info("[OS] index=%s hits=%d", index, len(hits))

        return [
            {
                **(hit.get("_source") or {}),
                "_id": hit.get("_id"),
                "_score": hit.get("_score"),
            }
            for hit in hits
        ]

    @staticmethod
    def _filters_to_clauses(
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """필터 dict를 OpenSearch bool.filter 절 리스트로 변환.

        - 단일 값  → term 쿼리
        - 리스트  → terms 쿼리
        예:
            {"table_name": ["sales", "orders"]} → [{"terms": {"table_name": [...]}}]
            {"knowledge_type": "조직정보"}     → [{"term":  {"knowledge_type": "조직정보"}}]
        """
        if not filters:
            return []
        clauses: List[Dict[str, Any]] = []
        for key, value in filters.items():
            if isinstance(value, (list, tuple, set)):
                clauses.append({"terms": {key: list(value)}})
            else:
                clauses.append({"term": {key: value}})
        return clauses

    @staticmethod
    def _build_bool_query(
        must: Optional[List[Dict[str, Any]]] = None,
        should: Optional[List[Dict[str, Any]]] = None,
        filter_: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """bool 쿼리 dict 구성. 모든 절이 비어있으면 match_all."""
        bool_q: Dict[str, Any] = {}
        if must:
            bool_q["must"] = must
        if should:
            bool_q["should"] = should
        if filter_:
            bool_q["filter"] = filter_
        return {"bool": bool_q} if bool_q else {"match_all": {}}

    @staticmethod
    def _rrf_merge(
        result_lists: Sequence[List[Dict[str, Any]]],
        k: int = DEFAULT_RRF_K,
    ) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion으로 여러 검색 결과를 병합.

        score(doc) = Σ_i  1 / (k + rank_i(doc))   (rank는 1부터)
        결과는 _rrf_score 내림차순 정렬.
        """
        scores: Dict[str, float] = {}
        docs: Dict[str, Dict[str, Any]] = {}

        for hits in result_lists:
            for rank0, hit in enumerate(hits):
                doc_id = hit.get("_id")
                if doc_id is None:
                    continue
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank0 + 1)
                if doc_id not in docs:
                    docs[doc_id] = hit

        merged: List[Dict[str, Any]] = []
        for doc_id, score in scores.items():
            doc = dict(docs[doc_id])
            doc["_rrf_score"] = score
            merged.append(doc)
        merged.sort(key=lambda d: d["_rrf_score"], reverse=True)
        return merged
