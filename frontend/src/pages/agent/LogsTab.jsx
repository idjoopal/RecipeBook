import { useState, useEffect, useRef } from 'react'
import { openLogStream } from '../../lib/consoleApi.js'

const MAX_LINES = 1500

/**
 * Logs 탭 — 해당 에이전트의 로그 원문을 실시간 스트리밍(SSE)으로 표시.
 * agent.logPrefixes(logger 이름 prefix)로 필터된 라인만 받는다. 별도 가공 없이 원문만.
 */
export default function LogsTab({ agent }) {
  const prefixes = agent?.logPrefixes || []
  const [lines, setLines] = useState([])
  const [open, setOpen] = useState(false)
  const [autoscroll, setAutoscroll] = useState(true)
  const boxRef = useRef(null)

  useEffect(() => {
    if (prefixes.length === 0) return
    setLines([])
    const es = openLogStream(prefixes, 0,
      (e) => setLines(prev => {
        const base = prev.length >= MAX_LINES ? prev.slice(prev.length - MAX_LINES + 1) : prev
        return [...base, e]
      }),
      setOpen,
    )
    return () => es.close()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefixes.join(',')])

  // 자동 스크롤 (하단 고정)
  useEffect(() => {
    if (autoscroll && boxRef.current) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight
    }
  }, [lines, autoscroll])

  if (prefixes.length === 0) {
    return (
      <div className="logs-tab">
        <div className="placeholder-card">
          <div className="logs-placeholder-icon">🧭</div>
          <p className="placeholder-note">이 에이전트는 로그 필터(logPrefixes)가 설정되지 않았습니다.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="logs-tab">
      <div className="logs-head">
        <span className={`sqlx-dot ${open ? 'ok' : 'off'}`} />
        <span className="logs-head-status">{open ? '실시간 연결됨' : '연결 끊김 (재시도 중)'}</span>
        <code className="logs-head-prefix">{prefixes.join(', ')}</code>
        <span className="logs-head-count">{lines.length}줄</span>
        <label className="logs-autoscroll">
          <input type="checkbox" checked={autoscroll} onChange={e => setAutoscroll(e.target.checked)} /> 자동 스크롤
        </label>
        <button className="sqlx-btn small" onClick={() => setLines([])}>지우기</button>
      </div>

      <div className="logs-stream" ref={boxRef}>
        {lines.length === 0 ? (
          <div className="placeholder-note">로그 대기 중… 이 에이전트를 호출하면 여기에 실시간으로 표시됩니다.</div>
        ) : (
          lines.map((e, i) => (
            <div key={`${e.seq}-${i}`} className="logs-line">
              <span className="logs-time">{(e.ts || '').slice(11, 23)}</span>
              <span className={`logs-level lv-${(e.level || 'info').toLowerCase()}`}>{e.level}</span>
              <span className="logs-name">{e.name}</span>
              <span className="logs-msg">{e.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
