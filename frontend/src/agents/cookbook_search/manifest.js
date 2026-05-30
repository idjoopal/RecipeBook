// Cookbook search — Skill·Workflow·Tool Manual 통합 검색 진입점.
export default {
  toolName: 'cookbook_search',
  envFiles: ['cookbook'],
  logPrefixes: ['cookbook'],
  label: 'Cookbook Search',
  icon: '📖',
  blurb: 'Skill·Workflow·Tool Manual 통합 인덱스 (BM25, hot reload).',
  test: 'text',
  sampleQueries: [
    'cookbook_search(query="자연어로 차트 만들기", kind="workflow")',
    'cookbook_search(query="모호 질의 재질의 절차")',
    '워크플로 카탈로그 보여줘',
  ],
}
