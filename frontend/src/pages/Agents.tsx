import { api } from '../lib/api'
import { PARTY_COLOR } from '../lib/format'
import { useAsync } from '../lib/hooks'

export function Agents() {
  const agents = useAsync(api.agents, [])
  return (
    <main className="main" style={{ maxWidth: 1180 }}>
      <div className="page-head">
        <div>
          <h1>Agents</h1>
          <p>Each party's agent is its own A2A server. Other systems discover it through its public Agent Card.</p>
        </div>
      </div>
      {agents.error && <p className="error-text">{agents.error}</p>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {!agents.data && !agents.error && [0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 150 }} />)}
        {agents.data?.map((a) => {
          const iface = a.card.supportedInterfaces[0]
          return (
            <section key={a.role} className="panel panel-pad" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', gap: 14 }}>
                  <span className="dot" style={{ background: PARTY_COLOR[a.role], marginTop: 8 }} />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <strong style={{ fontSize: 18 }}>{a.card.name}</strong>
                    <span className="muted" style={{ fontSize: 15, maxWidth: '70ch' }}>{a.card.description}</span>
                  </div>
                </div>
                <a className="btn btn-secondary btn-sm" href={a.card_url} target="_blank" rel="noreferrer">Open Agent Card</a>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '140px minmax(0, 1fr)', gap: '8px 16px', fontSize: 14 }}>
                <span className="muted">Endpoint</span><span className="code" style={{ overflowWrap: 'anywhere' }}>{iface?.url}</span>
                <span className="muted">Protocol</span><span>A2A {iface?.protocolVersion} over {iface?.protocolBinding}</span>
                <span className="muted">Version</span><span>{a.card.version}</span>
              </div>
              <div className="chips">{a.card.skills.map((s) => <span key={s.id} className="chip" title={s.description}>{s.name}</span>)}</div>
            </section>
          )
        })}
      </div>
    </main>
  )
}