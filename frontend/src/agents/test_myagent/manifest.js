// 에이전트 작성 예시(exemplar) 매니페스트.
// 새 에이전트를 만들 때 이 폴더를 복사해 toolName/메타를 바꾸면 된다.
export default {
  toolName: 'test_myagent',
  envFiles: ['agent_my_agent'],
  logPrefixes: ['my_agent'],
  label: 'My Agent',
  icon: '🧩',
  blurb: '에이전트 작성 예시(exemplar). 입력을 받아 처리 결과를 반환합니다.',
  test: 'text',
  sampleQueries: [
    '안녕하세요, 동작 테스트입니다.',
    '다음 문장을 한 줄로 요약해줘: 프리빌트 에이전트 콘솔은 MCP·REST로 노출되는 에이전트를 운영자와 사용자가 함께 다루도록 설계되었다.',
    '오늘 날짜와 함께 인사말을 만들어줘.',
  ],
}
