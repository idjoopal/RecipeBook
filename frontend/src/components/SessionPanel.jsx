export default function SessionPanel({ connection }) {
  const { status, sessionId, protocolVersion, serverInfo } = connection

  const rows = [
    ['status', status],
    ['protocol', protocolVersion ?? '—'],
    ['session', sessionId ? sessionId.slice(0, 12) + '…' : '—'],
    ['server', serverInfo?.name ?? '—'],
  ]

  return (
    <div className="sidebar-section">
      <div className="sidebar-section-title">Session</div>
      {rows.map(([label, value]) => (
        <div className="session-row" key={label}>
          <span className="session-label">{label}</span>
          <span className="session-value">{value}</span>
        </div>
      ))}
    </div>
  )
}
