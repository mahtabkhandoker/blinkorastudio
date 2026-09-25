"""Builds the final, provider-agnostic video-generation prompt.

This is deliberately separate from the creative brief the user sees: the
brief is friendly and human-readable, this prompt is what would be sent
to a video-generation model. It never names a specific model/provider —
routing to an actual model is an internal implementation detail decided
elsewhere (never here, and never exposed to the user).
"""

from __future__ import annotations

from app.models.assets import AssetInfo
from app.models.creative import CreativeBrief


def build_video_prompt(brief: CreativeBrief, assets: list[AssetInfo]) -> str:
    style_text = ", ".join(s.lower() for s in brief.style) or "clean, modern"
    asset_count = len(assets) or brief.assets

    return (
        f"Create a {style_text} {brief.duration} {brief.product.lower()} promo "
        f"using the {asset_count} uploaded product image(s). Preserve the exact "
        "product design, colors, texture, and details. Use subtle cinematic "
        "motion, elegant close-ups, premium lighting, and smooth transitions. "
        "Natural, polished, professional look. No distortion, no unnecessary text. "
        f"Format: {brief.format}. Caption language: {brief.caption_language}. "
        f"Call to action: \"{brief.cta}\"."
    )
