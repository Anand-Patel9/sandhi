"""ERP MCP server: cash position of a company from its (sandbox) ledger."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

server = MCPServer(
    name="sandhi-erp", version="1.0.0",
    instructions="Reads cash balances and outflows from connected ERP ledgers. Sandbox data.",
)

LEDGERS = {
    "rajkot-castings": {"name": "Rajkot casting unit", "cash_balance": 2_660_000.0,
                        "monthly_outflow": 2_100_000.0, "receivables_30d": 850_000.0},
    "surat-garments": {"name": "Surat garment unit", "cash_balance": 1_250_000.0,
                       "monthly_outflow": 1_500_000.0, "receivables_30d": 400_000.0},
}


@server.tool()
def cash_position(entity_id: str) -> dict:
    """Cash balance, monthly outflow and days of cash runway for a company."""
    if entity_id not in LEDGERS:
        raise ValueError(f"No ledger connected for '{entity_id}'")
    ledger = LEDGERS[entity_id]
    runway = ledger["cash_balance"] / (ledger["monthly_outflow"] / 30.0)
    return {"entity_id": entity_id, **ledger, "runway_days": int(round(runway))}


@server.tool()
def list_entities() -> list:
    """Companies with a connected ledger."""
    return [{"entity_id": k, "name": v["name"]} for k, v in LEDGERS.items()]