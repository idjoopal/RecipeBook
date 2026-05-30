import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useMcp } from '../context/McpContext.jsx'
import { resolveAgents } from '../lib/agentRegistry.js'
import GuideTab from './agent/GuideTab.jsx'
import TestTab from './agent/TestTab.jsx'
import AdminTab from './agent/AdminTab.jsx'
import LogsTab from './agent/LogsTab.jsx'

const TABS = [
  { id: 'guide', label: 'Guide' },
  { id: 'test', label: 'Test' },
  { id: 'admin', label: 'Admin' },
  { id: 'logs', label: 'Logs' },
]

export default function AgentDetailPage() {
  const { agentName } = useParams()
  const { tools, disabledTools } = useMcp()
  const agent = resolveAgents(tools).find(a => a.name === agentName)
  const [tab, setTab] = useState('guide')

  if (!agent) {
    return (
      <div className="agent-detail">
        <p className="placeholder-note">
          에이전트 <code>{agentName}</code>를 찾을 수 없습니다. <Link to="/" className="ov-link">Overview로</Link>
        </p>
      </div>
    )
  }

  const disabled = disabledTools.has(agent.name)

  return (
    <div className="agent-detail">
      <header className="agent-detail-head">
        <span className="agent-detail-icon">{agent.icon}</span>
        <div>
          <h1 className="agent-detail-title">
            {agent.label}
            {disabled && <span className="agent-disabled-badge">비활성</span>}
          </h1>
          <p className="agent-detail-desc">{agent.description}</p>
        </div>
      </header>

      <div className="agent-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`agent-tab${tab === t.id ? ' active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="agent-tab-panel">
        {tab === 'guide' && <GuideTab agent={agent} />}
        {tab === 'test' && <TestTab agent={agent} />}
        {tab === 'admin' && <AdminTab agent={agent} />}
        {tab === 'logs' && <LogsTab agent={agent} />}
      </div>
    </div>
  )
}
