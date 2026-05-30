/**
 * 에이전트 매니페스트 중앙 로더.
 *
 * 각 에이전트는 `src/agents/<name>/manifest.js`를 default export 한다.
 * 여기서 Vite의 import.meta.glob으로 빌드 시 자동 수집하므로,
 * 새 에이전트는 폴더 하나만 추가하면 사이드바·Overview·워크스페이스 라우트에
 * 자동 반영된다(이 파일이나 App.jsx를 손댈 필요 없음).
 *
 * manifest 스키마:
 *   {
 *     toolName,            // MCP 도구명 (메타 바인딩 키, 필수)
 *     label, icon, blurb,
 *     test,                // 'text' | 'workspace'
 *     sampleQueries?, healthPrefixes?,
 *     workspace?: { id, label, icon, route, component }  // 풀스크린 워크스페이스가 있을 때만
 *   }
 */

const _modules = import.meta.glob('../agents/*/manifest.{js,jsx}', { eager: true })

/** 수집된 매니페스트 배열 (default export만). */
const MANIFESTS = Object.values(_modules)
  .map(m => m && m.default)
  .filter(m => m && m.toolName)

/**
 * MCP 도구명 → 콘솔 표시 메타 매핑.
 * 미등록 도구는 resolveAgents가 제네릭 메타로 렌더한다.
 */
export const AGENT_REGISTRY = Object.fromEntries(
  MANIFESTS.map(m => [
    m.toolName,
    {
      label: m.label,
      icon: m.icon,
      blurb: m.blurb,
      test: m.test,
      sampleQueries: m.sampleQueries || [],
      healthPrefixes: m.healthPrefixes || [],
      envFiles: m.envFiles || [],
      logPrefixes: m.logPrefixes || [],
      workspaceRoute: m.workspace ? m.workspace.route : null,
      workspaceLabel: m.workspace ? m.workspace.label : null,
    },
  ])
)

/**
 * 워크스페이스 레지스트리 (사이드바 Workspaces 그룹 렌더용).
 * manifest.workspace를 가진 에이전트에서 파생된다.
 */
export const WORKSPACES = MANIFESTS
  .filter(m => m.workspace)
  .map(m => ({
    id: m.workspace.id,
    label: m.workspace.label,
    icon: m.workspace.icon,
    route: m.workspace.route,
  }))

/**
 * 워크스페이스 라우트 정의 (App.jsx의 <Route> 자동 생성용).
 * @type {Array<{route:string, Component:React.ComponentType}>}
 */
export const WORKSPACE_ROUTES = MANIFESTS
  .filter(m => m.workspace && m.workspace.component)
  .map(m => ({ route: m.workspace.route, Component: m.workspace.component }))

/** MCP description의 첫 의미 있는 줄/문장을 추려 카드용 한 줄 설명으로. */
export function firstLine(text, max = 140) {
  if (!text) return ''
  const line = String(text)
    .split('\n')
    .map(s => s.trim())
    .find(s => s.length > 0) || ''
  const sentence = line.split(/(?<=[.。!?])\s/)[0] || line
  return sentence.length > max ? sentence.slice(0, max - 1) + '…' : sentence
}

/**
 * MCP listTools 결과를 콘솔 에이전트 목록으로 정규화.
 * @param {Array<{name:string, description?:string, inputSchema?:object}>} tools
 * @returns {Array<{name, label, icon, description, rawDescription, inputSchema,
 *   test, sampleQueries, healthPrefixes, workspaceRoute?, workspaceLabel?}>}
 */
export function resolveAgents(tools = []) {
  return tools.map(t => {
    const meta = AGENT_REGISTRY[t.name] || {}
    return {
      name: t.name,
      label: meta.label || t.name,
      icon: meta.icon || '🤖',
      description: firstLine(t.description) || meta.blurb || '설명이 없습니다.',
      rawDescription: t.description || '',
      inputSchema: t.inputSchema || null,
      test: meta.test || 'text',
      sampleQueries: meta.sampleQueries || [],
      healthPrefixes: meta.healthPrefixes || [],
      envFiles: meta.envFiles || [],
      logPrefixes: meta.logPrefixes || [],
      workspaceRoute: meta.workspaceRoute || null,
      workspaceLabel: meta.workspaceLabel || null,
    }
  })
}
