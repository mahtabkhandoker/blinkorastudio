"""Conversation orchestrator.

This is the one place that decides workflow stage, missing fields,
confirmation state, and whether generation is allowed. The LLM client is
used only for `extracted` field values; everything else here is plain,
deterministic Python so it needs no network access to test and can never
drift from what the frontend expects.

Flow per request:
1. If `message` is non-empty, ask the configured LLM client to extract
   fields from it, then merge those into the known `CreativeInput`
   (never overwriting a known field with nothing).
2. If `message` is empty (used by the frontend to "advance" the
   conversation after an asset event, with no new user text), skip
   extraction entirely — this step is purely about recomputing state.
3. Deterministically compute the next missing field / asset requirement /
   brief-readiness, and build the reply from fixed templates
   (never from the LLM's own phrasing) — see system_prompt.py.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.models.assets import AssetInfo
from app.models.chat import ChatMessageRequest, ChatResponse
from app.models.creative import CreationStage, CreativeInput
from app.services.chatbot.brief_builder import build_creative_brief
from app.services.chatbot.llm_client import ChatLLMClient
from app.services.chatbot.missing_fields import get_next_missing_field, needs_assets
from app.services.chatbot.system_prompt import (
    ASSET_REQUEST,
    BRIEF_READY,
    MISSING_FIELD_QUESTIONS,
    QUICK_REPLIES,
    ReplyLanguage,
)

logger = get_logger(__name__)

_BANGLA_RANGE = re.compile(r"[ঀ-৿]")
_ENGLISH_HINT_WORDS = re.compile(
    r"\b(the|is|want|need|please|video|for|and|with|make|create)\b", re.IGNORECASE
)


def detect_reply_language(message: str, creative_input: CreativeInput) -> ReplyLanguage:
    """Approximates conversational language for reply phrasing.

    Bangla script anywhere -> Bangla reply (this also covers mixed
    Bangla/English messages, which should get a Bangla-style reply per
    the system prompt). Otherwise, a message that reads as plain English
    (ASCII, common English function words, no Banglish markers) gets an
    English reply. Everything else (Banglish) defaults to Bangla, matching
    the system prompt's own examples.
    """
    if creative_input.language == "en":
        return "en"
    if creative_input.language == "bn":
        return "bn"
    if _BANGLA_RANGE.search(message):
        return "bn"
    if message and message.isascii() and _ENGLISH_HINT_WORDS.search(message):
        return "en"
    return "bn"


def merge_creative_input(current: CreativeInput, extracted: dict) -> CreativeInput:
    """Only overwrites a field when the extraction clearly provided a new
    value; never erases a previously known value with silence.
    """
    updates = {k: v for k, v in extracted.items() if v not in (None, [], "")}
    merged = current.model_copy(update=updates)
    return merged


def _stage_for_missing_field(current_stage: CreationStage, missing_field: str) -> CreationStage:
    if missing_field == "product_name" and current_stage in ("WELCOME", "INTENT"):
        return "INTENT"
    return "DETAILS_COLLECTION"


class ChatOrchestrator:
    def __init__(self, llm_client: ChatLLMClient) -> None:
        self._llm_client = llm_client

    async def handle_message(self, request: ChatMessageRequest) -> ChatResponse:
        state = request.state
        creative_input = state.creative_input
        assets: list[AssetInfo] = state.assets
        message = request.message.strip()

        extracted: dict = {}
        if message:
            try:
                result = await self._llm_client.extract_and_reply(message, creative_input)
                extracted = result.extracted
            except Exception:  # noqa: BLE001 - provider/network failure must not crash the chat
                logger.exception(
                    "LLM extraction failed for conversation_id=%s", request.conversation_id
                )
                return self._fallback_response(state.stage, creative_input, message)

        merged_input = merge_creative_input(creative_input, extracted)
        language = detect_reply_language(message, merged_input)
        if not merged_input.language:
            merged_input = merged_input.model_copy(update={"language": language})

        missing_field = get_next_missing_field(merged_input)

        if missing_field is not None:
            stage = _stage_for_missing_field(state.stage, missing_field)
            reply = MISSING_FIELD_QUESTIONS[missing_field][language]
            quick_replies = QUICK_REPLIES.get(missing_field, [])
            return ChatResponse(
                reply=reply,
                stage=stage,
                extracted=extracted,
                creative_input=merged_input,
                missing_field=missing_field,
                quick_replies=quick_replies,
                brief_ready=False,
                requires_confirmation=False,
            )

        if needs_assets(assets):
            return ChatResponse(
                reply=ASSET_REQUEST[language],
                stage="ASSET_UPLOAD",
                extracted=extracted,
                creative_input=merged_input,
                missing_field=None,
                quick_replies=[],
                brief_ready=False,
                requires_confirmation=False,
                needs_assets=True,
            )

        # All required fields known and at least one usable asset -> brief.
        brief = build_creative_brief(merged_input, assets)
        return ChatResponse(
            reply=BRIEF_READY[language],
            stage="BRIEF_REVIEW",
            extracted=extracted,
            creative_input=merged_input,
            missing_field=None,
            quick_replies=[],
            brief_ready=True,
            requires_confirmation=True,
            creative_brief=brief,
        )

    def _fallback_response(
        self, stage: CreationStage, creative_input: CreativeInput, message: str
    ) -> ChatResponse:
        from app.services.chatbot.system_prompt import FALLBACK_ERROR

        language = detect_reply_language(message, creative_input)
        return ChatResponse(
            reply=FALLBACK_ERROR[language],
            stage=stage,
            extracted={},
            creative_input=creative_input,
            missing_field=get_next_missing_field(creative_input),
            quick_replies=[],
            brief_ready=False,
            requires_confirmation=False,
        )
