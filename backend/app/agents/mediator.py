"""Neutral mediator: sees only public offers and proposes compromise packages."""
from __future__ import annotations

from ..core.guards import prices_consistent
from ..core.models import DealSpec, Terms
from ..llm.client import LLMClient, LLMError


class Mediator:
    role = "mediator"
    name = "Mediator (neutral)"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def package(self, a: Terms, b: Terms, rate: float, spec: DealSpec) -> Terms:
        price = round((a.price + b.price) / 2, 2)
        days = min(spec.day_options, key=lambda d: abs(d - (a.days + b.days) / 2))
        limit = spec.legal_limit_days
        if a.treds or b.treds or days > limit:
            if a.days <= limit or b.days <= limit:
                days = min(days, limit)
            share = min(spec.share_options, key=lambda s: abs(s - (a.buyer_share + b.buyer_share) / 2))
            return Terms(price, days, True, share, rate)
        return Terms(price, days)

    def speak(self, pkg: Terms, a: Terms, b: Terms, round_no: int, spec: DealSpec) -> str:
        default = (f"The parties are ₹{abs(a.price - b.price):.2f}/unit and {abs(a.days - b.days)} days "
                   f"apart. I propose {pkg.short()}.")
        if pkg.treds:
            default += " TReDS lets the MSME be paid on day 2 while the buyer keeps its cycle."
        elif pkg.days > spec.legal_limit_days:
            default += f" Note: payment beyond {spec.legal_limit_days} days breaches the MSMED Act."
        if not self.llm.online:
            return default
        try:
            message = self.llm.chat(
                "You are a neutral mediator in an Indian MSME trade-credit negotiation. You only know "
                "the public offers. Be concise and even-handed.",
                f"Round {round_no}. Supplier's last offer: {a.short()}. Buyer's last offer: {b.short()}. "
                f"Propose exactly this compromise in at most 3 sentences, explaining why it is fair: "
                f"{pkg.short()}.", max_tokens=200)
        except LLMError:
            return default
        allowed = [pkg.price, a.price, b.price, abs(a.price - b.price)]
        return message if message and prices_consistent(message, allowed) else default