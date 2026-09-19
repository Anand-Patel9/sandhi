"""Outbound message guards: privacy redaction and price consistency."""
from __future__ import annotations

import re
from typing import Iterable, Iterator, Tuple

NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?")
PRICE_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)")
PUBLIC_DAY_TERMS = {15, 30, 45, 60, 75, 90, 120}
REDACTED = "[private]"


def numbers_in(text: str) -> Iterator[Tuple[int, int, float]]:
    for m in NUM_RE.finditer(text):
        try:
            yield m.start(), m.end(), float(m.group(0).replace(",", ""))
        except ValueError:
            continue


def redact_private(message: str, secrets: Iterable[float], public_text: str = "") -> Tuple[str, bool]:
    """Replace any number matching a private value, unless it is part of the public offer."""
    public = {round(v, 2) for _, _, v in numbers_in(public_text)}
    secret_vals = [round(v, 2) for v in secrets]
    out, leaked, shift = message, False, 0
    for start, end, val in list(numbers_in(message)):
        v = round(val, 2)
        if v in public or v in PUBLIC_DAY_TERMS:
            continue
        if any(abs(v - s) < 0.051 for s in secret_vals):
            out = out[:start + shift] + REDACTED + out[end + shift:]
            shift += len(REDACTED) - (end - start)
            leaked = True
    return out, leaked


def prices_consistent(message: str, allowed: Iterable[float]) -> bool:
    """True if every rupee amount quoted in the message is one of the allowed prices."""
    allowed = [round(a, 2) for a in allowed]
    for m in PRICE_RE.finditer(message):
        try:
            v = round(float(m.group(1).replace(",", "")), 2)
        except ValueError:
            return False
        if not any(abs(v - a) < 0.051 for a in allowed):
            return False
    return True