/**
 * 콘솔이 사용하는 기존 백엔드 API 래퍼.
 * 신규 엔드포인트는 만들지 않는다 — 실패 시 graceful 빈값으로 폴백한다.
 */

/** GET /health/ready → { status, components: { name: {status, message, latency_ms} } } */
export async function getReadiness() {
  try {
    const r = await fetch('/health/ready')
    // 503(error)도 본문은 JSON이다.
    const data = await r.json()
    return {
      status: data.status ?? (r.ok ? 'ok' : 'error'),
      components: data.components ?? {},
      reachable: true,
    }
  } catch (_) {
    return { status: 'unknown', components: {}, reachable: false }
  }
}

/**
 * GET /openapi.json → 비즈니스 REST API operation 개수(경로×메서드).
 * /health/* 프로브는 제외. 실패/미도달 시 null.
 */
export async function getRestApiCount() {
  const METHODS = new Set(['get', 'post', 'put', 'patch', 'delete'])
  try {
    const r = await fetch('/openapi.json')
    if (!r.ok) return null
    const data = await r.json()
    const paths = data.paths || {}
    let count = 0
    for (const [path, ops] of Object.entries(paths)) {
      if (path.startsWith('/health')) continue
      for (const method of Object.keys(ops || {})) {
        if (METHODS.has(method.toLowerCase())) count++
      }
    }
    return count
  } catch (_) {
    return null
  }
}

/** GET /api/admin/env → { files: [{id, label, entries: [{key, value, sensitive}]}] } */
export async function getEnv() {
  try {
    const r = await fetch('/api/admin/env')
    if (!r.ok) return { files: [], reachable: true }
    const data = await r.json()
    return { files: data.files ?? [], reachable: true }
  } catch (_) {
    return { files: [], reachable: false }
  }
}

/** PUT /api/admin/env — 한 파일의 entries 전체를 덮어쓴다. → { ok, status } */
export async function saveEnvFile(fileId, entries) {
  try {
    const r = await fetch('/api/admin/env', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: fileId, entries }),
    })
    return { ok: r.ok, status: r.status }
  } catch (_) {
    return { ok: false, status: 0 }
  }
}

/** POST /api/admin/restart — 서버 프로세스를 재기동한다. → { ok } */
export async function restartServer() {
  try {
    const r = await fetch('/api/admin/restart', { method: 'POST' })
    return { ok: r.ok }
  } catch (_) {
    // 재기동 중 연결이 끊겨 fetch가 실패할 수 있으므로 ok로 간주한다.
    return { ok: true }
  }
}

/** GET /api/admin/logs — prefix 필터된 최근 로그. → { entries:[{seq,ts,level,name,message}], last_seq } */
export async function getLogs(prefixes = [], after = 0, limit = 200) {
  const params = new URLSearchParams()
  if (prefixes.length) params.set('prefixes', prefixes.join(','))
  if (after) params.set('after', String(after))
  params.set('limit', String(limit))
  try {
    const r = await fetch(`/api/admin/logs?${params.toString()}`)
    if (!r.ok) return { entries: [], last_seq: after }
    return await r.json()
  } catch (_) {
    return { entries: [], last_seq: after }
  }
}

/**
 * GET /api/admin/logs/stream (SSE) 구독. EventSource 반환(.close()로 정리).
 * @param {string[]} prefixes  logger 이름 prefix 필터
 * @param {number} after  이 seq 이후만
 * @param {(e:object)=>void} onEvent  로그 1건마다
 * @param {(open:boolean)=>void} [onState]
 */
export function openLogStream(prefixes = [], after = 0, onEvent, onState) {
  const params = new URLSearchParams()
  if (prefixes.length) params.set('prefixes', prefixes.join(','))
  if (after) params.set('after', String(after))
  const es = new EventSource(`/api/admin/logs/stream?${params.toString()}`)
  es.onopen = () => onState && onState(true)
  es.onerror = () => onState && onState(false)
  es.onmessage = (ev) => {
    if (!ev.data) return
    try { onEvent(JSON.parse(ev.data)) } catch { /* skip */ }
  }
  return es
}

/** env 파일들에서 키 하나를 찾아 값을 반환(없으면 null). */
export function findEnvValue(envFiles, keys) {
  const wanted = (Array.isArray(keys) ? keys : [keys]).map(k => k.toUpperCase())
  for (const f of envFiles || []) {
    for (const e of f.entries || []) {
      if (wanted.includes(String(e.key).toUpperCase()) && e.value) return e.value
    }
  }
  return null
}
