"""Prompt templates, slot defaults and avoid lists (spec Part 2).

Templates are stored as parts. The sentence is only built by
`assemble_prompt` at generation time, so a model change means editing one
assembler, not every template (spec §2.1 rule 6).

Template syntax:
* `{{SLOT}}`             — replaced with the slot value.
* `[[FLAG|text]]`        — optional segment, kept only when FLAG is on.
  Flags: ACCENT (the accent slot is not "none"), READABLE (the label may
  be promised as readable).

Nothing in a template or slot may carry shop names, prices, phone numbers
or Bengali text: those belong to post-production overlays.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Template:
    id: str
    group: str  # G1..G5 or S1..S4
    role: str
    text: str
    subject_motion: str
    camera_move: str
    wider_opening: tuple[str, str] | None = None  # (find, replace) for framing="wider"


_TEMPLATES: tuple[Template, ...] = (
    # G1 · Soft
    Template(
        "G1-A", "G1", "main",
        "The {{PRODUCT}} in the image stays centred, unchanged and in sharp focus. A breeze moves "
        "{{MOTION_LEVEL}} through the {{MATERIAL}}, making the fabric ripple and settle. The camera "
        "pushes in slowly from a medium shot. {{LIGHT}} sweeps across the surface, and {{DETAIL}} "
        "catches the light as it moves. {{MOOD}} pace. Shallow depth of field, natural colour, no cuts.",
        "fabric ripples and settles", "slow push-in from a medium shot",
    ),
    Template(
        "G1-B", "G1", "closeup",
        "Extreme close-up on {{DETAIL}} of the {{PRODUCT}}. The garment itself does not move or "
        "change. The camera glides slowly from right to left across the surface while soft light "
        "travels over the {{MATERIAL}}, revealing weave and thread texture. {{LIGHT}}. Slow, "
        "deliberate pace. Macro lens look, fine texture, no cuts.",
        "none (garment locked)", "slow right-to-left glide",
    ),
    Template(
        "G1-C", "G1", "wide",
        "The {{PRODUCT}} hangs still against {{SETTING}}, slightly left of frame with empty space "
        "on the right. Only the lower hem sways very slightly. The camera slowly pulls back to a "
        "wide shot. {{LIGHT}} with soft falling shadows. {{MOOD}} pace. Clean commercial product "
        "look, no cuts.",
        "lower hem sways very slightly", "slow pull-back to wide",
    ),
    # G2 · Rigid
    Template(
        "G2-A", "G2", "main",
        "The {{PRODUCT}} stays standing upright on {{SURFACE}}, label unchanged[[READABLE| and fully "
        "readable]], shape fixed. It rotates very slowly by a few degrees[[ACCENT| while {{ACCENT}} "
        "drifts past behind it]]. The camera orbits gently around it. {{LIGHT}} creates a soft "
        "highlight running down one side. {{MOOD}} pace. Clean commercial product cinematography, "
        "no cuts.",
        "very slow rotation by a few degrees", "gentle orbit",
    ),
    Template(
        "G2-B", "G2", "closeup",
        "Close-up on {{DETAIL}} of the {{PRODUCT}}. The product does not move; its label and shape "
        "stay exactly as they are. The camera drifts slowly downward across the surface while light "
        "travels over it. {{LIGHT}}. Slow pace. Macro lens look, high detail, no cuts.",
        "none (product locked)", "slow downward drift",
    ),
    Template(
        "G2-C", "G2", "wide",
        "The {{PRODUCT}} sits on {{SURFACE}} in {{SETTING}}, centred and unchanged, with empty space "
        "above it. Light gradually brightens across the scene[[ACCENT|; {{ACCENT}} moves faintly in "
        "the air]]. The camera slowly tilts up from the base to the top. {{MOOD}} pace. Warm clean "
        "lifestyle look, no cuts.",
        "none (light brightens)", "slow tilt up",
    ),
    # G3 · Reflective
    Template(
        "G3-A", "G3", "main",
        "The {{PRODUCT}} stays completely still on {{SURFACE}}, every edge and link unchanged and in "
        "sharp focus. Nothing moves except a soft highlight travelling slowly across the "
        "{{MATERIAL}}. The camera orbits by only a few degrees. {{LIGHT}}, controlled reflections, "
        "uncluttered surroundings. {{MOOD}} pace. Macro product look, no cuts.",
        "none (only a highlight travels)", "orbit of a few degrees",
    ),
    Template(
        "G3-B", "G3", "closeup",
        "Extreme close-up on {{DETAIL}}. The product is locked in place and does not deform or "
        "change shape. A narrow band of light moves slowly across the surface, revealing its "
        "finish. The camera holds almost still. Soft directional light, no harsh glare. Slow pace. "
        "Macro lens, shallow depth of field, no cuts.",
        "none (a band of light moves)", "almost still",
    ),
    Template(
        "G3-C", "G3", "wide",
        "The {{PRODUCT}} rests on {{SURFACE}} against {{SETTING}}, still and unchanged, placed to "
        "one side with empty space beside it. The camera pulls back slowly while the highlight "
        "settles across the surface. {{LIGHT}}. {{MOOD}} pace. Clean jewellery photography look, "
        "no cuts.",
        "none (highlight settles)", "slow pull-back",
    ),
    # G4 · Flowing
    Template(
        "G4-A", "G4", "main",
        "The {{PRODUCT}} stays centred on {{SURFACE}}, container shape and label unchanged. The "
        "camera orbits slowly around it while {{LIGHT}} produces a soft glossy highlight along the "
        "glass. [[ACCENT|{{ACCENT}} drifts faintly behind. ]]{{MOOD}} pace. Rich colour, shallow "
        "depth of field, no cuts.",
        "none (sealed container)", "slow orbit",
    ),
    Template(
        "G4-B", "G4", "closeup",
        "Extreme close-up of {{MATERIAL}} in slow motion: a thick stream flows and pools, light "
        "catching the surface as it moves. The {{PRODUCT}} stays still at the edge of frame, "
        "unchanged. The camera holds steady with a very slow push in. {{LIGHT}}, glossy "
        "reflections. Slow, luxurious pace. Macro lens look, no cuts.",
        "a thick stream flows and pools", "steady, very slow push-in",
        wider_opening=("Extreme close-up of", "Medium shot of"),
    ),
    Template(
        "G4-C", "G4", "wide",
        "The {{PRODUCT}} sits closed on {{SURFACE}} in {{SETTING}}, unchanged and still, with empty "
        "space to one side. Warm light spreads slowly across the scene. The camera slowly pulls "
        "back. {{MOOD}} pace. Warm homely commercial look, no cuts.",
        "none (light spreads)", "slow pull-back",
    ),
    # G5 · Fresh
    Template(
        "G5-A", "G5", "main",
        "The {{PRODUCT}} stays in place on {{SURFACE}}, shape and colour unchanged. Water droplets "
        "on the surface glisten and one slowly rolls down the side. A light mist drifts through the "
        "background. The camera pushes in slowly. {{LIGHT}} with crisp natural colour. Fresh and "
        "lively pace. Shallow depth of field, high detail, no cuts.",
        "droplets glisten, one rolls down", "slow push-in",
    ),
    Template(
        "G5-A-DRY", "G5", "main",
        "The {{PRODUCT}} stays in place on {{SURFACE}}, shape and colour unchanged and completely "
        "dry. No water and no mist. Light moves slowly across the surface, revealing grain and "
        "texture. The camera pushes in slowly. {{LIGHT}}, crisp natural colour. Steady pace. "
        "Shallow depth of field, high detail, no cuts.",
        "none (light moves across)", "slow push-in",
    ),
    Template(
        "G5-B", "G5", "closeup",
        "Close-up on {{DETAIL}}. The produce does not move or deform. The camera tracks slowly from "
        "left to right while light shifts over the surface, revealing texture and colour variation. "
        "{{LIGHT}}. Steady appetising pace. Macro food photography look, rich natural colour, "
        "no cuts.",
        "none (produce locked)", "slow left-to-right track",
    ),
    Template(
        "G5-C", "G5", "wide",
        "The {{PRODUCT}} fills {{SURFACE}}, arranged neatly and staying still, with empty space at "
        "the top of frame. The camera slowly pulls back and rises to reveal the full arrangement. "
        "{{LIGHT}} warming gradually. {{MOOD}} pace. Natural documentary food look, no cuts.",
        "none (arrangement still)", "slow pull-back and rise",
    ),
    # Services
    Template(
        "S1", "S1", "room",
        "The room in the image stays exactly as it is, with nothing moving and no people present. "
        "The camera pushes in slowly and steadily from the doorway toward the far wall. {{LIGHT}} "
        "through the windows, natural colour, furniture and layout unchanged. Calm, unhurried pace. "
        "Wide lens look, steady motion, no cuts.",
        "none", "slow steady push-in (no pans)",
    ),
    Template(
        "S2", "S2", "result",
        "The {{SUBJECT}} in the image stays exactly as it is, clean and unchanged. The camera pushes "
        "in slowly and holds. {{LIGHT}}, natural colour, nothing in the scene moves or shifts. Calm, "
        "satisfied pace. Wide lens look, steady motion, no cuts.",
        "none", "slow push-in, then hold",
    ),
    Template(
        "S3-A", "S3", "tools",
        "Close-up of the {{TOOLS}} laid out on the {{SURFACE}}. Nothing moves and nothing changes "
        "shape. Only a soft highlight travels slowly across them. The camera drifts slowly from left "
        "to right. Soft daylight, natural colour. Calm pace. Macro look, shallow depth of field, "
        "no cuts.",
        "none (a highlight travels)", "slow left-to-right drift",
    ),
    Template(
        "S3-B", "S3", "hands",
        "Close-up of the {{WORKER}}'s hands at work. The hands move slowly and steadily, one small "
        "controlled motion only. No faces in frame. Everything else in the scene stays unchanged. "
        "The camera holds almost still. Soft daylight, natural colour. Calm, careful pace. Shallow "
        "depth of field, no cuts.",
        "one small controlled hand motion", "almost still",
    ),
    Template(
        "S3-C", "S3", "scene",
        "The scene in the image stays exactly as it is. Everyone holds their pose, with only a very "
        "slight natural shift of the head and shoulders. Faces, hair, hands and clothing stay "
        "completely unchanged. Any mirror and its reflection stay exactly as they are. The camera "
        "pushes in slowly and steadily. Soft daylight, natural colour. Calm pace. Medium shot, "
        "no cuts.",
        "very slight shift of head and shoulders", "slow steady push-in",
    ),
    # S4 has no generation: a slow zoom and pan over the seller's own image in editing.
    Template("S4", "S4", "poster", "", "none", "zoom and pan added in editing"),
)

TEMPLATES: dict[str, Template] = {t.id: t for t in _TEMPLATES}

# --- Slot defaults (spec §1.6) ------------------------------------------------------------

GROUP_DEFAULTS: dict[str, dict[str, str]] = {
    "G1": {
        "DETAIL": "the woven texture and border",
        "SURFACE": "a plain surface",
        "SETTING": "a soft neutral backdrop",
        "MOOD": "calm and premium",
        "LIGHT": "warm side light",
        "ACCENT": "drifting dust motes",
    },
    "G2": {
        "DETAIL": "the front of the label",
        "SURFACE": "a dark wooden table",
        "SETTING": "a warm simple interior",
        "MOOD": "calm and premium",
        "LIGHT": "even studio light",
        "ACCENT": "drifting dust motes",
    },
    "G3": {
        "DETAIL": "the surface and finish",
        "SURFACE": "a dark cloth",
        "SETTING": "an uncluttered dark background",
        "MOOD": "calm and premium",
        "LIGHT": "soft directional light",
        "ACCENT": "none",
    },
    "G4": {
        "DETAIL": "the thick surface",
        "SURFACE": "a dark wooden table",
        "SETTING": "a warm simple interior",
        "MOOD": "warm and unhurried",
        "LIGHT": "warm window light",
        "ACCENT": "none",
    },
    "G5": {
        "DETAIL": "the surface texture",
        "SURFACE": "a woven bamboo tray",
        "SETTING": "a simple market setting",
        "MOOD": "fresh and lively",
        "LIGHT": "bright daylight",
        "ACCENT": "light mist",
    },
}

# The spec's defaults table has no MATERIAL row and gives no service slot
# defaults. These are neutral stand-ins added for P0 (flagged in the report).
MATERIAL_DEFAULTS: dict[str, str] = {
    "G1": "fabric",
    "G2": "surface",
    "G3": "surface",
    "G4": "the liquid",
    "G5": "surface",
}
SERVICE_DEFAULTS: dict[str, str] = {
    "LIGHT": "soft daylight",
    "SUBJECT": "finished work",
    "TOOLS": "tools",
    "SURFACE": "work surface",
    "WORKER": "worker",
}

# English stand-in for {{PRODUCT}} when the seller's description cannot be
# used as-is (it is Bengali, or was skipped). Templates describe motion,
# not the product, so a neutral noun is safe.
GENERIC_PRODUCT: dict[str, str] = {
    "clothing": "garment",
    "cosmetics": "product",
    "jewellery_watches": "jewellery piece",
    "electronics": "device",
    "other": "product",
    "food:G5": "produce",
    "food:G4": "container",
    "food:G2": "food item",
}

GQ1_MOTION_LEVEL: dict[str, str] = {
    "light": "noticeably",
    "medium": "gently",
    "heavy": "slowly, the fabric holding its weight",
}
GQ3A_SURFACE: dict[str, str] = {
    "cloth": "a dark cloth",
    "wood": "a dark wooden table",
    "white": "a clean white surface",
}

# --- Avoid lists (spec §2.6) ----------------------------------------------------------------

BASE_NEGATIVE: tuple[str, ...] = (
    "text", "letters", "words", "captions", "subtitles", "watermark", "logo", "changing label",
    "morphing product shape", "warped packaging", "extra fingers", "deformed hands",
    "distorted face", "jitter", "flicker", "sudden cut", "scene change", "camera shake",
    "oversaturated colours", "plastic texture", "extra objects appearing",
)
GROUP_NEGATIVE: dict[str, tuple[str, ...]] = {
    "G1": ("pattern drift", "dissolving border", "changing print"),
    "G3": ("warped reflections", "bent metal", "smeared stones", "mirror distortion"),
    "G4": ("plastic-looking liquid", "rubbery flow", "splashing"),
    "S1": ("people", "moving furniture", "changing room layout", "camera pan"),
    "S3": ("changing faces", "morphing beard", "melting hair", "extra people", "warped reflection"),
}
DRY_NEGATIVE: tuple[str, ...] = ("water", "droplets", "mist", "steam", "wet surface")


# --- Assembler --------------------------------------------------------------------------------

_OPTIONAL = re.compile(r"\[\[(\w+)\|(.*?)\]\]", re.DOTALL)
_SLOT = re.compile(r"\{\{(\w+)\}\}")
_SENTENCE_START = re.compile(r"(^|\.\s+)([a-z])")


def assemble_prompt(
    template_id: str,
    slots: dict[str, str],
    *,
    readable_label: bool = True,
    framing: str = "standard",
) -> str:
    """Builds the English prompt for one shot from its stored parts."""
    template = TEMPLATES[template_id]
    text = template.text
    if not text:
        return ""
    if framing == "wider" and template.wider_opening:
        find, replace = template.wider_opening
        text = text.replace(find, replace, 1)

    flags = {
        "ACCENT": slots.get("ACCENT", "none").strip().lower() not in ("", "none"),
        "READABLE": readable_label,
    }
    text = _OPTIONAL.sub(lambda m: m.group(2) if flags.get(m.group(1), False) else "", text)

    def fill(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in slots:
            raise KeyError(f"Template {template_id} needs slot {name}")
        return slots[name]

    text = _SLOT.sub(fill, text)
    text = re.sub(r"\s+", " ", text).strip()
    return _SENTENCE_START.sub(lambda m: m.group(1) + m.group(2).upper(), text)


def template_slots(template_id: str) -> set[str]:
    return set(_SLOT.findall(TEMPLATES[template_id].text))
