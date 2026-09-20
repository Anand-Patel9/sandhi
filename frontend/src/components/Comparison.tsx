import type { Evaluation } from '../lib/api'
import { lakh } from '../lib/format'

const LABELS: Record<string, [string, string]> = {
  buyer_ai: ['Buyer-only AI', "Optimises the buyer's cost alone"],
  legacy_ai: ['Legacy procurement', 'Lowest price, longest days'],
  supplier_ai: ['Supplier-only AI', "Optimises the MSME's cash"],
  status_quo: ['Industry status quo', '90-day terms, no financing'],
  negotiated: ['Sandhi agents', 'Negotiated with private data kept private'],
}

export function Comparison({ evaluation }: { evaluation: Evaluation }) {
  const rows = evaluation.approaches.filter((a) => a.key in LABELS)
  const peak = Math.max(1, ...rows.flatMap((a) => [a.realised.supplier, a.realised.buyer]))
  const scale = (v: number) => `${Math.max(2, (v / peak) * 160)}px`
  const ours = evaluation.approaches.find((a) => a.key === 'negotiated')
  const better = ours?.viable ? (['supplier', 'buyer', 'financier'] as const).filter((p) => ours.surplus[p] >= 0).length : 0

  return (
    <section className="panel panel-pad" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <h2 className="h2">Why this deal holds</h2>
      <p style={{ margin: '4px 0 10px', fontSize: 14, lineHeight: 1.5, color: 'var(--muted)' }}>
        Gain for each side over walking away, compared with a single AI optimising one side's goal.
      </p>
      <div className="legend" style={{ paddingBottom: 8 }}>
        <span><i className="bar" style={{ width: 12, height: 10, background: 'var(--supplier)' }} />Supplier</span>
        <span><i className="bar" style={{ width: 12, height: 10, background: 'var(--buyer)' }} />Buyer</span>
      </div>
      {rows.map((a) => {
        const [label, desc] = LABELS[a.key]
        const walker = a.blocked_by[0] === 'supplier' ? 'Supplier' : a.blocked_by[0] === 'buyer' ? 'Buyer' : 'Financier'
        return (
          <div key={a.key} className={`compare-row${a.key === 'negotiated' ? ' ours' : ''}`}>
            <div className="cmp-label"><strong>{label}</strong><span>{desc}</span></div>
            {a.viable ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div className="bar-line"><span className="bar" style={{ width: scale(a.realised.supplier), background: 'var(--supplier)' }} />{lakh(a.realised.supplier)}</div>
                <div className="bar-line"><span className="bar" style={{ width: scale(a.realised.buyer), background: 'var(--buyer)' }} />{lakh(a.realised.buyer)}</div>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span className="stamp stamp-red" style={{ fontSize: 12, padding: '0 8px', transform: 'rotate(-2deg)' }}>
                  {a.key === 'negotiated' ? 'No deal' : 'Collapses'}
                </span>
                <span style={{ fontSize: 13, color: 'var(--muted)' }}>
                  {a.blocked_by[0] === 'deadline' ? 'Agents ran out of rounds' : `${walker} walks away`}
                </span>
              </div>
            )}
          </div>
        )
      })}
      <div className="stats3">
        <div><strong>{Math.round(evaluation.efficiency * 100)}%</strong><span>of the best possible joint gain</span></div>
        <div><strong>{evaluation.pareto_efficient ? 'Yes' : 'No'}</strong><span>Pareto-efficient</span></div>
        <div><strong>{better} of 3</strong><span>parties better off</span></div>
      </div>
    </section>
  )
}