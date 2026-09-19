"""Application settings, loaded from environment variables or a .env file."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Sandhi API"
    environment: str = "development"
    database_url: str = "sqlite:///./sandhi.db"
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    public_base_url: str = "http://127.0.0.1:8000"
    agent_transport: str = "a2a"
    supplier_agent_url: Optional[str] = None
    buyer_agent_url: Optional[str] = None
    financier_agent_url: Optional[str] = None
    a2a_timeout_seconds: float = 60.0

    pace_seconds: float = 0.4
    max_concurrent_negotiations: int = 4
    sandbox_mode: bool = True

    default_llm_provider: str = "offline"
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    groq_model: Optional[str] = None
    openai_model: Optional[str] = None
    anthropic_model: Optional[str] = None

    def agent_url(self, role: str) -> str:
        return getattr(self, f"{role}_agent_url", None) or f"{self.public_base_url.rstrip('/')}/a2a/{role}"

    def api_key_for(self, provider: str) -> Optional[str]:
        return getattr(self, f"{provider}_api_key", None)

    def model_for(self, provider: str) -> Optional[str]:
        return getattr(self, f"{provider}_model", None)


@lru_cache
def get_settings() -> Settings:
    return Settings()