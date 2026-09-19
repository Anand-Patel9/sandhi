"""Wire format shared by A2A agent servers and the orchestrator's A2A client."""
from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any, Dict, Optional

from ..agents.base import TurnContext
from ..core.models import (BuyerProfile, DealSpec, FinancierProfile, MarketState,
                           SupplierProfile, Terms)

A2A_VERSION = "1.0"
CARD_PATH = "/.well-known/agent-card.json"
ROLES = ("supplier", "buyer", "financier")

NEGOTIATOR_SKILLS = ("open_session", "propose", "respond", "evaluate", "shock", "snapshot", "close_session")
FINANCIER_SKILLS = ("open_session", "quote", "announce", "accepts", "evaluate", "shock", "snapshot",
                    "close_session")

PROFILE_TYPES = {"supplier": SupplierProfile, "buyer": BuyerProfile, "financier": FinancierProfile}


def terms_to_wire(t: Optional[Terms]) -> Optional[dict]:
    return t.to_dict() if t else None


def terms_from_wire(d: Optional[dict]) -> Optional[Terms]:
    return Terms.from_dict(d) if d else None


def ctx_to_wire(ctx: TurnContext) -> dict:
    return {"round": ctx.round, "max_rounds": ctx.max_rounds, "spec": asdict(ctx.spec),
            "market": asdict(ctx.market), "rate": ctx.rate, "counterpart": ctx.counterpart,
            "opponent_last": terms_to_wire(ctx.opponent_last), "recent_events": list(ctx.recent_events)}


def ctx_from_wire(d: dict) -> TurnContext:
    s = d["spec"]
    spec = DealSpec(item=s["item"], quantity=int(s["quantity"]),
                    price_bounds=tuple(float(x) for x in s["price_bounds"]),
                    day_options=tuple(int(x) for x in s["day_options"]),
                    share_options=tuple(float(x) for x in s["share_options"]),
                    max_rounds=int(s["max_rounds"]), legal_limit_days=int(s["legal_limit_days"]),
                    treds_settlement_days=int(s["treds_settlement_days"]))
    return TurnContext(round=int(d["round"]), max_rounds=int(d["max_rounds"]), spec=spec,
                       market=MarketState(bank_rate=float(d["market"]["bank_rate"])),
                       rate=float(d["rate"]), counterpart=d.get("counterpart", ""),
                       opponent_last=terms_from_wire(d.get("opponent_last")),
                       recent_events=list(d.get("recent_events") or []))


def profile_from_wire(role: str, d: dict):
    cls = PROFILE_TYPES[role]
    fields = cls.__dataclass_fields__
    values = {}
    for name, f in fields.items():
        raw = d[name]
        values[name] = int(raw) if f.type in ("int", int) else raw
    return cls(**values)


def rpc_request(payload: Dict[str, Any]) -> dict:
    return {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "SendMessage",
            "params": {"message": {"role": "ROLE_USER", "messageId": str(uuid.uuid4()),
                                   "parts": [{"data": payload}]}}}


def rpc_result_data(body: dict) -> dict:
    """Extract the first data part from a JSON-RPC SendMessage response."""
    if "error" in body:
        raise A2ACallError(f"A2A error {body['error'].get('code')}: {body['error'].get('message')}")
    result = body.get("result") or {}
    message = result.get("message") or (result.get("task") or {}).get("status", {}).get("message") or {}
    for part in message.get("parts", []):
        if "data" in part:
            data = part["data"]
            if isinstance(data, dict) and data.get("error"):
                raise A2ACallError(data["error"])
            return data
    raise A2ACallError("A2A response contained no data part")


class A2ACallError(RuntimeError):
    pass