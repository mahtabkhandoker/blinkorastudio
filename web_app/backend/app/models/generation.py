"""Generation request/state models.

This backend never calls a real paid video provider — `video_generation_provider`
in config defaults to "mock" and nothing here performs an external call.
The endpoint exists so the orchestration contract (idempotency, status
polling) is in place and testable before a real provider is connected.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.creative import CreativeBrief

GenerationStatus = Literal[
    "QUEUED", "PREPARING", "GENERATING", "VALIDATING", "FINALIZING", "COMPLETED", "FAILED"
]


class GenerationRequest(BaseModel):
    conversation_id: str
    idempotency_key: str
    brief: CreativeBrief


class GenerationRecord(BaseModel):
    id: str
    conversation_id: str
    idempotency_key: str
    status: GenerationStatus = "QUEUED"
    progress: int = 0
    video_url: str | None = None
    error: str | None = None


class GenerationResponse(BaseModel):
    id: str
    status: GenerationStatus
    progress: int = Field(ge=0, le=100)
    video_url: str | None = None
    error: str | None = None
    deduplicated: bool = False
