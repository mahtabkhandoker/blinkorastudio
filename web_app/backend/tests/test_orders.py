"""P0 order workflow: routing, question sequencing, plans, confirmation,
generation safety, uploads and the HTTP contract."""

from __future__ import annotations

import io
import random

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.models.orders import Order
from app.services.orders import questions
from app.services.orders.catalog import QUESTIONS
from app.services.orders.plan_builder import shot_negative_prompt, shot_prompt
from app.services.orders.service import get_order_service
from app.services.orders.templates import TEMPLATES, assemble_prompt

# --- Helpers --------------------------------------------------------------------------


def _image_bytes(kind: str = "good", fmt: str = "PNG") -> bytes:
    if kind == "small":
        image = Image.new("RGB", (200, 200), (180, 180, 180))
    elif kind == "blurry":
        image = Image.new("RGB", (600, 800), (150, 150, 150))
    else:
        rng = random.Random(7)
        image = Image.new("RGB", (600, 800))
        image.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(600 * 800)])
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


GOOD = _image_bytes("good")


def create(client: TestClient, **body) -> dict:
    response = client.post("/api/orders", json={"channel": "web", "locale": "bn", **body})
    assert response.status_code == 201, response.text
    return response.json()


def upload(client: TestClient, order_id: str, data: bytes = GOOD, purpose: str = "product", name: str = "p.png"):
    return client.post(
        f"/api/orders/{order_id}/assets",
        files={"file": (name, data, "image/png")},
        data={"purpose": purpose},
    )


def answer(client: TestClient, order_id: str, code: str, value: str | None = None, skip: bool = False) -> dict:
    response = client.post(f"/api/orders/{order_id}/answers", json={"code": code, "value": value, "skip": skip})
    assert response.status_code == 200, response.text
    return response.json()


def confirm(client: TestClient, order_id: str, revision: int, key: str = "key-1"):
    return client.post(
        f"/api/orders/{order_id}/plan/confirm",
        json={"plan_revision": revision},
        headers={"Idempotency-Key": key},
    )


def ready_order(client: TestClient, answers: list[tuple[str, str]], **body) -> dict:
    """Creates an order, uploads a good photo and answers in sequence."""
    view = create(client, **body)
    assert upload(client, view["id"]).status_code == 200
    for code, value in answers:
        view = answer(client, view["id"], code, value)
    return view


def stored(order_id: str) -> Order:
    return get_order_service().get(order_id)


def template_ids(order_id: str) -> list[str]:
    plan = stored(order_id).plan
    assert plan is not None
    return [shot.template_id for shot in plan.shots]


SAREE = [("Q1", "clothing"), ("Q2", "লাল সুতির শাড়ি"), ("GQ1", "medium")]

# --- Step order ---------------------------------------------------------------------------


def test_new_order_starts_with_the_photo_then_q1(client):
    view = create(client)
    assert view["status"] == "DRAFT"
    assert view["step"]["kind"] == "photo"
    assert view["format"]["value"] == "reels"

    view = upload(client, view["id"]).json()
    assert view["photos"][0]["usable"] is True
    assert view["step"]["question"]["code"] == "Q1"
    assert len(view["step"]["question"]["options"]) == 7


def test_one_question_at_a_time_and_out_of_turn_answers_are_rejected(client):
    view = create(client)
    upload(client, view["id"])
    response = client.post(f"/api/orders/{view['id']}/answers", json={"code": "GQ1", "value": "light"})
    assert response.status_code == 409
    assert response.json()["error_code"] == "QUESTION_NOT_APPLICABLE"


# --- Every product-group mapping --------------------------------------------------------------


@pytest.mark.parametrize(
    ("category", "group", "group_question"),
    [
        ("clothing", "G1", "GQ1"),
        ("cosmetics", "G2", "GQ2"),
        ("jewellery_watches", "G3", "GQ3a"),
        ("electronics", "G3", "GQ3a"),
        ("other", "G2", "GQ2"),
    ],
)
def test_category_routes_to_group_and_its_question(client, category, group, group_question):
    view = ready_order(client, [("Q1", category)])
    assert view["step"]["question"]["code"] == "Q2"
    view = answer(client, view["id"], "Q2", "ekta jinish")
    assert view["step"]["question"]["code"] == group_question
    assert questions.resolve_route(stored(view["id"])).group == group


@pytest.mark.parametrize(
    ("subtype", "group", "next_code"),
    [
        ("fresh", "G5", "GQ5"),
        ("flowing", "G4", "GQ4"),
        ("prepared", "G2", "GQ2"),
    ],
)
def test_food_subtype_classification(client, subtype, group, next_code):
    view = ready_order(client, [("Q1", "food")])
    assert view["step"]["question"]["code"] == "Q1a"
    view = answer(client, view["id"], "Q1a", subtype)
    view = answer(client, view["id"], "Q2", "khabar")
    assert view["step"]["question"]["code"] == next_code
    assert questions.resolve_route(stored(view["id"])).group == group


def test_dry_goods_never_get_asked_wet_or_dry(client):
    view = ready_order(client, [("Q1", "food"), ("Q1a", "dry_goods"), ("Q2", "শুঁটকি")])
    # The subtype already answers GQ5, so the plan is ready with no group question.
    assert view["step"]["kind"] == "plan"
    assert view["status"] == "PLAN_READY"
    assert template_ids(view["id"]) == ["G5-A-DRY", "G5-B", "G5-C"]
    assert "GQ5" not in [a["code"] for a in view["answered"]]


def test_q1a_is_only_asked_for_food(client):
    view = ready_order(client, [("Q1", "cosmetics")])
    assert view["step"]["question"]["code"] == "Q2"


def test_reflective_group_asks_both_parts_of_gq3(client):
    view = ready_order(client, [("Q1", "jewellery_watches"), ("Q2", "gold chain"), ("GQ3a", "wood")])
    assert view["step"]["question"]["code"] == "GQ3b"
    view = answer(client, view["id"], "GQ3b", "no")
    assert view["step"]["kind"] == "plan"
    plan = stored(view["id"]).plan
    assert plan.shots[0].slots["SURFACE"].value == "a dark wooden table"
    assert plan.shots[0].slots["SURFACE"].source == "GQ3a"


def test_glare_asks_for_a_new_photo_before_the_plan(client):
    view = ready_order(
        client, [("Q1", "jewellery_watches"), ("Q2", "ring"), ("GQ3a", "cloth"), ("GQ3b", "yes")]
    )
    assert view["step"]["question"]["code"] == "PH_GLARE"
    assert view["plan"] is None
    view = upload(client, view["id"], name="no-glare.png").json()
    assert view["step"]["kind"] == "plan"
    assert len(view["photos"]) == 1  # the new photo replaced the old one


def test_glare_can_be_overridden_and_is_flagged_for_the_operator(client):
    view = ready_order(
        client, [("Q1", "jewellery_watches"), ("Q2", "ring"), ("GQ3a", "cloth"), ("GQ3b", "yes")]
    )
    view = answer(client, view["id"], "PH_GLARE", "use_anyway")
    assert view["step"]["kind"] == "plan"
    assert any("glare" in flag for flag in stored(view["id"]).plan.operator_flags)


# --- Skips and defaults ---------------------------------------------------------------------------


def test_skipping_every_question_still_produces_a_plan(client):
    view = create(client)
    upload(client, view["id"])
    for _ in range(6):
        if view["step"]["kind"] != "question":
            view = client.get(f"/api/orders/{view['id']}").json()
        if view["step"]["kind"] != "question":
            break
        view = answer(client, view["id"], view["step"]["question"]["code"], skip=True)
    assert view["step"]["kind"] == "plan"
    # "Something else" → G2, the safest default group.
    assert template_ids(view["id"]) == ["G2-A", "G2-B", "G2-C"]
    assert all(a["source"] == "default" for a in view["answered"])


def test_every_choose_question_has_a_default_except_flow_and_feedback():
    without_default = {
        code
        for code, q in QUESTIONS.items()
        if q.kind == "choose" and q.default_option is None
    }
    # R1 is an opinion and C2 is an action: neither can be guessed.
    assert without_default == {"R1", "C2"}


def test_invalid_option_and_empty_text_are_rejected(client):
    view = create(client)
    upload(client, view["id"])
    bad = client.post(f"/api/orders/{view['id']}/answers", json={"code": "Q1", "value": "spaceship"})
    assert bad.status_code == 422 and bad.json()["error_code"] == "INVALID_OPTION"
    answer(client, view["id"], "Q1", "clothing")
    empty = client.post(f"/api/orders/{view['id']}/answers", json={"code": "Q2", "value": "   "})
    assert empty.status_code == 422 and empty.json()["error_code"] == "ANSWER_REQUIRED"


# --- Three-shot plans ---------------------------------------------------------------------------------


def test_soft_plan_structure_and_motion_level(client):
    view = ready_order(client, [("Q1", "clothing"), ("Q2", "red cotton saree"), ("GQ1", "heavy")])
    plan = stored(view["id"]).plan
    assert plan.kind == "product" and plan.group == "G1"
    assert [s.role for s in plan.shots] == ["main", "closeup", "wide"]
    assert [s.index for s in plan.shots] == [1, 2, 3]
    assert plan.shots[0].slots["MOTION_LEVEL"].value == "slowly, the fabric holding its weight"
    assert plan.shots[0].slots["PRODUCT"].value == "red cotton saree"
    assert plan.aspect_ratio == "9:16"
    assert plan.shots[0].subject_motion and plan.shots[0].camera_move
    assert "pattern drift" in plan.shots[0].negative_terms
    assert plan.group_answers == {"GQ1": "heavy"}
    assert len(view["plan"]["shots"]) == 3


@pytest.mark.parametrize(
    ("gq4", "expected", "first_framing"),
    [
        ("both", ["G4-A", "G4-B", "G4-C"], "standard"),
        ("pour", ["G4-B", "G4-B", "G4-C"], "wider"),
        ("closed", ["G2-A", "G2-B", "G2-C"], "standard"),
    ],
)
def test_flowing_shot_plan_depends_on_gq4(client, gq4, expected, first_framing):
    view = ready_order(client, [("Q1", "food"), ("Q1a", "flowing"), ("Q2", "মধু"), ("GQ4", gq4)])
    plan = stored(view["id"]).plan
    assert [s.template_id for s in plan.shots] == expected
    assert plan.shots[0].framing == first_framing
    assert plan.group == "G4"  # the order's group stays Flowing even when shots use Rigid templates


def test_fresh_wet_and_dry_variants(client):
    wet = ready_order(client, [("Q1", "food"), ("Q1a", "fresh"), ("Q2", "আম"), ("GQ5", "wet")])
    assert template_ids(wet["id"]) == ["G5-A", "G5-B", "G5-C"]
    assert "water" not in stored(wet["id"]).plan.shots[0].negative_terms

    dry = ready_order(client, [("Q1", "food"), ("Q1a", "fresh"), ("Q2", "কাঁচা আম"), ("GQ5", "dry")])
    plan = stored(dry["id"]).plan
    assert [s.template_id for s in plan.shots] == ["G5-A-DRY", "G5-B", "G5-C"]
    # The dry avoid terms apply to all three shots, not only the first.
    assert all({"water", "droplets", "mist"} <= set(s.negative_terms) for s in plan.shots)


def test_blurry_label_drops_the_readable_promise(client):
    clear = ready_order(client, [("Q1", "cosmetics"), ("Q2", "face cream"), ("GQ2", "clear")])
    blurry = ready_order(client, [("Q1", "cosmetics"), ("Q2", "face cream"), ("GQ2", "blurry")])
    assert "fully readable" in shot_prompt(stored(clear["id"]).plan.shots[0])
    shot = stored(blurry["id"]).plan.shots[0]
    assert "fully readable" not in shot_prompt(shot)
    assert shot.crop == "tighter"


def test_post_format_changes_aspect_ratio_and_bumps_revision(client):
    view = ready_order(client, SAREE)
    first = view["plan"]["revision"]
    view = client.put(f"/api/orders/{view['id']}/format", json={"format": "post"}).json()
    assert stored(view["id"]).plan.aspect_ratio == "1:1"
    assert view["plan"]["revision"] == first + 1


def test_both_formats_only_offered_when_configured(client, monkeypatch):
    view = create(client)
    both = next(o for o in view["format"]["options"] if o["id"] == "both")
    assert both["available"] is False
    response = client.put(f"/api/orders/{view['id']}/format", json={"format": "both"})
    assert response.status_code == 422 and response.json()["error_code"] == "FORMAT_UNAVAILABLE"


# --- Prompts: internal only, and clean -------------------------------------------------------------------


def _all_plans(client) -> list[Order]:
    flows = [
        SAREE,
        [("Q1", "cosmetics"), ("Q2", "ফেস ক্রিম"), ("GQ2", "blurry")],
        [("Q1", "electronics"), ("Q2", "smart watch"), ("GQ3a", "white"), ("GQ3b", "no")],
        [("Q1", "food"), ("Q1a", "flowing"), ("Q2", "খাঁটি মধু ৫০০ টাকা"), ("GQ4", "pour")],
        [("Q1", "food"), ("Q1a", "flowing"), ("Q2", "ghee"), ("GQ4", "closed")],
        [("Q1", "food"), ("Q1a", "fresh"), ("Q2", "ilish"), ("GQ5", "wet")],
        [("Q1", "food"), ("Q1a", "dry_goods"), ("Q2", "চাল")],
        [("Q1", "service"), ("SQ1", "S3"), ("SQ2", "চুল কাটা"), ("SQ8", "with_face"), ("SQ3", "১০০ টাকা"), ("SQ4", "মিরপুর ১০")],
        [("Q1", "service"), ("SQ1", "S2"), ("SQ2", "রং করা"), ("SQ7", "no"), ("SQ3", ""), ("SQ4", "ঢাকা")],
    ]
    orders = []
    for flow in flows:
        view = create(client)
        upload(client, view["id"])
        for code, value in flow:
            view = answer(client, view["id"], code, value or None, skip=not value)
        assert view["step"]["kind"] == "plan", flow
        orders.append(stored(view["id"]))
    return orders


def test_prompts_are_english_complete_and_free_of_overlay_content(client):
    for order in _all_plans(client):
        for shot in order.plan.generated_shots:
            prompt = shot_prompt(shot)
            assert prompt.isascii(), prompt  # no Bengali ever reaches the video model
            assert "{{" not in prompt and "[[" not in prompt
            assert not any(ch.isdigit() for ch in prompt), prompt  # no prices or phone numbers
            assert "none" not in prompt.lower().split()  # an empty accent is dropped, not printed
            assert 35 <= len(prompt.split()) <= 75, (shot.template_id, len(prompt.split()))
            negative = shot_negative_prompt(shot)
            assert negative.startswith("text, letters, words")


def test_bengali_description_falls_back_to_a_generic_noun_and_is_flagged(client):
    view = ready_order(client, SAREE)
    plan = stored(view["id"]).plan
    assert plan.product_description == "লাল সুতির শাড়ি"  # kept for the operator
    assert plan.shots[0].slots["PRODUCT"].value == "garment"
    assert plan.shots[0].slots["PRODUCT"].source == "generic_default"
    assert any("PRODUCT" in flag for flag in plan.operator_flags)


def test_every_template_assembles_with_its_own_slots():
    for template_id, template in TEMPLATES.items():
        if not template.text:
            continue
        slots = {name: "value" for name in ("PRODUCT", "MATERIAL", "DETAIL", "SURFACE", "SETTING", "MOOD", "LIGHT", "MOTION_LEVEL", "SUBJECT", "TOOLS", "WORKER")}
        with_accent = assemble_prompt(template_id, {**slots, "ACCENT": "light mist"})
        without = assemble_prompt(template_id, {**slots, "ACCENT": "none"})
        assert "{{" not in with_accent and "[[" not in without
        assert "none" not in without.lower().split()


def test_customer_view_never_contains_prompts_or_template_internals(client):
    view = ready_order(client, [("Q1", "clothing"), ("Q2", "red cotton saree"), ("GQ1", "light")])
    body = client.get(f"/api/orders/{view['id']}").text
    for leaked in ("stays centred", "G1-A", "negative", "pattern drift", "slots", "MOTION_LEVEL", "noticeably"):
        assert leaked not in body, leaked
    # What the customer does see is the Bengali description of each scene.
    assert view["plan"]["shots"][0]["description"] == "কাপড় হালকা বাতাসে দুলছে"
    assert view["plan"]["intro"] == "৩টি দৃশ্য বানাব:"
    assert "ভিডিওর ভেতরে না" in view["plan"]["post_production_note"]


def test_plan_is_shown_in_english_when_asked(client):
    view = ready_order(client, SAREE)
    english = client.get(f"/api/orders/{view['id']}", params={"locale": "en"}).json()
    assert english["plan"]["shots"][0]["description"] == "The fabric moves in a light breeze"
    assert english["answered"][0]["display"] == "Clothing"


def test_operator_endpoint_is_off_by_default_and_needs_the_token(client, monkeypatch):
    view = ready_order(client, SAREE)
    assert client.get(f"/api/internal/orders/{view['id']}").status_code == 404

    monkeypatch.setenv("OPERATOR_API_TOKEN", "s3cret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert client.get(f"/api/internal/orders/{view['id']}", headers={"X-Operator-Token": "wrong"}).status_code == 404
    record = client.get(f"/api/internal/orders/{view['id']}", headers={"X-Operator-Token": "s3cret"}).json()
    assert record["shots"][0]["prompt"].startswith("The garment in the image stays centred")
    assert record["order_line"].startswith(view["number"])
    assert "shots G1-A, G1-B, G1-C" in record["order_line"]


# --- Confirmation and revision ------------------------------------------------------------------------------


def test_changing_an_answer_rebuilds_the_plan(client):
    view = ready_order(client, SAREE)
    first = view["plan"]["revision"]
    assert all(a["editable"] for a in view["answered"])
    view = answer(client, view["id"], "GQ1", "light")
    assert view["plan"]["revision"] == first + 1
    assert stored(view["id"]).plan.shots[0].slots["MOTION_LEVEL"].value == "noticeably"


def test_changing_the_category_drops_dependent_answers_but_keeps_the_description(client):
    view = ready_order(client, SAREE)
    view = answer(client, view["id"], "Q1", "cosmetics")
    assert view["status"] == "DRAFT" and view["plan"] is None
    assert [a["code"] for a in view["answered"]] == ["Q1", "Q2"]
    assert view["step"]["question"]["code"] == "GQ2"


def test_c2_change_note_on_a_shot_updates_the_plan(client):
    view = ready_order(client, SAREE)
    first = view["plan"]["revision"]
    view = client.post(f"/api/orders/{view['id']}/plan/change").json()
    question = view["step"]["question"]
    assert question["code"] == "C2"
    assert [o["id"] for o in question["options"]] == ["shot_1", "shot_2", "shot_3", "product_type", "nothing"]

    view = answer(client, view["id"], "C2", "shot_2")
    assert view["step"]["question"]["code"] == "C2N"
    view = answer(client, view["id"], "C2N", "পাড়টা আরও কাছ থেকে")
    assert view["step"]["kind"] == "plan"
    assert view["plan"]["revision"] == first + 1
    assert view["plan"]["shots"][1]["note"].endswith("পাড়টা আরও কাছ থেকে")
    # The note is for the operator. It is never spliced into the prompt.
    shot = stored(view["id"]).plan.shots[1]
    assert shot.change_note == "পাড়টা আরও কাছ থেকে"
    assert shot_prompt(shot).isascii()


def test_c2_product_type_goes_back_to_q1(client):
    view = ready_order(client, SAREE)
    client.post(f"/api/orders/{view['id']}/plan/change")
    view = answer(client, view["id"], "C2", "product_type")
    assert view["step"]["question"]["code"] == "Q1"
    assert view["status"] == "DRAFT"


def test_c2_nothing_returns_to_the_same_plan(client):
    view = ready_order(client, SAREE)
    first = view["plan"]["revision"]
    client.post(f"/api/orders/{view['id']}/plan/change")
    view = answer(client, view["id"], "C2", "nothing")
    assert view["step"]["kind"] == "plan" and view["plan"]["revision"] == first


def test_confirm_needs_the_revision_the_customer_saw(client):
    view = ready_order(client, SAREE)
    stale = view["plan"]["revision"]
    answer(client, view["id"], "GQ1", "heavy")
    response = confirm(client, view["id"], stale)
    assert response.status_code == 409
    assert response.json()["error_code"] == "PLAN_REVISION_STALE"
    assert stored(view["id"]).generation is None


def test_confirm_is_refused_while_a_change_request_is_open(client):
    view = ready_order(client, SAREE)
    client.post(f"/api/orders/{view['id']}/plan/change")
    response = confirm(client, view["id"], view["plan"]["revision"])
    assert response.status_code == 409 and response.json()["error_code"] == "PLAN_NOT_READY"


def test_confirm_without_idempotency_key_is_refused(client):
    view = ready_order(client, SAREE)
    response = client.post(f"/api/orders/{view['id']}/plan/confirm", json={"plan_revision": view["plan"]["revision"]})
    assert response.status_code == 400
    assert response.json()["error_code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_confirm_before_the_plan_exists_is_refused(client):
    view = create(client)
    response = confirm(client, view["id"], 1)
    assert response.status_code == 409 and response.json()["error_code"] == "PLAN_NOT_READY"


# --- Generation: mock only, traceable, never duplicated ---------------------------------------------------------


def test_confirm_creates_one_traceable_mock_generation(client):
    view = ready_order(client, SAREE)
    result = confirm(client, view["id"], view["plan"]["revision"]).json()
    generation = result["generation"]
    assert generation["id"].startswith("GEN-")
    assert generation["simulated"] is True
    assert generation["deduplicated"] is False
    assert len(generation["shots"]) == 3
    assert result["environment"]["simulated_generation"] is True
    assert "video_url" not in str(result)  # a simulated run produces no video

    order = stored(view["id"])
    assert order.status == "GENERATED"  # the mock finishes instantly in tests
    assert order.generation.plan_revision == view["plan"]["revision"]
    assert [s.client_reference for s in order.generation.shots] == [
        f"{generation['id']}:shot{i}:try1" for i in (1, 2, 3)
    ]
    assert any(e.type == "order_line" for e in order.events)


def test_duplicate_confirm_returns_the_same_generation(client):
    view = ready_order(client, SAREE)
    revision = view["plan"]["revision"]
    first = confirm(client, view["id"], revision, key="tap-1").json()
    again_same_key = confirm(client, view["id"], revision, key="tap-1").json()
    again_new_key = confirm(client, view["id"], revision, key="tap-2").json()

    assert again_same_key["generation"]["id"] == first["generation"]["id"]
    assert again_new_key["generation"]["id"] == first["generation"]["id"]
    assert again_same_key["generation"]["deduplicated"] is True
    provider = get_order_service()._provider
    assert len(provider.submitted) == 3  # three shots, submitted once


def test_generation_request_carries_prompt_parts_but_no_overlay_text(client):
    view = ready_order(client, [("Q1", "food"), ("Q1a", "flowing"), ("Q2", "খাঁটি মধু ৫০০ টাকা"), ("GQ4", "both")])
    confirm(client, view["id"], view["plan"]["revision"])
    requests = get_order_service()._provider.submitted
    assert [r.aspect_ratio for r in requests] == ["9:16"] * 3
    assert all(r.duration_seconds == 5 and r.resolution == "720p" for r in requests)
    assert all(r.image_storage_key and r.image_storage_key.startswith("uploads/") for r in requests)
    assert all(r.prompt.isascii() and "500" not in r.prompt for r in requests)
    assert "splashing" in requests[1].negative_prompt


def test_order_is_locked_after_confirmation(client):
    view = ready_order(client, SAREE)
    confirm(client, view["id"], view["plan"]["revision"])
    locked = client.post(f"/api/orders/{view['id']}/answers", json={"code": "GQ1", "value": "light"})
    assert locked.status_code == 409
    assert upload(client, view["id"]).status_code == 409
    assert client.put(f"/api/orders/{view['id']}/format", json={"format": "post"}).status_code == 409


def test_unsupported_video_provider_is_refused_at_startup(monkeypatch):
    from app.core.config import Settings
    from app.services.generations.providers import get_video_provider

    with pytest.raises(RuntimeError):
        get_video_provider(Settings(video_generation_provider="seedance"))


# --- Brand questions and feedback (after confirmation) -------------------------------------------------------------


def test_brand_questions_follow_confirmation_on_the_web(client):
    view = ready_order(client, SAREE)
    view = confirm(client, view["id"], view["plan"]["revision"]).json()
    assert view["step"]["question"]["code"] == "P1"

    view = answer(client, view["id"], "P1", "আম বাজার")
    assert view["step"]["question"]["code"] == "P1c"
    assert "আম বাজার" in view["step"]["question"]["text"]
    view = answer(client, view["id"], "P1c", "yes")
    assert view["step"]["question"]["code"] == "P2"
    assert view["step"]["question"]["kind"] == "upload"
    view = answer(client, view["id"], "P2", "no_logo")
    # No WhatsApp number is known for a web customer, so it is typed, not confirmed.
    assert view["step"]["question"]["code"] == "P3n"
    bad = client.post(f"/api/orders/{view['id']}/answers", json={"code": "P3n", "value": "12345"})
    assert bad.status_code == 422 and bad.json()["error_code"] == "INVALID_PHONE"
    view = answer(client, view["id"], "P3n", "+880 1712-345678")
    assert view["brand"] == {"shop_name": "আম বাজার", "phone": "01712345678", "has_logo": False}


def test_shop_name_read_back_can_be_corrected(client):
    view = ready_order(client, SAREE)
    confirm(client, view["id"], view["plan"]["revision"])
    answer(client, view["id"], "P1", "Am Bazr")
    view = answer(client, view["id"], "P1c", "fix")
    assert view["step"]["question"]["code"] == "P1"
    assert view["brand"]["shop_name"] is None


def test_known_whatsapp_number_is_confirmed_not_retyped(client):
    view = ready_order(client, SAREE, channel="whatsapp", known_phone="8801812345678")
    confirm(client, view["id"], view["plan"]["revision"])
    answer(client, view["id"], "P1", skip=True)
    view = answer(client, view["id"], "P2", "no_logo")
    assert view["step"]["question"]["code"] == "P3"
    assert "01812345678" in view["step"]["question"]["text"]
    view = answer(client, view["id"], "P3", "yes")
    assert view["brand"]["phone"] == "01812345678"


def test_logo_upload_answers_p2_and_is_refused_before_confirmation(client):
    view = ready_order(client, SAREE)
    early = upload(client, view["id"], purpose="logo")
    assert early.status_code == 409 and early.json()["error_code"] == "LOGO_NOT_REQUESTED"

    confirm(client, view["id"], view["plan"]["revision"])
    answer(client, view["id"], "P1", skip=True)
    view = upload(client, view["id"], _image_bytes("small"), purpose="logo").json()
    assert view["logo"]["usable"] is True  # logos skip the product-photo quality checks
    assert view["brand"]["has_logo"] is True
    assert view["step"]["question"]["code"] == "P3n"


def test_feedback_is_tied_to_the_order_and_generation(client):
    view = ready_order(client, SAREE)
    view = confirm(client, view["id"], view["plan"]["revision"]).json()
    generation_id = view["generation"]["id"]
    answer(client, view["id"], "P1", skip=True)
    answer(client, view["id"], "P2", "no_logo")
    view = answer(client, view["id"], "P3n", skip=True)
    assert view["step"]["question"]["code"] == "R1"
    view = answer(client, view["id"], "R1", "change")
    assert view["step"]["question"]["code"] == "R2"
    view = answer(client, view["id"], "R2", "2")
    assert view["step"]["kind"] == "done"
    assert view["feedback"] == {"rating": "change", "scene": "2", "generation_id": generation_id}
    order = stored(view["id"])
    assert order.feedback[0].plan_revision == order.plan.revision
    assert get_order_service().order_line(order).endswith("R1 change")


# --- Services (S1–S4 stay a separate route) ---------------------------------------------------------------------------


def test_service_is_never_classified_as_a_product(client):
    view = ready_order(client, [("Q1", "service")])
    assert view["step"]["question"]["code"] == "SQ1"
    route = questions.resolve_route(stored(view["id"]))
    assert route.kind == "service" and route.group is None


def test_person_at_work_plan_orders_shots_by_risk(client):
    flow = [("Q1", "service"), ("SQ1", "S3"), ("SQ2", "চুল আর দাড়ি"), ("SQ8", "with_face"), ("SQ3", "১০০ টাকা"), ("SQ4", "মিরপুর ১০")]
    view = ready_order(client, flow)
    plan = stored(view["id"]).plan
    assert plan.kind == "service" and plan.scenario == "S3"
    assert [s.template_id for s in plan.shots] == ["S3-A", "S3-B", "S3-C"]
    assert plan.shots[2].max_tries == 3
    assert "changing faces" in plan.shots[0].negative_terms

    work_only = ready_order(client, flow[:3] + [("SQ8", "work_only")] + flow[4:])
    assert template_ids(work_only["id"]) == ["S3-A", "S3-B"]
    assert work_only["plan"]["intro"] == "২টি দৃশ্য বানাব:"


def test_service_text_goes_to_post_production_not_the_prompt(client, monkeypatch):
    flow = [("Q1", "service"), ("SQ1", "S2"), ("SQ2", "গাড়ি রং করা"), ("SQ7", "yes"), ("SQ3", "৫০০০ টাকা"), ("SQ4", "উত্তরা")]
    view = ready_order(client, flow)
    order = stored(view["id"])
    assert shot_prompt(order.plan.shots[0]).isascii()
    record = get_order_service().operator_record(order)
    assert record["post_production"]["price_text"] == "৫০০০ টাকা"
    assert record["post_production"]["location_text"] == "উত্তরা"
    assert any("before" in flag for flag in order.plan.operator_flags)


def test_property_needs_one_photo_per_room(client):
    view = ready_order(
        client, [("Q1", "service"), ("SQ1", "S1"), ("SQ2", "ফ্ল্যাট ভাড়া"), ("SQ5", "2"), ("SQ6", "rent"), ("SQ3", "২০০০০"), ("SQ4", "ধানমন্ডি")]
    )
    assert view["step"]["kind"] == "photo"
    assert view["step"]["photo"] == {"reason": "more_photos", "required_count": 2, "have_count": 1}
    view = upload(client, view["id"], name="room2.png").json()
    assert view["step"]["kind"] == "plan"
    plan = stored(view["id"]).plan
    assert [s.template_id for s in plan.shots] == ["S1", "S1"]
    assert plan.shots[0].source_asset_id != plan.shots[1].source_asset_id


def test_poster_order_confirms_without_any_generation(client):
    view = ready_order(client, [("Q1", "service"), ("SQ1", "S4"), ("SQ2", "পার্লার"), ("SQ3", "তালিকায় আছে"), ("SQ4", "বনানী")])
    assert view["plan"]["shots"][0]["generates_video"] is False
    result = confirm(client, view["id"], view["plan"]["revision"]).json()
    assert result["status"] == "CONFIRMED"
    assert result["generation"] is None
    assert get_order_service()._provider.submitted == []


# --- Uploads ------------------------------------------------------------------------------------------------------------


def test_non_image_upload_is_rejected_whatever_the_client_claims(client):
    view = create(client)
    response = upload(client, view["id"], b"%PDF-1.4 not an image", name="photo.png")
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "UNSUPPORTED_IMAGE"
    assert "JPG" in body["message"]  # a localized sentence the UI can show
    assert client.get(f"/api/orders/{view['id']}").json()["photos"] == []


def test_unsupported_image_format_is_rejected(client):
    view = create(client)
    response = upload(client, view["id"], _image_bytes("good", fmt="BMP"), name="p.bmp")
    assert response.status_code == 422 and response.json()["error_code"] == "UNSUPPORTED_IMAGE"


def test_empty_and_oversized_uploads_are_rejected(client, monkeypatch):
    view = create(client)
    assert upload(client, view["id"], b"").json()["error_code"] == "EMPTY_FILE"

    monkeypatch.setenv("MAX_UPLOAD_MB", "0")
    from app.core.config import get_settings
    from app.services.orders.service import reset_order_service

    get_settings.cache_clear()
    reset_order_service()
    fresh = create(client)
    response = upload(client, fresh["id"])
    assert response.status_code == 413 and response.json()["error_code"] == "FILE_TOO_LARGE"


def test_too_many_pixels_is_rejected_before_decoding(client, monkeypatch):
    monkeypatch.setenv("MAX_IMAGE_PIXELS", "1000")
    from app.core.config import get_settings
    from app.services.orders.service import reset_order_service

    get_settings.cache_clear()
    reset_order_service()
    view = create(client)
    response = upload(client, view["id"])
    assert response.status_code == 422 and response.json()["error_code"] == "IMAGE_TOO_MANY_PIXELS"


def test_weak_photo_asks_once_then_accepts_the_sellers_choice(client):
    view = create(client)
    view = upload(client, view["id"], _image_bytes("blurry")).json()
    assert view["photos"][0]["status"] == "WARNING" and view["photos"][0]["usable"] is False
    question = view["step"]["question"]
    assert question["code"] == "PH_QUALITY" and question["kind"] == "upload"
    assert "ঝাপসা" in question["text"]

    view = answer(client, view["id"], "PH_QUALITY", "use_anyway")
    assert view["photos"][0]["usable"] is True
    assert view["step"]["question"]["code"] == "Q1"  # asked once, never again


def test_replacing_a_weak_photo_supersedes_it(client):
    view = create(client)
    upload(client, view["id"], _image_bytes("small"))
    view = upload(client, view["id"]).json()
    assert len(view["photos"]) == 1 and view["photos"][0]["status"] == "VALID"


def test_uploaded_photo_is_stored_on_the_server_and_served_back(client):
    view = create(client)
    view = upload(client, view["id"]).json()
    photo = view["photos"][0]
    assert not photo["content_path"].startswith("blob:")
    served = client.get(photo["content_path"])
    assert served.status_code == 200 and served.content == GOOD
    assert served.headers["content-type"] == "image/png"
    assert view["environment"]["storage"] == "local_disk_dev"


# --- Persistence and missing orders ---------------------------------------------------------------------------------------


def test_unknown_order_is_a_404_not_a_new_order(client):
    response = client.get("/api/orders/5b0f0f0e-0000-4000-8000-000000000000")
    assert response.status_code == 404 and response.json()["error_code"] == "ORDER_NOT_FOUND"


def test_file_store_survives_a_service_restart(client, monkeypatch):
    monkeypatch.setenv("ORDER_STORE", "file")
    from app.core.config import get_settings
    from app.services.orders.service import reset_order_service

    get_settings.cache_clear()
    reset_order_service()
    view = ready_order(client, SAREE)
    confirmed = confirm(client, view["id"], view["plan"]["revision"]).json()

    reset_order_service()  # a new process would start exactly like this
    again = client.get(f"/api/orders/{view['id']}").json()
    assert again["number"] == view["number"]
    assert again["generation"]["id"] == confirmed["generation"]["id"]
    assert again["status"] == "GENERATED"
    assert client.get(again["photos"][0]["content_path"]).status_code == 200


def test_order_numbers_are_sequential_and_ids_are_not_guessable(client):
    first, second = create(client), create(client)
    assert first["number"] == "ORD-000001" and second["number"] == "ORD-000002"
    assert len(first["id"]) == 36 and first["id"] != second["id"]


def test_options_endpoint_describes_formats_and_what_is_simulated(client):
    options = client.get("/api/orders/options", params={"locale": "en"}).json()
    assert [o["id"] for o in options["format"]["options"]] == ["reels", "post", "both"]
    assert options["format"]["options"][0]["aspect_ratio"] == "9:16"
    assert options["environment"]["simulated_generation"] is True
    assert options["max_upload_mb"] == 10
