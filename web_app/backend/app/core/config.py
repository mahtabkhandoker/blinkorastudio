"""Environment-based configuration for the Blinkora Studio chatbot backend.

Nothing here hardcodes the public domain/brand: `blinkorastudio.com` and
similar public-facing values belong in the frontend's own env/config, per
the "reuse existing config mechanisms" project rule. This module only
configures the backend service itself.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ChatbotProvider = Literal["mock", "openai"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # --- App -----------------------------------------------------------
    app_name: str = "Blinkora Studio Chatbot API"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # --- CORS ------------------------------------------------------------
    # Comma-separated list of allowed origins for the Next.js frontend.
    cors_allow_origins: str = "http://localhost:3000"

    # --- Chatbot provider --------------------------------------------------
    # "mock" (default, no external calls) or "openai" (real LLM).
    chatbot_provider: ChatbotProvider = "mock"
    openai_api_key: str | None = Field(default=None, repr=False)
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None
    openai_timeout_seconds: float = 15.0

    # --- Generation (mock/paid-guarded) --------------------------------------
    # Never used to actually call a paid video provider in this codebase;
    # kept here so a real integration has a single documented switch.
    video_generation_provider: str = "mock"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
