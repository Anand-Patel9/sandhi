"""Corporate buyer agent: wants the lowest total cost with a reliable, compliant supplier."""
from __future__ import annotations

from ..core.models import BuyerProfile, Terms
from ..core.utilities import buyer_surplus
from .base import TurnContext
from .negotiator import NegotiatorAgent


class BuyerAgent(NegotiatorAgent):
    role = "buyer"
    profile: BuyerProfile

    def surplus(self, t: Terms, ctx: TurnContext) -> float:
        return buyer_surplus(t, self.profile, ctx.spec, ctx.market)

    def private_values(self):
        p = self.profile
        return [p.batna_price, p.cost_of_capital * 100, p.switching_cost,
                p.switching_cost / 100_000, p.claim_probability * 100]

    def private_brief(self) -> str:
        p = self.profile
        return (f"PRIVATE: treasury cost of capital {p.cost_of_capital * 100:.1f}%, alternate supplier "
                f"quotes ₹{p.batna_price:.0f} at {p.batna_days} days plus ₹{p.switching_cost:,.0f} "
                f"switching cost; chance the MSME files an MSMED interest claim "
                f"~{p.claim_probability * 100:.0f}%. Paying after 45 days defers your tax deduction "
                "under Section 43B(h). Goal: lowest total cost with a reliable, compliant supplier.")

    def template_offer(self, o: Terms, ctx: TurnContext) -> str:
        lines = [self.rng.choice([
            f"Our procurement budget supports ₹{o.price:,.2f}/unit.",
            f"We can commit to ₹{o.price:,.2f}/unit on this volume.",
        ])]
        if o.treds:
            share = round(o.buyer_share * 100)
            lines.append(f"We'll pay the financier in {o.days} days via TReDS"
                         + (f" and absorb {share}% of the discounting cost." if share else "."))
        elif o.days <= ctx.spec.legal_limit_days:
            lines.append(f"Payment in {o.days} days, within the MSMED Act limit.")
        else:
            lines.append(f"Our standard cycle is {o.days} days.")
        if ctx.round > ctx.max_rounds * 0.6:
            lines.append("We need to close this week.")
        return " ".join(lines)