import { useMemo, useState, type ReactNode } from 'react'
import type { NegotiationEvent, Party, Terms } from '../lib/api'
import { PARTY_COLOR, initials, inr } from '../lib/format'
import { Icon } from './icons'

interface Props {
  events: NegotiationEvent[]
  parties: Record<Party, string>
  live: boolean
}

interface Item { key: number; round: number; node: ReactNode; isMessage: boolean; pinned?: boolean }

function chipsFor(t: Terms) {
  const financing = !t.treds
    ? 'Paid directly'
    : t.buyer_share === 0 ? 'TReDS, supplier bears cost'
      : t.buyer_share === 1 ? 'TReDS, buyer bears 100%'
        : `TReDS, buyer bears ${Math.round(t.buyer_share * 100)}%`
  return [`${inr(t.price)} per unit`, `Pay in ${t.days} days`, financing]
}

function Message({ color, avatar, name, round, text, terms, redacted }: {
  color: string; avatar: string; name: string; round: number; text: string; terms?: Terms | null; redacted?: boolean
}) {
  return (
    <div className="msg enter">
      <span className="avatar" style={{ background: color }}>{avatar}</span>
      <div className="msg-body">
        <div className="msg-meta"><strong style={{ color }}>{name}</strong><span>Round {round}</span></div>
        <p>{text}</p>
        {terms && <div className="chips">{chipsFor(terms).map((c) => <span key={c} className="chip">{c}</span>)}</div>}
        {redacted && (
          <div className="privacy-note"><Icon name="lock" size={14} strokeWidth={2} />A private figure was removed from this message before it was sent.</div>
        )}
      </div>
    </div>
  )
}

function SystemLine({ tone = 'grey', icon, title, children }: {
  tone?: 'grey' | 'teal' | 'amber' | 'red'; icon: 'bolt' | 'check' | 'x' | 'scale' | 'lock'; title: string; children?: ReactNode
}) {
  const cls = tone === 'teal' ? 'notice notice-teal' : tone === 'red' ? 'notice notice-red' : tone === 'amber' ? 'notice' : 'notice'
  const color = tone === 'teal' ? 'var(--financier)' : tone === 'red' ? 'var(--stamp)' : tone === 'amber' ? 'var(--supplier-ink)' : 'var(--muted)'
  const style = tone === 'grey' ? { background: 'var(--surface-2)', borderColor: 'var(--rule)' } : undefined
  return (
    <div className={`${cls} enter`} style={style}>
      <Icon name={icon} size={22} color={color} strokeWidth={2} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ fontSize: 15, fontWeight: 600 }}>{title}</span>
        {children && <span style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--ink-2)' }}>{children}</span>}
      </div>
    </div>
  )
}

export function Transcript({ events, parties, live }: Props) {
  const [expanded, setExpanded] = useState(false)

  const items = useMemo<Item[]>(() => {
    const redactedSeqs = new Set<number>()
    events.forEach((e, i) => {
      if (e.kind !== 'privacy') return
      for (let j = i - 1; j >= 0; j--) {
        if (events[j].agent === e.agent && ['offer', 'rate'].includes(events[j].kind)) { redactedSeqs.add(events[j].seq); break }
      }
    })
    const out: Item[] = []
    for (const e of events) {
      const role = e.agent as Party
      const name = parties[role] ? `${parties[role]} agent` : 'Agent'
      const color = PARTY_COLOR[e.agent] ?? 'var(--muted)'
      const avatar = parties[role] ? initials(parties[role]) : 'M'
      let node: ReactNode = null
      let isMessage = false
      switch (e.kind) {
        case 'offer':
        case 'rate':
          isMessage = true
          node = <Message color={color} avatar={avatar} name={name} round={e.round} text={e.message}
            terms={e.kind === 'offer' ? e.terms : null} redacted={redactedSeqs.has(e.seq)} />
          break
        case 'mediation':
          isMessage = true
          node = <Message color="var(--mediator)" avatar="M" name="Mediator" round={e.round} text={e.message} terms={e.terms} />
          break
        case 'info':
          if (e.agent === 'mediator') {
            node = <p className="hint" style={{ margin: '0 0 0 50px' }}>{e.message}</p>
          } else if (e.round === 0 && e.message.startsWith('Negotiation opened')) {
            node = <p className="hint" style={{ margin: 0 }}>{e.message}</p>
          }
          break
        case 'shock': {
          const [title, ...rest] = e.message.split('. ')
          node = <SystemLine tone="amber" icon="bolt" title={`Round ${e.round}: ${title}`}>
            {rest.join('. ')} Each agent re-plans from its own updated position.
          </SystemLine>
          break
        }
        case 'accept':
          if (e.agent !== 'system') {
            node = <SystemLine tone="teal" icon="check" title={`${name} accepted`}>{e.terms ? chipsFor(e.terms).join(', ') : e.message}</SystemLine>
          }
          break
        case 'deal':
          node = <SystemLine tone="teal" icon="check" title={`Agreement reached in round ${e.round}`}>{e.message}</SystemLine>
          break
        case 'no_deal':
          node = <SystemLine icon="x" title="No agreement">{e.message}</SystemLine>
          break
        case 'approval_required':
          node = <SystemLine tone="amber" icon="scale" title="Waiting for people to sign">{e.message}</SystemLine>
          break
        case 'approval':
          node = <SystemLine tone={e.meta.decision === 'reject' ? 'red' : 'teal'} icon={e.meta.decision === 'reject' ? 'x' : 'check'}
            title={e.message} />
          break
        case 'signed':
          node = <SystemLine tone="teal" icon="check" title="Agreement final">{e.message}</SystemLine>
          break
        case 'rejected':
        case 'cancelled':
          node = <SystemLine tone="red" icon="x" title={e.kind === 'rejected' ? 'Deal rejected' : 'Negotiation stopped'}>{e.message}</SystemLine>
          break
      }
      if (node) out.push({ key: e.seq, round: e.round, node, isMessage, pinned: e.kind === 'shock' || e.kind === 'mediation' })
    }
    return out
  }, [events, parties])

  const rounds = [...new Set(items.filter((i) => i.round > 0).map((i) => i.round))].sort((a, b) => a - b)
  const messageCount = items.filter((i) => i.isMessage).length
  let hidden: Set<number> = new Set()
  let hiddenLabel = ''
  if (!expanded && messageCount > 10 && rounds.length > 4) {
    const middle = rounds.slice(1, rounds.length - 3)
    hidden = new Set(middle)
    const n = items.filter((i) => hidden.has(i.round) && i.isMessage && !i.pinned).length
    const range = middle.length === 1 ? `round ${middle[0]}` : `rounds ${middle[0]} to ${middle[middle.length - 1]}`
    hiddenLabel = `Show ${range} (${n} messages)`
  }

  const last = [...events].reverse().find((e) => e.kind === 'offer')
  const nextRole: Party | null = last ? (last.agent === 'supplier' ? 'buyer' : 'supplier') : null

  const rendered: ReactNode[] = []
  let insertedToggle = false
  for (const item of items) {
    if (hidden.has(item.round) && !item.pinned) {
      if (!insertedToggle) {
        insertedToggle = true
        rendered.push(
          <button key="toggle" type="button" className="pill" style={{ alignSelf: 'flex-start', marginLeft: 50 }} onClick={() => setExpanded(true)}>
            {hiddenLabel}
          </button>,
        )
      }
      continue
    }
    rendered.push(<div key={item.key}>{item.node}</div>)
  }

  return (
    <section aria-label="Negotiation transcript" aria-live="polite" className="panel transcript">
      {rendered.length === 0 && <p className="hint" style={{ margin: 0 }}>Connecting to the agents…</p>}
      {rendered}
      {live && (
        <div className="typing" style={{ color: nextRole ? PARTY_COLOR[nextRole] : 'var(--muted)' }}>
          {nextRole && <span className="avatar" style={{ background: PARTY_COLOR[nextRole] }}>{initials(parties[nextRole])}</span>}
          <span style={{ fontSize: 15, fontWeight: 600 }}>
            {nextRole ? `${parties[nextRole]} agent is weighing the offer` : 'Agents are preparing their opening positions'}
          </span>
          <span className="typing-dots"><span /><span /><span /></span>
        </div>
      )}
    </section>
  )
}