import { useState, useEffect, useRef, useCallback } from 'react'
import { getReadiness } from '../lib/consoleApi.js'
import { resolveStores, HEALTH_POLL_OPTIONS } from '../lib/adminConfig.js'

/**
 * 외부 저장소 연결 위젯 (Global admin · Overview 공용).
 *
 * - showControls=true  : 자체 readiness 폴링 + "지금 확인"/자동주기 컨트롤 (Global admin)
 * - showControls=false : 부모가 넘긴 components 로 렌더 (Overview, 추가 fetch 없음)
 *
 * 데이터 소스는 /health/ready 의 external=true 컴포넌트뿐이다(실연결 probe).
 * 객체 저장소처럼 external health check가 없는 자원은 표시되지 않으며,
 * 백엔드에 external health check를 추가하면 자동으로 카드가 나타난다.
 *
 * @param {{ components?: object, showControls?: boolean }} props
 */
function fmtTime(d) {
  if (!d) return '—'
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function ExternalStores({ components, showControls = false }) {
  const [readiness, setReadiness] = useState(
    () => (components ? { components, reachable: true } : { components: {}, reachable: true })
  )
  const [lastChecked, setLastChecked] = useState(null)
  const [loading, setLoading] = useState(false)
  const [pollSec, setPollSec] = useState(0)
  const timerRef = useRef(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    const r = await getReadiness()
    setReadiness(r)
    setLastChecked(new Date())
    setLoading(false)
  }, [])

  // showControls: 자체 fetch + 폴링. 아니면 부모 components prop 동기화.
  useEffect(() => {
    if (showControls) refresh()
  }, [showControls, refresh])

  useEffect(() => {
    if (!showControls) setReadiness({ components: components || {}, reachable: true })
  }, [components, showControls])

  useEffect(() => {
    if (!showControls) return
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
    if (pollSec > 0) timerRef.current = setInterval(refresh, pollSec * 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [pollSec, refresh, showControls])

  const stores = resolveStores(readiness.components || {})
  const okCount = stores.filter(s => s.status === 'ok').length

  return (
    <>
      {showControls && (
        <div className="ga-health-controls ext-stores-controls">
          <span className="ga-health-meta">
            마지막 확인 {fmtTime(lastChecked)}
            {stores.length > 0 && ` · ${okCount}/${stores.length} 정상`}
          </span>
          <select
            className="ga-poll-select"
            value={pollSec}
            onChange={e => setPollSec(Number(e.target.value))}
            title="자동 확인 주기"
          >
            {HEALTH_POLL_OPTIONS.map(s => (
              <option key={s} value={s}>{s === 0 ? '자동 off' : `자동 ${s}s`}</option>
            ))}
          </select>
          <button className="btn-ghost-sm" onClick={refresh} disabled={loading}>
            {loading ? '확인 중…' : '지금 확인'}
          </button>
        </div>
      )}

      {!readiness.reachable && (
        <div className="placeholder-note">상태 서버에 연결할 수 없습니다.</div>
      )}
      {readiness.reachable && stores.length === 0 && (
        <div className="placeholder-note">
          연결된 외부 저장소가 없습니다. (DB·OpenSearch 등 연동 시 표시)
        </div>
      )}

      <div className="ga-store-list">
        {stores.map(s => (
          <div key={s.name} className="ga-store-row">
            <span className="ga-store-icon">{s.icon}</span>
            <div className="ga-store-text">
              <div className="ga-store-label">{s.label}</div>
              {s.desc && <div className="ga-store-desc">{s.desc}</div>}
              {s.message && <div className="ga-store-msg">{s.message}</div>}
            </div>
            {s.latency_ms != null && <span className="ga-store-latency">{s.latency_ms}ms</span>}
            <span className={`status-dot ${s.status === 'ok' ? 'connected' : 'error'}`} />
            <span className="ga-store-badge">{s.status === 'ok' ? '연결됨' : '오류'}</span>
          </div>
        ))}
      </div>
    </>
  )
}
