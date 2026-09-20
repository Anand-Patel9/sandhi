"""Runs negotiations in background worker threads and persists every event."""
from __future__ import annotations

import itertools
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

from ..a2a.client import RemoteAgent, connect
from ..agents.buyer import BuyerAgent
from ..agents.financier import FinancierAgent
from ..agents.mediator import Mediator
from ..agents.supplier import SupplierAgent
from ..config import get_settings
from ..core.models import Event, Scenario, Shock, Terms
from ..core.scenarios import get_scenario
from ..db import repository as repo
from ..db.session import session_scope
from ..llm.client import OFFLINE, LLMClient
from ..mcp_servers.client import MCPToolbox, default_toolbox
from . import approvals
from .engine import NegotiationEngine

log = logging.getLogger(__name__)
PARTIES = ("supplier", "buyer", "financier")
LOCAL_CLASSES = {"supplier": SupplierAgent, "buyer": BuyerAgent, "financier": FinancierAgent}

_executor = ThreadPoolExecutor(max_workers=get_settings().max_concurrent_negotiations,
                               thread_name_prefix="negotiation")
_cancelled: set = set()


def request_cancel(negotiation_id: str) -> None:
    _cancelled.add(negotiation_id)


@dataclass
class Assembly:
    scenario: Scenario
    engine: NegotiationEngine
    transport: str
    engines: Dict[str, str]
    remote: List[RemoteAgent] = field(default_factory=list)
    http: Optional[httpx.Client] = None
    sources: Dict[str, List[str]] = field(default_factory=dict)

    def connection_event(self) -> Optional[Event]:
        if self.transport != "a2a":
            return None
        agents = [{"role": a.role, "name": a.name, "url": a.conn.rpc_url, "card": a.conn.card.get("name")}
                  for a in self.remote]
        names = ", ".join(a["card"] or a["name"] for a in agents)
        return Event("info", 0, "system", f"Connected over A2A to {names}.", meta={"agents": agents})

    def data_event(self) -> Optional[Event]:
        used = {role: s for role, s in self.sources.items() if s}
        if not used:
            return None
        text = "; ".join(f"{role} agent read {', '.join(s)}" for role, s in used.items())
        return Event("info", 0, "system", f"Live data loaded over MCP: {text}.", meta={"sources": used})

    def close(self) -> None:
        for agent in self.remote:
            agent.close()
        if self.http is not None:
            self.http.close()


def build_scenario(config: dict) -> Scenario:
    sc = get_scenario(config["scenario"])
    if config.get("max_rounds"):
        sc.spec.max_rounds = int(config["max_rounds"])
    overrides = config.get("overrides") or {}
    for section in ("supplier", "buyer", "financier", "market"):
        target = getattr(sc, section)
        for field_name, value in (overrides.get(section) or {}).items():
            if value is not None and hasattr(target, field_name):
                setattr(target, field_name, type(getattr(target, field_name))(value))
    return sc


def resolve_providers(config: dict) -> Dict[str, str]:
    llm_cfg = config.get("llm") or {}
    default = llm_cfg.get("provider") or get_settings().default_llm_provider
    per_agent = llm_cfg.get("per_agent") or {}
    return {role: per_agent.get(role) or default for role in PARTIES + ("mediator",)}


def make_llm(provider: str) -> LLMClient:
    settings = get_settings()
    if provider == OFFLINE:
        return LLMClient.create(OFFLINE, None)
    return LLMClient.create(provider, settings.api_key_for(provider), settings.model_for(provider))


def compliance_checker(tools: MCPToolbox, sc: Scenario):
    def check(terms: Terms) -> Optional[dict]:
        return tools.try_call("compliance", "check_payment_terms", payment_days=terms.days,
                              via_treds=terms.treds, invoice_value=terms.price * sc.spec.quantity,
                              bank_rate=sc.market.bank_rate, legal_limit_days=sc.spec.legal_limit_days)
    return check


def build_engine(config: dict, transport: Optional[str] = None,
                 http: Optional[httpx.Client] = None) -> Assembly:
    settings = get_settings()
    sc = build_scenario(config)
    providers = resolve_providers(config)
    transport = transport or config.get("transport") or settings.agent_transport
    shocks = [Shock(s["key"], int(s["at_round"])) for s in config.get("shocks") or []]
    mediator_llm = make_llm(providers["mediator"])
    tools = default_toolbox()
    remote: List[RemoteAgent] = []

    if transport == "a2a":
        http = http or httpx.Client(timeout=settings.a2a_timeout_seconds)
        agents = {}
        try:
            for role in PARTIES:
                agent = connect(role, settings.agent_url(role), http)
                agent.open(getattr(sc, role), providers[role], sc.market)
                remote.append(agent)
                agents[role] = agent
        except Exception:
            for agent in remote:
                agent.close()
            http.close()
            raise
        engines = {role: agents[role].engine for role in PARTIES}
    else:
        agents = {role: LOCAL_CLASSES[role](getattr(sc, role), make_llm(providers[role]), tools=tools)
                  for role in PARTIES}
        for agent in agents.values():
            agent.bootstrap(sc.market)
        engines = {role: agents[role].llm.label for role in PARTIES}
    engines["mediator"] = mediator_llm.label

    engine = NegotiationEngine(sc.spec, sc.market, agents["supplier"], agents["buyer"],
                               agents["financier"], Mediator(mediator_llm), shocks,
                               compliance=compliance_checker(tools, sc) if tools else None)
    sources = {role: list(agents[role].sources) for role in PARTIES}
    return Assembly(sc, engine, transport, engines, remote, http if transport == "a2a" else None, sources)


def final_state(assembly: Assembly) -> dict:
    """Sandbox-only snapshot of every party's end state, used for evaluation."""
    state = assembly.scenario.to_dict()
    for role, agent in assembly.engine.agents.items():
        state[role] = agent.snapshot()
    return state


def run_negotiation(negotiation_id: str) -> None:
    settings = get_settings()
    assembly: Optional[Assembly] = None
    try:
        with session_scope() as db:
            config = dict(repo.get_negotiation(db, negotiation_id).config)
            repo.set_status(db, negotiation_id, "running")
        pace = config.get("pace_seconds")
        pace = settings.pace_seconds if pace is None else float(pace)

        assembly = build_engine(config)
        opening = [e for e in (assembly.connection_event(), assembly.data_event()) if e]
        for event in itertools.chain(opening, assembly.engine.run()):
            if negotiation_id in _cancelled:
                _cancelled.discard(negotiation_id)
                with session_scope() as db:
                    repo.append_event(db, negotiation_id, Event(
                        "cancelled", event.round, "system", "Negotiation stopped by a user. No terms were agreed."))
                    repo.set_status(db, negotiation_id, "cancelled")
                return
            with session_scope() as db:
                repo.append_event(db, negotiation_id, event)
            if pace and event.kind in ("offer", "mediation", "rate", "shock", "accept"):
                time.sleep(pace)

        outcome = assembly.engine.outcome.to_dict()
        outcome["engines"] = assembly.engines
        outcome["transport"] = assembly.transport
        state = final_state(assembly) if settings.sandbox_mode else {}
        needs_approval = config.get("require_approval", settings.require_approval)
        with session_scope() as db:
            if not assembly.engine.outcome.agreed:
                repo.finish(db, negotiation_id, "no_deal", outcome, state)
            elif needs_approval:
                outcome["required_approvals"] = approvals.required_roles(assembly.engine.outcome.terms)
                repo.finish(db, negotiation_id, "awaiting_approval", outcome, state)
                repo.append_event(db, negotiation_id, approvals.request_event(outcome["required_approvals"]))
            else:
                repo.finish(db, negotiation_id, "agreed", outcome, state)
    except Exception as exc:
        log.exception("Negotiation %s failed", negotiation_id)
        with session_scope() as db:
            repo.set_status(db, negotiation_id, "failed", error=str(exc))
    finally:
        if assembly is not None:
            assembly.close()


def submit(negotiation_id: str) -> None:
    _executor.submit(run_negotiation, negotiation_id)