"""Deterministic utility functions in INR.

Surplus = value of a deal minus the value of the party's walk-away alternative (BATNA).
Modelling notes:
- Section 43B(h): paying an MSME after the legal limit defers the buyer's deduction ~1 year,
  costed at the buyer's cost of capital.
- MSMED Act interest (3x bank rate) is an expected cost weighted by claim probability, and is
  treated as removed when the MSME is paid through TReDS.
"""
from __future__ import annotations

from .models import BuyerProfile, DealSpec, FinancierProfile, MarketState, Scenario, SupplierProfile, Terms


def invoice_value(t: Terms, spec: DealSpec) -> float:
    return t.price * spec.quantity


def discount_cost(t: Terms, spec: DealSpec) -> float:
    return invoice_value(t, spec) * t.rate * t.days / 365.0 if t.treds else 0.0


def supplier_value(t: Terms, s: SupplierProfile, spec: DealSpec) -> float:
    v = invoice_value(t, spec)
    if t.treds:
        cash = v - (1.0 - t.buyer_share) * discount_cost(t, spec)
        days_to_cash = spec.treds_settlement_days
    else:
        cash, days_to_cash = v, t.days
    time_cost = cash * s.cost_of_capital * days_to_cash / 365.0
    liquidity = v * s.liquidity_penalty * max(0, days_to_cash - s.runway_days) / 30.0
    return cash - spec.quantity * s.unit_cost - time_cost - liquidity


def supplier_surplus(t: Terms, s: SupplierProfile, spec: DealSpec) -> float:
    return supplier_value(t, s, spec) - supplier_value(Terms(s.batna_price, s.batna_days), s, spec)


def buyer_cost(t: Terms, b: BuyerProfile, spec: DealSpec, m: MarketState) -> float:
    v = invoice_value(t, spec)
    absorbed = t.buyer_share * discount_cost(t, spec)
    float_benefit = v * b.cost_of_capital * t.days / 365.0
    late = t.days > spec.legal_limit_days
    tax_exposure = v * b.tax_rate * b.cost_of_capital if late else 0.0
    msmed_interest = 0.0
    if late and not t.treds:
        msmed_interest = (b.claim_probability * v * 3 * m.bank_rate
                          * (t.days - spec.legal_limit_days) / 365.0)
    return v + absorbed - float_benefit + tax_exposure + msmed_interest


def buyer_surplus(t: Terms, b: BuyerProfile, spec: DealSpec, m: MarketState) -> float:
    batna = buyer_cost(Terms(b.batna_price, b.batna_days), b, spec, m) + b.switching_cost
    return batna - buyer_cost(t, b, spec, m)


def financier_floor_rate(f: FinancierProfile) -> float:
    return f.cost_of_funds + f.buyer_default_prob * f.loss_given_default + f.min_spread


def financier_surplus(t: Terms, f: FinancierProfile, spec: DealSpec) -> float:
    if not t.treds:
        return 0.0
    v = invoice_value(t, spec)
    horizon = t.days / 365.0
    income = discount_cost(t, spec)
    funding = v * f.cost_of_funds * horizon
    expected_loss = v * f.buyer_default_prob * f.loss_given_default * horizon
    required = v * f.min_spread * horizon
    return income - funding - expected_loss - required


def all_surpluses(t: Terms, sc: Scenario) -> dict:
    return {
        "supplier": supplier_surplus(t, sc.supplier, sc.spec),
        "buyer": buyer_surplus(t, sc.buyer, sc.spec, sc.market),
        "financier": financier_surplus(t, sc.financier, sc.spec),
    }