export default function ToolSelector({ tools, selected, onChange }) {
  if (tools.length === 0) return null

  return (
    <div className="tool-selector">
      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Tool:</span>
      <select value={selected} onChange={e => onChange(e.target.value)}>
        {tools.map(t => (
          <option key={t.name} value={t.name}>{t.name}</option>
        ))}
      </select>
    </div>
  )
}
