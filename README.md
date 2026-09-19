# TradeCredit

**Autonomous agents that negotiate fair, compliant payment terms between Indian MSMEs, corporate buyers and invoice financiers.**

Indian MSMEs have an estimated ₹7–8 lakh crore stuck in delayed payments (GAME–FISME–C2FO Delayed Payments Report 3.0; Economic Survey 2025-26). Buyers stretch terms, suppliers run out of cash, and the MSMED Act 45-day limit and Section 43B(h) of the Income Tax Act now make late payment costly for buyers too. A single AI optimising one party's objective produces terms another party rejects, and the deal collapses.

TradeCredit gives each party its own autonomous agent with private goals and data. The agents negotiate price, payment days, TReDS invoice discounting and cost sharing, respond to market shocks, and reach a deal every party prefers to walking away.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## Quick start (backend)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # add an LLM key, or keep offline mode
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API.

Start a negotiation:

```bash
curl -X POST http://localhost:8000/api/negotiations \
  -H "Content-Type: application/json" \
  -d '{"scenario": "auto_parts", "shocks": [{"key": "rate_hike", "at_round": 4}]}'
```

Follow it live:

```bash
curl -N http://localhost:8000/api/negotiations/<id>/stream
```

## Tests

```bash
cd backend
pytest
```

## Assumptions

Scenario figures are illustrative. Section 43B(h) is modelled as a one-year deduction deferral costed at the buyer's cost of capital; MSMED Act interest (three times the RBI bank rate) is an expected cost weighted by claim probability. These are modelling simplifications, not legal advice.