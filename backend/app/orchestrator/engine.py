"""Negotiation orchestrator. Runs the protocol and never reads agents' private profiles.

Round protocol:
  1. apply scheduled shocks (public effect here, private effect inside each agent)
  2. financier publishes its TReDS rate
  3. supplier proposes -> buyer and financier respond
  4. buyer counter-proposes -> supplier and financier respond
  5. every third round without agreement, the mediator proposes a package
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterator, List, Optional

from ..agents.base import FinancierPort, NegotiatorPort, TurnContext
from ..agents.mediator import Mediator
from ..core.models import DealSpec, Event, MarketState, Shock, Terms
from ..core.scenarios import SHOCKS, apply_market_shock

MEDIATION_EVERY = 3


@dataclass
class Outcome:
    agreed: bool
    terms: Optional[Terms]
    round: int
    via: str = ""
    values: Dict[str, float] = field(default_factory=dict)
    redactions: int = 0
    llm_messages: int = 0
    template_messages: int = 0
    compliance: Optional[dict] = None

    def to_dict(self) -> dict:
        return {"agreed": self.agreed, "terms": self.terms.to_dict() if self.terms else None,
                "round": self.round, "via": self.via, "values": self.values,
                "compliance": self.compliance,
                "redactions": self.redactions, "llm_messages": self.llm_messages,
                "template_messages": self.template_messages}


class NegotiationEngine:
    def __init__(self, spec: DealSpec, market: MarketState, supplier: NegotiatorPort,
                 buyer: NegotiatorPort, financier: FinancierPort, mediator: Mediator,
                 shocks: Optional[List[Shock]] = None,
                 compliance: Optional[Callable[[Terms], Optional[dict]]] = None):
        self.spec = spec
        self.market = market
        self.supplier = supplier
        self.buyer = buyer
        self.financier = financier
        self.mediator = mediator
        self.agents = {"supplier": supplier, "buyer": buyer, "financier": financier}
        self.shocks = sorted(shocks or [], key=lambda s: s.at_round)
        self.compliance = compliance
        self.recent: List[str] = []
        self.outcome: Optional[Outcome] = None
        self._stats = {"redactions": 0, "llm": 0, "template": 0}

    def _ctx(self, t: int, rate: float, counterpart: str = "", opponent_last: Optional[Terms] = None) -> TurnContext:
        return TurnContext(round=t, max_rounds=self.spec.max_rounds, spec=self.spec, market=self.market,
                           rate=rate, counterpart=counterpart, opponent_last=opponent_last,
                           recent_events=list(self.recent))

    def _values(self, terms: Terms, ctx: TurnContext) -> Dict[str, float]:
        return {role: agent.evaluate(terms, ctx) for role, agent in self.agents.items()}

    def _check(self, terms: Terms) -> dict:
        report = self.compliance(terms) if self.compliance else None
        return {"compliance": report} if report else {}

    def _count(self, redacted: bool, used_llm: bool) -> None:
        self._stats["redactions"] += int(redacted)
        self._stats["llm" if used_llm else "template"] += 1

    def _close(self, agreed: bool, terms: Optional[Terms], t: int, via: str, ctx: TurnContext) -> Outcome:
        self.outcome = Outcome(
            agreed=agreed, terms=terms, round=t, via=via,
            values=self._values(terms, ctx) if terms else {},
            redactions=self._stats["redactions"], llm_messages=self._stats["llm"],
            template_messages=self._stats["template"],
            compliance=self._check(terms).get("compliance") if terms else None)
        return self.outcome

    def run(self) -> Iterator[Event]:
        spec = self.spec
        yield Event("info", 0, "system",
                    f"Negotiation opened for {spec.quantity:,} {spec.item}. Legal payment limit "
                    f"{spec.legal_limit_days} days. Maximum {spec.max_rounds} rounds.")
        last: Dict[str, Optional[Terms]] = {"supplier": None, "buyer": None}
        pending = list(self.shocks)
        last_rate: Optional[float] = None

        for t in range(1, spec.max_rounds + 1):
            shocked = False
            while pending and pending[0].at_round == t:
                shock = pending.pop(0)
                apply_market_shock(shock.key, self.market)
                for agent in self.agents.values():
                    agent.on_shock(shock.key)
                info = SHOCKS[shock.key]
                self.recent.append(info["title"])
                shocked = True
                yield Event("shock", t, "market", f"{info['title']}. {info['description']}",
                            meta={"key": shock.key})

            rate = self.financier.quote(self._ctx(t, 0.0))
            if last_rate is None or shocked or abs(rate - last_rate) >= 0.0025:
                reason = ("Opening quote." if last_rate is None
                          else "Updated for changed market conditions." if shocked
                          else "Sharpened to win the mandate.")
                ann = self.financier.announce(rate, reason, self._ctx(t, rate))
                self._count(ann.redacted, ann.used_llm)
                yield Event("rate", t, "financier", ann.message, meta={"rate": rate})
                if ann.redacted:
                    yield Event("privacy", t, "financier", "Privacy guard redacted a private number.")
                last_rate = rate

            for proposer, responder in ((self.supplier, self.buyer), (self.buyer, self.supplier)):
                ctx = self._ctx(t, rate, responder.name, last[responder.role])
                proposal = proposer.propose(ctx)
                self._count(proposal.redacted, proposal.used_llm)
                offer = proposal.terms
                last[proposer.role] = offer
                values = self._values(offer, ctx)
                yield Event("offer", t, proposer.role, proposal.message, offer, values, self._check(offer))
                if proposal.redacted:
                    yield Event("privacy", t, proposer.role, "Privacy guard redacted a private number.")

                resp_ctx = self._ctx(t, rate, proposer.name, offer)
                if responder.respond(offer, resp_ctx) and self.financier.accepts(offer, resp_ctx):
                    yield Event("accept", t, responder.role, f"Agreed: {offer.short()}.", offer, values)
                    out = self._close(True, offer, t, proposer.role, resp_ctx)
                    yield Event("deal", t, "system", "Deal closed.", offer, out.values)
                    return

            if t >= MEDIATION_EVERY and t % MEDIATION_EVERY == 0 and last["supplier"] and last["buyer"]:
                pkg = self.mediator.package(last["supplier"], last["buyer"], rate, spec)
                ctx = self._ctx(t, rate)
                message = self.mediator.speak(pkg, last["supplier"], last["buyer"], t, spec)
                values = self._values(pkg, ctx)
                yield Event("mediation", t, "mediator", message, pkg, values, self._check(pkg))
                verdicts = {"supplier": self.supplier.respond(pkg, ctx),
                            "buyer": self.buyer.respond(pkg, ctx),
                            "financier": self.financier.accepts(pkg, ctx)}
                if all(verdicts.values()):
                    yield Event("accept", t, "system", "All parties accept the mediator's package.", pkg, values)
                    out = self._close(True, pkg, t, "mediator", ctx)
                    yield Event("deal", t, "system", "Deal closed via mediation.", pkg, out.values)
                    return
                rejected = [k for k, ok in verdicts.items() if not ok]
                yield Event("info", t, "mediator", "Package declined by: " + ", ".join(rejected) + ".",
                            meta={"verdicts": verdicts})

        self._close(False, None, spec.max_rounds, "", self._ctx(spec.max_rounds, last_rate or 0.0))
        yield Event("no_deal", spec.max_rounds, "system",
                    "Deadline reached without agreement. Each party falls back to its alternative.")