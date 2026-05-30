---
id: wf.report_pipeline
kind: workflow
title: NL질의 → SQL → Chart → 보고서 풀파이프
tags: [workflow, report, nl2sql, chart]
trigger_patterns:
  - "복합 보고서 요청 (분석 + 시각화 + 요약)"
  - "데이터 조회 후 차트와 문구가 모두 필요"
  - "월간/분기 리포트 생성"
related_ids:
  - skill.nl2sql_disambig
  - tool_manual.test_myagent
steps:
  - tool: test_myagent
    input_hint: "사용자 자연어 질의를 그대로 전달. mode='default'."
    output_use: "처리 결과 문자열을 다음 step 의 input prefix 로."
    next_steps:
      - tool_manual.test_myagent
chain_with:
  - tool_manual.test_myagent
summary: 자연어 질의를 받아 데이터 조회 → 시각화 → 보고서 문구까지 한 번에 완성하는 표준 파이프라인.
---

## 본문

### Step 1 — 질의 처리
`test_myagent` 도구로 사용자 질의를 1차 가공.
가공된 결과를 다음 단계의 입력으로 사용.

### Step 2 — 데이터 조회 (예: nl2sql)
도메인 패키지 기반 hybrid RAG 로 SQL 생성 후 실행. 결과 DataFrame 확보.

### Step 3 — 시각화 (예: nl2chart)
DataFrame + 사용자 의도를 받아 차트 HTML/PNG 생성.

### Step 4 — 보고서 문구 작성
표·차트의 핵심 인사이트를 1~2 문단으로 요약. 가정과 데이터 출처 명시.

## 주의

- Step 1 에서 모호한 질의는 `skill.nl2sql_disambig` 절차로 먼저 해소.
- Step 3 의 차트 종류 선정은 데이터 형태에 따라 다름 (시계열→선/막대, 비교→막대, 비율→파이).
- 최종 산출물은 한 번의 응답에 표·차트·요약을 모두 포함.
