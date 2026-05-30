export default function Message({ message }) {
  const { role, content, meta, error } = message
  const type = error ? 'error' : role

  return (
    <div className={`message ${type}`}>
      <div className="message-meta">
        {role === 'user' ? (
          '💬 you'
        ) : error ? (
          '⚠ error'
        ) : (
          <>
            🤖 <span className="tool-label">{meta?.tool ?? 'assistant'}</span>
            {meta?.elapsed != null && (
              <span style={{ color: 'var(--text-muted)' }}>
                {' '}(tools/call · {meta.elapsed}ms)
              </span>
            )}
          </>
        )}
      </div>
      <div className="message-bubble">{content}</div>
    </div>
  )
}
