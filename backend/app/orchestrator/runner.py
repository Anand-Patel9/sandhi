"""Runs negotiations in background worker threads and persists every event."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from ..agents.buyer import BuyerAgent
from ..agents.financier import FinancierAgent
from ..agents.mediator import Mediator
from ..agents.supplier import SupplierAgent
from ..config import get_settings
from ..core.models import Scenario, Shock
from ..core.scenarios import get_scenario
from ..db import repository as repo
from ..db.session import session_scope
from ..llm.client import OFFLINE, LLMClient
from .engine import NegotiationEngine

log = logging.getLogger(__name__)
ROLES = ("supplier", "buyer", "financier", "mediator")

_executor = ThreadPoolExecutor(max_workers=get_settings().max_concurrent_negotiations,
                               thread_name_prefix="negotiation")


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


def build_llms(config: dict) -> Dict[str, LLMClient]:
    settings = get_settings()
    llm_cfg = config.get("llm") or {}
    default = llm_cfg.get("provider") or settings.default_llm_provider
    per_agent = llm_cfg.get("per_agent") or {}
    clients: Dict[str, LLMClient] = {}
    out: Dict[str, LLMClient] = {}
    for role in ROLES:
        provider = per_agent.get(role) or default
        if provider not in clients:
            clients[provider] = (LLMClient.create(OFFLINE, None) if provider == OFFLINE else
                                 LLMClient.create(provider, settings.api_key_for(provider),
                                                  settings.model_for(provider)))
        out[role] = clients[provider]
    return out


def build_engine(config: dict):
    sc = build_scenario(config)
    llms = build_llms(config)
    supplier = SupplierAgent(sc.supplier, llms["supplier"])
    buyer = BuyerAgent(sc.buyer, llms["buyer"])
    financier = FinancierAgent(sc.financier, llms["financier"])
    mediator = Mediator(llms["mediator"])
    shocks = [Shock(s["key"], int(s["at_round"])) for s in config.get("shocks") or []]
    engine = NegotiationEngine(sc.spec, sc.market, supplier, buyer, financier, mediator, shocks)
    return sc, engine, llms


def final_state(sc: Scenario, engine: NegotiationEngine) -> dict:
    """Sandbox-only snapshot of every party's end state, used for evaluation."""
    state = sc.to_dict()
    for role, agent in engine.agents.items():
        state[role] = agent.snapshot()
    return state


def run_negotiation(negotiation_id: str) -> None:
    settings = get_settings()
    try:
        with session_scope() as db:
            row = repo.get_negotiation(db, negotiation_id)
            config = dict(row.config)
            repo.set_status(db, negotiation_id, "running")
        pace = config.get("pace_seconds")
        pace = settings.pace_seconds if pace is None else float(pace)

        sc, engine, llms = build_engine(config)
        seq = 0
        for event in engine.run():
            seq += 1
            with session_scope() as db:
                repo.add_event(db, negotiation_id, seq, event)
            if pace and event.kind in ("offer", "mediation", "rate", "shock", "accept"):
                time.sleep(pace)

        outcome = engine.outcome.to_dict()
        outcome["engines"] = {role: client.label for role, client in llms.items()}
        status = "agreed" if engine.outcome.agreed else "no_deal"
        state = final_state(sc, engine) if settings.sandbox_mode else {}
        with session_scope() as db:
            repo.finish(db, negotiation_id, status, outcome, state)
    except Exception as exc:  # keep the worker alive and record the failure
        log.exception("Negotiation %s failed", negotiation_id)
        with session_scope() as db:
            repo.set_status(db, negotiation_id, "failed", error=str(exc))


def submit(negotiation_id: str) -> None:
    _executor.submit(run_negotiation, negotiation_id)