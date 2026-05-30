import { useState, useEffect } from 'react'

function EnvTable({ entries, onChange }) {
  const [revealed, setRevealed] = useState({})

  return (
    <table className="env-table">
      <thead>
        <tr>
          <th>Key</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry, i) => (
          <tr key={entry.key}>
            <td><span className="env-key">{entry.key}</span></td>
            <td>
              <div className="env-value-cell">
                <input
                  className="env-value-input"
                  type={entry.sensitive && !revealed[i] ? 'password' : 'text'}
                  value={entry.value}
                  onChange={e => onChange(i, e.target.value)}
                />
                {entry.sensitive && (
                  <button
                    className="env-toggle-btn"
                    onClick={() => setRevealed(r => ({ ...r, [i]: !r[i] }))}
                  >
                    {revealed[i] ? 'Hide' : 'Show'}
                  </button>
                )}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function SettingsModal({ onClose, onRestart }) {
  const [files, setFiles] = useState([])
  const [activeTab, setActiveTab] = useState(0)
  const [saving, setSaving] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [savedMsg, setSavedMsg] = useState('')

  useEffect(() => {
    fetch('/api/admin/env')
      .then(r => r.json())
      .then(data => setFiles(data.files ?? []))
      .catch(() => setFiles([]))
  }, [])

  function updateEntry(fileIdx, entryIdx, value) {
    setFiles(prev => prev.map((f, fi) =>
      fi !== fileIdx ? f : {
        ...f,
        entries: f.entries.map((e, ei) => ei !== entryIdx ? e : { ...e, value }),
      }
    ))
  }

  async function handleSave() {
    const file = files[activeTab]
    if (!file) return
    setSaving(true)
    setSavedMsg('')
    try {
      const res = await fetch('/api/admin/env', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id: file.id, entries: file.entries }),
      })
      if (res.ok) setSavedMsg('저장됨')
      else setSavedMsg('저장 실패')
    } catch {
      setSavedMsg('저장 실패')
    } finally {
      setSaving(false)
    }
  }

  async function handleRestart() {
    setRestarting(true)
    try {
      await fetch('/api/admin/restart', { method: 'POST' })
    } catch (_) {}
    onClose()
    onRestart()
  }

  const current = files[activeTab]

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">⚙ Environment Settings</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {files.length > 0 && (
          <div className="modal-tabs">
            {files.map((f, i) => (
              <button
                key={f.id}
                className={`modal-tab ${i === activeTab ? 'active' : ''}`}
                onClick={() => { setActiveTab(i); setSavedMsg('') }}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}

        <div className="modal-body">
          {!current ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>로딩 중...</div>
          ) : current.entries.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              .env 파일이 없습니다. .env.example을 참고해 직접 생성하세요.
            </div>
          ) : (
            <EnvTable
              entries={current.entries}
              onChange={(i, v) => updateEntry(activeTab, i, v)}
            />
          )}
        </div>

        <div className="modal-footer">
          <span className="modal-footer-hint">
            {restarting ? '재기동 중... 잠시 후 자동 재연결됩니다.' : savedMsg || '변경 후 Save → Restart로 적용'}
          </span>
          <div className="modal-footer-actions">
            <button className="btn btn-ghost" onClick={onClose}>닫기</button>
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={saving || !current || current.entries.length === 0}
            >
              {saving ? '저장 중...' : 'Save'}
            </button>
            <button
              className="btn btn-danger"
              onClick={handleRestart}
              disabled={restarting}
            >
              {restarting ? <span className="spinner" /> : 'Restart Server'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
