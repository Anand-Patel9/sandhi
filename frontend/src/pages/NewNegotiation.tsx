import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { api } from '../lib/api'
import { count, inr, sentence } from '../lib/format'
import { useCatalog } from '../lib/hooks'

const ENGINES = [
  { value: 'offline', label: 'Rule-based (no AI key needed)' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'groq', label: 'Groq' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic Claude' },
]
const PACES = [
  { value: 0.6, label: 'Presentation pace' },
  { value: 0.3, label: 'Normal' },
  { value: 0, label: 'Instant' },
]

export function NewNegotiation() {
  const catalog = useCatalog()
  const navigate = useNavigate()
  const [scenario, setScenario] = useState('auto_parts')
  const [shocks, setShocks] = useState<Record<string, number | null>>({ rate_hike: 4 })
  const [rounds, setRounds] = useState(12)
  const [engine, setEngine] = useState('offline')
  const [pace, setPace] = useState(0.6)
  const [approval, setApproval] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (ev: FormEvent) => {
    ev.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const n = await api.create({
        scenario, max_rounds: rounds, pace_seconds: pace, require_approval: approval,
        llm: { provider: engine },
        shocks: Object.entries(shocks).filter(([, r]) => r !== null).map(([key, r]) => ({ key, at_round: r as number })),
      })
      navigate(`/deals/${n.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start the negotiation')
      setBusy(false)
    }
  }

  const sc = catalog.data?.scenarios.find((s) => s.key === scenario)

  return (
    <main className="main" style={{ maxWidth: 1040 }}>
      <div>
        <Link to="/" className="crumb">Deals</Link>
        <div className="page-head" style={{ marginTop: 10 }}>
          <div>
            <h1>Start a negotiation</h1>
            <p>Pick the deal, set the market conditions, and let the agents work. You approve the result.</p>
          </div>
        </div>
      </div>

      {catalog.error && <p className="error-text">{catalog.error}</p>}

      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
        <fieldset style={{ border: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <legend className="h2" style={{ marginBottom: 12 }}>Deal</legend>
          <div className="grid-2">
            {(catalog.data?.scenarios ?? []).map((s) => (
              <button key={s.key} type="button" className="option-card" aria-pressed={scenario === s.key} onClick={() => setScenario(s.key)}>
                <strong>{sentence(s.spec.item)}, {count(s.spec.quantity)} units</strong>
                <span>{s.parties.supplier} supplies {s.parties.buyer}. {s.parties.financier} can discount the invoice.</span>
                <span className="num">Price range {inr(s.spec.price_bounds[0])} to {inr(s.spec.price_bounds[1])} per unit</span>
              </button>
            ))}
            {!catalog.data && [0, 1].map((i) => <div key={i} className="skeleton" style={{ height: 120 }} />)}
          </div>
          {sc && <p className="hint" style={{ margin: 0, maxWidth: '80ch', lineHeight: 1.5 }}>{sc.story}</p>}
        </fieldset>

        <fieldset style={{ border: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <legend className="h2" style={{ marginBottom: 4 }}>Market conditions</legend>
          <p className="hint" style={{ margin: '0 0 4px' }}>Events that hit mid-negotiation. Each agent re-plans from its own position when they land.</p>
          {(catalog.data?.shocks ?? []).map((s) => {
            const on = shocks[s.key] !== undefined && shocks[s.key] !== null
            return (
              <div key={s.key} className="check-row">
                <input id={`shock-${s.key}`} type="checkbox" checked={on}
                  onChange={(e) => setShocks({ ...shocks, [s.key]: e.target.checked ? 4 : null })} />
                <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <label htmlFor={`shock-${s.key}`} style={{ fontWeight: 600, fontSize: 15 }}>{s.title}</label>
                  <span className="hint">{s.description}</span>
                </div>
                {on && (
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14 }}>
                    In round
                    <select className="select" style={{ width: 84, height: 40 }} value={shocks[s.key] ?? 4}
                      onChange={(e) => setShocks({ ...shocks, [s.key]: Number(e.target.value) })}>
                      {Array.from({ length: rounds - 1 }, (_, i) => i + 2).map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </label>
                )}
              </div>
            )
          })}
        </fieldset>

        <fieldset style={{ border: 'none', padding: 0, margin: 0, display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 16 }}>
          <legend className="h2" style={{ marginBottom: 12 }}>How the agents run</legend>
          <div className="field">
            <label htmlFor="engine">Agent reasoning</label>
            <select id="engine" className="select" value={engine} onChange={(e) => setEngine(e.target.value)}>
              {ENGINES.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
            </select>
            <span className="hint">AI engines use the key set on the server.</span>
          </div>
          <div className="field">
            <label htmlFor="rounds">Deadline</label>
            <select id="rounds" className="select" value={rounds} onChange={(e) => setRounds(Number(e.target.value))}>
              {[8, 10, 12, 16, 20].map((r) => <option key={r} value={r}>{r} rounds</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="pace">Replay speed</label>
            <select id="pace" className="select" value={pace} onChange={(e) => setPace(Number(e.target.value))}>
              {PACES.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
            </select>
          </div>
        </fieldset>

        <div className="check-row">
          <input id="approval" type="checkbox" checked={approval} onChange={(e) => setApproval(e.target.checked)} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <label htmlFor="approval" style={{ fontWeight: 600, fontSize: 15 }}>Require every party to sign before the deal is final</label>
            <span className="hint">Recommended. Turn off only for automated test runs.</span>
          </div>
        </div>

        {error && <p className="error-text" role="alert" style={{ margin: 0 }}>{error}</p>}
        <div style={{ display: 'flex', gap: 12 }}>
          <button type="submit" className="btn btn-primary btn-lg" disabled={busy || !catalog.data}>
            {busy ? 'Opening talks…' : 'Start negotiating'}
          </button>
          <Link to="/" className="btn btn-secondary btn-lg">Cancel</Link>
        </div>
      </form>
    </main>
  )
}