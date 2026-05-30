import { NavLink } from 'react-router-dom'
import { useMcp } from '../context/McpContext.jsx'
import { resolveAgents, WORKSPACES } from '../lib/agentRegistry.js'

function itemClass({ isActive }) {
  return `console-nav-item${isActive ? ' active' : ''}`
}

export default function ConsoleSidebar() {
  const { tools, connection, disabledTools } = useMcp()
  const agents = resolveAgents(tools)
  const loading = connection.status === 'connecting' || connection.status === 'restarting'

  return (
    <nav className="console-sidebar">
      <NavLink to="/" end className={itemClass}>
        <span className="console-nav-icon">🏠</span>
        <span>Overview</span>
      </NavLink>

      <NavLink to="/admin" className={itemClass}>
        <span className="console-nav-icon">⚙️</span>
        <span>Global admin</span>
      </NavLink>

      <div className="console-nav-group">
        <div className="console-nav-group-title">Agents</div>
        {agents.length === 0 && (
          <div className="console-nav-empty">
            {loading ? '불러오는 중…' : '등록된 에이전트 없음'}
          </div>
        )}
        {agents.map(a => (
          <NavLink key={a.name} to={`/agents/${a.name}`} className={itemClass}>
            <span className="console-nav-icon">{a.icon}</span>
            <span className="console-nav-text">
              <span className="console-nav-label">{a.label}</span>
              <span className="console-nav-toolname">{a.name}</span>
            </span>
            {disabledTools.has(a.name) && <span className="status-dot disabled" title="비활성" />}
          </NavLink>
        ))}
      </div>

      {WORKSPACES.length > 0 && (
        <div className="console-nav-group">
          <div className="console-nav-group-title">Workspaces</div>
          {WORKSPACES.map(w => (
            <NavLink key={w.id} to={w.route} className={itemClass}>
              <span className="console-nav-icon">{w.icon}</span>
              <span className="console-nav-label">{w.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </nav>
  )
}
