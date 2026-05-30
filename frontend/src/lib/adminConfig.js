/**
 * Global admin — env 키 분류 / 외부 저장소 / 헬스 폴링 설정.
 * 데이터는 /api/admin/env(파일별 key/value) 뿐이라, 키 이름으로 의미 섹션을 만든다.
 */

// LLM·모델 관련 키 판별 (root의 무접두 키 + 에이전트의 *_MODEL/*_API_KEY/*_BASE_URL)
const LLM_EXACT = new Set([
  'API_KEY', 'MODEL', 'BASE_URL', 'MAX_TOKENS', 'TEMPERATURE', 'TOP_K', 'THINKING', 'TIMEOUT',
])
const LLM_SUFFIX = /(_MODEL|_API_KEY|_BASE_URL|_MAX_TOKENS|_TEMPERATURE|_TOP_K|_THINKING)$/

export function isLlmKey(key) {
  const k = String(key).toUpperCase()
  if (LLM_EXACT.has(k)) return true
  if (k.startsWith('OPENAI_')) return true
  if (k.startsWith('COHERE_')) return true   // COHERE_ENDPOINT_*, COHERE_MODEL 등
  return LLM_SUFFIX.test(k)
}

/** 알려진 에이전트 env → 친화 이름/아이콘. 미등록은 폴백 처리. */
const AGENT_SCOPE_META = {
  nl2sql: { icon: '🗄️', title: 'NL2SQL' },
  web_search: { icon: '🌐', title: 'Web Search' },
  web_fetch: { icon: '🔗', title: 'Web Fetch' },
  dart_search: { icon: '📑', title: 'DART Search' },
  analysis_completion: { icon: '🧠', title: 'Analysis Completion' },
  task_decomposer: { icon: '🧭', title: 'Task Decomposer' },
  chart_generator: { icon: '📈', title: 'NL2Chart' },
  ppt_template_generator: { icon: '📊', title: 'PPT 저작' },
  ppt_report_generator: { icon: '🖋️', title: 'PPT 채우기' },
  my_agent: { icon: '🧩', title: 'My Agent' },
}

/**
 * env 파일 → 표시 메타 { icon, title, sub }.
 * - Root(.env): 공통 스코프.
 * - 에이전트(agent_<name>): AGENT_SCOPE_META 매핑, 미등록은 파일명 기반 폴백.
 */
export function scopeMeta(file) {
  const filename = file.label || file.id || ''
  if (file.id === 'root') {
    return { icon: '⚙️', title: 'Root · 공통', sub: filename || '.env' }
  }
  const name = String(file.id || '').replace(/^agent_/, '')
  const meta = AGENT_SCOPE_META[name]
  if (meta) return { icon: meta.icon, title: meta.title, sub: filename }
  // 폴백: 파일명에서 .env 제거한 이름
  return { icon: '🧩', title: filename.replace(/\.env$/, '') || name, sub: filename }
}

/**
 * files(=getEnv().files)를 스코프(파일)별 그룹으로 분해. 파일 순서(Root 먼저) 유지.
 * 각 item은 원본 위치(fileIdx, entryIdx)를 들고 있어 인라인 편집 시 원본을 수정한다.
 * 카드 내 정렬용으로 모델·LLM 키(llmItems)와 기타(otherItems)로 나눠 담는다.
 * @returns {Array<{ id, label, sub, icon, isRoot,
 *   llmItems: Item[], otherItems: Item[] }>}  Item = {fileIdx, entryIdx, entry}
 */
export function groupByScope(files = []) {
  return files.map((file, fileIdx) => {
    const meta = scopeMeta(file)
    const llmItems = []
    const otherItems = []
    ;(file.entries || []).forEach((entry, entryIdx) => {
      const item = { fileIdx, entryIdx, entry }
      ;(isLlmKey(entry.key) ? llmItems : otherItems).push(item)
    })
    return {
      id: file.id,
      label: meta.title,
      sub: meta.sub,
      icon: meta.icon,
      isRoot: file.id === 'root',
      llmItems,
      otherItems,
    }
  })
}

// 외부 저장소 표시 메타 — /health/ready 의 external 컴포넌트명 → 아이콘/라벨/설명.
// 미등록 external 컴포넌트는 폴백(원본 이름)으로 표시된다.
const STORE_META = {
  nl2sql_opensearch: { icon: '🔍', label: 'OpenSearch', desc: '벡터 RAG · 골든 SQL 인덱스' },
  nl2sql_db: { icon: '🗄️', label: '경영정보 DB', desc: 'NL2SQL 조회 대상 DB' },
}

/**
 * readiness.components → 외부 저장소 카드 목록.
 * external=true 컴포넌트만 골라 STORE_META로 표시 메타를 입힌다.
 * @returns {Array<{name, icon, label, desc, status, latency_ms, message}>}
 */
export function resolveStores(components = {}) {
  return Object.entries(components)
    .filter(([, c]) => c && c.external)
    .map(([name, c]) => {
      const meta = STORE_META[name] || { icon: '🗃️', label: name, desc: '' }
      return {
        name,
        icon: meta.icon,
        label: meta.label,
        desc: meta.desc,
        status: c.status,
        latency_ms: c.latency_ms,
        message: c.message,
      }
    })
}

// 리소스 헬스 자동 폴링 주기(초). 0 = off.
export const HEALTH_POLL_OPTIONS = [0, 30, 60]
