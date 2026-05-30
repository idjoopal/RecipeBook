---
id: tool_manual.test_myagent
kind: tool_manual
title: test_myagent — MCP tool manual (입력 처리 예시 도구)
tool_name: test_myagent
tags: [example, stub, my_agent]
trigger_patterns:
  - "MCP 동작 검증이 필요할 때"
  - "단일 텍스트 처리 데모"
related_ids:
  - wf.report_pipeline
chain_with:
  - wf.report_pipeline
# D=1 (도메인 의존 낮음), O=1 (단일 단계), M=1 (모델 의존 낮음). 합 3 → "recommended" 등급.
dom: [1, 1, 1]
params:
  - name: input
    semantics: 처리할 사용자 입력 텍스트
    valid_range: "string, 빈 문자열 허용하나 의미 있는 결과 보장 X"
    gotcha: "stub 구현이므로 결과는 echo 패턴. 실제 비즈니스 로직 대체 필요."
examples:
  - 'test_myagent(input="안녕")'
  - 'test_myagent(input="요청 텍스트 예시")'
output_format: |
  string. 형식: "[stub] input=<원본> 처리 완료"
  e.g. test_myagent(input="안녕") → "[stub] input=안녕 처리 완료"
summary: |
  단일 텍스트를 받아 처리 결과 문자열을 반환하는 stub 예시 도구의 상세 매뉴얼.
---

## 상세

### 호출 의도
"이 도구가 어떤 처리를 한다" 를 확정한 상황에서만 호출.
모호한 의도라면 사용자에게 명확화 요청 후 호출.

### 출력 사용법
반환된 문자열은 그대로 사용자에게 전달하거나, 다음 도구의 input prefix 로 사용.
구조화된 결과 (목록·상태) 가 필요하면 REST `/api/my-agent/{items,status,...}` 사용.

### 함정 (gotchas)
- stub 구현이므로 의미 있는 비즈니스 로직 없음.
- 빈 문자열 입력은 "[stub] input= 처리 완료" 가 반환됨 — 디버깅에는 좋지만 사용자에게 그대로 노출 비추천.

### 권장 체인
이 도구 다음으로 자주 호출되는 것: `wf.report_pipeline` (보고서 파이프라인 진입).
