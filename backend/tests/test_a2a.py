import httpx

from app.core.models import Scenario
from app.orchestrator.runner import build_engine, final_state

CONFIG = {"scenario": "auto_parts", "shocks": [{"key": "rate_hike", "at_round": 4},
                                               {"key": "payroll_crunch", "at_round": 6}]}


def test_agent_cards_are_published(agent_server):
    for role in ("supplier", "buyer", "financier"):
        card = httpx.get(f"{agent_server}/a2a/{role}/.well-known/agent-card.json").json()
        assert card["name"].startswith("Sandhi")
        assert card["supportedInterfaces"][0]["protocolBinding"] == "JSONRPC"
        assert any(s["id"] == "open_session" for s in card["skills"])


def test_a2a_negotiation_matches_in_process(agent_server):
    local = build_engine(CONFIG, transport="local")
    local_events = list(local.engine.run())
    local.close()

    remote = build_engine(CONFIG, transport="a2a")
    try:
        remote_events = list(remote.engine.run())
        state = Scenario.from_dict(final_state(remote))
    finally:
        remote.close()

    assert remote.engine.outcome.agreed
    assert remote.engine.outcome.terms == local.engine.outcome.terms
    assert [e.kind for e in remote_events] == [e.kind for e in local_events]
    assert state.supplier.runway_days == 23


def test_unknown_skill_returns_error(agent_server):
    body = {"jsonrpc": "2.0", "id": "1", "method": "SendMessage",
            "params": {"message": {"role": "ROLE_USER", "messageId": "m1", "parts": [{"data": {"skill": "hack"}}]}}}
    r = httpx.post(f"{agent_server}/a2a/buyer/", json=body, headers={"A2A-Version": "1.0"})
    part = r.json()["result"]["message"]["parts"][0]["data"]
    assert "Unsupported skill" in part["error"]


def test_orchestrator_holds_no_private_profiles(agent_server):
    assembly = build_engine({"scenario": "textiles"}, transport="a2a")
    try:
        for agent in assembly.engine.agents.values():
            assert not hasattr(agent, "profile")
    finally:
        assembly.close()