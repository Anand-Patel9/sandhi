"""A2A agent servers. Each agent keeps its private profile inside its own server session."""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable, Dict

from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import add_a2a_routes_to_fastapi, create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types.a2a_pb2 import AgentCapabilities, AgentCard, AgentInterface, AgentProvider, AgentSkill
from fastapi import FastAPI

from ..agents.buyer import BuyerAgent
from ..agents.financier import FinancierAgent
from ..agents.supplier import SupplierAgent
from ..config import get_settings
from ..core.models import MarketState
from ..llm.client import OFFLINE, LLMClient
from ..mcp_servers.client import default_toolbox
from .protocol import (A2A_VERSION, FINANCIER_SKILLS, NEGOTIATOR_SKILLS, ctx_from_wire,
                       profile_from_wire, terms_from_wire, terms_to_wire)

log = logging.getLogger(__name__)

AGENT_CLASSES = {"supplier": SupplierAgent, "buyer": BuyerAgent, "financier": FinancierAgent}

CARD_INFO = {
    "supplier": ("Sandhi Supplier Agent",
                 "Negotiates on behalf of an MSME supplier: fair price and cash before its runway ends."),
    "buyer": ("Sandhi Buyer Agent",
              "Negotiates on behalf of a corporate buyer: lowest total cost with a compliant, reliable supplier."),
    "financier": ("Sandhi Financier Agent",
                  "Quotes and underwrites TReDS invoice discounting for the deal."),
}

SKILL_INFO = {
    "open_session": "Start a negotiation session with this agent's private policy.",
    "propose": "Produce the next offer and message for the current round.",
    "respond": "Accept or reject an offer from the counterparty.",
    "evaluate": "Score an offer as a share of this agent's best case (no private values disclosed).",
    "quote": "Publish the current TReDS discounting rate.",
    "announce": "Explain the current rate to the other parties.",
    "accepts": "Confirm whether the financier will fund a package.",
    "shock": "Apply a market event to this agent's private position.",
    "snapshot": "Export the private end state (sandbox evaluation only).",
    "close_session": "End the session and discard private state.",
}


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def open(self, session_id: str, agent: Any) -> None:
        with self._lock:
            self._sessions[session_id] = agent

    def get(self, session_id: str) -> Any:
        with self._lock:
            agent = self._sessions.get(session_id)
        if agent is None:
            raise KeyError(f"Unknown session '{session_id}'")
        return agent

    def close(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


class NegotiationAgentExecutor(AgentExecutor):
    def __init__(self, role: str):
        self.role = role
        self.sessions = SessionStore()
        self.handlers: Dict[str, Callable[[dict], dict]] = {
            name: getattr(self, f"_{name}") for name in
            (FINANCIER_SKILLS if role == "financier" else NEGOTIATOR_SKILLS)
        }

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        parts = get_data_parts(context.message.parts) if context.message else []
        payload = parts[0] if parts and isinstance(parts[0], dict) else {}
        handler = self.handlers.get(payload.get("skill", ""))
        try:
            if handler is None:
                raise ValueError(f"Unsupported skill '{payload.get('skill')}' for {self.role} agent")
            result = await asyncio.to_thread(handler, payload)
        except Exception as exc:
            log.warning("%s agent skill %s failed: %s", self.role, payload.get("skill"), exc)
            result = {"error": str(exc)}
        await event_queue.enqueue_event(new_data_message(result, context_id=context.context_id))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None

    # --- skills ---
    def _open_session(self, p: dict) -> dict:
        settings = get_settings()
        provider = p.get("llm_provider") or OFFLINE
        llm = LLMClient.create(provider, settings.api_key_for(provider), settings.model_for(provider))
        profile = profile_from_wire(self.role, p["profile"])
        agent = AGENT_CLASSES[self.role](profile, llm, tools=default_toolbox())
        agent.bootstrap(MarketState(bank_rate=float(p["market"]["bank_rate"])))
        self.sessions.open(p["session"], agent)
        return {"ok": True, "name": agent.name, "engine": llm.label, "sources": agent.sources}

    def _propose(self, p: dict) -> dict:
        proposal = self.sessions.get(p["session"]).propose(ctx_from_wire(p["ctx"]))
        return {"terms": terms_to_wire(proposal.terms), "message": proposal.message,
                "redacted": proposal.redacted, "used_llm": proposal.used_llm}

    def _respond(self, p: dict) -> dict:
        agent = self.sessions.get(p["session"])
        return {"accept": bool(agent.respond(terms_from_wire(p["offer"]), ctx_from_wire(p["ctx"])))}

    def _evaluate(self, p: dict) -> dict:
        agent = self.sessions.get(p["session"])
        return {"score": agent.evaluate(terms_from_wire(p["terms"]), ctx_from_wire(p["ctx"]))}

    def _quote(self, p: dict) -> dict:
        return {"rate": self.sessions.get(p["session"]).quote(ctx_from_wire(p["ctx"]))}

    def _announce(self, p: dict) -> dict:
        ann = self.sessions.get(p["session"]).announce(float(p["rate"]), p.get("reason", ""),
                                                       ctx_from_wire(p["ctx"]))
        return {"rate": ann.rate, "message": ann.message, "redacted": ann.redacted, "used_llm": ann.used_llm}

    def _accepts(self, p: dict) -> dict:
        agent = self.sessions.get(p["session"])
        return {"accept": bool(agent.accepts(terms_from_wire(p["terms"]), ctx_from_wire(p["ctx"])))}

    def _shock(self, p: dict) -> dict:
        self.sessions.get(p["session"]).on_shock(p["key"])
        return {"ok": True}

    def _snapshot(self, p: dict) -> dict:
        if not get_settings().sandbox_mode:
            raise PermissionError("Private state export is disabled outside sandbox mode")
        return {"profile": self.sessions.get(p["session"]).snapshot()}

    def _close_session(self, p: dict) -> dict:
        self.sessions.close(p["session"])
        return {"ok": True}


def build_agent_card(role: str, url: str) -> AgentCard:
    name, description = CARD_INFO[role]
    skills = FINANCIER_SKILLS if role == "financier" else NEGOTIATOR_SKILLS
    return AgentCard(
        name=name, description=description, version="1.0.0",
        provider=AgentProvider(organization="Sandhi", url=get_settings().public_base_url),
        supported_interfaces=[AgentInterface(url=url, protocol_binding="JSONRPC",
                                             protocol_version=A2A_VERSION)],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["application/json"], default_output_modes=["application/json"],
        skills=[AgentSkill(id=s, name=s.replace("_", " ").title(), description=SKILL_INFO[s],
                           tags=["negotiation", role]) for s in skills],
    )


def build_agent_app(role: str) -> FastAPI:
    url = f"{get_settings().public_base_url.rstrip('/')}/a2a/{role}/"
    card = build_agent_card(role, url)
    handler = DefaultRequestHandler(agent_executor=NegotiationAgentExecutor(role),
                                    task_store=InMemoryTaskStore(), agent_card=card)
    app = FastAPI(title=CARD_INFO[role][0], version="1.0.0")
    add_a2a_routes_to_fastapi(app, agent_card_routes=create_agent_card_routes(card),
                              jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url="/"))
    app.state.card = card
    return app