import { useState } from 'react'

function ToolCard({ tool, disabled, onToggle }) {
  const [expanded, setExpanded] = useState(false)
  const enabled = !disabled

  const handleToggle = (e) => {
    e.stopPropagation()
    onToggle(tool.name)
  }

  const hasMoreLines = (tool.description || '').includes('\n')
  const schemaProps = tool.inputSchema?.properties
  const schemaKeys = schemaProps ? Object.keys(schemaProps) : []

  return (
    <div className={`tool-card ${disabled ? 'tool-card--disabled' : ''}`}>
      <div className="tool-card-header" onClick={() => setExpanded(v => !v)}>
        <div className="tool-card-main">
          <div className="tool-card-name">{tool.name}</div>
          {!expanded && (
            <div className="tool-card-desc">
              {(tool.description || '').split('\n')[0] || '— no description'}
            </div>
          )}
        </div>
        <label className="tool-toggle" onClick={(e) => e.stopPropagation()}>
          <input type="checkbox" checked={enabled} onChange={handleToggle} />
          <span className="tool-toggle-slider" />
        </label>
      </div>
      {expanded && (
        <div className="tool-card-body">
          {tool.description ? (
            <div className="tool-card-desc-full">{tool.description}</div>
          ) : (
            <div className="tool-card-desc-full tool-card-desc-empty">— no description</div>
          )}
          {schemaKeys.length > 0 && (
            <div className="tool-card-schema">
              <div className="tool-card-schema-title">Input</div>
              {schemaKeys.map(k => {
                const prop = schemaProps[k]
                const required = tool.inputSchema?.required?.includes(k)
                return (
                  <div className="tool-card-schema-row" key={k}>
                    <span className="schema-key">
                      {k}
                      {required && <span className="schema-required">*</span>}
                    </span>
                    <span className="schema-type">{prop.type || 'any'}</span>
                    {prop.description && (
                      <span className="schema-desc">— {prop.description}</span>
                    )}
                  </div>
                )
              })}
            </div>
          )}
          <button className="tool-card-collapse" onClick={() => setExpanded(false)}>
            접기
          </button>
        </div>
      )}
      {!expanded && hasMoreLines && (
        <button className="tool-card-more" onClick={() => setExpanded(true)}>
          더 보기
        </button>
      )}
    </div>
  )
}

function EmptyState({ status }) {
  const style = { fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }
  if (status === 'connecting') return <div style={style}>MCP 연결 중…</div>
  if (status === 'restarting') return <div style={style}>서버 재시작 중…</div>
  if (status === 'error') return <div style={style}>MCP 연결 실패. 콘솔에서 오류를 확인하세요.</div>
  if (status === 'ready') return <div style={style}>등록된 도구가 없습니다.</div>
  return <div style={style}>대기 중…</div>
}

export default function ToolsPanel({ tools, disabledTools, onToggleTool, connectionStatus }) {
  const total = tools.length
  const enabledCount = tools.filter(t => !disabledTools?.has(t.name)).length

  return (
    <div className="sidebar-section">
      <div className="sidebar-section-title">
        Registered Tools
        {total > 0 && (
          <span className="tools-count">({enabledCount}/{total})</span>
        )}
      </div>
      {total === 0 ? (
        <EmptyState status={connectionStatus} />
      ) : (
        tools.map(t => (
          <ToolCard
            key={t.name}
            tool={t}
            disabled={disabledTools?.has(t.name)}
            onToggle={onToggleTool}
          />
        ))
      )}
    </div>
  )
}
