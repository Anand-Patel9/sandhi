import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { ConvergenceArt, Mark } from '../components/Logo'
import { useAuth } from '../lib/auth'

const DEMO_PASSWORD = 'sandhi-demo'
const DEMOS = [
  { email: 'supplier@sandhi.demo', name: 'Rajkot Castings', role: 'MSME supplier', color: 'var(--supplier)' },
  { email: 'buyer@sandhi.demo', name: 'Bharat Motors', role: 'Corporate buyer', color: 'var(--buyer)' },
  { email: 'financier@sandhi.demo', name: 'Trident TReDS Bank', role: 'Financier', color: 'var(--financier)' },
  { email: 'admin@sandhi.demo', name: 'Platform admin', role: 'Signs for any party', color: 'var(--ink)' },
]

export function Login() {
  const { user, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const next = (location.state as { from?: string } | null)?.from ?? '/'

  if (user) return <Navigate to={next} replace />

  const go = async (e: string, p: string) => {
    setBusy(true)
    setError(null)
    try {
      await signIn(e, p)
      navigate(next, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed')
    } finally {
      setBusy(false)
    }
  }
  const onSubmit = (ev: FormEvent) => { ev.preventDefault(); void go(email, password) }

  return (
    <div className="login">
      <section className="login-art">
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <Mark size={44} onDark stroke={5.5} />
          <span style={{ fontSize: 26, fontWeight: 600, letterSpacing: '-0.03em' }}>Sandhi</span>
          <span style={{ fontFamily: "'Tiro Devanagari Hindi', serif", fontSize: 22, color: 'var(--rail-dim)' }}>संधि</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
          <ConvergenceArt />
          <h1>Payment terms every party can sign.</h1>
          <p>Your agent negotiates price, payment days and invoice financing with the other side's agents, keeps your limits private, and brings the deal to you for approval.</p>
        </div>
        <div style={{ fontSize: 14, color: 'var(--rail-dim)' }}>Sandbox environment with sample companies. No real money moves.</div>
      </section>

      <main className="login-form-wrap">
        <div className="login-form">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <h2 style={{ margin: 0, fontSize: 32, fontWeight: 600, letterSpacing: '-0.02em' }}>Sign in</h2>
            <p style={{ margin: 0, fontSize: 16, color: 'var(--muted)' }}>Use your company account, or step into one of the sample companies.</p>
          </div>

          <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="field">
              <label htmlFor="email">Work email</label>
              <input id="email" className="input" type="email" autoComplete="username" required value={email}
                onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input id="password" className="input" type="password" autoComplete="current-password" required value={password}
                onChange={(e) => setPassword(e.target.value)} />
            </div>
            {error && <p className="error-text" role="alert" style={{ margin: 0 }}>{error}</p>}
            <button type="submit" className="btn btn-primary btn-lg" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
          </form>

          <div className="divider">or try a sample company</div>

          <div className="demo-grid">
            {DEMOS.map((d) => (
              <button key={d.email} type="button" className="demo-btn" disabled={busy} onClick={() => void go(d.email, DEMO_PASSWORD)}>
                <span className="dot" style={{ background: d.color }} />
                <span><strong>{d.name}</strong><span className="sub">{d.role}</span></span>
              </button>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}