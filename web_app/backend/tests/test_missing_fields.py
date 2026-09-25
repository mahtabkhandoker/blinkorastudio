from app.models.assets import AssetInfo
from app.models.creative import CreativeInput
from app.services.chatbot.missing_fields import (
    get_next_missing_field,
    is_ready_for_brief,
    needs_assets,
)


def test_missing_product_name_first():
    assert get_next_missing_field(CreativeInput()) == "product_name"


def test_missing_campaign_type_next():
    state = CreativeInput(product_name="Marifa dress")
    assert get_next_missing_field(state) == "campaign_type"


def test_missing_duration_next():
    state = CreativeInput(product_name="Marifa dress", campaign_type="Eid")
    assert get_next_missing_field(state) == "duration_seconds"


def test_missing_style_last():
    state = CreativeInput(product_name="Marifa dress", campaign_type="Eid", duration_seconds=15)
    assert get_next_missing_field(state) == "style"


def test_nothing_missing_when_all_present():
    state = CreativeInput(
        product_name="Marifa dress", campaign_type="Eid", duration_seconds=15, style=["premium"]
    )
    assert get_next_missing_field(state) is None


def test_needs_assets_true_when_empty():
    assert needs_assets([]) is True


def test_needs_assets_false_when_valid_present():
    assets = [AssetInfo(id="a1", filename="x.jpg", status="VALID")]
    assert needs_assets(assets) is False


def test_needs_assets_false_when_warning_accepted():
    assets = [AssetInfo(id="a1", filename="x.jpg", status="WARNING", warning_code="BLURRY")]
    assert needs_assets(assets) is False


def test_needs_assets_true_when_only_rejected():
    assets = [AssetInfo(id="a1", filename="x.jpg", status="REJECTED", warning_code="CORRUPT")]
    assert needs_assets(assets) is True


def test_is_ready_for_brief_requires_both():
    complete_input = CreativeInput(
        product_name="Marifa dress", campaign_type="Eid", duration_seconds=15, style=["premium"]
    )
    assert is_ready_for_brief(complete_input, []) is False
    assert is_ready_for_brief(complete_input, [AssetInfo(id="a1", filename="x.jpg", status="VALID")]) is True
