import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useMcp } from '../context/McpContext.jsx'
import { resolveAgents } from '../lib/agentRegistry.js'
import { getReadiness, getEnv, getRestApiCount, findEnvValue } from '../lib/consoleApi.js'
import ExternalStores from '../components/ExternalStores.jsx'

const CONSOLE_NAME = 'Prebuilt Agent Console'
const CONSOLE_TAGLINE = '우리 환경에 맞춰진 에이전트 패키지 — 시연부터 자산 큐레이션, 운영 관제까지 한 곳에서.'

const READY_LABEL = {
  ok: '정상',
  error: '이슈 있음',
  unknown: '확인 불가',
}

export default function OverviewPage() {
  const { connection, tools, disabledTools } = useMcp()
  const agents = resolveAgents(tools)
  const firstAgent = agents[0]?.name

  const [readiness, setReadiness] = useState({ status: 'unknown', components: {}, reachable: false })
  const [envFiles, setEnvFiles] = useState([])
  const [restApiCount, setRestApiCount] = useState(null)
  const [audience, setAudience] = useState('operator') // 'operator' | 'user'

  useEffect(() => {
    let alive = true
    Promise.all([getReadiness(), getEnv(), getRestApiCount()]).then(([r, e, apiCount]) => {
      if (!alive) return
      setReadiness(r)
      setEnvFiles(e.files)
      setRestApiCount(apiCount)
    })
    return () => { alive = false }
  }, [connection.status])

  const tenant =
    findEnvValue(envFiles, ['CLIENT_NAME', 'TENANT', 'TENANT_NAME', 'CUSTOMER', 'CUSTOMER_NAME']) ||
    connection.serverInfo?.name ||
    null

  return (
    <div className="overview">
      {/* A. 헤더 */}
      <header className="ov-hero">
        <div>
          <h1 className="ov-title">{CONSOLE_NAME}</h1>
          <p className="ov-tagline">{CONSOLE_TAGLINE}</p>
        </div>
        {tenant && <span className="ov-tenant">🏢 {tenant}</span>}
      </header>

      {/* B. 시스템 상태 요약 */}
      <section className="ov-section">
        <div className="ov-metrics">
          <MetricCard label="등록 에이전트" value={tools.length} hint="MCP tools/list" />
          <MetricCard label="REST API" value={restApiCount ?? '—'} hint="/openapi.json" />
          <MetricCard
            label="시스템 상태"
            value={READY_LABEL[readiness.status] ?? readiness.status}
            tone={readiness.status === 'ok' ? 'ok' : readiness.status === 'error' ? 'error' : 'muted'}
            hint="/health/ready"
          />
        </div>

      </section>

      {/* B-2. 외부 저장소 연결 (실시간 상태) */}
      <section className="ov-section">
        <h2 className="ov-section-title">외부 저장소 연결</h2>
        <ExternalStores components={readiness.components} />
      </section>

      {/* C. Agents 카드 그리드 */}
      <section className="ov-section">
        <h2 className="ov-section-title">에이전트</h2>
        <div className="ov-agent-grid">
          {agents.length === 0 && (
            <div className="ov-component-empty">
              {connection.status === 'ready' ? '등록된 에이전트가 없습니다.' : '에이전트를 불러오는 중…'}
            </div>
          )}
          {agents.map(a => (
            <div key={a.name} className="ov-agent-card">
              <div className="ov-agent-head">
                <span className="ov-agent-icon">{a.icon}</span>
                <span className="ov-agent-name">{a.label}</span>
                {disabledTools.has(a.name) && <span className="ov-agent-tag">비활성</span>}
              </div>
              <code className="ov-agent-toolname">{a.name}</code>
              <p className="ov-agent-desc">{a.description}</p>
              <div className="ov-agent-actions">
                <Link to={`/agents/${a.name}`} className="ov-link">자세히 →</Link>
                {a.workspaceRoute && (
                  <Link to={a.workspaceRoute} className="ov-link ov-link-muted">
                    {a.workspaceLabel || 'Workspace'} →
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* D. 시작하기 가이드 (운영자/사용자 토글) */}
      <section className="ov-section">
        <div className="ov-getstarted-head">
          <h2 className="ov-section-title">시작하기</h2>
          <div className="ov-toggle">
            <button
              className={audience === 'operator' ? 'active' : ''}
              onClick={() => setAudience('operator')}
            >운영자</button>
            <button
              className={audience === 'user' ? 'active' : ''}
              onClick={() => setAudience('user')}
            >사용자</button>
          </div>
        </div>
        <ol className="ov-steps">
          {(audience === 'operator' ? operatorSteps(firstAgent) : userSteps(firstAgent)).map((s, i) => (
            <li key={i} className="ov-step">
              <span className="ov-step-num">{i + 1}</span>
              <span className="ov-step-text">{s.text}</span>
              {s.to && <Link to={s.to} className="ov-link">이동 →</Link>}
            </li>
          ))}
        </ol>
      </section>

      {/* G. 도움말 / 문서 링크 */}
      <footer className="ov-footer">
        <a href="/docs" target="_blank" rel="noreferrer">📘 API 문서 (Swagger)</a>
        <a href="/redoc" target="_blank" rel="noreferrer">📗 API 레퍼런스 (ReDoc)</a>
      </footer>
    </div>
  )
}

function MetricCard({ label, value, hint, tone = 'default' }) {
  return (
    <div className={`ov-metric tone-${tone}`}>
      <div className="ov-metric-value">{value}</div>
      <div className="ov-metric-label">{label}</div>
      {hint && <div className="ov-metric-hint">{hint}</div>}
    </div>
  )
}

function operatorSteps(firstAgent) {
  const agentTo = firstAgent ? `/agents/${firstAgent}` : '/'
  return [
    { text: 'LLM API Key 등록', to: '/admin' },
    { text: '공용 저장소 연결 확인', to: '/admin' },
    { text: '에이전트 활성화·리소스 연결', to: agentTo },
    { text: 'Test 탭에서 동작 확인', to: agentTo },
  ]
}

function userSteps(firstAgent) {
  const agentTo = firstAgent ? `/agents/${firstAgent}` : '/'
  return [
    { text: '사용할 에이전트 선택', to: agentTo },
    { text: '엔드포인트(MCP/REST URL) 복사', to: agentTo },
    { text: 'MCP 클라이언트에 등록', to: null },
    { text: '호출 테스트', to: agentTo },
  ]
}
