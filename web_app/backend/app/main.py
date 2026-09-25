from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import assets, chat, creative_plan, generations
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Conversational creative-brief backend for Blinkora Studio.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(assets.router)
app.include_router(creative_plan.router)
app.include_router(generations.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "chatbot_provider": settings.chatbot_provider}
