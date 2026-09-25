"""Deterministic missing-field logic.

This is the piece the implementation spec is most insistent about: the
LLM must never decide what's missing or what stage the conversation is
in. This module is pure, has no dependency on any LLM client, and is
fully unit-testable on its own.
"""

from __future__ import annotations

from app.models.assets import AssetInfo, has_usable_asset
from app.models.creative import REQUIRED_FIELDS, CreativeInput, MissingField


def get_next_missing_field(state: CreativeInput) -> MissingField | None:
    """Returns the single next `CreativeInput` field to ask about, or None
    once all required fields are known. Order matches the implementation
    spec exactly: product -> campaign -> duration -> style.
    """
    if not state.product_name:
        return "product_name"
    if not state.campaign_type:
        return "campaign_type"
    if not state.duration_seconds:
        return "duration_seconds"
    if not state.style:
        return "style"
    return None


def is_creative_input_complete(state: CreativeInput) -> bool:
    return get_next_missing_field(state) is None


def needs_assets(assets: list[AssetInfo]) -> bool:
    """True when generation-blocking: no accepted (valid/warning) asset yet."""
    return not has_usable_asset(assets)


def is_ready_for_brief(creative_input: CreativeInput, assets: list[AssetInfo]) -> bool:
    return is_creative_input_complete(creative_input) and not needs_assets(assets)


__all__ = [
    "REQUIRED_FIELDS",
    "get_next_missing_field",
    "is_creative_input_complete",
    "needs_assets",
    "is_ready_for_brief",
]
