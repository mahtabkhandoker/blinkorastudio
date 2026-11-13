"""Builds the structured creative plan for an order (spec Part 2).

The plan stores parts — template IDs, slots, motion settings, avoid
terms — never a finished sentence. `build_generation_requests` turns those
parts into provider requests only when generation is actually submitted.

The group is chosen per shot, not per ad (spec §2.4): a sealed honey jar
is shot with the Rigid templates even though the order's group is Flowing.
"""

from __future__ import annotations

import hashlib
import json
import re

from app.models.orders import AspectRatio, CreativePlan, Order, PlanShotView, PlanView, Shot, SlotValue
from app.services.orders import texts
from app.services.orders.questions import Route, resolve_route, rooms_required, to_bn_digits
from app.services.orders.templates import (
    BASE_NEGATIVE,
    DRY_NEGATIVE,
    GENERIC_PRODUCT,
    GQ1_MOTION_LEVEL,
    GQ3A_SURFACE,
    GROUP_DEFAULTS,
    GROUP_NEGATIVE,
    MATERIAL_DEFAULTS,
    SERVICE_DEFAULTS,
    TEMPLATES,
    assemble_prompt,
    template_slots,
)

_NON_PROMPT_CHARS = re.compile(r"[^A-Za-z \-]")
_MAX_PRODUCT_WORDS = 8
S3_FACE_MAX_TRIES = 3


def _aspect_for(format_choice: str) -> AspectRatio:
    # "both" generates 9:16 and crops the square in editing (spec F1, §3.4).
    return "1:1" if format_choice == "post" else "9:16"


def _deliverables(format_choice: str) -> list[str]:
    if format_choice == "both":
        return ["9:16", "1:1 (cropped from 9:16 in editing)"]
    return ["1:1"] if format_choice == "post" else ["9:16"]


def product_slot(order: Order, route: Route) -> tuple[SlotValue, str | None]:
    """The English {{PRODUCT}} value, plus an operator flag when the
    seller's own words could not be used.

    Bengali text must never reach the video model, and P0 has no text
    model to translate it, so a Bengali description falls back to a
    neutral noun and is flagged for the operator.
    """
    description = (order.answer("Q2") or "").strip()
    key = route.category or "other"
    if key == "food":
        key = f"food:{route.group}"
    generic = SlotValue(value=GENERIC_PRODUCT.get(key, "product"), source="generic_default")

    if not description:
        return generic, None
    if not description.isascii():
        return generic, "PRODUCT slot uses a generic noun: the description is in Bengali and needs an English wording"
    cleaned = " ".join(_NON_PROMPT_CHARS.sub(" ", description).split()[:_MAX_PRODUCT_WORDS]).lower()
    if not cleaned:
        return generic, None
    return (
        SlotValue(value=cleaned, source="q2"),
        "PRODUCT slot was taken from the typed description as-is: check it reads as English",
    )


def _negative_terms(template_group: str, dry: bool) -> list[str]:
    terms = list(BASE_NEGATIVE) + list(GROUP_NEGATIVE.get(template_group, ()))
    if dry:
        terms += list(DRY_NEGATIVE)
    return terms


def _product_shot(
    index: int,
    template_id: str,
    values: dict[str, SlotValue],
    *,
    aspect: AspectRatio,
    clip_seconds: int,
    resolution: str,
    dry: bool,
    readable_label: bool = True,
    framing: str = "standard",
    asset_id: str | None,
) -> Shot:
    template = TEMPLATES[template_id]
    needed = template_slots(template_id) | ({"ACCENT"} if "ACCENT" in template.text else set())
    return Shot(
        index=index,
        role=template.role,
        template_id=template_id,
        template_group=template.group,
        framing=framing,  # type: ignore[arg-type]
        readable_label=readable_label,
        crop="standard" if readable_label else "tighter",
        slots={name: values[name] for name in sorted(needed)},
        subject_motion=template.subject_motion,
        camera_move=template.camera_move,
        aspect_ratio=aspect,
        duration_seconds=clip_seconds,
        resolution=resolution,
        negative_terms=_negative_terms(template.group, dry),
        source_asset_id=asset_id,
    )


def _build_product(order: Order, route: Route, revision: int, clip_seconds: int, resolution: str) -> CreativePlan:
    group = route.group
    assert group is not None
    aspect = _aspect_for(order.format)
    flags: list[str] = []

    defaults = GROUP_DEFAULTS[group]
    values: dict[str, SlotValue] = {
        name: SlotValue(value=value, source="group_default") for name, value in defaults.items()
    }
    values["MATERIAL"] = SlotValue(value=MATERIAL_DEFAULTS[group], source="group_default")
    values["PRODUCT"], product_flag = product_slot(order, route)
    if product_flag:
        flags.append(product_flag)

    group_answers = {c: a.value for c, a in order.answers.items() if c.startswith("GQ") or c == "PH_GLARE"}
    variant: str | None = None
    dry = False
    readable = True
    template_ids: list[str]
    framings = ["standard", "standard", "standard"]

    if group == "G1":
        level = GQ1_MOTION_LEVEL[order.answer("GQ1") or "medium"]
        values["MOTION_LEVEL"] = SlotValue(value=level, source="GQ1")
        template_ids = ["G1-A", "G1-B", "G1-C"]
    elif group == "G2":
        readable = order.answer("GQ2") != "blurry"
        template_ids = ["G2-A", "G2-B", "G2-C"]
    elif group == "G3":
        values["SURFACE"] = SlotValue(value=GQ3A_SURFACE[order.answer("GQ3a") or "cloth"], source="GQ3a")
        template_ids = ["G3-A", "G3-B", "G3-C"]
        if order.answer("PH_GLARE") == "use_anyway":
            flags.append("Seller reported glare and kept the photo: expect warped reflections")
    elif group == "G4":
        variant = order.answer("GQ4") or "both"
        if variant == "pour":
            template_ids = ["G4-B", "G4-B", "G4-C"]
            framings[0] = "wider"
        elif variant == "closed":
            template_ids = ["G2-A", "G2-B", "G2-C"]
            # The Rigid close-up looks at the label, not at a liquid surface.
            values["DETAIL"] = SlotValue(value=GROUP_DEFAULTS["G2"]["DETAIL"], source="group_default")
        else:
            template_ids = ["G4-A", "G4-B", "G4-C"]
    else:  # G5
        variant = route.preset_variant or order.answer("GQ5") or "wet"
        dry = variant == "dry"
        if dry:
            values["ACCENT"] = SlotValue(value="none", source="GQ5")
            template_ids = ["G5-A-DRY", "G5-B", "G5-C"]
        else:
            template_ids = ["G5-A", "G5-B", "G5-C"]

    photos = order.product_assets()
    asset_id = photos[-1].id if photos else None
    shots = [
        _product_shot(
            i + 1,
            template_id,
            values,
            aspect=aspect,
            clip_seconds=clip_seconds,
            resolution=resolution,
            dry=dry,
            readable_label=readable if template_id == "G2-A" else True,
            framing=framings[i],
            asset_id=asset_id,
        )
        for i, template_id in enumerate(template_ids)
    ]
    return CreativePlan(
        revision=revision,
        kind="product",
        group=group,
        variant=variant,
        category=route.category or "other",
        product_description=order.answer("Q2") or "",
        group_answers=group_answers,
        format=order.format,
        aspect_ratio=aspect,
        deliverables=_deliverables(order.format),
        shots=shots,
        operator_flags=flags,
    )


def _service_shot(
    index: int,
    template_id: str,
    *,
    aspect: AspectRatio,
    clip_seconds: int,
    resolution: str,
    asset_id: str | None,
    max_tries: int | None = None,
) -> Shot:
    template = TEMPLATES[template_id]
    generates = bool(template.text)
    return Shot(
        index=index,
        role=template.role,
        template_id=template_id,
        template_group=template.group,
        slots={
            name: SlotValue(value=SERVICE_DEFAULTS[name], source="service_default")
            for name in sorted(template_slots(template_id))
        },
        subject_motion=template.subject_motion,
        camera_move=template.camera_move,
        aspect_ratio=aspect,
        duration_seconds=clip_seconds,
        resolution=resolution,
        negative_terms=_negative_terms(template.group, dry=False) if generates else [],
        generates_video=generates,
        max_tries=max_tries,
        source_asset_id=asset_id,
    )


def _build_service(order: Order, route: Route, revision: int, clip_seconds: int, resolution: str) -> CreativePlan:
    scenario = route.scenario
    assert scenario is not None
    aspect = _aspect_for(order.format)
    photos = order.product_assets()
    last_asset = photos[-1].id if photos else None
    common = {"aspect": aspect, "clip_seconds": clip_seconds, "resolution": resolution}
    flags: list[str] = []
    shots: list[Shot]

    if scenario == "S1":
        rooms = rooms_required(order)
        shots = [
            _service_shot(i + 1, "S1", asset_id=photos[i].id if i < len(photos) else None, **common)
            for i in range(rooms)
        ]
        if order.answer("SQ5") == "3plus":
            flags.append("Seller asked for more than 3 rooms: P0 plans 3, agree the rest by hand")
    elif scenario == "S2":
        shots = [_service_shot(1, "S2", asset_id=last_asset, **common)]
        if order.answer("SQ7") == "yes":
            flags.append("Seller has a 'before' photo: collect it and cut the before/after in editing")
    elif scenario == "S3":
        # Generated in order of risk: tools, then hands, then the full scene.
        shots = [
            _service_shot(1, "S3-A", asset_id=last_asset, **common),
            _service_shot(2, "S3-B", asset_id=last_asset, **common),
        ]
        if order.answer("SQ8") == "with_face":
            shots.append(_service_shot(3, "S3-C", asset_id=last_asset, max_tries=S3_FACE_MAX_TRIES, **common))
            flags.append("S3-C face shot: at most 3 tries, then a still push-in made in editing")
    else:  # S4
        shots = [_service_shot(1, "S4", asset_id=last_asset, **common)]
        flags.append("S4 poster: no generation; slow zoom and pan in editing")

    service_answers = {c: a.value for c, a in order.answers.items() if c.startswith("SQ")}
    return CreativePlan(
        revision=revision,
        kind="service",
        scenario=scenario,
        category="service",
        product_description=order.answer("SQ2") or "",
        group_answers=service_answers,
        format=order.format,
        aspect_ratio=aspect,
        deliverables=_deliverables(order.format),
        shots=shots,
        operator_flags=flags,
    )


def _fingerprint(plan: CreativePlan) -> str:
    payload = plan.model_dump(mode="json", exclude={"revision", "fingerprint"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def build_plan(order: Order, *, clip_seconds: int = 5, resolution: str = "720p") -> CreativePlan:
    """Builds the plan from the order's current answers. The revision only
    moves forward when the plan's content actually changed."""
    route = resolve_route(order)
    if route.kind == "service":
        plan = _build_service(order, route, 0, clip_seconds, resolution)
    else:
        plan = _build_product(order, route, 0, clip_seconds, resolution)

    for shot in plan.shots:
        shot.change_note = order.change_notes.get(shot.index)
    if order.change_notes:
        plan.operator_flags.append(
            "Customer change requests are attached to shots: apply them by hand before generating"
        )

    plan.fingerprint = _fingerprint(plan)
    if order.plan is not None and order.plan.fingerprint == plan.fingerprint:
        plan.revision = order.plan.revision
    else:
        plan.revision = order.plan_revision_counter + 1
    return plan


# --- Internal: generation payload ------------------------------------------------------------


def shot_prompt(shot: Shot) -> str:
    return assemble_prompt(
        shot.template_id,
        {name: slot.value for name, slot in shot.slots.items()},
        readable_label=shot.readable_label,
        framing=shot.framing,
    )


def shot_negative_prompt(shot: Shot) -> str:
    return ", ".join(shot.negative_terms)


# --- Customer view -----------------------------------------------------------------------------


def _item_words(order: Order, shot: Shot, locale: str) -> tuple[str, str]:
    """(noun, genitive) used in the Bengali/English shot lines."""
    category = order.answer("Q1")
    if shot.template_group == "G2":
        if resolve_route(order).group == "G4":
            return ("কৌটা", "কৌটার") if locale == "bn" else ("container", "container")
        if category == "cosmetics":
            return ("বোতল", "বোতলের") if locale == "bn" else ("bottle", "bottle")
        return ("পণ্য", "পণ্যের") if locale == "bn" else ("product", "product")
    if category == "jewellery_watches":
        return ("গয়না", "গয়নার") if locale == "bn" else ("jewellery", "jewellery")
    return ("পণ্য", "পণ্যের") if locale == "bn" else ("product", "product")


def describe_shot(order: Order, shot: Shot, locale: str) -> str:
    key = shot.template_id
    if shot.framing == "wider" and f"{key}:wider" in texts.SHOT_LINES:
        key = f"{key}:wider"
    line = texts.pick(texts.SHOT_LINES[key], locale)
    noun, genitive = _item_words(order, shot, locale)
    detail = texts.pick(texts.DETAIL_LABEL.get(shot.template_group, ("", "")), locale)
    number = to_bn_digits(str(shot.index)) if locale == "bn" else str(shot.index)
    return line.format(item=noun, item_gen=genitive, detail=detail, n=number)


def plan_view(order: Order, locale: str) -> PlanView | None:
    plan = order.plan
    if plan is None:
        return None
    generated = len(plan.generated_shots)
    count = to_bn_digits(str(generated)) if locale == "bn" else str(generated)
    intro = (
        texts.pick(texts.PLAN_INTRO, locale).format(n=count)
        if generated
        else texts.pick(texts.PLAN_INTRO_NO_GENERATION, locale)
    )
    prefix = texts.pick(texts.CHANGE_NOTE_PREFIX, locale)
    return PlanView(
        revision=plan.revision,
        intro=intro,
        shots=[
            PlanShotView(
                index=shot.index,
                description=describe_shot(order, shot, locale),
                note=f"{prefix}{shot.change_note}" if shot.change_note else None,
                generates_video=shot.generates_video,
            )
            for shot in plan.shots
        ],
        closing=texts.pick(texts.PLAN_CLOSING, locale),
        post_production_note=texts.pick(texts.POST_PRODUCTION_NOTE, locale),
        confirm_label=texts.pick(texts.CONFIRM_LABEL, locale),
        change_label=texts.pick(texts.CHANGE_LABEL, locale),
        confirmed=order.status not in ("DRAFT", "PLAN_READY"),
    )
