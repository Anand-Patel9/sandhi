import { PriceChart } from '../components/PriceChart'
import { Transcript } from '../components/Transcript'
import type { Compliance, Negotiation, NegotiationEvent, Party, Scenario, Terms } from '../lib/api'
import { PARTY_COLOR, costShare, inr, isLive } from '../lib/format'
import { Icon } from '../components/icons'

interface Props {
  negotiation: Negotiation
  events: NegotiationEvent[]
  scenario: Scenario
}

function latest(events: NegotiationEvent[], agent: string): NegotiationEvent | undefined {
  return [...events].reverse().find((e) => e.kind === 'offer' && e.agent === agent)
}

function partyLines(role: Party, events: NegotiationEvent[]): [string, string] {
  const connected = events.find((e) => e.kind === 'info' && e.round === 0 && e.message.startsWith('Connected over A2A'))
  const data = events.find((e) => e.kind === 'info' && e.message.startsWith('Live data loaded over MCP'))
  const sources = ((data?.meta.sources ?? {}) as Record<string, string[]>)[role] ?? []
  const link = connected ? 'Agent connected over A2A' : 'Agent running in-process'
  if (role === 'supplier') return [link, sources.includes('erp.cash_position') ? 'Cash position read from ERP' : 'Cash position from its policy']
  if (role === 'financier') return [link, sources.includes('treds.market_rates') ? 'Rates capped by TReDS market band' : 'Rates from its policy']
  return [link, 'Every offer checked for MSMED and 43B(h)']
}

function StandCell({ t, field }: { t?: Terms | null; field: 'price' | 'days' | 'fin' | 'share' }) {
  if (!t) return <span className="muted">Waiting</span>
  if (field === 'price') return <span>{inr(t.price)}</span>
  if (field === 'days') return <span>{t.days} days</span>
  if (field === 'fin') return <span>{t.treds ? 'TReDS' : 'Direct'}</span>
  return <span>{costShare(t)}</span>
}

export function Room({ negotiation, events, scenario }: Props) {
  const live = isLive(negotiation)
  const maxRounds = negotiation.config.max_rounds ?? scenario.spec.max_rounds
  const current = Math.max(0, ...events.map((e) => e.round))
  const sup = latest(events, 'supplier')
  const buy = latest(events, 'buyer')
  const lastChecked = [...events].reverse().find((e) => e.kind === 'offer' && e.meta.compliance)
  const compliance = lastChecked?.meta.compliance as Compliance | undefined
  const bothCompliant = [sup, buy].every((e) => (e?.meta.compliance as Compliance | undefined)?.msmed_compliant)

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
          <span style={{ fontWeight: 600 }}>{live ? `Round ${Math.max(1, current)} of ${maxRounds}` : `Finished in round ${current} of ${maxRounds}`}</span>
          <span className="muted">A mediator steps in every third round without agreement</span>
        </div>
        <div className="progress" aria-hidden="true">
          {Array.from({ length: maxRounds }, (_, i) => <span key={i} className={i < current ? 'done' : ''} />)}
        </div>
      </div>

      <div className="party-grid">
        {(['supplier', 'buyer', 'financier'] as Party[]).map((role) => {
          const [a, b] = partyLines(role, events)
          return (
            <div key={role} className="panel party-card">
              <span className="dot" style={{ background: PARTY_COLOR[role] }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <strong>{scenario.parties[role]}</strong><span>{a}</span><span>{b}</span>
              </div>
            </div>
          )
        })}
      </div>

      <div className="room">
        <Transcript events={events} parties={scenario.parties} live={live} />
        <aside className="side">
          <div className="panel" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <h2 className="h2">Price offers</h2>
              <span className="legend">
                <span><i style={{ background: 'var(--supplier)' }} />Supplier</span>
                <span><i style={{ background: 'var(--buyer)' }} />Buyer</span>
              </span>
            </div>
            <PriceChart events={events} maxRounds={maxRounds} />
          </div>

          <div className="panel" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <h2 className="h2">Where they stand</h2>
            <div className="stand">
              <span /><span style={{ fontWeight: 600, color: 'var(--supplier)' }}>Supplier asks</span>
              <span style={{ fontWeight: 600, color: 'var(--buyer)' }}>Buyer offers</span>
              <span className="muted">Price</span><StandCell t={sup?.terms} field="price" /><StandCell t={buy?.terms} field="price" />
              <span className="muted">Buyer pays in</span><StandCell t={sup?.terms} field="days" /><StandCell t={buy?.terms} field="days" />
              <span className="muted">Financing</span><StandCell t={sup?.terms} field="fin" /><StandCell t={buy?.terms} field="fin" />
              <span className="muted">Cost share</span><StandCell t={sup?.terms} field="share" /><StandCell t={buy?.terms} field="share" />
            </div>
          </div>

          {compliance && (
            <div className={`notice ${bothCompliant ? 'notice-teal' : ''}`} style={{ padding: '18px 20px', borderRadius: 16 }}>
              <Icon name="audit" size={22} color={bothCompliant ? 'var(--financier)' : 'var(--supplier-ink)'} strokeWidth={2} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontSize: 15, fontWeight: 600, color: bothCompliant ? 'var(--financier-ink)' : 'var(--supplier-ink)' }}>
                  {bothCompliant ? 'Both offers are compliant' : 'One offer breaks the payment rules'}
                </span>
                <span style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--ink-2)' }}>
                  {bothCompliant
                    ? `The MSME is paid on day ${compliance.days_to_msme_payment}, inside the ${scenario.spec.legal_limit_days}-day MSMED limit, and the buyer keeps its Section 43B(h) deduction.`
                    : compliance.notes.join(' ') || 'Payment after the legal limit exposes the buyer to MSMED interest and a deferred 43B(h) deduction.'}
                </span>
              </div>
            </div>
          )}
        </aside>
      </div>
    </>
  )
}