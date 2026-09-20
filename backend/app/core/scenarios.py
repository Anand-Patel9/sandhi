"""Built-in scenarios and market shocks. Figures are illustrative assumptions."""
from __future__ import annotations

import copy
from typing import Dict

from .models import (BuyerProfile, DealSpec, FinancierProfile, MarketState, Scenario,
                     SupplierProfile)


def _auto_parts() -> Scenario:
    return Scenario(
        key="auto_parts",
        title="Caliper housings for Bharat Motors",
        story=("A 40-person casting unit in Rajkot supplies 10,000 brake-caliper housings to a large "
               "vehicle maker. The OEM's standard terms are long, the unit has weeks of cash left, "
               "and a TReDS financier can step in if the price is right."),
        spec=DealSpec(item="caliper housings", quantity=10_000, price_bounds=(370.0, 470.0)),
        market=MarketState(bank_rate=0.0575),
        supplier=SupplierProfile(
            name="Rajkot Castings", unit_cost=355.0, cost_of_capital=0.21,
            runway_days=38, liquidity_penalty=0.06, batna_price=392.0, batna_days=60,
            concession_beta=1.4, erp_entity="rajkot-castings"),
        buyer=BuyerProfile(
            name="Bharat Motors", cost_of_capital=0.095, tax_rate=0.2517,
            claim_probability=0.25, batna_price=438.0, batna_days=45, switching_cost=180_000.0,
            concession_beta=0.55),
        financier=FinancierProfile(
            name="Trident TReDS Bank", cost_of_funds=0.074, min_spread=0.008,
            buyer_default_prob=0.006, loss_given_default=0.45, opening_spread=0.035,
            concession_beta=0.8, buyer_rating="AA"),
    )


def _textiles() -> Scenario:
    return Scenario(
        key="textiles",
        title="Festive shirts for Kalyan Retail",
        story=("A Surat garment unit is making 20,000 shirts for a retail chain ahead of the festive "
               "season. The retailer wants to pay after sell-through; the unit has to pay weavers and "
               "workers this month."),
        spec=DealSpec(item="shirts", quantity=20_000, price_bounds=(186.0, 240.0)),
        market=MarketState(bank_rate=0.0575),
        supplier=SupplierProfile(
            name="Surat Garment Works", unit_cost=182.0, cost_of_capital=0.19,
            runway_days=25, liquidity_penalty=0.05, batna_price=196.0, batna_days=75,
            concession_beta=1.3, erp_entity="surat-garments"),
        buyer=BuyerProfile(
            name="Kalyan Retail", cost_of_capital=0.09, tax_rate=0.2517,
            claim_probability=0.2, batna_price=224.0, batna_days=45, switching_cost=300_000.0,
            concession_beta=0.6),
        financier=FinancierProfile(
            name="Trident TReDS Bank", cost_of_funds=0.078, min_spread=0.009,
            buyer_default_prob=0.012, loss_given_default=0.5, opening_spread=0.04,
            concession_beta=0.8, buyer_rating="A"),
    )


SCENARIOS: Dict[str, Scenario] = {s.key: s for s in (_auto_parts(), _textiles())}


def get_scenario(key: str) -> Scenario:
    if key not in SCENARIOS:
        raise KeyError(f"Unknown scenario '{key}'")
    return copy.deepcopy(SCENARIOS[key])


SHOCKS: Dict[str, Dict[str, str]] = {
    "rate_hike": {
        "title": "RBI hikes rates by 50 bps",
        "description": ("Funding costs rise for everyone, and MSMED Act interest (3x bank rate) "
                        "gets more expensive."),
    },
    "raw_material": {
        "title": "Raw-material price spike (+6%)",
        "description": ("Input costs jump across the industry; both sides' outside options "
                        "reprice upward."),
    },
    "payroll_crunch": {
        "title": "Supplier cash crunch",
        "description": ("A large customer of the supplier defaults, cutting its cash runway "
                        "by 15 days."),
    },
    "quarter_end": {
        "title": "Buyer quarter-end cash squeeze",
        "description": "The buyer's treasury is tight; its cost of capital rises 2 points.",
    },
}


def apply_market_shock(key: str, market: MarketState) -> None:
    """Public effect of a shock, applied by the orchestrator."""
    if key not in SHOCKS:
        raise KeyError(f"Unknown shock '{key}'")
    if key == "rate_hike":
        market.bank_rate += 0.005


def apply_private_shock(key: str, role: str, profile) -> None:
    """Private effect of a shock, applied by each agent to its own profile."""
    if key == "rate_hike":
        if role == "financier":
            profile.cost_of_funds += 0.005
        else:
            profile.cost_of_capital += 0.005
    elif key == "raw_material":
        if role == "supplier":
            profile.unit_cost *= 1.06
            profile.batna_price *= 1.06
        elif role == "buyer":
            profile.batna_price *= 1.06
    elif key == "payroll_crunch" and role == "supplier":
        profile.runway_days = max(5, profile.runway_days - 15)
        profile.concession_beta *= 1.3
    elif key == "quarter_end" and role == "buyer":
        profile.cost_of_capital += 0.02