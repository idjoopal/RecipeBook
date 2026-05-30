# Agent Tool 작성 가이드

> **목적**: Prebuilt Agent 플랫폼에서 새 Agent / Component / Tool을 추가할 때, **System Prompt**와 **Tool Description**에 무엇을 어떻게 써야 하는지 정의하는 작성 가이드.
>
> **근거**: Anthropic Claude의 실제 system prompt와 tool description 패턴 분석 기반.
>
> **버전**: v1.0

---

## 0. TL;DR

- **Tool Description**은 도구 하나를 "단독으로 보고도" 호출 결정이 가능하도록 작성한다.
- **System Prompt**는 여러 도구가 관여하는 라우팅 결정과 에이전트 전체의 운영 원칙을 담는다.
- **Negative example**(쓰지 마라)은 1급 시민이다. 도구 description의 절반이 negative example로 채워지는 것이 정상.
- **Critical safety policy는 양쪽 모두에 명시**한다 (의도적 redundancy).
- Description은 schema와 정책을 **분리하지 않고 한 곳에 융합**한다.

---

## 1. 핵심 원칙: 책임 분리

| 영역 | 책임 범위 | 비유 | 갱신 빈도 |
|---|---|---|---|
| **Tool Description** | 단일 도구의 self-description | 도구 사용 설명서 | 도구 추가/변경 시 |
| **System Prompt** | 에이전트 전체 운영 원칙 | 사규 + 의사결정 매뉴얼 | Agent 정책 변경 시 |
| **양쪽 모두** | Critical safety, 강제 선행 행동 | 안전수칙 (반복 명시) | 보안 정책 변경 시 |

### Rule of thumb

```
이 정보가 단 하나의 도구에만 적용되는가?
  YES → Tool Description
  NO  → System Prompt

이 정보가 누락되면 사용자에게 실제 피해가 가는가?
  YES → 양쪽 모두 (redundant by design)
  NO  → 한쪽만
```

---

## 2. Tool Description 작성 가이드

### 2.1 필수 항목 (Required)

#### (a) Purpose Line — 한 줄 정의

도구가 무엇을 하는지 한 문장으로. **동사로 시작**하고, 결과형이 아닌 행위형으로 작성한다.

```
✅ Search the web for current information.
✅ Run a bash command in the container.
✅ Execute a parameterized SQL query against the data warehouse.

❌ Web search tool.                    (행위 명시 X)
❌ This tool helps you find things.    (모호함)
❌ Returns search results.             (입력이 아닌 출력 중심)
```

#### (b) Schema — 파라미터, 타입, 제약, 기본값

모든 파라미터에 대해:
- `name`, `type`, `required` 여부, `description`, `default`(있다면), `constraints`(범위/형식)
- Returns 형식과 예시

```yaml
parameters:
  query:
    type: string
    required: true
    description: "Natural language search query"
    constraints:
      max_length: 200
      no_special_chars: ["site:", "-", "\""]
  max_results:
    type: integer
    required: false
    default: 5
    constraints: {min: 1, max: 10}

returns:
  type: array
  shape: "{ title, url, snippet, published_at }[]"
  example: [{title: "...", url: "https://...", snippet: "..."}]
```

#### (c) When to USE — 긍정 예시 2~5개

호출이 적절한 상황의 구체 예시를 자연어로.

```
USE THIS TOOL WHEN:
- User asks "compare A vs B" with explicit visual intent
- User says "show me X" or "what does X look like"
- Multi-faceted content where visual aids understanding
```

#### (d) When NOT to use — 부정 예시 2~5개

호출하면 안 되는 상황. **이 섹션이 없으면 도구가 오용된다.** Description의 절반이 여기에 들어가는 게 정상이다.

```
SKIP THIS TOOL WHEN:
- User is venting emotions (just listen)
- User explicitly wants a textual answer
- Factual questions answerable from knowledge
- User already provided detailed constraints (don't re-ask)
```

특히 **유사 기능 도구가 있을 때** 경계를 명확히 한다.

```
DO NOT use this tool if:
- The user names another tool explicitly → use that one
- The data is in internal_db → use query_internal instead
```

### 2.2 권장 항목 (Recommended)

#### (e) Input/Output 예시 — JSON 또는 cURL 형태

복잡한 schema는 예시 한 개가 명세 10줄보다 효과적.

```json
{
  "queries": [
    {"query": "temples in Asakusa", "max_results": 3},
    {"query": "ramen in Shibuya", "max_results": 3}
  ]
}
```

#### (f) Post-call Behavior — 호출 직후 동작 룰

호출이 끝난 후 에이전트가 어떻게 행동해야 하는지.

```
After calling this tool, your turn is done — the user's selection 
arrives as their next message. Don't keep writing.
```

#### (g) Error / Edge Case 핸들링

실패 종류와 대응 방향.

```
ERROR HANDLING:
- Auth failure → call refresh_token, retry once
- Empty result → respond directly without retry  
- Rate limit (429) → wait and inform user, don't retry silently
```

### 2.3 안티패턴 (Don'ts)

| ❌ 안티패턴 | 왜 문제인가 | 대안 |
|---|---|---|
| 한 줄짜리 sparse description ("Searches stuff") | 호출 실수 발생 | Positive + negative example 추가 |
| 다른 도구와의 우선순위를 description에 넣기 | 변경 시 N개 도구 동기화 필요 | System prompt에서 통합 라우팅 |
| 입력만 정의, 출력 형식 누락 | Downstream chain 깨짐 | Returns schema와 예시 필수 |
| Agent 전체의 페르소나/톤 명시 | 도구 재사용성 저하 | System prompt로 |
| "적절히 판단해서 사용하세요" 류 모호한 지시 | 실효성 0 | 구체 예시로 |

### 2.4 템플릿

```yaml
# tool: <snake_case_name>
purpose: |
  <도구가 무엇을 하는지 한 줄. 동사 시작.>

parameters:
  - name: <param_name>
    type: <string | integer | array | object | enum>
    required: <true | false>
    description: <한 줄 설명>
    default: <기본값, 있다면>
    constraints: <범위, 형식, allowed values>

returns:
  type: <array | object | scalar>
  shape: <간략한 schema>
  example: <실제 예시 한 개>

when_to_use:
  - <긍정 예시 1>
  - <긍정 예시 2>
  - <긍정 예시 3>

when_not_to_use:
  - <부정 예시 1>
  - <부정 예시 2>

input_example: |
  <JSON or pseudo-call>

post_call_behavior: |
  <호출 직후 에이전트의 행동 규칙>

errors:
  - condition: <에러 종류>
    response: <대응 방향>
```

---

## 3. System Prompt 작성 가이드

### 3.1 필수 항목 (Required)

#### (a) Identity & Role — 에이전트 정체성

- 이름, 담당 도메인, 사용자 페르소나
- 어떤 톤으로 응답하는지 (formal / casual / technical)
- 어떤 언어로 응답하는지 (한국어, 영어, 혼용)

```markdown
# Identity
당신은 LG CNS의 NL2SQL Agent입니다. 사내 BI 도메인 전문가가 자연어로 
질문하면, 도메인 지식 기반의 SQL을 생성해 데이터 웨어하우스에서 결과를 
조회하고 한국어로 응답합니다. 데이터 분석가 수준의 정확도와 신중함을 
유지하되, 답변은 간결하게 합니다.
```

#### (b) Tool Orchestration Rules — 도구 간 라우팅 결정 트리

여러 도구가 있다면 **명시적인 결정 트리**를 만든다. Claude의 `<request_evaluation_checklist>`가 모범 예시 (Step 0 → 1 → 2 → 3).

```markdown
# Tool Routing Decision Tree

Step 0 — 도구 호출이 필요한가?
  Knowledge로 답할 수 있으면 직접 응답. 더 진행하지 마라.

Step 1 — 사용자가 특정 도구를 지명했는가?
  YES → 해당 도구를 직접 호출. 다른 도구 후보 평가 생략.
  NO  → Step 2

Step 2 — 정적 도메인 지식만으로 답 가능한가?
  YES → `retrieve_static_knowledge` 1회 호출 후 응답
  NO  → Step 3

Step 3 — 동적 데이터 조회가 필요한가?
  YES → `execute_sql` 호출
  NO  → 사용자에게 명확화 요청
```

#### (c) Safety & Boundary Rules — 안전 정책

- 절대 하면 안 되는 행동 (irreversible action, PII 노출 등)
- 권한 경계 (read-only vs write 가능 도구)
- 사용자 데이터 처리 원칙

```markdown
# Critical Safety Rules

- DROP, DELETE, TRUNCATE 등 DDL/DML 변경 쿼리는 절대 생성하지 않는다.
- 사용자 ID, 주민번호, 카드번호 등 PII는 결과에서 항상 마스킹한다.
- 외부 도메인으로 데이터를 전송하는 도구는 호출하지 않는다.
```

#### (d) Output Format Rules — 응답 형식과 길이 규칙

- 응답 길이의 default (간결 vs 상세)
- 표/리스트 사용 기준
- 인용/citation 규칙

```markdown
# Output Format
- 기본 응답은 5문장 이내. 복잡한 분석 요청 시에만 길게.
- 숫자 비교는 항상 표로. 단일 수치는 인라인 텍스트로.
- SQL 쿼리는 코드 블록으로 함께 제시. 사용자 검증 가능하도록.
- 데이터 출처(테이블명)를 응답 말미에 명시.
```

#### (e) Error & Edge Case Handling

- 도구 실패 시 fallback
- 모호한 입력 시 clarification 정책

```markdown
# Error Handling
- execute_sql 실패 시: 에러 메시지 분석 후 1회 재시도. 두 번째 실패면 
  사용자에게 원인과 함께 보고하고 명확화 요청.
- 사용자 질문이 모호하면: 추측해서 실행하지 말고 ask_user_input으로 선택지 제시.
```

### 3.2 권장 항목 (Recommended)

#### (f) Memory / State 관리 원칙

- 무엇을 기억하고 무엇을 잊을지
- Conversation history 활용 범위

#### (g) Domain Context

사용자 또는 조직의 특수 컨텍스트 (사내 용어, 약어, 표준 등).

```markdown
# Domain Glossary
- "MAU" = Monthly Active User (월간활성사용자)
- "리텐션" = D7/D30 retention 지표
- "전월" = 직전 월 (예: 5월 질문이면 4월)
```

#### (h) Priority Order — 충돌 시 우선순위

규칙이 충돌할 때의 명시적 우선순위.

```markdown
# Priority Order (충돌 시)
1. Safety Rules (절대 양보 불가)
2. User's explicit instruction
3. Domain Context
4. Output Format defaults
```

### 3.3 안티패턴 (Don'ts)

| ❌ 안티패턴 | 왜 문제인가 | 대안 |
|---|---|---|
| 개별 도구 schema를 system prompt에 옮기기 | Deferred load 의미 상실, context 낭비 | Tool description에 두고 lazy load |
| "안전하게 사용하세요" 류 모호한 규칙 | 실효성 0 | 구체 금지 행동 enumerate |
| 결정 기준 없이 도구 나열만 | 라우팅 실패 | Step-by-step 결정 트리 |
| 너무 긴 페르소나 (3페이지) | Instruction 희석 | 5문장 이내 정체성 + 별도 섹션 |
| 충돌 가능한 규칙을 우선순위 없이 병치 | 동작 비결정적 | Priority Order 섹션 추가 |

### 3.4 템플릿

```markdown
# <Agent Name>

## Identity
<역할 / 도메인 / 사용자 / 톤 — 5문장 이내>

## Tool Routing Decision Tree
Step 0: <도구 호출 필요 여부 판단>
Step 1: <첫 분기 조건>
Step 2: <둘째 분기 조건>
...

## Safety Rules
- Critical 금지 1
- Critical 금지 2
- 사용자 데이터 처리 원칙

## Output Format
- 응답 길이 default
- 형식 (표 / 코드 블록 / 인라인)
- 인용 / 출처 표기

## Error Handling
- 도구 실패 시 fallback
- 모호한 입력 시 clarification 정책

## Memory & State (선택)
- 기억할 것 / 잊을 것

## Domain Context (선택)
- 사내 용어 / 약어 / 표준

## Priority Order (선택)
1. ...
2. ...
```

---

## 4. 어디에 써야 하는가 — 결정 트리

새 정보를 추가할 때 다음 질문을 순서대로 던진다.

### Q1. 이 정보가 단 하나의 도구에만 적용되는가?

- **YES** → Tool Description
- **NO** → Q2

### Q2. 이 정보가 여러 도구의 우선순위, 순서, 라우팅에 관한 것인가?

- **YES** → System Prompt의 Tool Routing 섹션
- **NO** → Q3

### Q3. 이 정보가 안전과 직결되어 누락 시 사용자에게 실제 피해가 가는가?

- **YES** → 양쪽 모두 (의도적 redundancy)
- **NO** → Q4

### Q4. 이 정보가 에이전트의 정체성, 응답 톤, 출력 형식과 관련된가?

- **YES** → System Prompt
- **NO** → Tool Description (default)

---

## 5. 검증 체크리스트

### Tool Description Checklist

- [ ] Purpose가 한 줄이고 동사로 시작하는가?
- [ ] 모든 파라미터에 type, description, default(해당 시)가 있는가?
- [ ] Returns 형식과 예시가 있는가?
- [ ] When to USE 예시가 **2개 이상**인가?
- [ ] When NOT to use 예시가 **1개 이상**인가?
- [ ] 호출 직후 동작 룰(post-call behavior)이 명시되어 있는가?
- [ ] Negative example이 **유사 기능 도구**와의 경계를 분명히 하는가?
- [ ] 다른 도구와의 우선순위가 description 안에 잘못 들어가 있지 않은가?
- [ ] Agent 페르소나/톤이 description 안에 잘못 들어가 있지 않은가?

### System Prompt Checklist

- [ ] Identity 단락이 5문장 이내인가?
- [ ] 도구가 2개 이상이라면 Routing Decision Tree가 step-by-step으로 명시되어 있는가?
- [ ] Safety Rules가 **별도 섹션**으로 명시적인가?
- [ ] 출력 형식(길이, 톤, 표/코드/인라인)이 정해져 있는가?
- [ ] 도구 실패 시 fallback 정책이 있는가?
- [ ] 모호한 입력 시 clarification 정책이 있는가?
- [ ] 규칙 간 충돌 가능성이 있다면 Priority Order가 있는가?
- [ ] 개별 도구의 schema가 system prompt에 잘못 옮겨져 있지 않은가?

---

## 6. 적용 예시 — NL2SQL Agent

주크님의 NL2SQL Agent를 예시로 매핑한다.

### 6.1 Tool Description 예시: `execute_sql`

```yaml
# tool: execute_sql
purpose: |
  Execute a validated SQL query against the data warehouse and return 
  result rows.

parameters:
  sql:
    type: string
    required: true
    description: "Validated SQL SELECT statement. DDL/DML rejected."
    constraints:
      - "Must start with SELECT or WITH"
      - "Max length: 8000 chars"
  limit:
    type: integer
    required: false
    default: 1000
    constraints: {min: 1, max: 10000}
  timeout_sec:
    type: integer
    default: 30

returns:
  type: object
  shape: "{ columns: string[], rows: any[][], row_count: int, elapsed_ms: int }"
  example:
    columns: ["user_id", "mau"]
    rows: [["u_1", 14], ["u_2", 22]]
    row_count: 2
    elapsed_ms: 421

when_to_use:
  - 사용자가 구체적인 수치/집계 조회를 요청한 경우 ("4월 MAU가 얼마야?")
  - retrieve_static_knowledge로 답할 수 없는 동적 데이터가 필요한 경우
  - SQL 검증(validate_sql)이 통과한 직후

when_not_to_use:
  - 사용자 질문이 도메인 정의에 대한 것일 때 (→ retrieve_static_knowledge)
  - SQL이 validate_sql을 통과하지 못한 경우 (먼저 correction 시도)
  - 사용자가 "쿼리만 보여줘"라고 명시한 경우 (실행 없이 SQL만 응답)

input_example: |
  {
    "sql": "SELECT user_id, COUNT(*) AS mau FROM events WHERE...",
    "limit": 1000
  }

post_call_behavior: |
  결과 row_count가 0이면, 빈 결과의 가능한 원인(필터 조건 너무 좁음, 
  데이터 미존재 등)을 1문장으로 보고 후 사용자에게 명확화 요청.
  row_count가 limit과 같으면 결과가 잘렸을 가능성을 명시.

errors:
  - condition: "DDL/DML detected"
    response: "사용자에게 read-only 정책 안내 후 SELECT 쿼리로 재작성 요청"
  - condition: "Timeout (30s)"
    response: "쿼리 최적화 1회 시도 후, 실패 시 사용자에게 보고"
  - condition: "Permission denied on table"
    response: "테이블 접근 권한 부족을 보고. 재시도 금지."
```

### 6.2 System Prompt 예시 (발췌)

```markdown
# NL2SQL Agent

## Identity
당신은 LG CNS의 NL2SQL Agent입니다. 사내 BI 도메인 전문가가 자연어로 
질문하면, 도메인 지식 기반 SQL을 생성해 데이터 웨어하우스에서 결과를 
조회하고 한국어로 응답합니다. 정확도와 신중함을 데이터 분석가 수준으로 
유지하되, 답변은 간결합니다.

## Tool Routing Decision Tree

Step 0 — 사용자 의도 분류
  데이터 조회 → Step 1
  도메인 정의/스키마 질문 → retrieve_static_knowledge로 단독 응답
  잡담/모호한 질문 → ask_user_input으로 명확화

Step 1 — 모호성 해소 필요?
  YES → disambiguate 호출
  NO  → Step 2

Step 2 — Plan & Retrieve
  plan → retrieve_dynamic_knowledge (OpenSearch hybrid) 호출

Step 3 — Generate & Validate
  generate → validate_sql 호출
  validation 실패 → correct (최대 2회) → 재 validate
  2회 실패 시 → 사용자에게 원인 보고

Step 4 — Execute
  validate 통과 시에만 execute_sql 호출
  결과 분석 후 한국어로 응답

## Safety Rules

- DDL/DML(DROP, DELETE, UPDATE, INSERT, TRUNCATE) 절대 생성/실행 금지
- PII 컬럼(주민번호, 카드번호, 휴대폰번호) 결과에 노출 금지
- LIMIT 없는 쿼리 생성 금지 (default 1000)
- Cross-schema JOIN은 도메인 팩에 명시된 join_rules 내에서만

## Output Format

- 결과 응답은 5문장 이내 한국어
- 숫자 비교/리스트는 표로
- 사용한 SQL을 코드 블록으로 함께 제시 (사용자 검증 가능하도록)
- 출처 테이블명을 응답 말미에 "출처: events, users" 형태로 명시

## Error Handling

- 도구 실패 시: 에러 분석 후 1회 재시도. 두 번째 실패는 사용자에게 보고.
- 모호한 입력: ask_user_input으로 2~4개 선택지 제시.
- 빈 결과: 가능한 원인 1문장 + 명확화 요청.

## Priority Order

1. Safety Rules (양보 불가)
2. 사용자의 명시적 지시
3. Domain Pack의 join_rules / unit_conversion
4. Output Format defaults
```

---

## 7. 부록: 자주 헷갈리는 경계 사례

### Case 1. "이 도구 다음에는 무조건 저 도구를 호출해야 합니다"

→ **System Prompt의 Routing 섹션**. 도구 description은 자기 자신만 알아야 한다.

### Case 2. "이 도구는 retry 가능한 에러일 때 1회 재시도하세요"

→ **Tool Description의 errors 섹션**. 도구 고유의 에러 의미는 description 내부.

### Case 3. "사용자가 분노하면 사과 모드로 응답하세요"

→ **System Prompt**. Agent 페르소나 / 톤 조정.

### Case 4. "이 도구는 결제 관련이라 사용자 확인 받고 호출"

→ **양쪽 모두**. Description에 "requires explicit user confirmation" 명시 + System Prompt의 Safety Rules에도.

### Case 5. "validate_sql이 실패하면 correct를 호출해서 고친다"

→ **System Prompt의 Routing Tree**. 두 도구의 관계는 개별 description이 아니라 라우팅이 다룬다.

### Case 6. "SQL 생성 시 LIMIT 없으면 자동으로 LIMIT 1000 추가"

→ **execute_sql의 Tool Description (post-call behavior)** 또는 generate 단계의 처리. 도구 단독 책임이면 description.

### Case 7. "응답은 항상 한국어로"

→ **System Prompt**. Agent 출력 형식 규칙.

### Case 8. "도구 호출 결과의 PII는 마스킹"

→ **양쪽 모두**. Tool description의 returns 처리 룰 + System Prompt의 Safety Rules.

---

## 8. 마지막 점검 (Pre-merge 체크)

새 도구 또는 새 에이전트를 머지하기 전 다음을 확인한다.

1. **Description만으로 시뮬레이션 가능한가?** Description만 보여주고 모델/엔지니어에게 "이 도구 언제 써?"라고 물었을 때 답이 일관되게 나오면 합격.
2. **다른 도구 description을 참조해야 답할 수 있는 게 있는가?** 있다면 그건 system prompt로 빠져야 한다.
3. **Negative example이 1개 이상인가?** 0개면 반려.
4. **Safety 정책이 양쪽에 정합적인가?** 한쪽만 강화되어 있으면 보강.
5. **결정 트리가 step 번호로 명시되었는가?** 자연어로 흐리게 적혀 있으면 step으로 재구성.

---

*문서 작성: Claude system prompt 분석 기반 · 적용 대상: Prebuilt Agent Platform v9+*
