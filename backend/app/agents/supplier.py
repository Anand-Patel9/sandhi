"""MSME supplier agent: wants a fair price and cash before its runway ends."""
from __future__ import annotations

from ..core.models import SupplierProfile, Terms
from ..core.utilities import supplier_surplus
from .base import TurnContext
from .negotiator import NegotiatorAgent


class SupplierAgent(NegotiatorAgent):
    role = "supplier"
    profile: SupplierProfile

    def surplus(self, t: Terms, ctx: TurnContext) -> float:
        return supplier_surplus(t, self.profile, ctx.spec)

    def private_values(self):
        p = self.profile
        return [p.unit_cost, p.runway_days, p.batna_price, p.cost_of_capital * 100,
                p.liquidity_penalty * 100]

    def private_brief(self) -> str:
        p = self.profile
        return (f"PRIVATE: unit cost ₹{p.unit_cost:.0f}, cash runway {p.runway_days} days, "
                f"borrowing cost {p.cost_of_capital * 100:.0f}%, an alternative buyer would pay "
                f"₹{p.batna_price:.0f} at {p.batna_days} days. Goal: get paid fast at a fair price "
                "without losing this customer.")

    def template_offer(self, o: Terms, ctx: TurnContext) -> str:
        limit = ctx.spec.legal_limit_days
        lines = []
        if o.treds:
            lines.append(self.rng.choice([
                f"Let's route this invoice through TReDS: you keep {o.days}-day terms and we get paid on day 2.",
                f"TReDS solves both our problems: you pay in {o.days} days, our workers get paid now.",
            ]))
            if o.buyer_share > 0:
                lines.append(f"We ask you to carry {round(o.buyer_share * 100)}% of the discounting cost, "
                             "since it protects your supply line.")
        elif o.days <= limit:
            lines.append(f"We can hold ₹{o.price:,.2f}/unit if payment comes within {o.days} days.")
        else:
            lines.append(f"We can stretch to {o.days} days only at ₹{o.price:,.2f}/unit.")
        last = ctx.opponent_last
        if last and last.days > limit and not o.treds:
            lines.append(f"Paying beyond {limit} days also costs you under Section 43B(h).")
        if ctx.round > ctx.max_rounds * 0.6:
            lines.append("We've moved a long way; this is close to our final position.")
        return " ".join(lines)