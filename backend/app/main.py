"""FastAPI application entry point: platform API plus hosted A2A agent servers."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .a2a.protocol import ROLES
from .a2a.server import build_agent_app
from .api.routes import agents, catalog, health, negotiations
from .config import get_settings
from .db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("a2a.server.events.event_queue_v2").setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan,
                  description="Sandhi: autonomous agents that negotiate MSME trade-credit agreements.")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    for module in (health, catalog, agents, negotiations):
        app.include_router(module.router, prefix="/api")

    app.state.agent_cards = {}
    for role in ROLES:
        agent_app = build_agent_app(role)
        app.mount(f"/a2a/{role}", agent_app)
        app.state.agent_cards[role] = agent_app.state.card

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    return app


app = create_app()