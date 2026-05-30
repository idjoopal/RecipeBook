import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useMcp } from '../../context/McpContext.jsx'
import { getReadiness } from '../../lib/consoleApi.js'
import AgentEnvEditor from './AgentEnvEditor.jsx'

export default function AdminTab({ agent }) {
  const { disabledTools, toggleTool } = useMcp()
  const enabled = !disabledTools.has(agent.name)

  const [readiness, setReadiness] = useState({ components: {}, reachable: false })

  useEffect(() => {
    let alive = true
    getReadiness().then(r => { if (alive) setReadiness(r) })
    return () => { alive = false }
  }, [])

  const prefixes = agent.healthPrefixes || []
  // 외부 리소스(DB·OpenSearch 등) 연결 체크만, 그리고 이 에이전트에 해당하는 것만.
  const components = Object.entries(readiness.components || {}).filter(
    ([name, c]) => c.external && (prefixes.length === 0 ? false : prefixes.some(p => name.startsWith(p)))
  )

  return (
    <div className="admin-tab">
      {/* 활성화 토글 */}
      <section className="admin-block">
        <div className="admin-row">
          <div>
            <div className="admin-row-title">활성화</div>
            <div className="admin-row-sub">이 콘솔에서 에이전트 호출 가능 여부 (클라이언트 설정).</div>
          </div>
          <button
            className={`toggle-switch${enabled ? ' on' : ''}`}
            role="switch"
            aria-checked={enabled}
            onClick={() => toggleTool(agent.name)}
          >
            <span className="toggle-knob" />
          </button>
        </div>
      </section>

      {/* 리소스 상태 (Health) — 외부 리소스 연결만 */}
      <section className="admin-block">
        <h3 className="admin-h">리소스 상태</h3>
        {!readiness.reachable && (
          <div className="placeholder-note">상태 서버에 연결할 수 없습니다.</div>
        )}
        {readiness.reachable && components.length === 0 && (
          <div className="placeholder-note">연결된 외부 리소스가 없습니다.</div>
        )}
        {components.map(([name, c]) => (
          <div key={name} className="admin-health-row">
            <span className={`status-dot ${c.status === 'ok' ? 'connected' : 'error'}`} />
            <span className="admin-health-name">{name}</span>
            {c.latency_ms != null && <span className="admin-health-latency">{c.latency_ms}ms</span>}
            {c.message && <span className="admin-health-msg">{c.message}</span>}
          </div>
        ))}
      </section>

      {/* 환경 설정 (.env) — 이 에이전트 전용 env 편집 */}
      {agent.envFiles?.length > 0 && (
        <section className="admin-block">
          <h3 className="admin-h">환경 설정 (.env)</h3>
          <p className="admin-row-sub">이 에이전트 전용 환경변수입니다. 저장 후 서버 재기동 시 적용됩니다.</p>
          <AgentEnvEditor fileIds={agent.envFiles} />
        </section>
      )}

      {/* Workspace 링크 */}
      {agent.workspaceRoute && (
        <section className="admin-block">
          <h3 className="admin-h">Workspace</h3>
          <Link to={agent.workspaceRoute} className="ws-open-link">
            🗂️ {agent.workspaceLabel || 'Workspace'} 열기 →
          </Link>
        </section>
      )}
    </div>
  )
}
