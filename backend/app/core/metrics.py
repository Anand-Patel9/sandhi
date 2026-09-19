"""Evaluation: negotiated deal vs single-objective baselines and the full-information optimum."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .models import Scenario, Terms
from .strategy import price_points
from .utilities import all_surpluses, buyer_surplus, financier_floor_rate, supplier_surplus


def full_grid(sc: Scenario) -> List[Terms]:
    floor = financier_floor_rate(sc.financier)
    rates = [round(floor + k * 0.005, 4) for k in range(7)]
    out = []
    for p in price_points(sc.spec):
        for d in sc.spec.day_options:
            out.append(Terms(p, d))
            for share in sc.spec.share_options:
                out.extend(Terms(p, d, True, share, r) for r in rates)
    return out


@dataclass
class Evaluated:
    key: str
    label: str
    description: str
    terms: Optional[Terms]
    surplus: Dict[str, float]
    viable: bool
    blocked_by: List[str]

    @property
    def joint(self) -> float:
        return sum(self.surplus.values()) if self.viable else 0.0

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "description": self.description,
                "terms": self.terms.to_dict() if self.terms else None,
                "surplus": {k: round(v, 2) for k, v in self.surplus.items()},
                "realised": {k: round(v if self.viable else 0.0, 2) for k, v in self.surplus.items()},
                "viable": self.viable, "blocked_by": self.blocked_by}


def evaluate(key: str, label: str, description: str, t: Optional[Terms], sc: Scenario) -> Evaluated:
    if t is None:
        return Evaluated(key, label, description, None,
                         {"supplier": 0.0, "buyer": 0.0, "financier": 0.0}, False, ["deadline"])
    s = all_surpluses(t, sc)
    blocked = [k for k, v in s.items() if v < -1e-6]
    return Evaluated(key, label, description, t, s, not blocked, blocked)


def nash_optimum(sc: Scenario, grid: Optional[List[Terms]] = None) -> Optional[Terms]:
    """Maximise supplier x buyer surplus with a non-losing financier. Requires all private data."""
    best, best_val = None, -1.0
    for t in grid or full_grid(sc):
        s = all_surpluses(t, sc)
        if s["supplier"] <= 0 or s["buyer"] <= 0 or s["financier"] < 0:
            continue
        val = s["supplier"] * s["buyer"]
        if val > best_val:
            best, best_val = t, val
    return best


def baselines(sc: Scenario, negotiated: Optional[Terms]) -> List[Evaluated]:
    grid = full_grid(sc)
    direct = [t for t in grid if not t.treds]
    buyer_ai = max(direct, key=lambda t: buyer_surplus(t, sc.buyer, sc.spec, sc.market))
    supplier_ai = max(direct, key=lambda t: supplier_surplus(t, sc.supplier, sc.spec))
    legacy_ai = Terms(sc.spec.price_bounds[0], max(sc.spec.day_options))
    status_quo = Terms(round((sc.supplier.batna_price + sc.buyer.batna_price) / 2, 2), 90)
    return [
        evaluate("buyer_ai", "Buyer-only AI",
                 "Optimises the buyer's full cost, including 43B(h).", buyer_ai, sc),
        evaluate("legacy_ai", "Legacy procurement AI",
                 "Lowest price, longest payment days.", legacy_ai, sc),
        evaluate("supplier_ai", "Supplier-only AI",
                 "Optimises the MSME's cash position.", supplier_ai, sc),
        evaluate("status_quo", "Industry status quo",
                 "Mid-market price on 90-day terms, no financing.", status_quo, sc),
        evaluate("negotiated", "Multi-agent negotiation",
                 "Autonomous agents with private information negotiate.", negotiated, sc),
        evaluate("optimum", "Full-information optimum",
                 "Theoretical ceiling; needs every party's private data.", nash_optimum(sc, grid), sc),
    ]


def pareto_gap(t: Terms, sc: Scenario) -> float:
    """Largest joint gain from a package that leaves no party worse off (0 = Pareto-efficient)."""
    base = all_surpluses(t, sc)
    best = 0.0
    for c in full_grid(sc):
        s = all_surpluses(c, sc)
        if all(s[k] >= base[k] - 1e-6 for k in base):
            best = max(best, sum(s.values()) - sum(base.values()))
    return best


def ideals(sc: Scenario) -> Dict[str, float]:
    grid = full_grid(sc)
    return {"supplier": max(supplier_surplus(t, sc.supplier, sc.spec) for t in grid),
            "buyer": max(buyer_surplus(t, sc.buyer, sc.spec, sc.market) for t in grid)}


def balance(surplus: Dict[str, float], ideal: Dict[str, float]) -> float:
    a = surplus["supplier"] / max(1.0, ideal["supplier"])
    b = surplus["buyer"] / max(1.0, ideal["buyer"])
    return 0.0 if a <= 0 or b <= 0 else min(a, b) / max(a, b)


def summary(sc: Scenario, negotiated: Optional[Terms]) -> dict:
    evals = baselines(sc, negotiated)
    ours = next(e for e in evals if e.key == "negotiated")
    opt = next(e for e in evals if e.key == "optimum")
    return {
        "approaches": [e.to_dict() for e in evals],
        "efficiency": round(ours.joint / opt.joint, 4) if opt.joint else 0.0,
        "pareto_efficient": bool(negotiated) and pareto_gap(negotiated, sc) < 1.0,
        "balance": round(balance(ours.surplus, ideals(sc)), 4) if ours.viable else 0.0,
    }


def deal_zone(sc: Scenario, steps: int = 201) -> List[dict]:
    """Price range per payment term where both supplier and buyer beat their walk-away options."""
    lo, hi = sc.spec.price_bounds
    prices = [lo + i * (hi - lo) / (steps - 1) for i in range(steps)]
    rate = financier_floor_rate(sc.financier) + 0.01
    zones = []
    for days in sc.spec.day_options:
        for treds in (False, True):
            ok = [p for p in prices
                  if supplier_surplus(Terms(p, days, treds, 0.0, rate), sc.supplier, sc.spec) >= 0
                  and buyer_surplus(Terms(p, days, treds, 0.0, rate), sc.buyer, sc.spec, sc.market) >= 0]
            zones.append({"days": days, "treds": treds,
                          "min_price": round(min(ok), 2) if ok else None,
                          "max_price": round(max(ok), 2) if ok else None})
    return zones