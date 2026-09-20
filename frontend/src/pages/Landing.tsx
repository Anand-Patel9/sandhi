import { Link } from 'react-router'
import { Mark } from '../components/Logo'
import { API_BASE } from '../lib/api'
import { useAuth } from '../lib/auth'

const DOCS = `${API_BASE || 'http://127.0.0.1:8000'}/docs`

function HeroArt() {
  return (
    <div className="hero-art" aria-hidden="true">
      <svg viewBox="0 0 520 300" width="100%" height="auto">
        <path d="M24 40 C 190 40, 230 150, 360 150" stroke="#E0A93A" strokeWidth="12" fill="none" strokeLinecap="round" />
        <path d="M24 150 L 360 150" stroke="#8FA8E6" strokeWidth="12" fill="none" strokeLinecap="round" />
        <path d="M24 260 C 190 260, 230 150, 360 150" stroke="#6FC2B6" strokeWidth="12" fill="none" strokeLinecap="round" />
        <circle cx="414" cy="150" r="46" fill="#F6F7F4" />
        <text x="24" y="24" fill="#E0A93A" fontSize="16" fontWeight="600">MSME supplier</text>
        <text x="24" y="134" fill="#8FA8E6" fontSize="16" fontWeight="600">Corporate buyer</text>
        <text x="24" y="292" fill="#6FC2B6" fontSize="16" fontWeight="600">TReDS financier</text>
      </svg>
      <span className="hero-stamp">Settled</span>
    </div>
  )
}

const STEPS = [
  {
    title: 'Each company sets its agent’s limits',
    body: 'The supplier knows its costs and how many days of cash it has left. The buyer knows its budget and alternatives. The bank knows its funding cost. Each agent keeps these to itself.',
  },
  {
    title: 'Agents negotiate, round by round',
    body: 'They trade price, payment days, TReDS invoice financing and who bears the discount cost. They read live data from ERP, market rates and compliance rules, and re-plan when the RBI moves rates.',
  },
  {
    title: 'People sign, and the record is sealed',
    body: 'Nothing is binding until an authorised person at every company approves. Every step is hash-chained into a tamper-evident log, and the term sheet is ready to download.',
  },
]

const TRANSCRIPT = [
  { who: 'Rajkot Castings agent', color: 'var(--supplier)', init: 'RC', text: 'TReDS solves both our problems: you keep 45-day terms and we get paid on day 2.' },
  { who: 'Bharat Motors agent', color: 'var(--buyer)', init: 'BM', text: 'We can commit to ₹392.50 per unit. We’ll pay the financier in 45 days via TReDS.' },
  { who: 'Mediator', color: 'var(--mediator)', init: 'M', text: 'The parties are ₹20.00 apart. I propose ₹402.50 per unit, paid in 45 days through TReDS.' },
]

const COMPARE = [
  { label: 'Buyer-only AI', note: 'Supplier walks away' },
  { label: 'Legacy procurement', note: 'Supplier walks away' },
  { label: 'Supplier-only AI', note: 'Buyer walks away' },
  { label: 'Industry status quo', note: 'Supplier walks away' },
]

const TECH = [
  { title: 'A2A protocol', body: 'Every party’s agent is its own server with a public Agent Card, built on the official A2A SDK. A company can run its agent on its own infrastructure.' },
  { title: 'MCP tools', body: 'Agents read cash position from ERP, TReDS market rates and MSMED / Section 43B(h) rules through Model Context Protocol servers.' },
  { title: 'The LLM argues, the code decides', body: 'Deterministic utility functions decide what each agent can accept. Gemini, Groq or OpenAI only choose among valid offers and write the message.' },
  { title: 'Privacy and price guards', body: 'Private numbers are redacted before a message leaves an agent, and any message that misquotes a price is replaced with a verified one.' },
  { title: 'Human approval', body: 'Agents reach agreement; people make it binding. Each company signs for itself.' },
  { title: 'Tamper-evident audit', body: 'Every event is sealed with a SHA-256 fingerprint of itself and the one before. One click verifies the whole chain.' },
]

export function Landing() {
  const { user } = useAuth()
  const cta = user
    ? { to: '/', label: 'Open your deals' }
    : { to: '/login', label: 'Try the live demo' }

  return (
    <div className="landing">
      <header className="lp-nav">
        <Link to="/about" className="lp-brand" aria-label="Sandhi home">
          <Mark size={32} onDark />
          <span>Sandhi</span>
        </Link>
        <nav aria-label="Page sections" className="lp-links">
          <a href="#how">How it works</a>
          <a href="#proof">Results</a>
          <a href="#tech">Technology</a>
        </nav>
        <Link to={cta.to} className="btn lp-btn-light">{user ? 'Open app' : 'Sign in'}</Link>
      </header>

      <section className="lp-hero">
        <div className="lp-hero-copy">
          <p className="lp-kicker">Multi-agent negotiation for India’s MSME trade credit</p>
          <h1>Payment terms every party can sign.</h1>
          <p className="lp-lede">
            Sandhi gives an MSME supplier, its corporate buyer and a TReDS financier each their own AI agent.
            The agents negotiate price, payment days and invoice financing with every company’s limits kept
            private, and bring back a deal all three prefer to walking away.
          </p>
          <div className="lp-cta-row">
            <Link to={cta.to} className="btn lp-btn-light btn-lg">{cta.label}</Link>
            <a href="#how" className="btn lp-btn-ghost btn-lg">See how it works</a>
          </div>
          <p className="lp-fine">Sandbox with sample companies. One click to sign in, no sign-up.</p>
        </div>
        <HeroArt />
      </section>

      <section className="lp-facts" aria-label="The problem">
        <div className="lp-fact">
          <span className="lp-fact-num">₹8.1 lakh crore</span>
          <span>owed to Indian MSMEs in delayed payments, by the Economic Survey 2025-26 estimate.</span>
        </div>
        <div className="lp-fact">
          <span className="lp-fact-num">45 days</span>
          <span>the MSMED Act payment limit. Pay later and Section 43B(h) defers the buyer’s tax deduction.</span>
        </div>
        <div className="lp-fact">
          <span className="lp-fact-num">1 objective</span>
          <span>is all a single procurement AI optimises. The other side walks away, and the deal collapses.</span>
        </div>
      </section>

      <section id="how" className="lp-section">
        <div className="lp-section-head">
          <h2>Three companies. Three agents. One agreement.</h2>
          <p>Sandhi means treaty in Sanskrit. The logo shows three positions bending toward one seal.</p>
        </div>
        <div className="lp-how">
          <ol className="lp-steps">
            {STEPS.map((s, i) => (
              <li key={s.title}>
                <span className="lp-step-num">{i + 1}</span>
                <div>
                  <h3>{s.title}</h3>
                  <p>{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
          <div className="lp-transcript" aria-label="Excerpt from a real negotiation">
            <div className="lp-transcript-head">
              <strong>Caliper housings, 10,000 units</strong>
              <span className="stamp stamp-live">Negotiating</span>
            </div>
            {TRANSCRIPT.map((m) => (
              <div key={m.who} className="lp-msg">
                <span className="avatar" style={{ background: m.color }}>{m.init}</span>
                <div>
                  <span className="lp-msg-who" style={{ color: m.color }}>{m.who}</span>
                  <p>{m.text}</p>
                </div>
              </div>
            ))}
            <div className="lp-transcript-foot">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>
              Each agent’s costs and limits never leave its own server.
            </div>
          </div>
        </div>
      </section>

      <section id="proof" className="lp-section lp-proof">
        <div className="lp-section-head">
          <h2>A single-objective AI breaks the deal. Sandhi’s agents close it.</h2>
          <p>Same deal, same private data, compared on each party’s gain over walking away.</p>
        </div>
        <div className="lp-proof-grid">
          <div className="lp-compare">
            {COMPARE.map((c) => (
              <div key={c.label} className="lp-compare-row">
                <span className="lp-compare-label">{c.label}</span>
                <span className="stamp stamp-red lp-small-stamp">Collapses</span>
                <span className="muted">{c.note}</span>
              </div>
            ))}
            <div className="lp-compare-row lp-compare-win">
              <span className="lp-compare-label">Sandhi agents</span>
              <div className="lp-bars">
                <span><i style={{ background: 'var(--supplier)' }} />Supplier +₹3.35 lakh</span>
                <span><i style={{ background: 'var(--buyer)' }} />Buyer +₹5.55 lakh</span>
              </div>
            </div>
          </div>
          <div className="lp-stats">
            <div><strong>100%</strong><span>of the best possible joint gain, reached without any agent seeing another’s data</span></div>
            <div><strong>Day 2</strong><span>when the MSME is paid through TReDS, instead of waiting 90 days</span></div>
            <div><strong>3 of 3</strong><span>parties better off than walking away, and the deal is Pareto-efficient</span></div>
          </div>
        </div>
        <p className="lp-note">Figures from the auto-component sandbox scenario with an RBI rate hike at round 4. Scenario data is illustrative.</p>
      </section>

      <section id="tech" className="lp-section">
        <div className="lp-section-head">
          <h2>Built like a product, not a demo</h2>
          <p>Open protocols, deterministic decisions and a full governance trail.</p>
        </div>
        <div className="lp-tech">
          {TECH.map((t) => (
            <div key={t.title} className="lp-tech-item">
              <h3>{t.title}</h3>
              <p>{t.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="lp-final">
        <h2>Watch a negotiation go from first offer to signed term sheet in under two minutes.</h2>
        <Link to={cta.to} className="btn lp-btn-light btn-lg">{cta.label}</Link>
      </section>

      <footer className="lp-footer">
        <div className="lp-brand">
          <Mark size={26} onDark />
          <span>Sandhi</span>
          <span className="lp-deva">संधि</span>
        </div>
        <span>Built for the Apexium International Hackathon 2026</span>
        <div className="lp-footer-links">
          <a href={DOCS} target="_blank" rel="noreferrer">API docs</a>
        </div>
      </footer>
    </div>
  )
}