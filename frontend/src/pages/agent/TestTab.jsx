import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { mcpClient } from '../../mcp/client.js'
import { useMcp } from '../../context/McpContext.jsx'
import ChatWindow from '../../components/ChatWindow.jsx'
import InputBar from '../../components/InputBar.jsx'

let _msgCounter = 0
const newMsg = (role, content, meta = null, error = false) => ({
  id: ++_msgCounter, role, content, meta, error, timestamp: Date.now(),
})

export default function TestTab({ agent }) {
  const { connection, disabledTools } = useMcp()
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [prefill, setPrefill] = useState(null)

  const disabled = disabledTools.has(agent.name)
  const notReady = connection.status !== 'ready'

  const handleSend = useCallback(async (text) => {
    setMessages(prev => [...prev, newMsg('user', text)])
    setIsLoading(true)
    try {
      const { text: result, elapsed } = await mcpClient.callTool(agent.name, { input: text })
      setMessages(prev => [...prev, newMsg('assistant', result, { tool: agent.name, elapsed })])
    } catch (e) {
      setMessages(prev => [...prev, newMsg('assistant', e.message || '오류가 발생했습니다.', null, true)])
    } finally {
      setIsLoading(false)
    }
  }, [agent.name])

  // Workspace 전용 에이전트(예: PptTemplate) — 콘솔 텍스트 호출 대신 Workspace로 유도.
  if (agent.test === 'workspace') {
    return (
      <div className="test-redirect">
        <div className="test-redirect-icon">🗂️</div>
        <p className="test-redirect-text">
          이 에이전트는 입력 형식이 복잡해 콘솔 텍스트 호출 대신
          전용 <strong>{agent.workspaceLabel || 'Workspace'}</strong>에서 사용합니다.
        </p>
        {agent.workspaceRoute && (
          <Link to={agent.workspaceRoute} className="ws-open-link">
            🗂️ {agent.workspaceLabel || 'Workspace'} 열기 →
          </Link>
        )}
      </div>
    )
  }

  return (
    <div className="test-tab">
      {agent.sampleQueries.length > 0 && (
        <div className="test-samples">
          <span className="test-samples-label">샘플</span>
          {agent.sampleQueries.map((q, i) => (
            <button
              key={i}
              className="test-chip"
              onClick={() => setPrefill(q)}
              disabled={disabled || notReady}
              title={q}
            >
              {q.length > 42 ? q.slice(0, 41) + '…' : q}
            </button>
          ))}
        </div>
      )}

      <div className="test-console">
        <ChatWindow messages={messages} isLoading={isLoading} />
        {disabled ? (
          <div className="test-disabled-note">
            이 에이전트는 콘솔에서 <strong>비활성</strong> 상태입니다. Admin 탭에서 활성화하세요.
          </div>
        ) : (
          <InputBar onSend={handleSend} disabled={isLoading || notReady} prefill={prefill} />
        )}
      </div>
    </div>
  )
}
