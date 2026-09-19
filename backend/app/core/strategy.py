"""Negotiation strategy: concession curve, offer grid, and offer ranking."""
from __future__ import annotations

from typing import Callable, List, Optional

from .models import DealSpec, Terms

PRICE_STEPS = 41


def aspiration(ideal: float, t: int, T: int, beta: float, floor_frac: float = 0.03) -> float:
    """Time-dependent concession (Faratin et al., 1998). beta > 1 concedes early, beta < 1 holds out."""
    t = min(max(t, 0), T)
    frac = 1.0 - (t / T) ** (1.0 / beta)
    return max(ideal * floor_frac, ideal * frac)


def price_points(spec: DealSpec, steps: int = PRICE_STEPS) -> List[float]:
    lo, hi = spec.price_bounds
    return [round(lo + i * (hi - lo) / (steps - 1), 2) for i in range(steps)]


def candidate_grid(spec: DealSpec, rate: float) -> List[Terms]:
    grid = []
    for p in price_points(spec):
        for d in spec.day_options:
            grid.append(Terms(p, d))
            for share in spec.share_options:
                grid.append(Terms(p, d, True, share, rate))
    return grid


def distance(a: Terms, b: Terms, spec: DealSpec) -> float:
    lo, hi = spec.price_bounds
    span_days = max(spec.day_options) - min(spec.day_options)
    return (abs(a.price - b.price) / (hi - lo)
            + abs(a.days - b.days) / span_days
            + 0.35 * (a.treds != b.treds)
            + 0.2 * abs(a.buyer_share - b.buyer_share))


def rank_options(candidates: List[Terms], surplus: Callable[[Terms], float], target: float,
                 opponent_last: Optional[Terms], spec: DealSpec, k: int = 3) -> List[Terms]:
    """Offers that meet our target, ordered by closeness to the other side's last offer."""
    valid = [c for c in candidates if surplus(c) >= target]
    if not valid:
        valid = sorted(candidates, key=surplus, reverse=True)[:k]
    if opponent_last is None:
        ranked = sorted(valid, key=lambda c: -surplus(c))
    else:
        ranked = sorted(valid, key=lambda c: (distance(c, opponent_last, spec), -surplus(c)))
    picked, seen = [], set()
    for c in ranked:
        sig = (round(c.price, 2), c.days, c.treds, c.buyer_share)
        if sig not in seen:
            seen.add(sig)
            picked.append(c)
        if len(picked) == k:
            break
    return picked