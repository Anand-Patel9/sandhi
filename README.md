# Sandhi

**Autonomous AI agents that negotiate fair, compliant payment terms between Indian MSMEs, corporate buyers and invoice financiers.**

*Sandhi (संधि) is Sanskrit for "treaty". In Kautilya's Arthashastra it is the policy of reaching agreement with parties whose interests differ from yours.*

## The problem

Indian MSMEs have an estimated ₹7–8 lakh crore stuck in delayed payments (GAME–FISME–C2FO Delayed Payments Report 3.0; Economic Survey 2025-26). Buyers stretch payment terms, suppliers run short of cash, and the MSMED Act 45-day limit and Section 43B(h) of the Income Tax Act now make late payment costly for buyers too. A single AI optimising one party's objective produces terms another party rejects, and the deal collapses.

## The solution

Sandhi gives each party its own autonomous agent with private goals, constraints and data. The agents negotiate price, payment days, TReDS invoice discounting and cost sharing over the open **A2A (Agent2Agent) protocol**, adapt to market shocks, and reach a deal every party prefers to walking away.

- **Private by design.** Each agent keeps its costs, cash position and walk-away options inside its own server. The orchestrator only sees public offers.
- **The LLM argues, the code decides.** Deterministic utility functions decide what an agent can accept; the LLM chooses among valid offers and writes the message.
- **Live data over MCP.** Agents read their company's cash position from ERP, TReDS market rates and payment-compliance rules through Model Context Protocol tool servers.
- **Guarded messages.** Private numbers are redacted and mis-quoted prices are rejected before any message is sent.
- **Humans sign off.** Agents agree on terms; each company's authorised user approves before the deal is final, and a term-sheet PDF is issued.
- **Tamper-evident audit trail.** Every event is hash-chained, and the chain can be verified at any time.
- **Measured outcomes.** Every deal is compared with single-objective AI baselines and the full-information optimum.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## Quick start

Run the backend and the web app in two terminals.

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # add an LLM key, or keep offline mode
uvicorn app.main:app --reload
```

The backend serves interactive API documentation at http://localhost:8000; click **Authorize** and sign in with a demo account.

| Demo account | Organisation | Role |
|---|---|---|
| `supplier@sandhi.demo` | Rajkot Castings Pvt Ltd | MSME supplier |
| `buyer@sandhi.demo` | Bharat Motors Ltd | Corporate buyer |
| `financier@sandhi.demo` | Trident TReDS Bank | TReDS financier |
| `admin@sandhi.demo` | Sandhi Platform | Platform admin (can sign for any party in the sandbox) |

All demo accounts use the password `sandhi-demo`.

Sign in and start a negotiation:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" \
  -d '{"email": "admin@sandhi.demo", "password": "sandhi-demo"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/negotiations -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "auto_parts", "shocks": [{"key": "rate_hike", "at_round": 4}]}'
```

Follow it live:

```bash
curl -N "http://localhost:8000/api/negotiations/<id>/stream?token=$TOKEN"
```

When the agents agree, each party approves with `POST /api/negotiations/<id>/approval`; the term sheet is then available at `GET /api/negotiations/<id>/term-sheet`.

List the MCP tool servers and their tools:

```bash
curl http://localhost:8000/api/tools
```

Inspect an agent's A2A Agent Card:

```bash
curl http://localhost:8000/a2a/supplier/.well-known/agent-card.json
```

### Web app

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and pick a sample company on the sign-in page. The dev server forwards API calls to the backend on port 8000.

## Tests

```bash
cd backend
pytest
```

## Assumptions

Scenario figures are illustrative. Section 43B(h) is modelled as a one-year deduction deferral costed at the buyer's cost of capital; MSMED Act interest (three times the RBI bank rate) is an expected cost weighted by claim probability. These are modelling simplifications, not legal advice.