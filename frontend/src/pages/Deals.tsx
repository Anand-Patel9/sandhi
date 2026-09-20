import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { Icon } from '../components/icons'
import { Stamp } from '../components/Stamp'
import { api, type Negotiation, type Party, type Scenario, type User } from '../lib/api'
import { useAuth } from '../lib/auth'
import {
  PARTY_COLOR, clockTime, count, financingLine, isLive, pendingRoles, relativeTime, sentence, termsLine,
} from '../lib/format'
import { useAsync, useCatalog } from '../lib/hooks'

type Filter = 'all' | 'sign' | 'live' | 'settled' | 'closed'

function canSign(n: Negotiation, user: User | null): boolean {
  if (!user || n.status !== 'awaiting_approval') return false
  const pending = pendingRoles(n)
  return user.org.kind === 'platform' ? pending.length > 0 : pending.includes(user.org.kind as Party)
}

function describe(n: Negotiation, sc: Scenario | undefined) {
  const t = n.outcome?.terms
  const settle = sc?.spec.treds_settlement_days ?? 2
  if (isLive(n)) return ['Negotiation in progress', 'Agents are exchanging offers now']
  if (n.status === 'cancelled') return ['Stopped before agreement', 'No terms were agreed']
  if (n.status === 'failed') return ['The negotiation could not finish', n.error ?? 'Technical error']
  if (n.status === 'no_deal') return [`No price both sides could accept in ${n.outcome?.round ?? ''} rounds`, 'Each party kept its outside option']
  if (!t) return ['', '']
  if (n.status === 'rejected') {
    const who = n.approvals.find((a) => a.decision === 'reject')?.role ?? 'a party'
    return [termsLine(t), `Rejected by the ${who}`]
  }
  return [termsLine(t), financingLine(t, settle)]
}

function when(n: Negotiation): string {
  if (isLive(n)) return 'Live now'
  if (n.status === 'awaiting_approval') return `Agreed in round ${n.outcome?.round}, ${relativeTime(n.finished_at)}`
  if (n.status === 'agreed') {
    const last = n.approvals[n.approvals.length - 1]
    return `Signed ${last ? clockTime(last.created_at) : relativeTime(n.finished_at)}`
  }
  return `Closed ${relativeTime(n.finished_at ?? n.created_at)}`
}

export function Deals() {
  const { user } = useAuth()
  const catalog = useCatalog()
  const deals = useAsync(api.negotiations, [])
  const [filter, setFilter] = useState<Filter>('all')

  const list = useMemo(() => deals.data ?? [], [deals.data])
  const anyLive = list.some(isLive)
  const reload = deals.reload
  useEffect(() => {
    if (!anyLive) return
    const t = window.setInterval(() => void reload(), 3000)
    return () => window.clearInterval(t)
  }, [anyLive, reload])

  const scenarios = useMemo(() => new Map((catalog.data?.scenarios ?? []).map((s) => [s.key, s])), [catalog.data])
  const counterpartRole: Party = user?.org.kind === 'supplier' ? 'buyer' : 'supplier'

  const groups: Record<Filter, Negotiation[]> = {
    all: list,
    sign: list.filter((n) => canSign(n, user)),
    live: list.filter(isLive),
    settled: list.filter((n) => n.status === 'agreed'),
    closed: list.filter((n) => ['no_deal', 'rejected', 'cancelled', 'failed'].includes(n.status)),
  }
  const tabs: [Filter, string][] = [
    ['all', 'All'], ['sign', 'Needs your sign-off'], ['live', 'Negotiating'], ['settled', 'Settled'], ['closed', 'Closed without a deal'],
  ]
  const attention = groups.sign[0]
  const shown = groups[filter]

  return (
    <main className="main">
      <div className="page-head">
        <div>
          <h1>Deals</h1>
          <p>Every agreement your agent is negotiating or has closed.</p>
        </div>
        <Link to="/new" className="btn btn-primary btn-lg"><Icon name="plus" size={18} strokeWidth={2} />Start a negotiation</Link>
      </div>

      {attention && (
        <div className="notice" style={{ alignItems: 'center', justifyContent: 'space-between', padding: '18px 22px', borderRadius: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Stamp status="awaiting_approval" />
            <p style={{ margin: 0, fontSize: 16, lineHeight: 1.5 }}>
              <strong>{sentence(scenarios.get(attention.scenario_key)?.spec.item ?? attention.title)}</strong>
              {' '}is agreed by the agents and waits for your approval.
              {attention.approvals.length > 0 && ` ${attention.approvals.length} of ${attention.outcome?.required_approvals?.length} parties have signed.`}
            </p>
          </div>
          <Link to={`/deals/${attention.id}`} className="btn btn-primary" style={{ flexShrink: 0 }}>Review and sign</Link>
        </div>
      )}

      <div role="group" aria-label="Filter deals" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {tabs.map(([key, label]) => (
          <button key={key} type="button" className="pill" aria-pressed={filter === key} onClick={() => setFilter(key)}>
            {label}<span className="count">{groups[key].length}</span>
          </button>
        ))}
      </div>

      <div className="panel ledger">
        <div className="ledger-row ledger-head">
          <span>Goods</span><span className="hide-md">{counterpartRole === 'buyer' ? 'Buyer' : 'Supplier'}</span>
          <span className="hide-md">Terms</span><span>Status</span><span className="hide-md">Updated</span><span />
        </div>
        {deals.loading && !deals.data && [0, 1, 2].map((i) => (
          <div key={i} className="ledger-row"><div className="skeleton" style={{ height: 40, gridColumn: '1 / -1' }} /></div>
        ))}
        {deals.error && <div className="empty"><p className="error-text">{deals.error}</p><button type="button" className="btn btn-secondary" onClick={() => void deals.reload()}>Try again</button></div>}
        {deals.data && shown.length === 0 && (
          <div className="empty">
            <strong style={{ fontSize: 18 }}>{filter === 'all' ? 'No deals yet' : 'Nothing here right now'}</strong>
            <p>{filter === 'all'
              ? 'Start a negotiation and your agent will open talks with the supplier and the financier.'
              : 'Deals move into this list as their status changes.'}</p>
            {filter === 'all' && <Link to="/new" className="btn btn-primary">Start a negotiation</Link>}
          </div>
        )}
        {shown.map((n) => {
          const sc = scenarios.get(n.scenario_key)
          const [line1, line2] = describe(n, sc)
          const sign = canSign(n, user)
          const action = sign ? 'Sign off' : isLive(n) ? 'Watch' : n.status === 'agreed' ? 'Term sheet' : 'Review'
          return (
            <div key={n.id} className={`ledger-row${sign ? ' attention' : ''}`}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span className="primary">{sentence(sc?.spec.item ?? n.title)}</span>
                <span className="secondary num">{sc ? `${count(sc.spec.quantity)} units` : ''}</span>
              </div>
              <div className="hide-md" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span className="dot" style={{ background: PARTY_COLOR[counterpartRole] }} />
                <span style={{ fontSize: 15 }}>{sc?.parties[counterpartRole]}</span>
              </div>
              <div className="hide-md" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span className="num" style={{ fontSize: 15 }}>{line1}</span>
                <span className="secondary">{line2}</span>
              </div>
              <div><Stamp status={n.status} /></div>
              <div className="hide-md secondary">{when(n)}</div>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Link to={`/deals/${n.id}`} className={`btn btn-sm ${sign ? 'btn-primary' : 'btn-secondary'}`}>{action}</Link>
              </div>
            </div>
          )
        })}
      </div>
    </main>
  )
}