"""Compliance MCP server: MSMED Act payment limit and Section 43B(h) checks."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

server = MCPServer(
    name="sandhi-compliance", version="1.0.0",
    instructions="Checks MSME payment terms against the MSMED Act 45-day limit and Section 43B(h).",
)

RULES = (
    "MSMED Act 2006, s.15-16: a buyer must pay an MSME within the agreed period, not exceeding 45 days; "
    "late payment attracts compound interest at three times the RBI bank rate. "
    "Income Tax Act s.43B(h): payments to micro and small enterprises made after the MSMED limit are "
    "deductible only in the year actually paid. "
    "TReDS: an invoice discounted on a TReDS platform pays the MSME within days while the buyer settles "
    "with the financier on the agreed due date."
)


@server.tool()
def check_payment_terms(payment_days: int, via_treds: bool, invoice_value: float, bank_rate: float,
                        legal_limit_days: int = 45) -> dict:
    """Assess whether payment terms comply with the MSMED Act and whether Section 43B(h) applies."""
    days_to_msme = 2 if via_treds else payment_days
    over = max(0, payment_days - legal_limit_days)
    msme_over = max(0, days_to_msme - legal_limit_days)
    interest = invoice_value * 3 * bank_rate * msme_over / 365.0
    notes = []
    if msme_over:
        notes.append(f"MSME is paid {msme_over} days after the {legal_limit_days}-day MSMED limit.")
    if via_treds:
        notes.append("TReDS discounting pays the MSME within 2 days.")
    if over:
        notes.append("Buyer's payment date is after the limit: Section 43B(h) defers its tax deduction.")
    return {
        "msmed_compliant": msme_over == 0,
        "days_to_msme_payment": days_to_msme,
        "days_over_limit": msme_over,
        "section_43bh_deduction_deferred": over > 0,
        "msmed_interest_exposure": round(interest, 2),
        "notes": notes,
    }


@server.tool()
def payment_rules() -> str:
    """Summary of the payment rules that apply to MSME supply contracts."""
    return RULES