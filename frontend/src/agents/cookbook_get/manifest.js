// Cookbook get — Recipe 본문 조회.
export default {
  toolName: 'cookbook_get',
  envFiles: ['cookbook'],
  logPrefixes: ['cookbook'],
  label: 'Cookbook Get',
  icon: '📑',
  blurb: 'cookbook_search 로 찾은 id 의 본문(steps / chain_with 포함)을 조회.',
  test: 'text',
  sampleQueries: [
    'cookbook_get(id="wf.report_pipeline")',
    'cookbook_get(id="tool_manual.test_myagent")',
    'cookbook_get(id="skill.nl2sql_disambig")',
  ],
}
