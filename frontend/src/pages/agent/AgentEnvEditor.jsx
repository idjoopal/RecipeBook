import { useState, useEffect, useCallback } from 'react'
import { useMcp } from '../../context/McpContext.jsx'
import { getEnv, saveEnvFile, restartServer } from '../../lib/consoleApi.js'
import { groupByScope } from '../../lib/adminConfig.js'
import EnvKeyRow from '../admin/EnvKeyRow.jsx'

/**
 * 에이전트 전용 env 편집기 — Global Admin의 편집 로직을 fileIds 범위로 좁혀 재사용.
 * @param {{ fileIds: string[] }} props  편집 대상 env 파일 id 목록 (예: ['agent_nl2sql'])
 */
export default function AgentEnvEditor({ fileIds = [] }) {
  const { handleRestart } = useMcp()
  const [files, setFiles] = useState([])      // fileIds로 필터된 파일들
  const [loaded, setLoaded] = useState(false)
  const [dirty, setDirty] = useState(() => new Set())
  const [saving, setSaving] = useState(false)
  const [needRestart, setNeedRestart] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    let alive = true
    getEnv().then(({ files }) => {
      if (!alive) return
      setFiles((files || []).filter(f => fileIds.includes(f.id)))
      setLoaded(true)
    }).catch(() => { if (alive) { setLoaded(true); setErrorMsg('env를 불러오지 못했습니다.') } })
    return () => { alive = false }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileIds.join(',')])

  const updateEntry = useCallback((fileIdx, entryIdx, value) => {
    setFiles(prev => {
      const fileId = prev[fileIdx]?.id
      if (fileId) setDirty(d => new Set(d).add(fileId))
      return prev.map((f, fi) =>
        fi !== fileIdx ? f : {
          ...f,
          entries: f.entries.map((e, ei) => ei !== entryIdx ? e : { ...e, value }),
        },
      )
    })
    setNeedRestart(false)
  }, [])

  async function handleSave() {
    setSaving(true); setErrorMsg('')
    const targets = files.filter(f => dirty.has(f.id))
    const results = await Promise.all(targets.map(f => saveEnvFile(f.id, f.entries)))
    setSaving(false)
    if (results.every(r => r.ok)) {
      setDirty(new Set())
      setNeedRestart(true)
    } else {
      setErrorMsg('일부 파일 저장에 실패했습니다.')
    }
  }

  async function handleApplyRestart() {
    setRestarting(true)
    await restartServer()
    setNeedRestart(false)
    handleRestart()
  }

  if (!loaded) return <div className="placeholder-note">설정을 불러오는 중…</div>
  if (files.length === 0) {
    return <div className="placeholder-note">이 에이전트는 편집할 전용 env가 없습니다.</div>
  }

  const scopes = groupByScope(files)
  const hasDirty = dirty.size > 0

  const renderItem = ({ fileIdx, entryIdx, entry }) => (
    <EnvKeyRow
      key={`${fileIdx}:${entry.key}`}
      entry={entry}
      onChange={v => updateEntry(fileIdx, entryIdx, v)}
    />
  )

  return (
    <div className="agent-env-editor">
      {(hasDirty || needRestart || restarting || errorMsg) && (
        <div className={`ga-savebar${needRestart ? ' restart' : ''}`}>
          <span className="ga-savebar-msg">
            {restarting ? '재기동 중… 잠시 후 자동 재연결됩니다.'
              : errorMsg ? `⚠ ${errorMsg}`
              : needRestart ? '저장됨 — 변경을 적용하려면 서버 재기동이 필요합니다.'
              : `변경된 파일 ${dirty.size}개`}
          </span>
          <div className="ga-savebar-actions">
            {hasDirty && (
              <button className="btn-primary-sm" onClick={handleSave} disabled={saving}>
                {saving ? '저장 중…' : '변경 저장'}
              </button>
            )}
            {needRestart && (
              <button className="btn-danger-sm" onClick={handleApplyRestart} disabled={restarting}>
                서버 재기동
              </button>
            )}
          </div>
        </div>
      )}

      {scopes.map(group => {
        const { llmItems, otherItems } = group
        const showSubTitles = llmItems.length > 0 && otherItems.length > 0
        return (
          <div key={group.id} className="ga-scope-card">
            <div className="ga-scope-head">
              <span className="ga-scope-icon">{group.icon}</span>
              <span className="ga-scope-title">{group.label}</span>
              <code className="ga-scope-file">{group.sub}</code>
              {dirty.has(group.id) && <span className="ga-scope-badge">변경됨</span>}
            </div>
            <div className="ga-scope-body">
              {llmItems.length > 0 && (
                <>
                  {showSubTitles && <div className="ga-subgroup-title">모델 · LLM</div>}
                  {llmItems.map(renderItem)}
                </>
              )}
              {otherItems.length > 0 && (
                <>
                  {showSubTitles && <div className="ga-subgroup-title">기타</div>}
                  {otherItems.map(renderItem)}
                </>
              )}
              {llmItems.length === 0 && otherItems.length === 0 && (
                <div className="placeholder-note">설정 키가 없습니다.</div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
