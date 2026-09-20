import { useState } from 'react'
import { Comparison } from '../components/Comparison'
import { Icon } from '../components/icons'
import { api, type Negotiation, type Party, type Scenario, type User } from '../lib/api'
import { PARTY_COLOR, PARTY_LABEL, clockTime, inr, inrWhole, pct, pendingRoles } from '../lib/format'
import { useAsync } from '../lib/hooks'

interface Props {
  negotiation: Negotiation
  scenario: Scenario
  user: User
  onChanged: (n: Negotiation) => void
  notify: (text: string) => void
}

function SignAction({ negotiation, role, orgName, isAdmin, onChanged, notify }: {
  negotiation: Negotiation; role: Party; orgName: string; isAdmin: boolean
  onChanged: (n: Negotiation) => void; notify: (text: string) => void
}) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const decide = async (decision: 'approve' | 'reject') => {
    setBusy(decision)
    setError(null)
    try {
      const updated = await api.decide(negotiation.id, decision, note, isAdmin ? role : undefined)
      onChanged(updated)
      notify(decision === 'approve' ? `Signed for ${orgName}` : `Terms rejected for ${orgName}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not record the decision')
    } finally {
      setBusy(null)
    }
  }
  const noteId = `note-${role}`
  return (
    <div className="sig-action" style={{ borderColor: PARTY_COLOR[role] }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <span className="dot" style={{ background: PARTY_COLOR[role] }} />
        <span style={{ fontSize: 15, fontWeight: 600 }}>{orgName}, {isAdmin ? `sign as the ${role} (sandbox)` : 'your signature'}</span>
      </div>
      <label htmlFor={noteId} className="label">Note for the record (optional)</label>
      <textarea id={noteId} rows={2} className="textarea" value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
      {error && <p className="error-text" role="alert" style={{ margin: 0 }}>{error}</p>}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button type="button" className="btn btn-primary" disabled={busy !== null} onClick={() => void decide('approve')}>
          {busy === 'approve' ? 'Signing…' : 'Approve and sign'}
        </button>
        <button type="button" className="btn btn-danger" disabled={busy !== null} onClick={() => void decide('reject')}>
          {busy === 'reject' ? 'Rejecting…' : 'Reject terms'}
        </button>
      </div>
    </div>
  )
}

export function Signoff({ negotiation: n, scenario, user, onChanged, notify }: Props) {
  const terms = n.outcome?.terms ?? null
  const compliance = n.outcome?.compliance
  const evaluation = useAsync(() => api.evaluation(n.id), [n.id, n.status])
  const audit = useAsync(() => api.audit(n.id), [n.id, n.status, n.approvals.length])
  const [downloading, setDownloading] = useState(false)
  const required = n.outcome?.required_approvals ?? []
  const pending = pendingRoles(n)
  const isAdmin = user.org.kind === 'platform'

  const download = async () => {
    setDownloading(true)
    try {
      const blob = await api.termSheet(n.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `sandhi-term-sheet-${n.id.slice(0, 8)}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      notify('Term sheet downloaded')
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Download failed')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="signoff">
      <div className="signoff-main">
        {terms ? (
          <section className="panel" style={{ padding: '26px 28px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <h2 className="h2" style={{ marginBottom: 10 }}>The agreement</h2>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, paddingBottom: 12, flexWrap: 'wrap' }}>
              <span className="big-price">{inr(terms.price)}</span>
              <span style={{ fontSize: 17, color: 'var(--muted)' }}>per unit, invoice value {inrWhole(terms.price * scenario.spec.quantity)}</span>
            </div>
            <div className="kv"><span>Buyer pays</span><span style={{ fontWeight: 600 }}>In {terms.days} days{terms.treds ? ', to the financier' : ''}</span></div>
            <div className="kv"><span>Supplier receives cash</span><span style={{ fontWeight: 600 }}>
              {terms.treds ? `On day ${scenario.spec.treds_settlement_days}, through TReDS` : `On day ${terms.days}`}</span></div>
            {terms.treds && (
              <div className="kv"><span>Discount rate</span><span>
                {pct(terms.rate)} a year, {terms.buyer_share === 0 ? 'borne by the supplier' : terms.buyer_share === 1 ? 'borne by the buyer' : `buyer bears ${Math.round(terms.buyer_share * 100)}%`}
              </span></div>
            )}
            {compliance && (
              <>
                <div className="kv"><span>MSMED Act {scenario.spec.legal_limit_days}-day limit</span>
                  <span>{compliance.msmed_compliant ? `Met: supplier paid on day ${compliance.days_to_msme_payment}` : `Missed by ${compliance.days_over_limit} days`}</span></div>
                <div className="kv"><span>Section 43B(h)</span>
                  <span>{compliance.section_43bh_deduction_deferred ? "Buyer's deduction is deferred" : "Buyer keeps this year's deduction"}</span></div>
              </>
            )}
          </section>
        ) : (
          <section className="panel panel-pad" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <h2 className="h2">No agreement</h2>
            <p style={{ margin: 0, lineHeight: 1.55, color: 'var(--ink-2)' }}>
              {n.status === 'cancelled' ? 'The negotiation was stopped before the agents agreed.'
                : n.status === 'failed' ? `The negotiation could not finish: ${n.error ?? 'technical error'}.`
                  : 'The agents could not find terms that beat every party\'s outside option before the deadline. Nobody is bound to anything.'}
            </p>
          </section>
        )}

        {required.length > 0 && (
          <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h2 className="h2">Signatures</h2>
            {required.map((role) => {
              const a = n.approvals.find((x) => x.role === role)
              const org = scenario.parties[role]
              if (a) {
                const ok = a.decision === 'approve'
                return (
                  <div key={role} className="sig">
                    <span className="dot" style={{ background: PARTY_COLOR[role] }} />
                    <span className="who"><strong>{org}</strong>
                      <span>{ok ? 'Approved' : 'Rejected'} by {a.user_email}, {clockTime(a.created_at)}{a.note ? `. “${a.note}”` : ''}</span></span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 600, color: ok ? 'var(--financier)' : 'var(--stamp)' }}>
                      <Icon name={ok ? 'check' : 'x'} size={18} strokeWidth={2.4} />{ok ? 'Signed' : 'Rejected'}
                    </span>
                  </div>
                )
              }
              const mine = n.status === 'awaiting_approval' && (isAdmin || user.org.kind === role)
              if (mine) {
                return <SignAction key={role} negotiation={n} role={role} orgName={org} isAdmin={isAdmin} onChanged={onChanged} notify={notify} />
              }
              return (
                <div key={role} className="sig">
                  <span className="dot" style={{ background: PARTY_COLOR[role] }} />
                  <span className="who"><strong>{org}</strong>
                    <span>{n.status === 'awaiting_approval' ? `Waiting for the ${PARTY_LABEL[role].toLowerCase()} to sign` : 'Did not sign'}</span></span>
                </div>
              )
            })}
            {n.status === 'awaiting_approval' && pending.length > 0 && !isAdmin && !pending.includes(user.org.kind as Party) && (
              <p className="hint" style={{ margin: 0 }}>You have signed. The deal becomes final when the remaining parties approve.</p>
            )}
          </section>
        )}
      </div>

      <aside className="signoff-side">
        {evaluation.data && <Comparison evaluation={evaluation.data} />}
        {evaluation.loading && !evaluation.data && <div className="skeleton" style={{ height: 420 }} />}

        <section className="panel" style={{ padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Icon name="audit" size={20} strokeWidth={2} color={audit.data?.valid === false ? 'var(--stamp)' : 'var(--financier)'} />
            <h2 className="h2">{audit.data ? (audit.data.valid ? 'Audit trail verified' : 'Audit trail broken') : 'Checking the audit trail'}</h2>
          </div>
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, color: 'var(--ink-2)' }}>
            {audit.data?.valid === false
              ? `Entry ${audit.data.broken_at_seq} no longer matches its fingerprint. The log was changed after it was written.`
              : `${audit.data?.events ?? '…'} events, each sealed with the fingerprint of the one before. Any later edit would break the chain at that entry.`}
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span className="num" style={{ fontSize: 13, color: 'var(--muted)' }}>
              {audit.data ? `Chain head ${audit.data.head_hash.slice(0, 8)}…${audit.data.head_hash.slice(-5)}` : ''}
            </span>
            <button type="button" className={`btn btn-sm ${n.status === 'agreed' ? 'btn-primary' : 'btn-secondary'}`}
              disabled={n.status !== 'agreed' || downloading} onClick={() => void download()}>
              <Icon name="download" size={16} strokeWidth={2} />
              {n.status === 'agreed' ? (downloading ? 'Preparing…' : 'Download term sheet') : 'Term sheet after all sign'}
            </button>
          </div>
        </section>
      </aside>
    </div>
  )
}