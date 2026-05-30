import ToolsPanel from './ToolsPanel.jsx'
import SessionPanel from './SessionPanel.jsx'

export default function Sidebar({ tools, disabledTools, onToggleTool, connection, onOpenSettings }) {
  return (
    <aside className="sidebar">
      <ToolsPanel
        tools={tools}
        disabledTools={disabledTools}
        onToggleTool={onToggleTool}
        connectionStatus={connection?.status}
      />
      <SessionPanel connection={connection} />
      <button className="settings-btn" onClick={onOpenSettings}>
        ⚙ Settings
      </button>
    </aside>
  )
}
