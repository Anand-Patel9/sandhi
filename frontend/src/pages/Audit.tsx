import { useState } from 'react'
import { Link } from 'react-router'
import { Stamp } from '../components/Stamp'
import { api, type AuditResult } from '../lib/api'
import { relativeTime, sentence } from '../lib/format'
import { useAsync, useCatalog } from '../lib/hooks'

export function Audit() {
  const deals = useAsync(api.negotiations, [])
  const catalog = useCatalog()
  const [results, setResults] = useState<Record<string, AuditResult | string>>({})
  const [checking, setChecking] = useState<string | null>(null)

  const verify = async (id: string) => {
    setChecking(id)
    try {
      const r = await api.audit(id)
      setResults((prev) => ({ ...prev, [id]: r }))
    } catch (e) {
      setResults((prev) => ({ ...prev, [id]: e instanceof Error ? e.message : 'Check failed' }))
    } finally {
      setChecking(null)
    }
  }
  const items = (s: string) => catalog.data?.scenarios.find((x) => x.key === s)?.spec.item ?? s

  return (
    <main className="main" style={{ maxWidth: 1180 }}>
      <div className="page-head">
        <div>
          <h1>Audit</h1>
          <p>Every event in a negotiation is sealed with a SHA-256 fingerprint of itself and the entry before. Verify any deal's log here.</p>
        </div>
      </div>
      <div className="panel ledger">
        {deals.data?.length === 0 && <div className="empty"><p>No negotiations yet.</p></div>}
        {deals.data?.map((n) => {
          const r = results[n.id]
          return (
            <div key={n.id} className="ledger-row" style={{ gridTemplateColumns: 'minmax(0, 1fr) 170px minmax(0, 1.4fr) 120px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Link to={`/deals/${n.id}`} className="primary" style={{ color: 'var(--ink)' }}>{sentence(items(n.scenario_key))}</Link>
                <span className="secondary">{relativeTime(n.created_at)}</span>
              </div>
              <div><Stamp status={n.status} /></div>
              <div style={{ fontSize: 14 }}>
                {typeof r === 'string' && <span className="error-text">{r}</span>}
                {r && typeof r !== 'string' && (r.valid
                  ? <span style={{ color: 'var(--financier-ink)' }}><strong>Intact.</strong> {r.events} events, head <span className="code">{r.head_hash.slice(0, 12)}…</span></span>
                  : <span style={{ color: 'var(--stamp)' }}><strong>Altered.</strong> Entry {r.broken_at_seq} does not match its fingerprint.</span>)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => void verify(n.id)} disabled={checking === n.id}>
                  {checking === n.id ? 'Checking…' : 'Verify'}
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </main>
  )
}