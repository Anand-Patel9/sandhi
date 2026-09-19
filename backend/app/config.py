"""Application settings, loaded from environment variables or a .env file."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TradeCredit API"
    environment: str = "development"
    database_url: str = "sqlite:///./tradecredit.db"
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

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

    def api_key_for(self, provider: str) -> Optional[str]:
        return getattr(self, f"{provider}_api_key", None)

    def model_for(self, provider: str) -> Optional[str]:
        return getattr(self, f"{provider}_model", None)


@lru_cache
def get_settings() -> Settings:
    return Settings()