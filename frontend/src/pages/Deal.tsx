import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { Stamp } from '../components/Stamp'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { count, isLive, sentence } from '../lib/format'
import { useCatalog, useNegotiation } from '../lib/hooks'
import { Room } from './Room'
import { Signoff } from './Signoff'

export function Deal() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const catalog = useCatalog()
  const { negotiation: n, setNegotiation, events, error, refresh, reloadEvents } = useNegotiation(id)
  const [view, setView] = useState<'deal' | 'talks'>('deal')
  const [toast, setToast] = useState<string | null>(null)
  const [stopping, setStopping] = useState(false)

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 3200)
    return () => window.clearTimeout(t)
  }, [toast])

  const scenario = catalog.data?.scenarios.find((s) => s.key === n?.scenario_key)

  if (error) {
    return (
      <main className="main">
        <Link to="/" className="crumb">Deals</Link>
        <div className="panel empty"><strong style={{ fontSize: 18 }}>This deal could not be loaded</strong><p>{error}</p>
          <button type="button" className="btn btn-secondary" onClick={() => void refresh()}>Try again</button></div>
      </main>
    )
  }
  if (!n || !scenario || !user) {
    return (
      <main className="main main-tight">
        <div className="skeleton" style={{ height: 70, maxWidth: 640 }} />
        <div className="skeleton" style={{ height: 90 }} />
        <div className="skeleton" style={{ height: 480 }} />
      </main>
    )
  }

  const live = isLive(n)
  const showTalks = live || view === 'talks'
  const subtitle = live
    ? `${scenario.parties.supplier}, ${scenario.parties.buyer} and ${scenario.parties.financier} are negotiating through their agents.`
    : n.status === 'awaiting_approval' ? `The agents agreed in round ${n.outcome?.round}. Nothing is binding until every party signs.`
      : n.status === 'agreed' ? 'Every party has signed. The agreement is final.'
        : n.status === 'rejected' ? 'A party rejected the agreed terms, so nothing is binding.'
          : n.status === 'no_deal' ? 'The agents did not reach terms every party prefers to walking away.'
            : n.status === 'cancelled' ? 'This negotiation was stopped before an agreement.'
              : 'This negotiation ended with an error.'

  const stop = async () => {
    setStopping(true)
    try {
      await api.cancel(n.id)
      setToast('Stopping the negotiation')
    } catch (e) {
      setToast(e instanceof Error ? e.message : 'Could not stop the negotiation')
    } finally {
      setStopping(false)
    }
  }

  return (
    <main className="main main-tight">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 24, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Link to="/" className="crumb">Deals</Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
            <h1 className="deal-title">{sentence(scenario.spec.item)}, {count(scenario.spec.quantity)} units</h1>
            {showTalks && <Stamp status={n.status} />}
          </div>
          <p style={{ margin: 0, fontSize: 16, color: 'var(--muted)', maxWidth: '70ch' }}>{subtitle}</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {live && (
            <button type="button" className="btn btn-danger" onClick={() => void stop()} disabled={stopping}>
              {stopping ? 'Stopping…' : 'Stop negotiation'}
            </button>
          )}
          {!live && (
            <button type="button" className="btn btn-secondary" onClick={() => setView(view === 'deal' ? 'talks' : 'deal')}>
              {view === 'deal' ? 'View the negotiation' : 'Back to the agreement'}
            </button>
          )}
          {!showTalks && <span style={{ marginTop: 6 }}><Stamp status={n.status} large /></span>}
        </div>
      </div>

      {showTalks
        ? <Room negotiation={n} events={events} scenario={scenario} />
        : <Signoff negotiation={n} scenario={scenario} user={user} notify={setToast}
            onChanged={(updated) => { setNegotiation(updated); void reloadEvents() }} />}

      {toast && <div className="toast" role="status">{toast}</div>}
    </main>
  )
}