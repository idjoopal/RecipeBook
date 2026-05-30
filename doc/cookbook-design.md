# cookbook MCP 설계서

> 복잡한 질의 앞에서 LLM이 **가장 먼저 펼쳐보는 색인**.
> Skill 카탈로그 · Tool Manual · Workflow Recipe를 하나의 진입점으로 제공.

---

## 1. 철학

cookbook은 세 가지 책임을 진다.

1. **Skill 카탈로그** — `skills.md`를 활용할 수 없는 환경에서 도메인 스킬의 대체 진입점.
2. **Tool Manual** — 동일 MCP 서버에 등록된 다른 도구들의 **상세 사용설명서**. 다른 도구들은 짧은 description만 갖고, 상세 사용법은 cookbook에서 찾는다.
3. **Workflow Recipe** — 복잡한 질의에 대해 어떤 도구를 어떤 순서로, 어떤 결과를 어떻게 연결할지 가이드.

**핵심 원리: 선택용 vs 실행용 분리**

| 위치 | 역할 | 비용 |
|---|---|---|
| 도구의 짧은 description | **선택** — 이 도구를 부를지 판단 | 매 턴 노출 |
| cookbook 매뉴얼 | **실행** — 어떻게 잘 부를지 판단 | 호출 시에만 |

UNIX의 `--help` vs `man` 분할과 같다.

---

## 2. API 표면

검색 + 조회 분리 (search + get).

```python
cookbook_search(
    query: str,
    kind: Optional[Literal["skill", "workflow", "tool_manual"]] = None,
    tags: Optional[list[str]] = None,
    top_k: int = 5,
) -> list[SearchResult]
# 메타데이터만 반환: {id, kind, title, summary, tags, score}

cookbook_get(id: str) -> Recipe
# 본문 + kind별 확장 필드 + 자율호출 메타필드 (chain_with, next_steps 등)
```

---

## 3. Schema

### 3.1 공통 코어 필드

모든 kind에 공통.

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | str | 안정적 식별자. 네임스페이스 접두 사용: `skill.nl2sql_disambig`, `wf.report_pipeline`, `tool_manual.nl2chart` |
| `kind` | enum | `skill` / `workflow` / `tool_manual` |
| `title` | str | 사람이 읽는 짧은 제목 |
| `tags` | list[str] | 검색 필터링용 키워드 |
| `summary` | str | 1~2줄 요약 (search 결과에 노출) |
| `body` | str (md) | 자연어 본문 |
| `related_ids` | list[str] | 교차 참조 |
| **`trigger_patterns`** | list[str] | **이 항목이 호출되어야 할 상황의 self-declare**. 예: `["multi-step query", "chart generation request"]` |

### 3.2 kind별 확장 필드

#### `skill`
| 필드 | 설명 |
|---|---|
| `prerequisites` | 선행 조건 (e.g. 필요한 권한, 사전 데이터) |
| `when_to_use` | 적용 상황 자연어 설명 |

#### `workflow` — 자연어 + 구조화 step 병기
| 필드 | 설명 |
|---|---|
| `trigger_patterns` | 발동 조건 패턴 |
| `steps[]` | 구조화 step 배열 |

`steps[]` 각 원소:
```yaml
- tool: nl2sql
  input_hint: "사용자 질의를 그대로 전달. domain 파라미터 명시 권장"
  output_use: "validated SQL과 결과 DataFrame을 다음 step의 input으로"
  next_steps: ["tool_manual.nl2chart", "wf.report_format"]
```

#### `tool_manual`
| 필드 | 설명 |
|---|---|
| `tool_name` | 매핑되는 도구 이름 |
| `params[]` | `{name, semantics, valid_range, gotcha}` |
| `examples[]` | 호출 예시 2~3개 |
| `output_format` | 반환 구조 + 파싱법 |
| **`chain_with`** | 자주 함께 쓰이는 도구·워크플로우 id |

---

## 4. 콘텐츠 소스 (Auto-discover + Static 혼합)

### 4.1 디렉토리 구조

```
cookbook/
├── skills/
│   ├── nl2sql_disambig.md
│   ├── financial_terms.md
│   └── ...
├── workflows/
│   ├── report_pipeline.md
│   ├── data_to_chart.md
│   └── ...
└── tool_manuals/                  # per-tool 확장 파일
    ├── nl2sql.md                  # auto-discover 골격에 보강 내용 머지
    ├── nl2chart.md
    └── ...
```

### 4.2 작동 방식

1. **부팅 시 Auto-discover**: 동일 MCP 서버에 등록된 모든 도구를 introspection으로 수집 → `name` / `description` / `input_schema`로 `tool_manual` 골격 자동 생성.
2. **Static 머지**: `tool_manuals/{tool_name}.md`가 존재하면 골격에 머지. 보강 가능한 항목: `examples`, `gotcha`, `chain_with`, `output_format` 등.
3. **Hot reload**: 파일 변경 감지 시 인덱스 재구축.

### 4.3 콘텐츠 파일 포맷 (YAML front matter + markdown)

```markdown
---
id: tool_manual.nl2sql
kind: tool_manual
title: NL2SQL — 자연어 → SQL 생성 도구
tool_name: nl2sql
tags: [sql, nl2sql, query, database]
trigger_patterns:
  - "자연어 데이터 조회 질의"
  - "SQL 작성 요청"
chain_with:
  - tool_manual.nl2chart
  - wf.report_pipeline
summary: |
  도메인 패키지 기반 hybrid RAG로 자연어 질의를 검증된 SQL로 변환.
---

## 파라미터 상세

### `query` (str, required)
사용자 질의 원문...

### `domain` (str, required)
...

## 예시

### 예시 1: 단순 조회
...

## 출력 구조
...

## 함정
...
```

---

## 5. 검색 알고리즘 — 태그 필터 → BM25 2단

```
1. kind/tags 필터로 후보 좁힘 (옵셔널)
2. rank_bm25로 (title + tags + summary + body) 토큰화 → 랭킹
3. top_k 메타데이터만 반환
```

**의존성**: `rank_bm25`만. OpenSearch 미사용.
**한국어 토크나이저**: `kiwipiepy` 또는 단순 whitespace+lowercase.

---

## 6. Description 비중 정책 — 선택충분형 (B형)

도구 작성자가 짧은 description에 담아야 할 것 vs cookbook 매뉴얼에 담아야 할 것.

| 콘텐츠 | 짧은 description (~150 token) | cookbook 매뉴얼 |
|---|:---:|:---:|
| 목적 1줄 + 트리거 조건 | ✅ | |
| input_schema (필드명/타입) | ✅ auto | |
| canonical 예시 1개 | ✅ | |
| 파라미터 상세 의미·valid range·함정 | | ✅ |
| 호출 예시 2~3개 | | ✅ |
| 출력 구조·파싱법 | | ✅ |
| 관련 workflow / chain_with | | ✅ |
| Rate limit·성능 노트 | | ✅ |

---

## 7. 자율 호출 메커니즘 — 3-Layer

사용자가 명시하지 않아도 cookbook이 자동으로 활용되도록 하는 3겹 구조.

```
[사용자 질의]
   │
   ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 1: cookbook_search description에 박힌 카탈로그    │
│   - 전체 항목의 (kind, id, title, summary) 노출         │
│   - LLM이 search 없이도 어떤 recipe가 있는지 인지       │
│   - 곧바로 cookbook_get(id=...) 호출 가능               │
└─────────────────────────────────────────────────────────┘
   │
   ▼ (도구 호출 직전)
┌─────────────────────────────────────────────────────────┐
│ Layer 2: 복잡/비싼/부작용 도구의 description 강제 referral │
│   "You MUST consult cookbook_get(id='tool_manual.X')    │
│    before calling this tool"                            │
│   - 호출 직전 자동 매뉴얼 fetch                         │
└─────────────────────────────────────────────────────────┘
   │
   ▼ (도구 결과 직후)
┌─────────────────────────────────────────────────────────┐
│ Layer 3: cookbook_get 응답의 chain_with / next_steps    │
│   - 도구 결과 + 매뉴얼의 chaining 힌트                  │
│   - LLM이 다음 호출 후보를 자동 인식                    │
└─────────────────────────────────────────────────────────┘
```

**핵심 통찰**

- Layer 1은 매 턴 ~1500 token 부담이 있지만 search 호출 1회를 절약.
- Layer 2가 가장 강력하다 — LLM 자발성에 의존하지 않고 도구 description에 강제 명시.
- Layer 3은 chain된 도구 호출의 자연스러운 유도.

---

## 8. 동료 도구 Referral 차등 정책

도구 난이도 (D/O/M 3차원) 합산값에 따라 referral 강도 차등.

| D+O+M 합 | referral 강도 | description 말미 문구 |
|---|---|---|
| 0~2 | 없음 / soft | (생략) 또는 *"If unsure, consult cookbook"* |
| 3~4 | recommended | *"For detailed usage, see cookbook_get('tool_manual.X')"* |
| 5~9 | **MUST** | *"You MUST consult cookbook_get('tool_manual.X') before calling this tool"* |

**기준 요약**
- **D (Domain dependency)**: 도메인 패키지·규칙 의존도
- **O (Orchestration complexity)**: 다단계 / 체이닝 복잡도
- **M (Model performance dependency)**: 고성능 LLM 요구도

NL2SQL · NL2Chart · Business Strategy Agent 같은 핵심 에이전트는 자연히 MUST 등급.
단순 echo · ping류는 무표시.

---

## 9. cookbook_search description 초안

### 9.1 정적 안내 섹션
```
Search the cookbook: a library of skills, workflows, and detailed tool manuals
for this MCP server. Call this whenever you face:
- A complex multi-step query (find a workflow recipe)
- An unfamiliar tool in this server (find its manual)
- A domain skill not preloaded as skills.md

Returns metadata only; follow up with cookbook_get(id) for full body.
```

### 9.2 카탈로그 섹션 (Layer 1)

부팅 시 자동 생성. 모든 항목의 한 줄 인덱스를 description에 직접 append.

```
== Available recipes ==

[skill]
  skill.nl2sql_disambig — 모호한 질의를 명확하게 다시 묻는 절차
  skill.financial_terms — 재무 용어 사전 (EBITDA, FCF, ...)
  ...

[workflow]
  wf.report_pipeline — NL질의 → SQL → Chart → 보고서 생성 풀파이프
  wf.data_to_chart — 데이터 조회 후 시각화까지의 표준 흐름
  ...

[tool_manual]
  tool_manual.nl2sql — 자연어 → SQL 생성 도구 매뉴얼
  tool_manual.nl2chart — 자연어 → 차트 생성 도구 매뉴얼
  ...
```

토큰 예산: 항목 50개 × 한 줄 30 token ≈ **1500 token**.

---

## 10. 결정 이력

| Q | 주제 | 결정 |
|---|---|---|
| Q1 | API 표면 | search + get 분리 |
| Q2 | 검색 모델 | in-memory (OpenSearch 미사용) |
| Q3 | 콘텐츠 소스 | Auto-discover + Static 혼합 |
| Q4 | 검색 알고리즘 | 태그 필터 → BM25 2단 |
| Q5 | Workflow 표현 | 자연어 + 구조화 step 병기 |
| Q6-pre | 짧은 설명 비중 | B (선택충분형, 100~150 token) |
| Q6 | Tool Manual 구성 | Auto-discover + per-tool 확장 파일 |
| Q7 | Tool 이름 | cookbook |
| Q8 | Schema 필드 | 공통 코어 + kind별 옵셔널 확장 |
| Q9 | search 응답 포맷 | 메타데이터만 |
| Q10 | 카탈로그 노출 전략 | cookbook_search description에 전체 카탈로그 박기 |
| Q11 | 동료 도구 referral 강도 | D/O/M 난이도별 차등 |

---

## 11. 다음 단계 후보

- [ ] Python prototype — `cookbook_search` / `cookbook_get` + BM25 + auto-discover 스켈레톤
- [ ] 샘플 콘텐츠 세트 — NL2SQL tool_manual + wf.report_pipeline + skill 예시
- [ ] cookbook 자체 SKILL.md 작성 (이 설계서를 운영용 가이드로 압축)
- [ ] 동료 도구 description 템플릿 (D/O/M 등급별)
