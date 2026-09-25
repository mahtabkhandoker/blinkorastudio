"""Builds the human-readable creative brief shown to the user for
confirmation. Kept separate from both the chatbot reply and the final
video-model prompt (see prompt_builder.py) per the spec's separation of
concerns.
"""

from __future__ import annotations

from app.models.assets import AssetInfo, has_usable_asset
from app.models.creative import CreativeBrief, CreativeInput

_STYLE_LABELS = {
    "premium": "Premium",
    "elegant": "Elegant",
    "festive": "Festive",
    "minimal": "Minimal",
    "energetic": "Energetic",
}

_DEFAULT_CTA = {"bn": "আজই অর্ডার করুন", "en": "Order today"}


def build_creative_brief(creative_input: CreativeInput, assets: list[AssetInfo]) -> CreativeBrief:
    usable_assets = [a for a in assets if a.status in ("VALID", "WARNING")]
    language = creative_input.language or "bn"
    styles = [_STYLE_LABELS.get(s.lower(), s.title()) for s in creative_input.style] or ["Clean", "Modern"]

    product = creative_input.product_name or creative_input.business_name or "Product"
    campaign = creative_input.campaign_type or "Product Promo"
    duration = creative_input.duration_seconds or 15
    aspect = creative_input.aspect_ratio or "9:16"
    cta = creative_input.cta or _DEFAULT_CTA.get(language, _DEFAULT_CTA["bn"])
    caption_language = "English" if language == "en" else "Bangla"

    visual_direction = (
        f"Natural product movement, {', '.join(styles).lower()} lighting and camera motion, "
        "focus on product details and craftsmanship."
    )

    return CreativeBrief(
        product=product,
        campaign=campaign,
        duration=f"{duration} seconds",
        format=f"{aspect} vertical" if aspect == "9:16" else f"{aspect}",
        style=styles,
        audience=creative_input.target_audience,
        assets=len(usable_assets) or (1 if has_usable_asset(assets) else 0),
        caption_language=caption_language,
        cta=cta,
        visual_direction=visual_direction,
    )
