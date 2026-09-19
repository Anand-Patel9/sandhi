"""Domain models. `DealSpec` and `MarketState` are public; profiles are private to each agent."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Optional


@dataclass(frozen=True)
class Terms:
    price: float
    days: int
    treds: bool = False
    buyer_share: float = 0.0
    rate: float = 0.0

    def normalised(self) -> "Terms":
        return self if self.treds else replace(self, buyer_share=0.0, rate=0.0)

    def short(self) -> str:
        base = f"₹{self.price:,.2f}/unit, pay in {self.days} days"
        if not self.treds:
            return f"{base}, no invoice discounting"
        return (f"{base}, TReDS discounting at {self.rate * 100:.2f}% p.a., "
                f"buyer bears {round(self.buyer_share * 100)}% of discount cost")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> Optional["Terms"]:
        if not d:
            return None
        return cls(price=float(d["price"]), days=int(d["days"]), treds=bool(d.get("treds", False)),
                   buyer_share=float(d.get("buyer_share", 0.0)), rate=float(d.get("rate", 0.0)))


@dataclass
class DealSpec:
    item: str
    quantity: int
    price_bounds: tuple
    day_options: tuple = (15, 30, 45, 60, 75, 90, 120)
    share_options: tuple = (0.0, 0.5, 1.0)
    max_rounds: int = 12
    legal_limit_days: int = 45
    treds_settlement_days: int = 2


@dataclass
class MarketState:
    bank_rate: float


@dataclass
class SupplierProfile:
    name: str
    unit_cost: float
    cost_of_capital: float
    runway_days: int
    liquidity_penalty: float
    batna_price: float
    batna_days: int
    concession_beta: float
    erp_entity: str = ""


@dataclass
class BuyerProfile:
    name: str
    cost_of_capital: float
    tax_rate: float
    claim_probability: float
    batna_price: float
    batna_days: int
    switching_cost: float
    concession_beta: float


@dataclass
class FinancierProfile:
    name: str
    cost_of_funds: float
    min_spread: float
    buyer_default_prob: float
    loss_given_default: float
    opening_spread: float
    concession_beta: float
    buyer_rating: str = "AA"


@dataclass
class Scenario:
    key: str
    title: str
    story: str
    spec: DealSpec
    market: MarketState
    supplier: SupplierProfile
    buyer: BuyerProfile
    financier: FinancierProfile

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Scenario":
        spec = dict(d["spec"])
        for k in ("price_bounds", "day_options", "share_options"):
            spec[k] = tuple(spec[k])
        return cls(key=d["key"], title=d["title"], story=d["story"], spec=DealSpec(**spec),
                   market=MarketState(**d["market"]), supplier=SupplierProfile(**d["supplier"]),
                   buyer=BuyerProfile(**d["buyer"]), financier=FinancierProfile(**d["financier"]))


@dataclass
class Shock:
    key: str
    at_round: int


@dataclass
class Event:
    kind: str
    round: int
    agent: str
    message: str = ""
    terms: Optional[Terms] = None
    utilities: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "round": self.round, "agent": self.agent, "message": self.message,
                "terms": self.terms.to_dict() if self.terms else None,
                "utilities": self.utilities, "meta": self.meta}