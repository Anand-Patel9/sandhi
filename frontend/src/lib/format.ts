import type { Negotiation, Party, Status, Terms } from './api'

export const PARTY_COLOR: Record<string, string> = {
  supplier: 'var(--supplier)', buyer: 'var(--buyer)', financier: 'var(--financier)',
  mediator: 'var(--mediator)', platform: 'var(--mediator)',
}
export const PARTY_LABEL: Record<Party, string> = { supplier: 'Supplier', buyer: 'Buyer', financier: 'Financier' }

const inrFmt = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const whole = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

export const inr = (x: number) => `₹${inrFmt.format(x)}`
export const inrWhole = (x: number) => `₹${whole.format(x)}`
export const lakh = (x: number) => `₹${(x / 1e5).toFixed(2)} lakh`
export const pct = (x: number, digits = 2) => `${(x * 100).toFixed(digits)}%`
export const count = (x: number) => whole.format(x)

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('')
}

export function sentence(s: string): string {
  return s ? s[0].toUpperCase() + s.slice(1) : s
}

export function termsLine(t: Terms): string {
  return `${inr(t.price)} per unit, buyer pays in ${t.days} days`
}

export function financingLine(t: Terms, settlementDays = 2): string {
  if (!t.treds) return 'Paid directly, no financing'
  return `TReDS at ${pct(t.rate)}, supplier paid on day ${settlementDays}`
}

export function costShare(t: Terms): string {
  if (!t.treds) return 'No financing'
  const s = Math.round(t.buyer_share * 100)
  if (s === 0) return 'Supplier bears'
  if (s === 100) return 'Buyer bears'
  return `Buyer bears ${s}%`
}

function parseTime(iso: string): number {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`).getTime()
}

export function relativeTime(iso: string | null): string {
  if (!iso) return ''
  const secs = Math.max(0, Math.round((Date.now() - parseTime(iso)) / 1000))
  if (secs < 60) return 'just now'
  if (secs < 3600) return `${Math.round(secs / 60)} min ago`
  if (secs < 86400) return `${Math.round(secs / 3600)} h ago`
  return new Date(parseTime(iso)).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export function clockTime(iso: string): string {
  return new Date(parseTime(iso)).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

export interface StampSpec { label: string; cls: string }
export function statusStamp(status: Status): StampSpec {
  switch (status) {
    case 'pending':
    case 'running': return { label: 'Negotiating', cls: 'stamp-live' }
    case 'awaiting_approval': return { label: 'Awaiting sign-off', cls: 'stamp-await' }
    case 'agreed': return { label: 'Settled', cls: 'stamp-settled' }
    case 'no_deal': return { label: 'No deal', cls: 'stamp-grey' }
    case 'cancelled': return { label: 'Stopped', cls: 'stamp-grey' }
    case 'rejected': return { label: 'Rejected', cls: 'stamp-red' }
    case 'failed': return { label: 'Failed', cls: 'stamp-red' }
  }
}

export const isLive = (n: Negotiation) => n.status === 'pending' || n.status === 'running'

export function pendingRoles(n: Negotiation): Party[] {
  const required = n.outcome?.required_approvals ?? []
  return required.filter((r) => !n.approvals.some((a) => a.role === r))
}