# Architecture

Sandhi is a multi-agent negotiation platform for MSME trade credit. An MSME supplier, a corporate buyer and a TReDS financier are each represented by an autonomous agent with its own goals and private data. A neutral orchestrator runs the negotiation protocol and a mediator proposes compromises. The platform records every step and evaluates the outcome.

## Design principles

1. **Private data stays with its owner.** The orchestrator never reads an agent's private profile. It only sees public offers, messages and each agent's self-reported score of an offer. In production each company runs its own agent; the agents talk over the A2A protocol.
2. **The LLM argues, the code decides.** Each agent's utility function is deterministic code. Code produces the set of offers the agent can afford at this round; the LLM chooses among them and writes the message. An LLM cannot push an agent below its walk-away point.
3. **Every message is guarded.** A consistency guard rejects messages that quote a price different from the actual offer. A privacy guard redacts private numbers before a message leaves the agent.
4. **Nothing depends on the LLM being available.** Every LLM step has a deterministic fallback, so negotiations complete even without an API key or during provider outages.
5. **Agents are swappable behind ports.** The orchestrator depends on `NegotiatorPort` and `FinancierPort` interfaces. In-process agents and remote A2A agents implement the same interface.

## System overview

```
                         ┌──────────────────────────────┐
  Web app (React) ──────►│  API gateway (FastAPI)       │
     REST + SSE          │  auth · validation · stream  │
                         └──────────────┬───────────────┘
                                        │
                         ┌──────────────▼───────────────┐
                         │  Negotiation orchestrator    │
                         │  protocol · shocks · mediator│
                         │  approvals · audit trail     │
                         └──────┬─────────┬─────────┬───┘
                     A2A        │         │         │        A2A
               ┌────────────────▼┐  ┌─────▼─────┐  ┌▼────────────────┐
               │ Supplier agent  │  │ Buyer     │  │ Financier agent │
               │ private profile │  │ agent     │  │ private profile │
               └───────┬─────────┘  └─────┬─────┘  └───────┬─────────┘
                  MCP  │             MCP  │           MCP  │
               ┌───────▼─────┐   ┌────────▼───────┐  ┌─────▼──────────┐
               │ ERP / cash  │   │ Compliance     │  │ TReDS rates /  │
               │ flow tools  │   │ (MSMED, 43B(h))│  │ credit tools   │
               └─────────────┘   └────────────────┘  └────────────────┘

                         ┌──────────────────────────────┐
                         │ PostgreSQL (Supabase)        │
                         │ negotiations · events · orgs │
                         └──────────────────────────────┘
```

## Negotiation protocol

Each round:

1. Scheduled market shocks are applied. The orchestrator applies the public effect (for example the RBI bank rate); each agent applies the private effect to its own profile.
2. The financier publishes its TReDS discounting rate for the round.
3. The supplier proposes; the buyer and financier respond.
4. The buyer counter-proposes; the supplier and financier respond.
5. Every third round without agreement, the mediator proposes a package built only from public offers.

A deal closes when the responding principal and the financier accept. If the deadline passes, every party falls back to its walk-away option.

Issues negotiated: unit price, payment days, whether the invoice is discounted on TReDS, and the share of the discounting cost the buyer absorbs.

## A2A communication

Every party's agent is an A2A server built with the official A2A Python SDK (protocol version 1.0).

- **Discovery.** Each agent publishes an Agent Card at `/.well-known/agent-card.json` describing its name, provider, JSON-RPC endpoint and skills. The orchestrator reads the card before connecting.
- **Transport.** The orchestrator calls agents with JSON-RPC `SendMessage` requests. Each request carries one structured data part naming a skill and its inputs; the agent replies with one data part.
- **Sessions.** `open_session` provisions the agent with its private policy for one negotiation. The profile stays inside the agent's server; later calls reference only the session id. `close_session` discards it.
- **Skills.** Negotiators: `propose`, `respond`, `evaluate`, `shock`. Financier: `quote`, `announce`, `accepts`, `evaluate`, `shock`. `snapshot` exports end state for evaluation and is refused outside sandbox mode.
- **Deployment options.** In the hosted setup all three agents are mounted on the platform under `/a2a/{role}`. Any agent can instead run on a company's own infrastructure: set `SUPPLIER_AGENT_URL`, `BUYER_AGENT_URL` or `FINANCIER_AGENT_URL` and the orchestrator negotiates with it over the network, unchanged.

In-process and A2A agents implement the same ports, and the test suite checks that both produce identical negotiations.

## MCP tools

Agents reach company data and market information through Model Context Protocol (MCP) servers, built with the official MCP Python SDK and served over streamable HTTP.

| Server | Tools | Used by | Effect |
|---|---|---|---|
| `compliance` | `check_payment_terms`, `payment_rules` | Orchestrator, negotiators | Every offer and the final deal carry an MSMED Act / Section 43B(h) report; LLM prompts include the rules |
| `treds` | `market_rates`, `list_platforms` | Financier | Quotes are capped at the market band for the buyer's credit rating |
| `erp` | `cash_position`, `list_entities` | Supplier | Cash runway is read from the ledger instead of being typed in |

Agents load their data when a session opens and record which tools they used; the negotiation log shows the sources without revealing the values. If a tool server is unreachable, agents fall back to their configured profile and the negotiation continues.

In the hosted setup the three servers are mounted under `/mcp/{name}/`. A customer connects its own systems by pointing `ERP_MCP_URL` (or the others) at an MCP server in front of its ERP, for example Tally or SAP, with no change to agent code. The bundled servers use sandbox data.

## Agent decision model

| Agent | Utility | Walk-away option |
|---|---|---|
| Supplier | Cash received − production cost − time value of waiting − liquidity penalty after cash runway | Alternative buyer's price and terms |
| Buyer | −(invoice cost + absorbed discount cost − payment float + Section 43B(h) exposure + expected MSMED Act interest) | Alternate supplier's price plus switching cost |
| Financier | Discount income − funding cost − expected credit loss − minimum spread | Not participating (zero) |

Concession follows a time-dependent tactic: aspiration(t) = ideal × (1 − (t/T)^(1/β)). A high β concedes early (an urgent MSME); a low β holds out (a powerful buyer). Each counter-offer is the package closest to the other side's last offer that still meets the agent's current aspiration, so agents trade across issues instead of only splitting the price.

## Evaluation

Finished negotiations are compared with single-objective baselines (buyer-only AI, legacy procurement AI, supplier-only AI, industry status quo) and with the full-information Nash bargaining optimum. Metrics: viability (every party beats its walk-away), efficiency against the optimum, Pareto efficiency and balance between supplier and buyer. Evaluation needs every party's private end state, so it runs only in sandbox mode, where the platform hosts all agents.

## Repository structure

```
sandhi/
├── README.md
├── ARCHITECTURE.md
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                 FastAPI app factory
│   │   ├── config.py               Settings from environment
│   │   ├── core/                   Pure domain logic, no I/O
│   │   │   ├── models.py           Terms, deal spec, private profiles, events
│   │   │   ├── utilities.py        Utility functions per party
│   │   │   ├── strategy.py         Concession curve, offer grid, ranking
│   │   │   ├── guards.py           Privacy and consistency guards
│   │   │   ├── scenarios.py        Scenarios and market shocks
│   │   │   └── metrics.py          Baselines, optimum, Pareto, deal zone
│   │   ├── llm/client.py           Provider-agnostic LLM client
│   │   ├── agents/                 Agent implementations
│   │   │   ├── base.py             Ports (interfaces) and turn context
│   │   │   ├── negotiator.py       Shared supplier/buyer behaviour
│   │   │   ├── supplier.py, buyer.py, financier.py, mediator.py
│   │   ├── orchestrator/
│   │   │   ├── engine.py           Negotiation protocol (state machine)
│   │   │   └── runner.py           Background execution and persistence
│   │   ├── db/                     SQLAlchemy session, tables, repository
│   │   ├── api/                    Schemas and REST/SSE routes
│   │   ├── a2a/                    A2A layer
│   │   │   ├── protocol.py         Wire format, skills, JSON-RPC envelopes
│   │   │   ├── server.py           Agent Cards, executor, hosted agent servers
│   │   │   └── client.py           Remote agent ports used by the orchestrator
│   │   ├── mcp_servers/            MCP layer
│   │   │   ├── compliance.py       MSMED Act and Section 43B(h) checks
│   │   │   ├── treds.py            TReDS market rates and platforms
│   │   │   ├── erp.py              Company cash position (sandbox ledger)
│   │   │   ├── registry.py         Hosted servers and their lifecycle
│   │   │   └── client.py           Synchronous MCP toolbox for agents
│   │   └── auth/                   Authentication and organisations      (Phase B4)
│   └── tests/
└── frontend/                       React + Vite + TypeScript web app      (Phases F1–F3)
```

## API (current)

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Redirects to the API documentation |
| GET | `/api/health` | Service status |
| GET | `/api/agents` | Hosted agents and their A2A Agent Cards |
| GET | `/api/tools` | MCP tool servers, status and tools |
| GET | `/api/scenarios` | Scenario catalog with public spec and default profiles |
| GET | `/api/shocks` | Available market shocks |
| POST | `/api/negotiations` | Start a negotiation (runs in the background) |
| GET | `/api/negotiations` | List negotiations |
| GET | `/api/negotiations/{id}` | Status and outcome |
| GET | `/api/negotiations/{id}/events` | Event log |
| GET | `/api/negotiations/{id}/stream` | Live Server-Sent Events stream |
| GET | `/api/negotiations/{id}/evaluation` | Comparison with baselines, deal zone |

A2A endpoints per agent (`supplier`, `buyer`, `financier`):

| Method | Path | Purpose |
|---|---|---|
| GET | `/a2a/{role}/.well-known/agent-card.json` | Agent Card |
| POST | `/a2a/{role}/` | A2A JSON-RPC endpoint (`SendMessage`) |

MCP endpoints: `POST /mcp/{compliance|treds|erp}/` (streamable HTTP).

Interactive documentation is served at `/docs`.

## Data model

- `negotiations`: id, scenario, status (`pending`, `running`, `agreed`, `no_deal`, `failed`), configuration, outcome, final state (sandbox only), timestamps.
- `negotiation_events`: ordered event log per negotiation (offers, rate quotes, shocks, mediation, privacy redactions, acceptance), with the terms and per-party scores.

## Deployment

| Component | Target |
|---|---|
| Backend | Docker container on Render |
| Database | Supabase PostgreSQL |
| Frontend | Vercel |

## Delivery phases

| Phase | Scope | Status |
|---|---|---|
| B1 | Core engine as a service, REST API, live stream, persistence, tests | Done |
| B2 | A2A agent servers with Agent Cards; orchestrator negotiates over A2A | Done |
| B3 | MCP servers for compliance, TReDS rates and ERP cash data | Done |
| B4 | Authentication, organisations, human approval, audit trail, term sheet | Planned |
| F1–F3 | Web app: dashboard, negotiation room, policy console, outcomes | Planned |