"""MCP servers hosted by this deployment and the ASGI apps that serve them."""
from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager

from mcp.server.transport_security import TransportSecuritySettings

from . import compliance, erp, treds

SERVERS = {"compliance": compliance.server, "treds": treds.server, "erp": erp.server}
_state = {"running": False}


def build_apps() -> dict:
    security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return {name: srv.streamable_http_app(streamable_http_path="/", stateless_http=True,
                                          json_response=True, transport_security=security)
            for name, srv in SERVERS.items()}


@asynccontextmanager
async def running():
    """Start the MCP session managers once per process (they cannot be restarted)."""
    if _state["running"]:
        yield
        return
    _state["running"] = True
    async with AsyncExitStack() as stack:
        for srv in SERVERS.values():
            await stack.enter_async_context(srv.session_manager.run())
        yield