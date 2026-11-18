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
    # Seconds the mock provider takes to "finish" a clip. No video is produced.
    mock_generation_seconds: float = 8.0
    clip_seconds: int = 5
    clip_resolution: str = "720p"

    # --- Orders (P0 workflow) ---------------------------------------------------
    # "postgres" is the real store (see Task D of the P0.5 spec). "file"
    # keeps the old JSON-under-STORAGE_DIR behavior for a no-database dev
    # loop; "memory" is for fast, isolated tests. Neither "file" nor
    # "memory" is a production database.
    order_store: Literal["postgres", "file", "memory"] = "postgres"
    storage_dir: str = "./storage"
    max_upload_mb: int = 10
    max_image_pixels: int = 40_000_000
    # F1 "both": only offered once the square crop has been tested and an
    # add-on price has been set (spec F1, §3.4).
    both_formats_enabled: bool = False
    both_formats_addon_bdt: int | None = None
    # Enables GET /api/internal/orders/{id} (prompts, order line) for the
    # operator. Leave unset to keep that endpoint switched off.
    operator_api_token: str | None = Field(default=None, repr=False)

    # --- Database (P0.5) ---------------------------------------------------
    # SQLAlchemy URL for the Postgres-backed order/auth store. See
    # docker-compose.yml for a local database on port 55432 (5432 is left
    # free in case a native Postgres install is already using it).
    database_url: str = "postgresql+psycopg://blinkora:blinkora_dev@localhost:55432/blinkora"

    # --- Auth sessions (P0.5) ----------------------------------------------
    session_cookie_name: str = "blinkora_session"
    csrf_cookie_name: str = "blinkora_csrf"
    session_ttl_days: int = 14
    # Secure requires HTTPS; only disabled for plain-http local development.
    # Set COOKIE_SECURE=true behind TLS in any shared/staging/prod deploy.
    cookie_secure: bool = False
    auth_rate_limit_attempts: int = 10
    auth_rate_limit_window_seconds: int = 300

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
