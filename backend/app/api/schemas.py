"""Request and response schemas for the REST API."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..core.scenarios import SCENARIOS, SHOCKS

Provider = Literal["offline", "gemini", "groq", "openai", "anthropic"]
Role = Literal["supplier", "buyer", "financier", "mediator"]


class TermsOut(BaseModel):
    price: float
    days: int
    treds: bool
    buyer_share: float
    rate: float


class ShockIn(BaseModel):
    key: str
    at_round: int = Field(ge=1, le=30)

    @model_validator(mode="after")
    def _known(self):
        if self.key not in SHOCKS:
            raise ValueError(f"Unknown shock '{self.key}'. Options: {', '.join(SHOCKS)}")
        return self


class SupplierOverrides(BaseModel):
    unit_cost: Optional[float] = Field(None, gt=0)
    cost_of_capital: Optional[float] = Field(None, ge=0, le=0.6)
    runway_days: Optional[int] = Field(None, ge=1, le=365)
    batna_price: Optional[float] = Field(None, gt=0)
    batna_days: Optional[int] = Field(None, ge=0, le=365)
    concession_beta: Optional[float] = Field(None, ge=0.1, le=5)


class BuyerOverrides(BaseModel):
    cost_of_capital: Optional[float] = Field(None, ge=0, le=0.6)
    claim_probability: Optional[float] = Field(None, ge=0, le=1)
    batna_price: Optional[float] = Field(None, gt=0)
    batna_days: Optional[int] = Field(None, ge=0, le=365)
    switching_cost: Optional[float] = Field(None, ge=0)
    concession_beta: Optional[float] = Field(None, ge=0.1, le=5)


class FinancierOverrides(BaseModel):
    cost_of_funds: Optional[float] = Field(None, ge=0, le=0.4)
    min_spread: Optional[float] = Field(None, ge=0, le=0.2)
    concession_beta: Optional[float] = Field(None, ge=0.1, le=5)


class MarketOverrides(BaseModel):
    bank_rate: Optional[float] = Field(None, ge=0, le=0.2)


class Overrides(BaseModel):
    supplier: SupplierOverrides = SupplierOverrides()
    buyer: BuyerOverrides = BuyerOverrides()
    financier: FinancierOverrides = FinancierOverrides()
    market: MarketOverrides = MarketOverrides()


class LLMConfig(BaseModel):
    provider: Optional[Provider] = None
    per_agent: Dict[Role, Provider] = {}


class NegotiationCreate(BaseModel):
    scenario: str = "auto_parts"
    max_rounds: Optional[int] = Field(None, ge=4, le=30)
    shocks: List[ShockIn] = []
    overrides: Overrides = Overrides()
    llm: LLMConfig = LLMConfig()
    pace_seconds: Optional[float] = Field(None, ge=0, le=5)

    @model_validator(mode="after")
    def _check(self):
        if self.scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario '{self.scenario}'. Options: {', '.join(SCENARIOS)}")
        rounds = self.max_rounds or SCENARIOS[self.scenario].spec.max_rounds
        for s in self.shocks:
            if s.at_round > rounds:
                raise ValueError(f"Shock '{s.key}' is scheduled after the last round ({rounds}).")
        return self


class NegotiationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scenario_key: str
    title: str
    status: str
    config: dict
    outcome: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    kind: str
    round: int
    agent: str
    message: str
    terms: Optional[TermsOut] = None
    utilities: dict = {}
    meta: dict = {}
    created_at: datetime


class ScenarioOut(BaseModel):
    key: str
    title: str
    story: str
    spec: dict
    market: dict
    parties: Dict[str, str]
    defaults: Dict[str, dict]


class ShockOut(BaseModel):
    key: str
    title: str
    description: str


class EvaluationOut(BaseModel):
    negotiation_id: str
    approaches: List[dict]
    efficiency: float
    pareto_efficient: bool
    balance: float
    deal_zone: List[dict]