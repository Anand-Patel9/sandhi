"""Synchronous MCP toolbox used by agents and the orchestrator."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from mcp.client import Client

log = logging.getLogger(__name__)


class MCPError(RuntimeError):
    pass


class MCPToolbox:
    def __init__(self, urls: Dict[str, str], timeout: float = 20.0):
        self.urls = urls
        self.timeout = timeout
        self.calls = 0

    def call(self, server: str, tool: str, **arguments) -> Any:
        if server not in self.urls:
            raise MCPError(f"MCP server '{server}' is not configured")
        self.calls += 1
        return asyncio.run(asyncio.wait_for(self._call(server, tool, arguments), self.timeout))

    def try_call(self, server: str, tool: str, **arguments) -> Optional[Any]:
        try:
            return self.call(server, tool, **arguments)
        except Exception as exc:
            log.warning("MCP %s.%s unavailable: %s", server, tool, exc)
            return None

    async def _call(self, server: str, tool: str, arguments: dict) -> Any:
        async with Client(self.urls[server]) as client:
            result = await client.call_tool(tool, arguments)
        text = "".join(getattr(c, "text", "") for c in result.content)
        if result.is_error:
            raise MCPError(text or f"{server}.{tool} failed")
        try:
            return json.loads(text)
        except ValueError:
            return text

    async def describe(self) -> List[dict]:
        out = []
        for name, url in self.urls.items():
            try:
                async with Client(url) as client:
                    tools = (await client.list_tools()).tools
                out.append({"server": name, "url": url, "status": "online",
                            "tools": [{"name": t.name, "description": t.description or ""} for t in tools]})
            except Exception as exc:
                out.append({"server": name, "url": url, "status": "offline", "error": str(exc), "tools": []})
        return out


def default_toolbox() -> Optional[MCPToolbox]:
    from ..config import get_settings

    settings = get_settings()
    if not settings.mcp_enabled:
        return None
    return MCPToolbox(settings.mcp_urls(), settings.mcp_timeout_seconds)