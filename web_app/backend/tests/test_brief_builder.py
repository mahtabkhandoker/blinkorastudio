from app.models.assets import AssetInfo
from app.models.creative import CreativeInput
from app.services.chatbot.brief_builder import build_creative_brief
from app.services.chatbot.prompt_builder import build_video_prompt


def _complete_input(**overrides) -> CreativeInput:
    base = dict(
        business_name="Marifa",
        product_name="Marifa dress",
        campaign_type="Eid",
        duration_seconds=15,
        style=["premium", "festive"],
        cta="আজই অর্ডার করুন",
        language="bn",
    )
    base.update(overrides)
    return CreativeInput(**base)


def test_brief_has_expected_fields():
    assets = [AssetInfo(id="a1", filename="x.jpg", status="VALID")]
    brief = build_creative_brief(_complete_input(), assets)

    assert brief.product == "Marifa dress"
    assert brief.campaign == "Eid"
    assert brief.duration == "15 seconds"
    assert brief.format == "9:16 vertical"
    assert brief.style == ["Premium", "Festive"]
    assert brief.assets == 1
    assert brief.caption_language == "Bangla"
    assert brief.cta == "আজই অর্ডার করুন"


def test_brief_defaults_cta_and_aspect_when_missing():
    assets = [AssetInfo(id="a1", filename="x.jpg", status="WARNING", warning_code="BLURRY")]
    brief = build_creative_brief(_complete_input(cta=None), assets)
    assert brief.cta  # a sensible default is applied, never empty
    assert brief.assets == 1  # warning-but-accepted assets still count


def test_prompt_builder_never_mentions_internal_provider_names():
    assets = [AssetInfo(id="a1", filename="x.jpg", status="VALID")]
    brief = build_creative_brief(_complete_input(), assets)
    prompt = build_video_prompt(brief, assets)

    banned_terms = ["gpt", "openai", "seedance", "wan 3", "gen-4", "runway", "sora"]
    lowered = prompt.lower()
    for term in banned_terms:
        assert term not in lowered
    assert "marifa dress" in lowered
