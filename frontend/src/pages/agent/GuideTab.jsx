/**
 * Guide 탭 — MCP tool의 description 원문 + inputSchema를 가독성 있게 노출.
 * 손글씨 운영/사용자 가이드는 저장소가 없어 후속 마일스톤.
 */
export default function GuideTab({ agent }) {
  const props = agent.inputSchema?.properties || {}
  const required = new Set(agent.inputSchema?.required || [])
  const propRows = Object.entries(props)

  return (
    <div className="guide-tab">
      <section className="guide-block">
        <h3 className="guide-h">도구명 (MCP tool name)</h3>
        <p><code className="mono">{agent.name}</code></p>
      </section>

      <section className="guide-block">
        <h3 className="guide-h">에이전트 설명 (MCP description)</h3>
        {agent.rawDescription ? (
          <pre className="guide-desc">{agent.rawDescription}</pre>
        ) : (
          <p className="placeholder-note">이 도구에 등록된 description이 없습니다.</p>
        )}
      </section>

      <section className="guide-block">
        <h3 className="guide-h">입력 스키마</h3>
        {propRows.length === 0 ? (
          <p className="placeholder-note">입력 스키마 정보가 없습니다.</p>
        ) : (
          <table className="guide-schema">
            <thead>
              <tr><th>파라미터</th><th>타입</th><th>필수</th><th>설명</th></tr>
            </thead>
            <tbody>
              {propRows.map(([name, def]) => (
                <tr key={name}>
                  <td className="mono">{name}</td>
                  <td className="mono">{def.type || '—'}</td>
                  <td>{required.has(name) ? '✓' : ''}</td>
                  <td>{def.description || def.title || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <p className="guide-foot placeholder-note">
        운영/사용자용 손글씨 가이드(좋은 질문 패턴, 사전 준비 등)는 콘텐츠 저장소 연동 후 추가됩니다.
      </p>
    </div>
  )
}
