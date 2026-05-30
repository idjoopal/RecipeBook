import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import ConsoleHeader from './ConsoleHeader.jsx'
import ConsoleSidebar from './ConsoleSidebar.jsx'
import SettingsModal from '../components/SettingsModal.jsx'
import { useMcp } from '../context/McpContext.jsx'

export default function AppShell() {
  const { handleRestart } = useMcp()
  const [showSettings, setShowSettings] = useState(false)

  return (
    <div className="console-layout">
      <ConsoleHeader onOpenSettings={() => setShowSettings(true)} />
      <div className="console-body">
        <ConsoleSidebar />
        <main className="console-main">
          <Outlet />
        </main>
      </div>

      {showSettings && (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          onRestart={handleRestart}
        />
      )}
    </div>
  )
}
