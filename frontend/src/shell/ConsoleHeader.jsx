import ConnectionBadge from '../components/ConnectionBadge.jsx'
import { useMcp } from '../context/McpContext.jsx'

export default function ConsoleHeader({ onOpenSettings }) {
  const { connection } = useMcp()
  return (
    <header className="console-header">
      <span className="header-logo">✨ AgentiKit</span>
      <span className="console-header-sub">Prebuilt Agent Console</span>
      <div className="header-spacer" />
      {/* 평상시엔 숨기고, 문제(연결 오류·재기동 중)일 때만 표시 */}
      {(connection.status === 'error' || connection.status === 'restarting') && (
        <ConnectionBadge connection={connection} />
      )}
      <button
        className="console-header-gear"
        onClick={onOpenSettings}
        title="환경설정 · 서버 재기동"
        aria-label="환경설정"
      >
        ⚙
      </button>
    </header>
  )
}
