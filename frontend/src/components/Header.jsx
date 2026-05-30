import ConnectionBadge from './ConnectionBadge.jsx'
import ToolSelector from './ToolSelector.jsx'

const PPT_STEPS = [
  { id: 'designer', label: '0. 디자이너', requires: null },
  { id: 'extract',  label: '1. 추출', requires: null },
  { id: 'edit',     label: '2. 편집', requires: 'pptReady' },
  { id: 'fill',     label: '3. 채우기', requires: null },
]

export default function Header({
  connection, tools, selectedTool, onToolChange,
  page, onNavigate, pptReady,
}) {
  const isPptPage = PPT_STEPS.some(s => s.id === page)

  return (
    <header className="header">
      <span className="header-logo">✨ AgentiKit</span>
      <ConnectionBadge connection={connection} />

      <div className="nav-group-row">
        <button
          className={`nav-tab nav-tab-standalone${page === 'mcp' ? ' active' : ''}`}
          onClick={() => onNavigate('mcp')}
          title="MCP 도구 테스터 (기본)"
        >
          MCP
        </button>

        <div className={`ppt-studio-group${isPptPage ? ' active' : ''}`}>
          <span className="ppt-studio-label">PPT Studio</span>
          <div className="ppt-studio-steps">
            {PPT_STEPS.map((step, i) => {
              const blocked = step.requires === 'pptReady' && !pptReady
              return (
                <div key={step.id} className="ppt-studio-step-wrap">
                  {i > 0 && <span className="ppt-studio-sep" aria-hidden>▸</span>}
                  <button
                    className={`ppt-studio-step${page === step.id ? ' active' : ''}${blocked ? ' blocked' : ''}`}
                    onClick={() => onNavigate(step.id)}
                    disabled={blocked}
                    title={blocked ? 'PPTX를 먼저 업로드하세요' : ''}
                  >
                    {step.label}
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <div className="header-spacer" />
      {page === 'mcp' && (
        <ToolSelector tools={tools} selected={selectedTool} onChange={onToolChange} />
      )}
    </header>
  )
}
