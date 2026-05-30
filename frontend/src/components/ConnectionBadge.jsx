export default function ConnectionBadge({ connection }) {
  const { status, sessionId } = connection

  const label = {
    connecting: '연결 중...',
    ready: `Connected · ${sessionId ? sessionId.slice(0, 8) + '…' : ''}`,
    restarting: '재기동 중...',
    error: '연결 오류',
  }[status] ?? status

  return (
    <div className="connection-badge">
      <span className={`status-dot ${status}`} />
      <span>{label}</span>
    </div>
  )
}
