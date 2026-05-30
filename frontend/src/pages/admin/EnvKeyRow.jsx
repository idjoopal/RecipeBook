import { useState } from 'react'

/**
 * env 키 한 줄 — 키 라벨 + 값 input.
 * 민감키(entry.sensitive)는 password로 마스킹하고 Show/Hide 토글 제공.
 * @param {{ entry: {key, value, sensitive}, onChange: (value:string)=>void }} props
 */
export default function EnvKeyRow({ entry, onChange }) {
  const [revealed, setRevealed] = useState(false)
  const masked = entry.sensitive && !revealed

  return (
    <div className="env-row">
      <label className="env-row-key" title={entry.key}>{entry.key}</label>
      <div className="env-row-value">
        <input
          className="env-row-input"
          type={masked ? 'password' : 'text'}
          value={entry.value}
          placeholder="(빈 값)"
          onChange={e => onChange(e.target.value)}
        />
        {entry.sensitive && (
          <button
            type="button"
            className="env-row-reveal"
            onClick={() => setRevealed(v => !v)}
          >
            {revealed ? 'Hide' : 'Show'}
          </button>
        )}
      </div>
    </div>
  )
}
