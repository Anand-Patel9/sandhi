import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'

const ABOUT: Record<string, [string, string]> = {
  compliance: ['Payment rules', 'Checks every offer against the MSMED Act 45-day limit and Section 43B(h).'],
  treds: ['TReDS market rates', 'Indicative discount-rate bands by buyer credit rating, and the TReDS platforms.'],
  erp: ['Company ledger', "Reads the supplier's cash balance and outflow so its agent knows its real runway."],
}

export function DataSources() {
  const tools = useAsync(api.tools, [])
  return (
    <main className="main" style={{ maxWidth: 1180 }}>
      <div className="page-head">
        <div>
          <h1>Data sources</h1>
          <p>Agents reach live data through Model Context Protocol servers. Point one at your own ERP and the agents use it unchanged.</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => void tools.reload()}>Check again</button>
      </div>
      {tools.error && <p className="error-text">{tools.error}</p>}
      <div className="grid-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        {!tools.data && !tools.error && [0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 220 }} />)}
        {tools.data?.map((s) => {
          const [title, about] = ABOUT[s.server] ?? [s.server, '']
          const online = s.status === 'online'
          return (
            <section key={s.server} className="panel panel-pad" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                <strong style={{ fontSize: 18 }}>{title}</strong>
                <span className={`stamp ${online ? 'stamp-settled' : 'stamp-red'}`} style={{ fontSize: 12 }}>{online ? 'Online' : 'Offline'}</span>
              </div>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, color: 'var(--ink-2)' }}>{about}</p>
              <span className="code muted" style={{ overflowWrap: 'anywhere' }}>{s.url}</span>
              <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {s.tools.map((t) => (
                  <li key={t.name} style={{ borderTop: '1px solid var(--rule-soft)', paddingTop: 8 }}>
                    <span className="code" style={{ fontWeight: 600 }}>{t.name}</span>
                    <span style={{ display: 'block', fontSize: 13, color: 'var(--muted)', lineHeight: 1.45 }}>{t.description}</span>
                  </li>
                ))}
              </ul>
              {!online && <p className="error-text" style={{ margin: 0 }}>{s.error}</p>}
            </section>
          )
        })}
      </div>
    </main>
  )
}