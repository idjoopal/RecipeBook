import { Routes, Route, Navigate } from 'react-router-dom'
import { McpProvider } from './context/McpContext.jsx'
import AppShell from './shell/AppShell.jsx'
import OverviewPage from './pages/OverviewPage.jsx'
import GlobalAdminPage from './pages/GlobalAdminPage.jsx'
import AgentDetailPage from './pages/AgentDetailPage.jsx'
import { WORKSPACE_ROUTES } from './lib/agentRegistry.js'

export default function App() {
  return (
    <McpProvider>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/admin" element={<GlobalAdminPage />} />
          <Route path="/agents/:agentName" element={<AgentDetailPage />} />
          {/* 워크스페이스 라우트는 각 에이전트 manifest에서 자동 수집된다. */}
          {WORKSPACE_ROUTES.map(w => (
            <Route key={w.route} path={w.route} element={<w.Component />} />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </McpProvider>
  )
}
