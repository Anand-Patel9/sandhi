import type { NegotiationEvent } from '../lib/api'
import { inr } from '../lib/format'

const W = 520, H = 232, LEFT = 40, RIGHT = 504, TOP = 16, BOTTOM = 192

interface Props { events: NegotiationEvent[]; maxRounds: number }

function lastPerRound(events: NegotiationEvent[], agent: string, kind = 'offer') {
  const byRound = new Map<number, number>()
  for (const e of events) if (e.kind === kind && e.agent === agent && e.terms) byRound.set(e.round, e.terms.price)
  return [...byRound.entries()].sort((a, b) => a[0] - b[0])
}

export function PriceChart({ events, maxRounds }: Props) {
  const sup = lastPerRound(events, 'supplier')
  const buy = lastPerRound(events, 'buyer')
  const med = lastPerRound(events, 'mediator', 'mediation')
  const shocks = events.filter((e) => e.kind === 'shock')
  const all = [...sup, ...buy, ...med].map(([, p]) => p)

  if (!all.length) {
    return <div className="skeleton" style={{ height: H }} aria-label="Waiting for the first offers" />
  }
  const lo = Math.floor((Math.min(...all) - 5) / 10) * 10
  const hi = Math.ceil((Math.max(...all) + 5) / 10) * 10
  const x = (r: number) => LEFT + ((r - 1) * (RIGHT - LEFT)) / Math.max(1, maxRounds - 1)
  const y = (p: number) => TOP + ((hi - p) / Math.max(1, hi - lo)) * (BOTTOM - TOP)
  const ticks = [0, 1, 2, 3].map((i) => lo + ((hi - lo) * i) / 3)
  const roundTicks = [...new Set([1, Math.round(maxRounds / 3), Math.round((2 * maxRounds) / 3), maxRounds])]
  const line = (pts: [number, number][]) => pts.map(([r, p]) => `${x(r).toFixed(1)},${y(p).toFixed(1)}`).join(' ')
  const lastS = sup[sup.length - 1]
  const lastB = buy[buy.length - 1]
  const gapRound = lastS && lastB ? Math.max(lastS[0], lastB[0]) : null
  const gap = lastS && lastB ? lastS[1] - lastB[1] : null

  const summary = `Price offers by round. Supplier ${sup.length ? `from ${inr(sup[0][1])} to ${inr(lastS[1])}` : 'none yet'}; `
    + `buyer ${buy.length ? `from ${inr(buy[0][1])} to ${inr(lastB[1])}` : 'none yet'}.`

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary}>
      <g stroke="#E6E8E0" strokeWidth="1">
        {ticks.map((t) => <line key={t} x1={LEFT} y1={y(t)} x2={RIGHT} y2={y(t)} />)}
      </g>
      <g fontFamily="Instrument Sans, sans-serif" fontSize="11" fill="#5A6378">
        {ticks.map((t) => <text key={t} x="0" y={y(t) + 4}>₹{Math.round(t)}</text>)}
        {roundTicks.map((r) => <text key={r} x={x(r) - 4} y="214">R{r}</text>)}
      </g>
      {shocks.map((s) => (
        <g key={s.seq}>
          <line x1={x(s.round)} y1={TOP} x2={x(s.round)} y2={BOTTOM} stroke="#EBCB85" strokeWidth="2" strokeDasharray="4 4" />
          <text x={x(s.round) + 6} y={TOP + 14} fontFamily="Instrument Sans, sans-serif" fontSize="11" fill="#8A5F08" fontWeight="600">
            {String(s.meta.key) === 'rate_hike' ? 'RBI hike' : 'Market shock'}
          </text>
        </g>
      ))}
      {gap !== null && gapRound !== null && gap > 0.01 && (
        <>
          <line x1={x(gapRound)} y1={y(lastS[1])} x2={x(gapRound)} y2={y(lastB[1])} stroke="#1B2440" strokeWidth="1.5" strokeDasharray="2 3" />
          <text x={Math.min(x(gapRound) + 12, RIGHT - 90)} y={(y(lastS[1]) + y(lastB[1])) / 2 + 4}
            fontFamily="Instrument Sans, sans-serif" fontSize="12" fill="#1B2440" fontWeight="600">{inr(gap)} apart</text>
        </>
      )}
      <polyline points={line(sup)} fill="none" stroke="#B9800E" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      <polyline points={line(buy)} fill="none" stroke="#3B5BA9" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      {lastS && <circle cx={x(lastS[0])} cy={y(lastS[1])} r="5" fill="#B9800E" />}
      {lastB && <circle cx={x(lastB[0])} cy={y(lastB[1])} r="5" fill="#3B5BA9" />}
      {med.map(([r, p]) => (
        <rect key={r} x={x(r) - 4} y={y(p) - 4} width="8" height="8" transform={`rotate(45 ${x(r)} ${y(p)})`} fill="#5A6378">
          <title>Mediator proposed {inr(p)} in round {r}</title>
        </rect>
      ))}
    </svg>
  )
}