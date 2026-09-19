"""Term-sheet PDF for an approved agreement."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..core.models import Scenario, Terms
from ..core.scenarios import get_scenario
from ..db.tables import NegotiationRow

INK = colors.HexColor("#1E2A4A")
RULE = colors.HexColor("#D9DCCF")


def _inr(x: float) -> str:
    return f"INR {x:,.2f}"


def _table(rows, widths):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def build_term_sheet(row: NegotiationRow, audit: dict) -> bytes:
    sc = Scenario.from_dict(row.final_state) if row.final_state else get_scenario(row.scenario_key)
    outcome = row.outcome or {}
    terms = Terms.from_dict(outcome.get("terms"))
    compliance = outcome.get("compliance") or {}

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=INK, fontSize=18, alignment=0, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading3"], textColor=INK, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], textColor=INK, fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.HexColor("#5B6479"))

    value = terms.price * sc.spec.quantity
    story = [
        Paragraph("Sandhi — Trade Credit Term Sheet", h1),
        Paragraph(f"Agreement reference {row.id}", small),
        Spacer(1, 6 * mm),
        Paragraph("Parties", h2),
        _table([["Supplier", sc.supplier.name], ["Buyer", sc.buyer.name],
                ["Financier", sc.financier.name if terms.treds else "Not used"]], [45 * mm, 120 * mm]),
        Paragraph("Commercial terms", h2),
        _table([
            ["Goods", f"{sc.spec.quantity:,} {sc.spec.item}"],
            ["Unit price", _inr(terms.price)],
            ["Invoice value", _inr(value)],
            ["Buyer payment", f"{terms.days} days from delivery"],
            ["Invoice financing", (f"TReDS discounting at {terms.rate * 100:.2f}% p.a.; buyer bears "
                                   f"{round(terms.buyer_share * 100)}% of the discount cost")
             if terms.treds else "None"],
            ["Supplier receives cash", f"{sc.spec.treds_settlement_days} days (via TReDS)" if terms.treds
             else f"{terms.days} days"],
        ], [45 * mm, 120 * mm]),
        Paragraph("Compliance", h2),
        _table([
            ["MSMED Act (45-day limit)", "Compliant" if compliance.get("msmed_compliant") else "Not compliant"],
            ["Section 43B(h) deduction", "Deferred" if compliance.get("section_43bh_deduction_deferred")
             else "Not affected"],
            ["Notes", Paragraph("<br/>".join(compliance.get("notes") or ["—"]), body)],
        ], [45 * mm, 120 * mm]),
        Paragraph("Negotiation", h2),
        _table([["Agreed in", f"Round {outcome.get('round')} ({outcome.get('via') or 'direct'})"],
                ["Agent transport", str(outcome.get("transport", "—")).upper()]], [45 * mm, 120 * mm]),
        Paragraph("Approvals", h2),
        _table([["Party", "Signed by", "Decision", "Time (UTC)"]] + [
            [a.role.title(), a.user_email, a.decision.title(), a.created_at.strftime("%d %b %Y %H:%M")]
            for a in row.approvals], [30 * mm, 60 * mm, 25 * mm, 50 * mm]),
        Paragraph("Audit", h2),
        Paragraph(f"Event log of {audit['events']} entries, integrity "
                  f"{'verified' if audit['valid'] else 'FAILED'}. Chain head: {audit['head_hash']}", small),
        Spacer(1, 8 * mm),
        Paragraph(f"Generated {datetime.now(timezone.utc):%d %b %Y %H:%M} UTC by Sandhi. Figures are "
                  "sandbox data. This summary does not constitute legal advice.", small),
    ]
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                      bottomMargin=18 * mm, title="Sandhi term sheet").build(story)
    return buffer.getvalue()