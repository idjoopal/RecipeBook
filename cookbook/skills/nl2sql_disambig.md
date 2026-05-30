---
id: skill.nl2sql_disambig
kind: skill
title: NL2SQL 질의 모호성 해소 절차
tags: [sql, disambiguation, nl2sql, clarification]
trigger_patterns:
  - "데이터 조회 요청에 기간·지표·대상이 명시되지 않음"
  - "동일 의미의 컬럼이 여러 테이블에 존재"
  - "사용자가 '매출 보여줘' 처럼 차원을 생략"
related_ids:
  - wf.report_pipeline
  - tool_manual.test_myagent
prerequisites: |
  - 도메인 메타데이터(테이블·컬럼·동의어) 로드 완료
  - 최소 1개의 유효 SQL dialect 설정
when_to_use: |
  사용자가 자연어로 데이터 조회를 요청했지만 (기간 / 집계 단위 / 대상 조직 등)
  최소 1개 이상의 차원이 누락되어 SQL 을 단정적으로 생성할 수 없을 때.
summary: 사용자 질의가 모호할 때 명확화 질문을 한 단계에 모아 되묻고, 확정 후 SQL 을 빌드하는 표준 절차.
---

## 절차

### 1. 누락 차원 식별
다음 4개 차원을 체크리스트로 확인:
- **기간** (year/quarter/month/day)
- **지표** (sum/avg/count/지표 정의)
- **대상** (전사 vs 조직별, 어느 조직)
- **필터** (제외 대상, 특수 조건)

### 2. 명확화 질문 1회 통합 발송
질문을 여러 차례 나누지 말고 **한 번에 모아서** 사용자에게 제시.
선택지 3-4개씩을 함께 제안해 응답을 빠르게 유도.

### 3. 응답 확정 후 SQL 빌드
응답이 와도 다시 모호하면 1회 더 묻고 (총 최대 2 라운드),
그 이후에는 가장 보편적인 해석을 선택하고 SQL 응답에 가정을 명시.

### 4. 응답 시 가정 명시
SQL 결과와 함께 적용된 가정 (기간/집계/조직) 을 한 줄로 첨부.
