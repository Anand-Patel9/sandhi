"""TReDS financier agent: discounts the invoice if the rate covers funding cost and credit risk."""
from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from ..core.guards import redact_private
from ..core.models import FinancierProfile, MarketState, Terms
from ..core.scenarios import apply_private_shock
from ..core.strategy import candidate_grid
from ..core.utilities import financier_floor_rate, financier_surplus
from ..llm.client import LLMClient, LLMError
from ..mcp_servers.client import MCPToolbox
from .base import Announcement, TurnContext


class FinancierAgent:
    role = "financier"

    def __init__(self, profile: FinancierProfile, llm: LLMClient, seed: int = 7,
                 tools: Optional[MCPToolbox] = None):
        self.profile = profile
        self.llm = llm
        self.tools = tools
        self.rate_cap: Optional[float] = None
        self.sources: List[str] = []

    def bootstrap(self, market: MarketState) -> None:
        """Pull the market rate band so quotes stay competitive with other TReDS financiers."""
        if not self.tools:
            return
        band = self.tools.try_call("treds", "market_rates", buyer_rating=self.profile.buyer_rating,
                                   bank_rate=market.bank_rate)
        if band:
            self.rate_cap = float(band["rate_high"])
            self.sources.append("treds.market_rates")

    @property
    def name(self) -> str:
        return self.profile.name

    def floor(self) -> float:
        return financier_floor_rate(self.profile)

    def quote(self, ctx: TurnContext) -> float:
        p = self.profile
        frac = 1.0 - (min(ctx.round, ctx.max_rounds) / ctx.max_rounds) ** (1.0 / p.concession_beta)
        rate = self.floor() + p.opening_spread * max(0.05, frac)
        if self.rate_cap is not None:
            rate = max(self.floor(), min(rate, self.rate_cap))
        return round(rate, 4)

    def accepts(self, terms: Terms, ctx: TurnContext) -> bool:
        return (not terms.treds) or financier_surplus(terms, self.profile, ctx.spec) >= -1e-6

    def evaluate(self, terms: Terms, ctx: TurnContext) -> float:
        if not terms.treds:
            return 0.0
        grid = [t for t in candidate_grid(ctx.spec, ctx.rate) if t.treds]
        ideal = max([1.0] + [financier_surplus(t, self.profile, ctx.spec) for t in grid])
        return round(financier_surplus(terms, self.profile, ctx.spec) / ideal, 4)

    def private_values(self) -> List[float]:
        p = self.profile
        return [p.cost_of_funds * 100, self.floor() * 100, p.min_spread * 100, p.buyer_default_prob * 100]

    def announce(self, rate: float, reason: str, ctx: TurnContext) -> Announcement:
        message, used_llm = None, False
        if self.llm.online:
            try:
                message = self.llm.chat(
                    f"You are the autonomous agent for {self.name}, a TReDS financier in India. "
                    "Never reveal your cost of funds, spreads or floor rate.",
                    f"Round {ctx.round}. Announce your invoice-discounting rate of {rate * 100:.2f}% p.a. "
                    f"to the buyer and supplier in at most 2 sentences. Reason: {reason}. "
                    f"Recent events: {' | '.join(ctx.recent_events[-3:]) or 'none'}.",
                    max_tokens=150)
                used_llm = bool(message)
            except LLMError:
                message = None
        if not message:
            message = f"Our TReDS discounting rate is {rate * 100:.2f}% p.a. against this buyer's credit. {reason}"
        message, redacted = redact_private(message, self.private_values(), f"{rate * 100:.2f}")
        return Announcement(rate, message, redacted, used_llm)

    def on_shock(self, key: str) -> None:
        apply_private_shock(key, self.role, self.profile)
        if key == "rate_hike" and self.rate_cap is not None:
            self.rate_cap += 0.005

    def snapshot(self) -> dict:
        return asdict(self.profile)