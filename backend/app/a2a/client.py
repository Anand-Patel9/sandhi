"""A2A client ports: remote agents that satisfy the same interfaces as in-process agents."""
from __future__ import annotations

import uuid
from dataclasses import asdict
import httpx

from ..agents.base import Announcement, Proposal, TurnContext
from ..core.models import Terms
from .protocol import (A2A_VERSION, CARD_PATH, A2ACallError, ctx_to_wire, rpc_request,
                       rpc_result_data, terms_from_wire, terms_to_wire)


class A2AConnection:
    """Discovers an agent from its Agent Card and calls its skills over JSON-RPC."""

    def __init__(self, base_url: str, http: httpx.Client):
        self.base_url = base_url.rstrip("/")
        self.http = http
        self.card: dict = {}
        self.rpc_url = f"{self.base_url}/"

    def discover(self) -> dict:
        r = self.http.get(f"{self.base_url}{CARD_PATH}")
        r.raise_for_status()
        self.card = r.json()
        for iface in self.card.get("supportedInterfaces", []):
            if iface.get("protocolBinding") == "JSONRPC":
                self.rpc_url = iface["url"]
                break
        return self.card

    def call(self, skill: str, **payload) -> dict:
        r = self.http.post(self.rpc_url, json=rpc_request({"skill": skill, **payload}),
                           headers={"A2A-Version": A2A_VERSION})
        r.raise_for_status()
        return rpc_result_data(r.json())


class RemoteAgent:
    def __init__(self, role: str, conn: A2AConnection):
        self.role = role
        self.conn = conn
        self.session = str(uuid.uuid4())
        self.name = role.title()
        self.engine = ""
        self.sources: list = []

    def open(self, profile, llm_provider: str, market) -> None:
        data = self.conn.call("open_session", session=self.session, profile=asdict(profile),
                              llm_provider=llm_provider, market=asdict(market))
        self.name = data.get("name", self.name)
        self.engine = data.get("engine", "")
        self.sources = list(data.get("sources") or [])

    def close(self) -> None:
        try:
            self.conn.call("close_session", session=self.session)
        except (A2ACallError, httpx.HTTPError):
            pass

    def evaluate(self, terms: Terms, ctx: TurnContext) -> float:
        return float(self.conn.call("evaluate", session=self.session, ctx=ctx_to_wire(ctx),
                                    terms=terms_to_wire(terms))["score"])

    def on_shock(self, key: str) -> None:
        self.conn.call("shock", session=self.session, key=key)

    def snapshot(self) -> dict:
        return self.conn.call("snapshot", session=self.session)["profile"]


class RemoteNegotiator(RemoteAgent):
    def propose(self, ctx: TurnContext) -> Proposal:
        d = self.conn.call("propose", session=self.session, ctx=ctx_to_wire(ctx))
        return Proposal(terms_from_wire(d["terms"]), d["message"], bool(d.get("redacted")),
                        bool(d.get("used_llm")))

    def respond(self, offer: Terms, ctx: TurnContext) -> bool:
        return bool(self.conn.call("respond", session=self.session, ctx=ctx_to_wire(ctx),
                                   offer=terms_to_wire(offer))["accept"])


class RemoteFinancier(RemoteAgent):
    def quote(self, ctx: TurnContext) -> float:
        return float(self.conn.call("quote", session=self.session, ctx=ctx_to_wire(ctx))["rate"])

    def announce(self, rate: float, reason: str, ctx: TurnContext) -> Announcement:
        d = self.conn.call("announce", session=self.session, ctx=ctx_to_wire(ctx), rate=rate, reason=reason)
        return Announcement(float(d["rate"]), d["message"], bool(d.get("redacted")), bool(d.get("used_llm")))

    def accepts(self, terms: Terms, ctx: TurnContext) -> bool:
        return bool(self.conn.call("accepts", session=self.session, ctx=ctx_to_wire(ctx),
                                   terms=terms_to_wire(terms))["accept"])


def connect(role: str, base_url: str, http: httpx.Client) -> RemoteAgent:
    conn = A2AConnection(base_url, http)
    conn.discover()
    return (RemoteFinancier if role == "financier" else RemoteNegotiator)(role, conn)