"""Directory of the MCP tool servers the agents use."""
from typing import List

from fastapi import APIRouter

from ...mcp_servers.client import default_toolbox

router = APIRouter(tags=["tools"])


@router.get("/tools", response_model=List[dict])
async def list_tool_servers():
    toolbox = default_toolbox()
    return await toolbox.describe() if toolbox else []