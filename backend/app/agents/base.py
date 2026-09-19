"""Agent contracts. The orchestrator talks to agents only through these interfaces,
so an agent can run in-process (Phase B1) or behind the A2A protocol (Phase B2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol

from ..core.models import DealSpec, MarketState, Terms


@dataclass
class TurnContext:
    round: int
    max_rounds: int
    spec: DealSpec
    market: MarketState
    rate: float
    counterpart: str = ""
    opponent_last: Optional[Terms] = None
    recent_events: List[str] = field(default_factory=list)


@dataclass
class Proposal:
    terms: Terms
    message: str
    redacted: bool = False
    used_llm: bool = False


@dataclass
class Announcement:
    rate: float
    message: str
    redacted: bool = False
    used_llm: bool = False


class NegotiatorPort(Protocol):
    role: str
    name: str

    def propose(self, ctx: TurnContext) -> Proposal: ...
    def respond(self, offer: Terms, ctx: TurnContext) -> bool: ...
    def evaluate(self, terms: Terms, ctx: TurnContext) -> float: ...
    def on_shock(self, key: str) -> None: ...
    def snapshot(self) -> dict: ...


class FinancierPort(Protocol):
    role: str
    name: str

    def quote(self, ctx: TurnContext) -> float: ...
    def announce(self, rate: float, reason: str, ctx: TurnContext) -> Announcement: ...
    def accepts(self, terms: Terms, ctx: TurnContext) -> bool: ...
    def evaluate(self, terms: Terms, ctx: TurnContext) -> float: ...
    def on_shock(self, key: str) -> None: ...
    def snapshot(self) -> dict: ...