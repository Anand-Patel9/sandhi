"""Directory of the A2A agents hosted by this deployment."""
from typing import List

from a2a.server.request_handlers.response_helpers import agent_card_to_dict
from fastapi import APIRouter, Request

from ...a2a.protocol import CARD_PATH
from ...config import get_settings

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=List[dict])
def list_agents(request: Request):
    settings = get_settings()
    cards = getattr(request.app.state, "agent_cards", {})
    return [{"role": role, "base_url": settings.agent_url(role),
             "card_url": f"{settings.agent_url(role)}{CARD_PATH}", "card": agent_card_to_dict(card)}
            for role, card in cards.items()]