"""Shared behaviour for principal negotiators: the LLM argues, the code decides."""
from __future__ import annotations

import random
from dataclasses import asdict, replace
from typing import List, Optional

from ..core.guards import prices_consistent, redact_private
from ..core.models import MarketState, Terms
from ..core.scenarios import apply_private_shock
from ..core.strategy import aspiration, candidate_grid, rank_options
from ..llm.client import LLMClient, LLMError
from ..mcp_servers.client import MCPToolbox
from .base import Proposal, TurnContext


class NegotiatorAgent:
    role = "negotiator"

    def __init__(self, profile, llm: LLMClient, seed: int = 7, tools: Optional[MCPToolbox] = None):
        self.profile = profile
        self.llm = llm
        self.tools = tools
        self.rng = random.Random(seed + sum(map(ord, self.role)))
        self.rules = ""
        self.sources: List[str] = []

    def bootstrap(self, market: MarketState) -> None:
        """Load live data through MCP before negotiating."""
        if self.tools and self.llm.online:
            rules = self.tools.try_call("compliance", "payment_rules")
            if rules:
                self.rules = str(rules)
                self.sources.append("compliance.payment_rules")

    @property
    def name(self) -> str:
        return self.profile.name

    # --- implemented by subclasses ---
    def surplus(self, t: Terms, ctx: TurnContext) -> float:
        raise NotImplementedError

    def private_brief(self) -> str:
        raise NotImplementedError

    def private_values(self) -> List[float]:
        raise NotImplementedError

    def template_offer(self, o: Terms, ctx: TurnContext) -> str:
        raise NotImplementedError

    # --- decision logic (deterministic) ---
    def _grid(self, ctx: TurnContext) -> List[Terms]:
        return candidate_grid(ctx.spec, ctx.rate)

    def _ideal(self, grid: List[Terms], ctx: TurnContext) -> float:
        return max(1.0, max(self.surplus(c, ctx) for c in grid))

    def _target(self, grid: List[Terms], ctx: TurnContext) -> float:
        return aspiration(self._ideal(grid, ctx), ctx.round, ctx.max_rounds, self.profile.concession_beta)

    def options(self, ctx: TurnContext, k: int = 3) -> List[Terms]:
        grid = self._grid(ctx)
        return rank_options(grid, lambda t: self.surplus(t, ctx), self._target(grid, ctx),
                            ctx.opponent_last, ctx.spec, k)

    def respond(self, offer: Terms, ctx: TurnContext) -> bool:
        value = self.surplus(offer, ctx)
        if value < 0:
            return False
        grid = self._grid(ctx)
        if value >= self._target(grid, ctx):
            return True
        own_next = self.options(replace(ctx, opponent_last=offer), k=1)
        return bool(own_next) and value >= self.surplus(own_next[0], ctx)

    def evaluate(self, terms: Terms, ctx: TurnContext) -> float:
        return round(self.surplus(terms, ctx) / self._ideal(self._grid(ctx), ctx), 4)

    def on_shock(self, key: str) -> None:
        apply_private_shock(key, self.role, self.profile)

    def snapshot(self) -> dict:
        return asdict(self.profile)

    # --- communication (LLM with deterministic fallback) ---
    def propose(self, ctx: TurnContext) -> Proposal:
        options = self.options(ctx)
        chosen, message, used_llm = options[0], None, False
        if self.llm.online:
            listing = "\n".join(f"{i}: {o.short()}" for i, o in enumerate(options))
            user = (
                f"Round {ctx.round} of {ctx.max_rounds}. You are negotiating with {ctx.counterpart}.\n"
                f"Their last offer: {ctx.opponent_last.short() if ctx.opponent_last else 'none yet'}.\n"
                f"Recent events: {' | '.join(ctx.recent_events[-4:]) or 'none'}.\n\n"
                f"Pre-approved counter-offers, all acceptable to you:\n{listing}\n\n"
                "Pick the option most likely to move the deal forward and write a persuasive "
                "message of at most 3 sentences proposing it. Use business arguments (cash flow, "
                "MSMED Act 45-day rule, Section 43B(h), TReDS, reliability). Never reveal private "
                'numbers, costs, limits or runway. JSON keys: "choice" (integer), "message" (string).'
            )
            try:
                data = self.llm.chat_json(self.system_prompt(), user)
                idx = int(data.get("choice", 0))
                if 0 <= idx < len(options):
                    chosen = options[idx]
                message = str(data.get("message", "")).strip() or None
            except (LLMError, ValueError, TypeError):
                message = None
        allowed = [chosen.price] + ([ctx.opponent_last.price] if ctx.opponent_last else [])
        if message and prices_consistent(message, allowed):
            used_llm = True
        else:
            message = self.template_offer(chosen, ctx)
        message, redacted = redact_private(message, self.private_values(), chosen.short())
        return Proposal(chosen, message, redacted, used_llm)

    def system_prompt(self) -> str:
        rules = f" Applicable rules: {self.rules}" if self.rules else ""
        return (f"You are the autonomous negotiation agent for {self.name} in an Indian MSME "
                f"trade-credit deal. {self.private_brief()}{rules} Be firm but professional.")