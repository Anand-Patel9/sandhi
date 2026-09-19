"""TReDS MCP server: indicative invoice-discounting rates and platforms."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

server = MCPServer(
    name="sandhi-treds", version="1.0.0",
    instructions="Indicative TReDS discounting rates by buyer credit rating. Figures are illustrative.",
)

SPREAD_BANDS = {"AAA": (0.012, 0.030), "AA": (0.018, 0.040), "A": (0.028, 0.055),
                "BBB": (0.040, 0.075)}
PLATFORMS = [
    {"name": "RXIL", "operator": "Receivables Exchange of India"},
    {"name": "M1xchange", "operator": "Mynd Solutions"},
    {"name": "Invoicemart", "operator": "A.TReDS"},
]


@server.tool()
def market_rates(buyer_rating: str, bank_rate: float) -> dict:
    """Indicative annual discount-rate band for invoices accepted by a buyer with this credit rating."""
    rating = buyer_rating.upper()
    if rating not in SPREAD_BANDS:
        raise ValueError(f"Unknown rating '{buyer_rating}'. Use one of {', '.join(SPREAD_BANDS)}.")
    low, high = SPREAD_BANDS[rating]
    base = bank_rate + 0.0125
    return {"buyer_rating": rating, "rate_low": round(base + low, 4), "rate_high": round(base + high, 4),
            "basis": "illustrative band: bank rate + funding premium + rating spread"}


@server.tool()
def list_platforms() -> list:
    """RBI-licensed TReDS platforms available for discounting."""
    return PLATFORMS