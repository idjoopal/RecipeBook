# SQL Explorer 배포 및 운영 가이드

실제 환경에 코드를 클론해서 적용할 때 참고하는 문서.

---

## 1. 전제 조건

| 항목 | 최소 버전 | 비고 |
|---|---|---|
| Python | 3.11+ | |
| uv | 최신 | 패키지 관리자 |
| PostgreSQL | 14+ | probe 대상 DB (read-only role 설정 필요) |
| LLM API | — | Cohere 또는 OpenAI |
| OpenSearch | 2.x (선택) | KB 임베딩 기반 벡터 검색 — 없으면 SQLite fallback |

---

## 2. 코드 클론 및 의존성 설치

```bash
git clone <repo-url>
cd SQLExplorer
uv sync
```

---

## 3. 환경변수 설정

### 3-1. 루트 `.env`

`.env.example`을 복사해서 수정한다.

```bash
cp .env.example .env
```

필수 항목:

```dotenv
APP_ENV=prod          # dev이면 uvicorn reload 활성화됨

# LLM — Cohere 경로
API_KEY=<cohere-api-key>
BASE_URL=<cohere-endpoint>
MODEL=command-r-plus

# LLM — OpenAI 경로 (openai:* 모델 또는 임베딩 사용 시)
OPENAI_API_KEY=<openai-api-key>
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# 임베딩 (Phase 4 KB 벡터 검색 사용 시)
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMS=1536
```

### 3-2. SQL Explorer 에이전트 전용 설정

```bash
cp src/agents/agent_env/sql_explorer.env.example \
   src/agents/agent_env/sql_explorer.env
```

항목별 설명:

```dotenv
# ── probe 대상 DB (read-only role 권장) ──────────────────────
SQL_EXPLORER_DB_TYPE=postgresql
SQL_EXPLORER_DB_HOST=<pg-host>
SQL_EXPLORER_DB_PORT=5432
SQL_EXPLORER_DB_NAME=<db-name>
SQL_EXPLORER_DB_USER=<read-only-user>
SQL_EXPLORER_DB_PASSWORD=<password>
SQL_EXPLORER_DIALECT=postgres        # postgres | mysql | sqlite

# ── 단계별 모델 라우팅 ────────────────────────────────────────
# 비워두면 루트 .env의 MODEL 기본값 사용
# OpenAI 모델은 "openai:gpt-4o" 형식으로 지정
SQL_EXPLORER_DRAFT_MODEL=openai:gpt-4o-mini
SQL_EXPLORER_HYPOTHESIZE_MODEL=openai:gpt-4o-mini
SQL_EXPLORER_UPDATE_MODEL=openai:gpt-4o-mini
SQL_EXPLORER_SYNTH_MODEL=openai:gpt-4o-mini
SQL_EXPLORER_CRITIC_MODEL=openai:gpt-4o

# ── 안전 / budget ────────────────────────────────────────────
SQL_EXPLORER_PROBE_BUDGET=8          # 쿼리당 최대 probe 횟수
SQL_EXPLORER_MAX_LLM_CALLS=30        # 쿼리당 최대 LLM 호출 횟수
SQL_EXPLORER_PROBE_TIMEOUT_S=5.0     # probe 쿼리 타임아웃 (초)
SQL_EXPLORER_PROBE_ROW_LIMIT=100     # probe 결과 최대 행 수
SQL_EXPLORER_CRITIC_MAX_ROUNDS=2     # critic 재시도 최대 횟수

# ── KB (audit/knowledge) 저장소 ──────────────────────────────
# probe DB와 반드시 분리! 별도 DB나 SQLite 경로 사용
SQL_EXPLORER_KB_BACKEND=sqlite       # sqlite | postgresql
SQL_EXPLORER_AUDIT_SQLITE_PATH=.sql_explorer/audit.db
# PostgreSQL KB 사용 시:
# SQL_EXPLORER_KB_BACKEND=postgresql
# SQL_EXPLORER_KB_DB_HOST=<kb-pg-host>
# SQL_EXPLORER_KB_DB_PORT=5432
# SQL_EXPLORER_KB_DB_NAME=sql_explorer_kb
# SQL_EXPLORER_KB_DB_USER=<kb-user>
# SQL_EXPLORER_KB_DB_PASSWORD=<kb-password>

# ── OpenSearch (임베딩 기반 KB, 선택) ────────────────────────
SQL_EXPLORER_OS_ENABLED=false        # true로 바꾸면 벡터 검색 활성화
SQL_EXPLORER_OS_HOST=localhost
SQL_EXPLORER_OS_PORT=9200
SQL_EXPLORER_OS_USER=
SQL_EXPLORER_OS_PASSWORD=
SQL_EXPLORER_OS_HYPO_INDEX=sql_explorer_hypothesis
SQL_EXPLORER_OS_PROFILE_INDEX=sql_explorer_profile

# ── KB TTL (§9.6) ────────────────────────────────────────────
SQL_EXPLORER_TTL_PROFILE_DAYS=7      # 스키마 프로파일 유효 기간
SQL_EXPLORER_TTL_HYPOTHESIS_DAYS=30  # 가설 캐시 유효 기간
SQL_EXPLORER_TTL_FACT_DAYS=90        # resolved fact 유효 기간
```

> **보안 주의**: `sql_explorer.env`는 `.gitignore`에 포함되어 있어 커밋되지 않는다. `.env.example` 파일만 커밋됨.

---

## 4. probe 대상 DB 설정

### 4-1. read-only role 생성 (PostgreSQL)

```sql
-- probe 전용 read-only 역할 생성
CREATE ROLE sql_explorer_reader LOGIN PASSWORD '<password>';
GRANT CONNECT ON DATABASE <db-name> TO sql_explorer_reader;
GRANT USAGE ON SCHEMA public TO sql_explorer_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sql_explorer_reader;
-- 향후 생성되는 테이블에도 자동 적용
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO sql_explorer_reader;
```

> **3중 안전장치**: sqlglot AST 파서 검증 + read-only role + `statement_timeout` — 단일 레이어에만 의존하지 않는다.

### 4-2. 개발/테스트용 시드 DB 적재

실제 DB가 없을 때 `doc/sql_explorer/seed.sql`로 테스트용 스키마를 만들 수 있다 (orders / stores / refunds 테이블).

```bash
createdb sql_explorer_dev
psql -U <user> -d sql_explorer_dev -f doc/sql_explorer/seed.sql
```

그 다음 `sql_explorer.env`의 DB 접속 정보를 이 dev DB로 지정한다.

---

## 5. SQLite 데이터 디렉터리 생성

audit DB와 knowledge DB는 SQLite 기본값으로 `.sql_explorer/` 에 저장된다.

```bash
mkdir -p .sql_explorer
```

---

## 6. 서버 실행

```bash
uv run python main.py
```

기본 포트는 `9101`. `SERVER_PORT` 환경변수로 변경 가능.

---

## 7. 동작 확인 체크리스트

### 7-1. Health check

```bash
curl http://localhost:9101/health/ready
# 기대값: {"status":"ok", ...}
# probe DB 미연결 시 sql_explorer_probe_db 항목이 "error"로 표시됨
```

### 7-2. 모니터링 UI

브라우저에서 접속:

```
http://localhost:9101/api/sql-explorer/monitor
```

질문을 입력하면:
- 워크플로우 노드가 Draft → Exploration → Synthesize → Critic 순서로 파란색 강조
- 완료된 노드는 초록색으로 전환
- 타임라인에 각 단계 이벤트(hypothesis, probe, update 등)가 실시간으로 쌓임
- 최종 SQL이 하단에 표시되고 복사 버튼 제공

### 7-3. API 직접 호출

```bash
# SQL 생성
curl -X POST http://localhost:9101/api/sql-explorer/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "지난달 매출 합계"}'

# 탐색 경로 포함 상세 결과
curl -X POST http://localhost:9101/api/sql-explorer/explain \
  -H "Content-Type: application/json" \
  -d '{"input": "지난달 매출 합계"}'
# → assumptions_before/after, probes_used, kb_hits, confidence_delta 확인

# 실행 없이 스펙만 확인 (DB 불필요)
curl -X POST http://localhost:9101/api/sql-explorer/dry-run \
  -H "Content-Type: application/json" \
  -d '{"input": "지난달 매출 합계"}'
```

### 7-4. KB 사전 적재 (선택)

information_schema와 컬럼 COMMENT를 KB에 미리 올려두면 첫 쿼리부터 probe 수가 줄어든다.

```bash
curl -X POST http://localhost:9101/api/sql-explorer/preload \
  -H "Content-Type: application/json" \
  -d '{"targets": ["system", "comments"]}'
# → {"count": N, "by_source": {...}, "kb_total": N}
```

glossary.yaml을 작성한 경우:

```bash
curl -X POST http://localhost:9101/api/sql-explorer/preload \
  -H "Content-Type: application/json" \
  -d '{"targets": ["system", "comments", "glossary"], "glossary_path": "doc/sql_explorer/glossary.yaml"}'
```

`doc/sql_explorer/glossary.yaml` 형식 참고:

```yaml
- term: 매출
  definition: orders 테이블의 amount 컬럼 합계. status='COMPLETED' 건만 집계.
- term: 활성 스토어
  definition: stores 테이블에서 closed_at IS NULL인 행.
```

### 7-5. KB 누적 효과 검증

동일 질문을 콜드 → 웜 순서로 2회 실행해 probe 감소를 측정한다.

```bash
# 내장 30개 픽스처 전체 실행
curl -X POST http://localhost:9101/api/sql-explorer/eval/compare
# 기대값: warm_run의 probes_used < cold_run의 probes_used
```

---

## 8. OpenSearch 활성화 (선택)

임베딩 기반 가설 유사도 검색을 사용하려면:

1. OpenSearch 2.x 클러스터 준비 (knn-search 플러그인 포함)
2. `sql_explorer.env` 수정:
   ```dotenv
   SQL_EXPLORER_OS_ENABLED=true
   SQL_EXPLORER_OS_HOST=<opensearch-host>
   SQL_EXPLORER_OS_PORT=9200
   SQL_EXPLORER_OS_USER=<user>
   SQL_EXPLORER_OS_PASSWORD=<password>
   ```
3. 루트 `.env`에 임베딩 설정 확인:
   ```dotenv
   OPENAI_API_KEY=<key>
   EMBEDDING_MODEL=text-embedding-3-small
   EMBEDDING_DIMS=1536
   ```
4. 서버 재시작 → `/health/ready`에 `sql_explorer_opensearch` 항목 추가됨

> OpenSearch 없이도 SQLite 텍스트 매칭 fallback으로 KB는 동작한다. 유사도 검색 품질만 낮아짐.

---

## 9. 향후 선택적 개선 (요청 시 구현)

| 항목 | 설명 |
|---|---|
| Monitor UI 다크 테마 | `prefers-color-scheme` 기반 테마 전환 |
| Monitor 이전 실행 기록 | localStorage에 최근 N개 결과 보관 |
| KB 관리 API | 특정 subject TTL 강제 만료, KB 항목 조회/삭제 |
| Multi-dialect 시드 | MySQL / SQLite용 seed.sql 추가 |
| Slack/웹훅 알림 | 쿼리 완료 시 결과 발송 |
| 인증 미들웨어 | Bearer token / API key로 엔드포인트 보호 |

---

## 10. 주요 파일 위치 참조

```
.env                                          # 루트 공통 설정 (API 키, LLM 엔드포인트)
src/agents/agent_env/sql_explorer.env         # SQL Explorer 전용 설정 (gitignore)
src/agents/agent_env/sql_explorer.env.example # 위 파일의 템플릿 (커밋됨)
doc/sql_explorer/seed.sql                     # 개발용 시드 DB (orders/stores/refunds)
doc/sql_explorer/glossary.yaml                # 비즈니스 용어 사전 (직접 작성)
frontend/src/agents/explore_internal_db/sql_explorer_monitor.html  # 모니터링 UI
.sql_explorer/audit.db                        # SQLite audit 로그 (런타임 생성)
.sql_explorer/knowledge.db                    # SQLite KB 저장소 (런타임 생성)
```
