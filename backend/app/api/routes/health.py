"""Health and version endpoints."""
from fastapi import APIRouter

from ...config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "app": s.app_name, "environment": s.environment,
            "default_llm_provider": s.default_llm_provider}