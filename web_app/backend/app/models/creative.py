"""Structured creative-video requirement state.

Field names and shape intentionally mirror the frontend's `CreativeInput`
type (`lib/chat/types.ts`) in snake_case, so the API boundary is a
mechanical case conversion rather than a semantic remapping.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AspectRatio = Literal["9:16", "1:1", "16:9"]

# CreationStage — kept identical to the frontend's TypeScript union so the
# backend's `stage` can be assigned directly into frontend state with no
# translation table.
CreationStage = Literal[
    "WELCOME",
    "INTENT",
    "ASSET_UPLOAD",
    "ASSET_VALIDATION",
    "DETAILS_COLLECTION",
    "BRIEF_REVIEW",
    "PACKAGE_CHECK",
    "GENERATION_CONFIRMATION",
    "GENERATING",
    "QUALITY_CHECK",
    "RESULT",
    "REVISION",
    "FAILED",
]

# The fields the orchestrator will actively ask about, in priority order.
# Assets are required for generation too, but are tracked/validated
# separately (see services/assets), not as a CreativeInput field.
REQUIRED_FIELDS: list[str] = ["product_name", "campaign_type", "duration_seconds", "style"]

MissingField = Literal["product_name", "campaign_type", "duration_seconds", "style"]


class CreativeInput(BaseModel):
    business_name: str | None = None
    business_type: str | None = None
    product_name: str | None = None
    product_category: str | None = None
    campaign_type: str | None = None
    target_audience: str | None = None
    duration_seconds: int | None = None
    aspect_ratio: AspectRatio | None = None
    platform: str | None = None
    style: list[str] = Field(default_factory=list)
    language: str | None = None
    captions: bool | None = None
    voiceover: bool | None = None
    music_mood: str | None = None
    cta: str | None = None
    notes: str | None = None


class CreativeBrief(BaseModel):
    """Human-readable brief shown to the user before generation.

    Deliberately excludes any internal model/provider name — only the
    final video-model prompt (built separately, see prompt_builder.py) is
    provider-facing, and even that stays hidden behind an "Advanced" its
    disclosure on the frontend.
    """

    product: str
    campaign: str
    duration: str
    format: str
    style: list[str]
    audience: str | None = None
    assets: int
    caption_language: str
    cta: str
    visual_direction: str
