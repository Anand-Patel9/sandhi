import pytest

from app.core import metrics
from app.core.models import Scenario
from app.orchestrator.runner import build_engine, final_state


def run(config, transport="local"):
    assembly = build_engine(config, transport=transport)
    try:
        events = list(assembly.engine.run())
        state = Scenario.from_dict(final_state(assembly))
    finally:
        assembly.close()
    return assembly, events, state


@pytest.mark.parametrize("scenario", ["auto_parts", "textiles"])
def test_offline_negotiation_reaches_viable_deal(scenario):
    assembly, events, state = run({"scenario": scenario})
    assert assembly.engine.outcome.agreed
    assert events[-1].kind == "deal"
    summary = metrics.summary(state, assembly.engine.outcome.terms)
    ours = next(a for a in summary["approaches"] if a["key"] == "negotiated")
    assert ours["viable"] and summary["pareto_efficient"]


def test_shocks_are_applied_and_announced():
    assembly, events, _ = run({"scenario": "auto_parts", "shocks": [{"key": "rate_hike", "at_round": 3}]})
    assert any(e.kind == "shock" and e.round == 3 for e in events)
    assert abs(assembly.scenario.market.bank_rate - 0.0625) < 1e-9


def test_single_objective_buyer_ai_collapses():
    assembly, _, state = run({"scenario": "auto_parts"})
    buyer_ai = next(e for e in metrics.baselines(state, assembly.engine.outcome.terms) if e.key == "buyer_ai")
    assert not buyer_ai.viable and "supplier" in buyer_ai.blocked_by