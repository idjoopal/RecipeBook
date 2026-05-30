import { useState, useEffect, useCallback } from 'react'
import { useMcp } from '../context/McpContext.jsx'
import { getEnv, saveEnvFile, restartServer } from '../lib/consoleApi.js'
import { groupByScope } from '../lib/adminConfig.js'
import EnvKeyRow from './admin/EnvKeyRow.jsx'
import ExternalStores from '../components/ExternalStores.jsx'

export default function GlobalAdminPage() {
  const { handleRestart } = useMcp()
  const [files, setFiles] = useState([])
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
      setFiles(files)
      setLoaded(true)
    })
    return () => { alive = false }
  }, [])

  const updateEntry = useCallback((fileIdx, entryIdx, value) => {
    setFiles(prev => {
      const fileId = prev[fileIdx]?.id
      if (fileId) setDirty(d => new Set(d).add(fileId))
      return prev.map((f, fi) =>
        fi !== fileIdx ? f : {
          ...f,
          entries: f.entries.map((e, ei) => ei !== entryIdx ? e : { ...e, value }),
        }
      )
    })
    setNeedRestart(false)
  }, [])

  async function handleSave() {
    setSaving(true)
    setErrorMsg('')
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
    handleRestart()  // 연결 'restarting' → /health/live 폴링 후 자동 재연결 (McpContext)
  }

  const scopes = groupByScope(files)
  const rootScope = scopes.find(s => s.isRoot)
  const agentScopes = scopes.filter(s => !s.isRoot)
  const hasDirty = dirty.size > 0

  // 스코프 카드 1개 렌더 (Root/에이전트 공용)
  function renderScopeCard(group) {
    const { llmItems, otherItems } = group
    const showSubTitles = llmItems.length > 0 && otherItems.length > 0
    const renderItem = ({ fileIdx, entryIdx, entry }) => (
      <EnvKeyRow
        key={`${fileIdx}:${entry.key}`}
        entry={entry}
        onChange={v => updateEntry(fileIdx, entryIdx, v)}
      />
    )
    return (
      <div key={group.id} className={`ga-scope-card${group.isRoot ? ' root' : ''}`}>
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
  }

  return (
    <div className="global-admin">
      <header className="page-head">
        <h1 className="page-title">Global admin</h1>
        <p className="page-sub">플랫폼 전체에 공통 적용되는 인프라성 설정. 한 번 설정하면 모든 에이전트가 상속합니다.</p>
      </header>

      {/* 저장/적용 바 */}
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

      {!loaded && <div className="placeholder-note">설정을 불러오는 중…</div>}

      {loaded && (
        <>
          {/* A. 공통 설정 (Root) */}
          <section className="ga-block">
            <h3 className="ga-h">공통 설정 (Root)</h3>
            <p className="ga-block-sub">모든 에이전트가 상속하는 글로벌 인프라·LLM 설정입니다.</p>
            {rootScope
              ? renderScopeCard(rootScope)
              : <div className="placeholder-note">Root 설정을 찾을 수 없습니다.</div>}
          </section>

          {/* B. 에이전트별 설정 */}
          <section className="ga-block">
            <h3 className="ga-h">에이전트별 설정</h3>
            <p className="ga-block-sub">각 에이전트 전용 env. 카드 단위로 분리되어 다른 에이전트·Root와 독립적으로 관리됩니다.</p>
            {agentScopes.length === 0 && <div className="placeholder-note">에이전트 env가 없습니다.</div>}
            {agentScopes.map(renderScopeCard)}
          </section>

          {/* C. 외부 저장소 연결 (실시간 상태) */}
          <section className="ga-block">
            <div className="ga-block-head">
              <h3 className="ga-h">외부 저장소 연결</h3>
            </div>
            <ExternalStores showControls />
          </section>
        </>
      )}
    </div>
  )
}
