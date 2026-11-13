"""Deterministic question sequencing for an order.

Everything here is a pure function of the order record: which group or
scenario the answers route to, which questions apply, which one is next,
and how an answer is validated and applied. No LLM is involved in P0.

Rules taken from the spec (Part 1):
* one question at a time, and only the relevant ones;
* every question has a default, so skipping still produces an ad;
* the group question is asked from P0 because it prevents the most
  expensive retries; Q3–Q6 are not asked in P0 (group defaults are used).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.orders import (
    Answer,
    Feedback,
    Order,
    OptionView,
    ProductGroup,
    QuestionView,
    ServiceScenario,
    StoredAsset,
)
from app.services.orders.catalog import (
    BRAND_CODES,
    CATEGORY_TO_GROUP,
    COLLECTION_CODES,
    FOOD_SUBTYPE_TO_GROUP,
    GROUP_QUESTIONS,
    QUESTIONS,
    SCENARIO_QUESTIONS,
    Option,
    QuestionDef,
)
from app.services.orders.errors import OrderError

PRE_CONFIRM_STATUSES = ("DRAFT", "PLAN_READY")
MAX_ROOMS = 3
_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_TO_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
_BD_MOBILE = re.compile(r"^01[3-9]\d{8}$")

# Answers that change which shots exist; notes attached to shots are dropped.
_SHOT_SET_CODES = {"Q1", "Q1a", "SQ1", "GQ4", "GQ5", "SQ5", "SQ8"}


# --- Routing ------------------------------------------------------------------------


@dataclass(frozen=True)
class Route:
    kind: str | None  # "product" | "service" | None while still unknown
    category: str | None = None
    group: ProductGroup | None = None
    preset_variant: str | None = None
    scenario: ServiceScenario | None = None


def resolve_route(order: Order) -> Route:
    category = order.answer("Q1")
    if category is None:
        return Route(kind=None)
    if category == "service":
        scenario = order.answer("SQ1")
        return Route(kind="service", category=category, scenario=scenario)  # type: ignore[arg-type]
    if category == "food":
        subtype = order.answer("Q1a")
        if subtype is None:
            return Route(kind="product", category=category)
        group, variant = FOOD_SUBTYPE_TO_GROUP[subtype]
        return Route(kind="product", category=category, group=group, preset_variant=variant)
    return Route(kind="product", category=category, group=CATEGORY_TO_GROUP[category])


def rooms_required(order: Order) -> int:
    """S1 needs one photo per room (capped at MAX_ROOMS in P0)."""
    if resolve_route(order).scenario != "S1":
        return 1
    answer = order.answer("SQ5")
    if answer is None:
        return 1
    return MAX_ROOMS if answer == "3plus" else int(answer)


def collection_codes(order: Order) -> list[str]:
    """Questions that apply before the plan, in asking order. Stops early
    where a routing answer is still missing, because what follows depends
    on it."""
    codes = ["Q1"]
    route = resolve_route(order)
    if route.kind is None:
        return codes

    if route.kind == "service":
        codes.append("SQ1")
        if route.scenario is None:
            return codes
        codes.append("SQ2")
        codes.extend(SCENARIO_QUESTIONS[route.scenario])
        codes.extend(["SQ3", "SQ4"])
        return codes

    if route.category == "food":
        codes.append("Q1a")
        if route.group is None:
            return codes
    codes.append("Q2")
    assert route.group is not None
    for code in GROUP_QUESTIONS[route.group]:
        if code == "GQ5" and route.preset_variant == "dry":
            continue  # already answered by the food subtype; never ask twice
        codes.append(code)
    if order.answer("GQ3b") == "yes":
        codes.append("PH_GLARE")
    return codes


def brand_codes(order: Order) -> list[str]:
    codes = ["P1"]
    if order.answer("P1"):
        codes.append("P1c")
    codes.append("P2")
    if order.known_phone:
        codes.append("P3")
        if order.answer("P3") == "other":
            codes.append("P3n")
    else:
        codes.append("P3n")
    return codes


def feedback_codes(order: Order) -> list[str]:
    if order.status != "GENERATED":
        return []
    codes = ["R1"]
    if order.answer("R1") == "change":
        codes.append("R2")
    return codes


# --- Next step ------------------------------------------------------------------------


@dataclass(frozen=True)
class Step:
    kind: str  # photo | question | plan | generation | done
    code: str | None = None
    photo_reason: str | None = None


def pending_warning_asset(order: Order) -> StoredAsset | None:
    for asset in order.product_assets(usable_only=False):
        if asset.status == "WARNING" and not asset.accepted_with_warning:
            return asset
    return None


def next_step(order: Order) -> Step:
    if order.status in PRE_CONFIRM_STATUSES:
        if pending_warning_asset(order) is not None:
            return Step("question", code="PH_QUALITY")
        if not order.product_assets():
            return Step("photo", photo_reason="initial")
        for code in collection_codes(order):
            if code not in order.answers:
                return Step("question", code=code)
        if len(order.product_assets()) < rooms_required(order):
            return Step("photo", photo_reason="more_photos")
        if order.revision_flow == "C2":
            return Step("question", code="C2")
        if order.revision_flow and order.revision_flow.startswith("C2N:"):
            return Step("question", code="C2N")
        return Step("plan")

    for code in brand_codes(order):
        if code not in order.answers:
            return Step("question", code=code)
    if order.generation is not None and order.generation.status in ("QUEUED", "RUNNING"):
        return Step("generation")
    for code in feedback_codes(order):
        if code not in order.answers:
            return Step("question", code=code)
    return Step("done")


def answers_complete(order: Order) -> bool:
    """True when the plan can be built (a pending C2 question does not
    make the answers incomplete)."""
    if order.status not in PRE_CONFIRM_STATUSES:
        return True
    step = next_step(order)
    return step.kind == "plan" or step.code in ("C2", "C2N")


# --- Views ----------------------------------------------------------------------------


def to_bn_digits(text: str) -> str:
    return text.translate(_TO_BN_DIGITS)


def item_noun(order: Order, locale: str) -> str:
    category = order.answer("Q1")
    if category == "jewellery_watches":
        return "গয়না" if locale == "bn" else "jewellery"
    return "পণ্য" if locale == "bn" else "product"


def _c2_options(order: Order) -> tuple[Option, ...]:
    shots = order.plan.shots if order.plan else []
    shot_options = tuple(
        Option(f"shot_{s.index}", to_bn_digits(f"দৃশ্য {s.index}"), f"Scene {s.index}") for s in shots
    )
    return shot_options + QUESTIONS["C2"].options


def options_for(order: Order, code: str) -> tuple[Option, ...]:
    if code == "C2":
        return _c2_options(order)
    return QUESTIONS[code].options


def _text_context(order: Order, code: str, locale: str) -> dict[str, str]:
    from app.services.orders.texts import asset_warning_text  # local: avoids an import cycle

    context = {"item": item_noun(order, locale), "name": "", "phone": "", "n": "", "warning": ""}
    if code == "P1c":
        context["name"] = order.answer("P1") or ""
    if code == "P3":
        context["phone"] = order.known_phone or ""
    if code == "C2N" and order.revision_flow:
        number = order.revision_flow.split(":", 1)[-1]
        context["n"] = to_bn_digits(number) if locale == "bn" else number
    if code == "PH_QUALITY":
        asset = pending_warning_asset(order)
        context["warning"] = asset_warning_text(asset.warning_code if asset else None, locale)
    return context


def question_view(order: Order, code: str, locale: str) -> QuestionView:
    qdef = QUESTIONS[code]
    text = (qdef.bn if locale == "bn" else qdef.en).format(**_text_context(order, code, locale))
    options = [
        OptionView(id=o.id, label=o.bn if locale == "bn" else o.en, default=o.default)
        for o in options_for(order, code)
    ]
    skippable = qdef.skip_value is not None if qdef.kind == "type" else False
    return QuestionView(
        code=code,
        kind=qdef.kind,
        text=text.strip(),
        options=options,
        placeholder=qdef.placeholder_bn if locale == "bn" else qdef.placeholder_en,
        input_mode="tel" if qdef.input_mode == "tel" else "text",
        max_length=qdef.max_length,
        skippable=skippable,
        skip_label=(qdef.skip_bn if locale == "bn" else qdef.skip_en) if skippable else None,
        upload_purpose=qdef.upload_purpose,
        upload_label=qdef.upload_bn if locale == "bn" else qdef.upload_en,
    )


def display_value(order: Order, code: str, value: str, locale: str) -> str:
    qdef = QUESTIONS[code]
    if qdef.kind == "type":
        if value:
            return value
        return (qdef.skip_bn if locale == "bn" else qdef.skip_en) or "—"
    for option in options_for(order, code):
        if option.id == value:
            return option.bn if locale == "bn" else option.en
    if value == "new_photo":
        return "নতুন ছবি দিয়েছি" if locale == "bn" else "Sent a new photo"
    if value == "uploaded":
        return "লোগো দিয়েছি" if locale == "bn" else "Logo sent"
    return value


def editable_codes(order: Order) -> set[str]:
    """Answers the customer may still change."""
    if order.status in PRE_CONFIRM_STATUSES:
        return {c for c in order.answers if c in COLLECTION_CODES and not c.startswith("PH_")}
    return {c for c in order.answers if c in BRAND_CODES and c != "P1c"}


def answerable_codes(order: Order) -> set[str]:
    allowed = editable_codes(order)
    step = next_step(order)
    if step.kind == "question" and step.code:
        allowed.add(step.code)
    return allowed


# --- Applying answers -------------------------------------------------------------------


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"[\s\-()]", "", raw.translate(_BN_DIGITS))
    if digits.startswith("+880"):
        digits = "0" + digits[4:]
    elif digits.startswith("880"):
        digits = "0" + digits[3:]
    if not _BD_MOBILE.match(digits):
        raise OrderError(
            "INVALID_PHONE",
            "Enter a Bangladeshi mobile number, for example 01712345678.",
            status_code=422,
        )
    return digits


def _resolve_value(order: Order, qdef: QuestionDef, value: str | None, skip: bool) -> tuple[str, str]:
    """Returns (value, source)."""
    if qdef.kind == "type":
        if skip:
            if qdef.skip_value is None:
                raise OrderError("ANSWER_REQUIRED", f"{qdef.code} cannot be skipped.", 422)
            return qdef.skip_value, "default"
        text = " ".join((value or "").split())
        if not text:
            raise OrderError("ANSWER_REQUIRED", "Please type an answer.", 422)
        if qdef.max_length and len(text) > qdef.max_length:
            raise OrderError("ANSWER_TOO_LONG", f"Keep it under {qdef.max_length} characters.", 422)
        if qdef.input_mode == "tel":
            text = normalize_phone(text)
        return text, "customer"

    options = options_for(order, qdef.code)
    if skip:
        default = next((o for o in options if o.default), None)
        if default is None:
            raise OrderError("ANSWER_REQUIRED", f"{qdef.code} has no default; choose an option.", 422)
        return default.id, "default"
    if value is None or not any(o.id == value for o in options):
        raise OrderError("INVALID_OPTION", f"'{value}' is not an option for {qdef.code}.", 422)
    return value, "customer"


def _drop(order: Order, *codes: str) -> None:
    for code in codes:
        order.answers.pop(code, None)


def _drop_prefix(order: Order, *prefixes: str) -> None:
    for code in [c for c in order.answers if c.startswith(prefixes)]:
        order.answers.pop(code)


def apply_answer(order: Order, code: str, value: str | None, skip: bool = False) -> None:
    qdef = QUESTIONS.get(code)
    if qdef is None:
        raise OrderError("UNKNOWN_QUESTION", f"Unknown question code '{code}'.", 404)
    if code not in answerable_codes(order):
        raise OrderError(
            "QUESTION_NOT_APPLICABLE",
            f"{code} cannot be answered at this point in the order.",
            409,
        )

    resolved, source = _resolve_value(order, qdef, value, skip)
    previous = order.answer(code)

    # Flow questions are actions, not stored answers.
    if code == "C2":
        if resolved == "nothing":
            order.revision_flow = None
        elif resolved == "product_type":
            _drop(order, "Q1", "Q1a", "PH_GLARE")
            _drop_prefix(order, "GQ", "SQ")
            order.change_notes = {}
            order.revision_flow = None
        else:
            order.revision_flow = f"C2N:{resolved.split('_', 1)[1]}"
        order.log("plan_change_choice", choice=resolved)
        return
    if code == "C2N":
        assert order.revision_flow is not None
        shot_index = int(order.revision_flow.split(":", 1)[1])
        order.change_notes[shot_index] = resolved
        order.revision_flow = None
        order.log("plan_change_note", shot=shot_index, note=resolved)
        return

    if code == "PH_QUALITY":
        asset = pending_warning_asset(order)
        if asset is not None:
            asset.accepted_with_warning = True
            order.log("photo_accepted_with_warning", asset_id=asset.id, warning=asset.warning_code)
        return

    if code == "P1c" and resolved == "fix":
        _drop(order, "P1", "P1c")
        return

    order.answers[code] = Answer(code=code, value=resolved, source=source)  # type: ignore[arg-type]
    order.log("answer", code=code, value=resolved, source=source)

    if resolved != previous:
        if code == "Q1":
            _drop(order, "Q1a", "PH_GLARE")
            _drop_prefix(order, "GQ", "SQ")
        elif code == "Q1a":
            _drop(order, "PH_GLARE")
            _drop_prefix(order, "GQ")
        elif code == "SQ1":
            _drop(order, "SQ5", "SQ6", "SQ7", "SQ8")
        elif code == "GQ3b":
            _drop(order, "PH_GLARE")
        elif code == "P1":
            _drop(order, "P1c")
        elif code == "P3" and resolved == "yes":
            _drop(order, "P3n")
        if code in _SHOT_SET_CODES:
            order.change_notes = {}

    if code == "R1":
        order.feedback.append(
            Feedback(
                rating=resolved,
                generation_id=order.generation.id if order.generation else None,
                plan_revision=order.plan.revision if order.plan else None,
            )
        )
        if resolved != "change":
            _drop(order, "R2")
    elif code == "R2" and order.feedback:
        order.feedback[-1].scene = resolved


def on_product_photo_added(order: Order, asset: StoredAsset) -> None:
    """Bookkeeping when a new product photo is stored. For most orders a
    new photo replaces the old one; S1 keeps one photo per room."""
    for existing in order.product_assets(usable_only=False):
        if existing.status == "WARNING" and not existing.accepted_with_warning:
            existing.superseded = True
    current = order.product_assets(usable_only=False)
    if resolve_route(order).scenario == "S1" and "SQ5" in order.answers:
        if len(current) >= rooms_required(order):
            current[-1].superseded = True
    else:
        for existing in current:
            existing.superseded = True
    order.assets.append(asset)
    if order.answer("GQ3b") == "yes" and "PH_GLARE" not in order.answers:
        order.answers["PH_GLARE"] = Answer(code="PH_GLARE", value="new_photo")


def brand_phone(order: Order) -> str | None:
    if order.known_phone and order.answer("P3") == "yes":
        return order.known_phone
    return order.answer("P3n") or None
