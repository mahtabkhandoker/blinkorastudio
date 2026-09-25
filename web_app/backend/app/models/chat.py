"""Request/response schemas for POST /api/chat/message.

These are intentionally strict: the frontend must never need to parse
`reply` text to figure out state — `stage`, `missing_field`, `brief_ready`
and `requires_confirmation` carry that, deterministically decided by the
orchestrator (see services/chatbot/orchestrator.py), never by the LLM.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.assets import AssetInfo
from app.models.creative import CreationStage, CreativeBrief, CreativeInput


class ConversationStateIn(BaseModel):
    """The slice of conversation state the frontend already holds.

    The backend is intentionally stateless per-request (see
    repositories/conversations.py for the optional persistence layer used
    only for idempotency/logging) — the frontend remains the source of
    truth for state, and the backend recomputes stage/missing_field from
    scratch every call. This avoids a second, divergent copy of state.
    """

    stage: CreationStage = "WELCOME"
    creative_input: CreativeInput = Field(default_factory=CreativeInput)
    assets: list[AssetInfo] = Field(default_factory=list)
    brief_confirmed: bool = False


class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str = Field(default="", max_length=4000)
    state: ConversationStateIn = Field(default_factory=ConversationStateIn)
    # Set by the frontend to dedupe an accidental double-submit of the same
    # user message (e.g. a double click / retried network request).
    request_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    stage: CreationStage
    extracted: dict = Field(default_factory=dict)
    creative_input: CreativeInput
    missing_field: str | None = None
    quick_replies: list[str] = Field(default_factory=list)
    brief_ready: bool = False
    requires_confirmation: bool = False
    creative_brief: CreativeBrief | None = None
    needs_assets: bool = False
