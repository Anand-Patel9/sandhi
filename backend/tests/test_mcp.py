import asyncio

from app.mcp_servers.client import default_toolbox
from app.orchestrator.runner import build_engine


def test_tool_servers_are_discoverable(agent_server):
    servers = asyncio.run(default_toolbox().describe())
    assert {s["server"] for s in servers} == {"compliance", "treds", "erp"}
    assert all(s["status"] == "online" for s in servers)
    names = {t["name"] for s in servers for t in s["tools"]}
    assert {"check_payment_terms", "market_rates", "cash_position"} <= names


def test_compliance_tool(agent_server):
    tools = default_toolbox()
    late = tools.call("compliance", "check_payment_terms", payment_days=90, via_treds=False,
                      invoice_value=4_000_000, bank_rate=0.0575)
    assert not late["msmed_compliant"] and late["section_43bh_deduction_deferred"]
    assert late["msmed_interest_exposure"] > 0
    treds = tools.call("compliance", "check_payment_terms", payment_days=90, via_treds=True,
                       invoice_value=4_000_000, bank_rate=0.0575)
    assert treds["msmed_compliant"] and treds["days_to_msme_payment"] == 2


def test_erp_runway_matches_ledger(agent_server):
    position = default_toolbox().call("erp", "cash_position", entity_id="rajkot-castings")
    assert position["runway_days"] == 38


def test_agents_load_live_data_and_offers_are_checked(agent_server):
    assembly = build_engine({"scenario": "auto_parts"}, transport="a2a")
    try:
        assert "erp.cash_position" in assembly.sources["supplier"]
        assert "treds.market_rates" in assembly.sources["financier"]
        events = list(assembly.engine.run())
    finally:
        assembly.close()
    offers = [e for e in events if e.kind == "offer"]
    assert offers and all("compliance" in e.meta for e in offers)
    assert assembly.engine.outcome.compliance["msmed_compliant"]
    rates = [e.meta["rate"] for e in events if e.kind == "rate"]
    band = default_toolbox().call("treds", "market_rates", buyer_rating="AA", bank_rate=0.0575)
    assert max(rates) <= band["rate_high"] + 1e-9