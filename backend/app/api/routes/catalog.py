"""Scenario and market-shock catalog."""
from dataclasses import asdict
from typing import List

from fastapi import APIRouter, HTTPException

from ...core.scenarios import SCENARIOS, SHOCKS
from ..schemas import ScenarioOut, ShockOut

router = APIRouter(tags=["catalog"])


def _scenario_out(key: str) -> ScenarioOut:
    sc = SCENARIOS[key]
    return ScenarioOut(
        key=sc.key, title=sc.title, story=sc.story, spec=asdict(sc.spec), market=asdict(sc.market),
        parties={"supplier": sc.supplier.name, "buyer": sc.buyer.name, "financier": sc.financier.name},
        defaults={"supplier": asdict(sc.supplier), "buyer": asdict(sc.buyer),
                  "financier": asdict(sc.financier)})


@router.get("/scenarios", response_model=List[ScenarioOut])
def list_scenarios():
    return [_scenario_out(k) for k in SCENARIOS]


@router.get("/scenarios/{key}", response_model=ScenarioOut)
def get_scenario(key: str):
    if key not in SCENARIOS:
        raise HTTPException(404, f"Scenario '{key}' not found")
    return _scenario_out(key)


@router.get("/shocks", response_model=List[ShockOut])
def list_shocks():
    return [ShockOut(key=k, **v) for k, v in SHOCKS.items()]