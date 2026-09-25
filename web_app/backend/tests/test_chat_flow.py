from fastapi.testclient import TestClient

from app.services.chatbot.llm_client import rule_based_extract


def _post(client: TestClient, message: str, state: dict | None = None, conversation_id: str = "conv_test"):
    payload = {
        "conversation_id": conversation_id,
        "message": message,
        "state": state or {"stage": "WELCOME", "creative_input": {}, "assets": []},
    }
    response = client.post("/api/chat/message", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


# --- Language extraction ------------------------------------------------------


def test_bangla_input_extracts_all_required_fields(client: TestClient):
    message = "আমার Marifa dress ব্যবসা আছে। ঈদের জন্য 15 second প্রিমিয়াম ভিডিও চাই।"
    data = _post(client, message)
    ci = data["creative_input"]
    assert ci["product_name"] == "Marifa"
    assert ci["campaign_type"] == "Eid"
    assert ci["duration_seconds"] == 15
    assert ci["style"] == ["premium"]


def test_banglish_input_extracts_all_required_fields(client: TestClient):
    message = "Amar Marifa dress business ache. Eid er jonno 15 sec premium video chai."
    data = _post(client, message)
    ci = data["creative_input"]
    assert ci["product_name"] == "Marifa"
    assert ci["campaign_type"] == "Eid"
    assert ci["duration_seconds"] == 15
    assert ci["style"] == ["premium"]
    # All 4 required fields known + no asset yet -> the bot asks for an
    # image next, not for anything already provided.
    assert data["missing_field"] is None
    assert data["needs_assets"] is True
    assert data["stage"] == "ASSET_UPLOAD"


def test_english_input_extraction(client: TestClient):
    message = "I want a 20 second minimal promo for my Urban Threads store."
    data = _post(client, message)
    ci = data["creative_input"]
    assert ci["duration_seconds"] == 20
    assert ci["style"] == ["minimal"]
    assert ci["campaign_type"] == "Product Promo"


def test_mixed_language_extraction():
    # Exercised directly against the extractor: Bangla + English in one
    # message, covering the "mixed-language input" requirement precisely.
    message = "Amar Sundari honey business ache, need 10 sec energetic video, ভিডিওটা যেন attractive hoy।"
    extracted = rule_based_extract(message)
    assert extracted["business_name"] == "Sundari"
    assert extracted["product_category"] == "honey"
    assert extracted["duration_seconds"] == 10
    assert extracted["style"] == ["energetic"]
    assert extracted["language"] == "bn"  # Bangla script present anywhere -> bn


# --- Corrections and preservation --------------------------------------------


def test_field_correction_updates_only_that_field(client: TestClient):
    state = {
        "stage": "DETAILS_COLLECTION",
        "creative_input": {
            "product_name": "Marifa",
            "campaign_type": "Eid",
            "duration_seconds": 15,
            "style": ["premium"],
        },
        "assets": [],
    }
    data = _post(client, "15 sec na, 20 sec kori", state=state)
    ci = data["creative_input"]
    assert ci["duration_seconds"] == 20
    # Untouched fields survive the correction message unchanged.
    assert ci["product_name"] == "Marifa"
    assert ci["campaign_type"] == "Eid"
    assert ci["style"] == ["premium"]


def test_existing_fields_preserved_on_vague_message(client: TestClient):
    creative_input = {
        "product_name": "Marifa",
        "campaign_type": "Eid",
        "duration_seconds": 15,
        "style": ["premium"],
    }
    state = {"stage": "BRIEF_REVIEW", "creative_input": creative_input, "assets": []}
    data = _post(client, "looks good", state=state)
    assert data["creative_input"]["product_name"] == "Marifa"
    assert data["creative_input"]["campaign_type"] == "Eid"
    assert data["creative_input"]["duration_seconds"] == 15
    assert data["creative_input"]["style"] == ["premium"]


# --- Missing-field question policy -------------------------------------------


def test_asks_product_only_when_nothing_known(client: TestClient):
    data = _post(client, "")
    assert data["missing_field"] == "product_name"
    assert data["stage"] == "INTENT"
    assert "product" in data["reply"].lower() or "promote" in data["reply"].lower()


def test_does_not_reask_duration_or_style_once_known(client: TestClient):
    state = {
        "stage": "DETAILS_COLLECTION",
        "creative_input": {"duration_seconds": 15, "style": ["premium"]},
        "assets": [],
    }
    data = _post(client, "Amar dokan ache", state=state)
    assert data["missing_field"] not in ("duration_seconds", "style")


# --- Asset-aware flow ---------------------------------------------------------

_COMPLETE_INPUT = {
    "product_name": "Marifa",
    "campaign_type": "Eid",
    "duration_seconds": 15,
    "style": ["premium"],
}


def test_brief_ready_requires_a_usable_asset(client: TestClient):
    state = {"stage": "DETAILS_COLLECTION", "creative_input": _COMPLETE_INPUT, "assets": []}
    data = _post(client, "", state=state)
    assert data["brief_ready"] is False
    assert data["needs_assets"] is True
    assert data["stage"] == "ASSET_UPLOAD"


def test_brief_ready_true_with_valid_asset(client: TestClient):
    state = {
        "stage": "ASSET_UPLOAD",
        "creative_input": _COMPLETE_INPUT,
        "assets": [{"id": "a1", "filename": "x.jpg", "status": "VALID"}],
    }
    data = _post(client, "", state=state)
    assert data["brief_ready"] is True
    assert data["requires_confirmation"] is True
    assert data["stage"] == "BRIEF_REVIEW"
    assert data["creative_brief"]["product"] == "Marifa"


def test_warning_asset_the_user_kept_still_counts_as_usable(client: TestClient):
    state = {
        "stage": "ASSET_UPLOAD",
        "creative_input": _COMPLETE_INPUT,
        "assets": [{"id": "a1", "filename": "x.jpg", "status": "WARNING", "warning_code": "BLURRY"}],
    }
    data = _post(client, "", state=state)
    assert data["brief_ready"] is True


def test_rejected_only_asset_does_not_count(client: TestClient):
    state = {
        "stage": "ASSET_UPLOAD",
        "creative_input": _COMPLETE_INPUT,
        "assets": [{"id": "a1", "filename": "x.jpg", "status": "REJECTED", "warning_code": "CORRUPT"}],
    }
    data = _post(client, "", state=state)
    assert data["brief_ready"] is False
    assert data["needs_assets"] is True


# --- Confirmation / generation safety ----------------------------------------


def test_chat_endpoint_never_starts_generation_itself(client: TestClient):
    """The chat endpoint can only ever *offer* confirmation — it has no
    ability to start generation. Confirmation and generation are a
    separate, explicit action (POST /api/generations)."""
    state = {
        "stage": "ASSET_UPLOAD",
        "creative_input": _COMPLETE_INPUT,
        "assets": [{"id": "a1", "filename": "x.jpg", "status": "VALID"}],
    }
    data = _post(client, "looks good, generate it now", state=state)
    assert data["stage"] == "BRIEF_REVIEW"
    assert data["requires_confirmation"] is True
    # Casual confirmation language in the message must not be treated as
    # an authorization — there is no "generation started" signal anywhere
    # in this response shape.
    assert "generation" not in data  # ChatResponse has no such field at all


def test_generation_submission_is_idempotent(client: TestClient):
    brief = {
        "product": "Marifa dress",
        "campaign": "Eid",
        "duration": "15 seconds",
        "format": "9:16 vertical",
        "style": ["Premium"],
        "assets": 1,
        "caption_language": "Bangla",
        "cta": "আজই অর্ডার করুন",
        "visual_direction": "Natural product movement.",
    }
    payload = {"conversation_id": "conv_test", "idempotency_key": "confirm-once-123", "brief": brief}

    first = client.post("/api/generations", json=payload)
    second = client.post("/api/generations", json=payload)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["deduplicated"] is False
    assert second.json()["deduplicated"] is True


# --- Failure handling ---------------------------------------------------------


def test_llm_failure_falls_back_without_losing_state(client, monkeypatch):
    from app.api.routes import chat as chat_route

    class BoomLLMClient:
        async def extract_and_reply(self, message, current_input):
            raise RuntimeError("provider is down")

    def boom_orchestrator():
        from app.services.chatbot.orchestrator import ChatOrchestrator

        return ChatOrchestrator(llm_client=BoomLLMClient())

    client.app.dependency_overrides[chat_route.get_orchestrator] = boom_orchestrator

    state = {"stage": "DETAILS_COLLECTION", "creative_input": {"product_name": "Marifa"}, "assets": []}
    response = client.post(
        "/api/chat/message",
        json={"conversation_id": "conv_fail", "message": "ekta message", "state": state},
    )
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "দুঃখিত" in data["reply"] or "sorry" in data["reply"].lower()
    # State is preserved exactly as it was — nothing was lost on failure.
    assert data["creative_input"]["product_name"] == "Marifa"
    assert data["stage"] == "DETAILS_COLLECTION"
