import pytest

from app.core import metrics
from app.core.models import Scenario
from app.orchestrator.runner import build_engine, final_state


def run(config):
    sc, engine, _ = build_engine(config)
    events = list(engine.run())
    return sc, engine, events


@pytest.mark.parametrize("scenario", ["auto_parts", "textiles"])
def test_offline_negotiation_reaches_viable_deal(scenario):
    sc, engine, events = run({"scenario": scenario})
    assert engine.outcome.agreed
    assert events[-1].kind == "deal"
    state = Scenario.from_dict(final_state(sc, engine))
    summary = metrics.summary(state, engine.outcome.terms)
    ours = next(a for a in summary["approaches"] if a["key"] == "negotiated")
    assert ours["viable"]
    assert summary["pareto_efficient"]


def test_shocks_are_applied_and_announced():
    config = {"scenario": "auto_parts", "shocks": [{"key": "rate_hike", "at_round": 3}]}
    sc, engine, events = run(config)
    assert any(e.kind == "shock" and e.round == 3 for e in events)
    assert abs(sc.market.bank_rate - 0.0625) < 1e-9


def test_single_objective_buyer_ai_collapses():
    sc, engine, _ = run({"scenario": "auto_parts"})
    state = Scenario.from_dict(final_state(sc, engine))
    buyer_ai = next(e for e in metrics.baselines(state, engine.outcome.terms) if e.key == "buyer_ai")
    assert not buyer_ai.viable and "supplier" in buyer_ai.blocked_by