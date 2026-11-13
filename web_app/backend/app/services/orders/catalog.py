"""Question catalog and routing tables for the P0 order workflow.

Source: `golpo-questions-templates-models.md`, Part 1. The document uses the
working name "Golpo"; the product is Blinkora Studio and nothing here is
customer-facing branding.

This module is data plus pure lookups. It decides nothing about order
state; `questions.py` does the sequencing.

Question text is kept here (not in the web app's message files) because the
same wording is meant to be reused by the WhatsApp channel later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.orders import AssetPurpose, ProductGroup, QuestionKind, ServiceScenario


@dataclass(frozen=True)
class Option:
    id: str
    bn: str
    en: str
    default: bool = False


@dataclass(frozen=True)
class QuestionDef:
    code: str
    kind: QuestionKind
    bn: str
    en: str
    options: tuple[Option, ...] = ()
    placeholder_bn: str | None = None
    placeholder_en: str | None = None
    input_mode: str = "text"
    max_length: int | None = None
    # Typed questions: value used when the seller skips. None = not skippable.
    skip_value: str | None = None
    skip_bn: str | None = None
    skip_en: str | None = None
    upload_purpose: AssetPurpose | None = None
    upload_bn: str | None = None
    upload_en: str | None = None
    family: str = "Q"
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def default_option(self) -> Option | None:
        for option in self.options:
            if option.default:
                return option
        return None

    def option(self, option_id: str) -> Option | None:
        for option in self.options:
            if option.id == option_id:
                return option
        return None


# --- F1 · format ------------------------------------------------------------------

FORMAT_OPTIONS: tuple[Option, ...] = (
    Option("reels", "রিল / টিকটক", "Reels / TikTok", default=True),
    Option("post", "পোস্ট", "Post"),
    Option("both", "দুইটাই", "Both"),
)
FORMAT_ASPECT: dict[str, str] = {"reels": "9:16", "post": "1:1", "both": "9:16 + 1:1"}


# --- Questions ----------------------------------------------------------------------

_QUESTIONS: tuple[QuestionDef, ...] = (
    # Q · core
    QuestionDef(
        code="Q1",
        kind="choose",
        bn="কী বিক্রি করেন?",
        en="What do you sell?",
        options=(
            Option("clothing", "পোশাক", "Clothing"),
            Option("food", "খাবার", "Food"),
            Option("cosmetics", "প্রসাধনী", "Cosmetics"),
            Option("jewellery_watches", "গয়না ও ঘড়ি", "Jewellery & watches"),
            Option("electronics", "মোবাইল ও ইলেকট্রনিক্স", "Mobile & electronics"),
            Option("service", "সার্ভিস", "A service"),
            # G2 is the safest default group, so "something else" is the default.
            Option("other", "অন্য কিছু", "Something else", default=True),
        ),
    ),
    QuestionDef(
        code="Q1a",
        kind="choose",
        bn="কী ধরনের খাবার?",
        en="What kind of food?",
        options=(
            Option("fresh", "তাজা — সবজি, ফল, মাছ", "Fresh — vegetables, fruit, fish"),
            Option("dry_goods", "চাল, ডাল, মসলা, শুঁটকি", "Rice, lentils, spices, dried fish"),
            Option("flowing", "মধু, ঘি, তেল, দই", "Honey, ghee, oil, yoghurt"),
            Option("prepared", "মিষ্টি, রান্না করা খাবার", "Sweets, cooked food", default=True),
        ),
    ),
    QuestionDef(
        code="Q2",
        kind="type",
        bn="এটা কী, কী দিয়ে তৈরি? এক লাইনে লিখুন",
        en="What is it, and what is it made of? One line is enough",
        placeholder_bn="যেমন: লাল সুতির শাড়ি",
        placeholder_en="e.g. red cotton saree",
        max_length=120,
        skip_value="",
        skip_bn="পরে লিখব",
        skip_en="Skip for now",
    ),
    # GQ · one per group
    QuestionDef(
        code="GQ1",
        kind="choose",
        family="GQ",
        bn="কাপড়টা পাতলা নাকি ভারী?",
        en="Is the fabric light or heavy?",
        options=(
            Option("light", "পাতলা", "Light"),
            Option("medium", "মাঝারি", "Medium", default=True),
            Option("heavy", "ভারী", "Heavy"),
        ),
    ),
    QuestionDef(
        code="GQ2",
        kind="choose",
        family="GQ",
        bn="লেবেলটা ছবিতে স্পষ্ট দেখা যাচ্ছে?",
        en="Is the label clear in the photo?",
        options=(
            Option("clear", "হ্যাঁ", "Yes", default=True),
            Option("blurry", "একটু ঝাপসা", "A bit blurry"),
        ),
    ),
    QuestionDef(
        code="GQ3a",
        kind="choose",
        family="GQ",
        bn="{item}টা কিসের উপর রাখা?",
        en="What is the {item} resting on?",
        options=(
            Option("cloth", "কাপড়", "Cloth", default=True),
            Option("wood", "কাঠ", "Wood"),
            Option("white", "সাদা", "White surface"),
        ),
    ),
    QuestionDef(
        code="GQ3b",
        kind="choose",
        family="GQ",
        bn="ছবিতে আলোর ঝলক আছে?",
        en="Is there glare in the photo?",
        options=(
            Option("yes", "হ্যাঁ", "Yes"),
            Option("no", "না", "No", default=True),
        ),
    ),
    QuestionDef(
        code="GQ4",
        kind="choose",
        family="GQ",
        bn="ঢালা দেখাব, নাকি বন্ধ কৌটা?",
        en="Show it pouring, or the sealed container?",
        options=(
            Option("pour", "ঢালা", "Pouring"),
            Option("closed", "বন্ধ কৌটা", "Sealed container"),
            Option("both", "দুইটাই", "Both", default=True),
        ),
    ),
    QuestionDef(
        code="GQ5",
        kind="choose",
        family="GQ",
        bn="পণ্যটা ভেজা নাকি শুকনো?",
        en="Is the product wet or dry?",
        options=(
            Option("wet", "ভেজা / তাজা", "Wet / fresh", default=True),
            Option("dry", "শুকনো", "Dry"),
        ),
    ),
    # Photo follow-ups (conditional messages in the spec)
    QuestionDef(
        code="PH_QUALITY",
        kind="upload",
        family="PH",
        bn="{warning} আসল ছবিটা দিতে পারবেন?",
        en="{warning} Can you send the original photo?",
        options=(Option("use_anyway", "এটা দিয়েই বানান", "Use this one"),),
        upload_purpose="product",
        upload_bn="নতুন ছবি পাঠাচ্ছি",
        upload_en="Send a new photo",
    ),
    QuestionDef(
        code="PH_GLARE",
        kind="upload",
        family="PH",
        bn="আলোর ঝলক থাকলে ভিডিওতে পণ্যটা বেঁকে যেতে পারে। ঝলক ছাড়া একটা ছবি দিতে পারবেন?",
        en="Glare can make the product warp in the video. Can you send a photo without glare?",
        options=(Option("use_anyway", "এটা দিয়েই বানান", "Use this one"),),
        upload_purpose="product",
        upload_bn="নতুন ছবি পাঠাচ্ছি",
        upload_en="Send a new photo",
    ),
    # SQ · services
    QuestionDef(
        code="SQ1",
        kind="choose",
        family="SQ",
        bn="কী ধরনের সার্ভিস?",
        en="What kind of service photo is it?",
        options=(
            Option("S1", "দোকান বা জায়গা", "A shop or place"),
            Option("S2", "কাজের ফলাফল", "A finished result", default=True),
            Option("S3", "কাজ করছেন এমন ছবি", "Someone at work"),
            Option("S4", "দামের তালিকা বা পোস্টার", "A price list or poster"),
        ),
    ),
    QuestionDef(
        code="SQ2",
        kind="type",
        family="SQ",
        bn="কী সার্ভিস দেন, এক লাইনে?",
        en="What service do you offer, in one line?",
        placeholder_bn="যেমন: চুল আর দাড়ি কাটা",
        placeholder_en="e.g. haircuts and beard trims",
        max_length=120,
        skip_value="",
        skip_bn="পরে লিখব",
        skip_en="Skip for now",
    ),
    QuestionDef(
        code="SQ5",
        kind="choose",
        family="SQ",
        bn="কয়টা রুম দেখাব?",
        en="How many rooms should we show?",
        options=(
            Option("1", "১", "1", default=True),
            Option("2", "২", "2"),
            Option("3", "৩", "3"),
            Option("3plus", "৩+", "3+"),
        ),
    ),
    QuestionDef(
        code="SQ6",
        kind="choose",
        family="SQ",
        bn="ভাড়া নাকি বিক্রি?",
        en="For rent or for sale?",
        options=(
            Option("rent", "ভাড়া", "Rent", default=True),
            Option("sale", "বিক্রি", "Sale"),
        ),
    ),
    QuestionDef(
        code="SQ7",
        kind="choose",
        family="SQ",
        bn="আগের ছবি আছে?",
        en="Do you have a 'before' photo?",
        options=(
            Option("yes", "আছে", "Yes"),
            Option("no", "নেই", "No", default=True),
        ),
    ),
    QuestionDef(
        code="SQ8",
        kind="choose",
        family="SQ",
        bn="মুখ একটু বদলে যেতে পারে — মুখসহ বানাব, নাকি শুধু হাত আর কাজ?",
        en="Faces can change slightly — include the face, or only hands and the work?",
        options=(
            Option("with_face", "মুখসহ", "With the face"),
            Option("work_only", "শুধু কাজ", "Work only", default=True),
        ),
    ),
    QuestionDef(
        code="SQ3",
        kind="type",
        family="SQ",
        bn="দাম কত?",
        en="What is the price?",
        placeholder_bn="যেমন: চুল কাটা ১০০ টাকা",
        placeholder_en="e.g. haircut 100 taka",
        max_length=120,
        skip_value="",
        skip_bn="দাম লিখব না",
        skip_en="Don't show a price",
    ),
    QuestionDef(
        code="SQ4",
        kind="type",
        family="SQ",
        bn="কোথায় বসেন বা কোন এলাকায় সার্ভিস দেন?",
        en="Where are you based, or which area do you serve?",
        placeholder_bn="যেমন: মিরপুর ১০",
        placeholder_en="e.g. Mirpur 10",
        max_length=120,
        skip_value="",
        skip_bn="পরে লিখব",
        skip_en="Skip for now",
    ),
    # C · confirmation follow-ups (C1 itself is the plan step)
    QuestionDef(
        code="C2",
        kind="choose",
        family="C",
        bn="কোনটা বদলাবেন?",
        en="Which one would you like to change?",
        # Shot options are generated from the plan; these two are always present.
        options=(
            Option("product_type", "পণ্যের ধরন", "The product type"),
            Option("nothing", "কিছু বদলাব না", "Nothing, keep it"),
        ),
    ),
    QuestionDef(
        code="C2N",
        kind="type",
        family="C",
        bn="দৃশ্য {n}-এ কী বদলাতে চান? এক লাইনে লিখুন",
        en="What would you like to change in scene {n}? One line is enough",
        max_length=200,
    ),
    # P · post-production (asked after confirmation)
    QuestionDef(
        code="P1",
        kind="type",
        family="P",
        bn="দোকানের নাম ভিডিওতে যেভাবে চান, ঠিক সেভাবে লিখুন",
        en="Type your shop name exactly as it should appear in the video",
        max_length=60,
        skip_value="",
        skip_bn="নাম দেব না",
        skip_en="No name",
    ),
    QuestionDef(
        code="P1c",
        kind="choose",
        family="P",
        bn="এভাবেই লিখব? {name}",
        en="Shall we write it like this? {name}",
        options=(
            Option("yes", "হ্যাঁ", "Yes", default=True),
            Option("fix", "ঠিক করব", "Let me fix it"),
        ),
    ),
    QuestionDef(
        code="P2",
        kind="upload",
        family="P",
        bn="লোগো থাকলে ছবিটা পাঠান",
        en="If you have a logo, send the image",
        options=(Option("no_logo", "লোগো নেই", "No logo", default=True),),
        upload_purpose="logo",
        upload_bn="লোগো পাঠাচ্ছি",
        upload_en="Send logo",
    ),
    QuestionDef(
        code="P3",
        kind="choose",
        family="P",
        bn="ভিডিওতে এই নাম্বারটা দেব? {phone}",
        en="Shall we show this number in the video? {phone}",
        options=(
            Option("yes", "হ্যাঁ", "Yes", default=True),
            Option("other", "অন্য নাম্বার", "A different number"),
        ),
    ),
    QuestionDef(
        code="P3n",
        kind="type",
        family="P",
        bn="ভিডিওতে কোন ফোন নাম্বার দেব?",
        en="Which phone number should we show in the video?",
        placeholder_bn="01XXXXXXXXX",
        placeholder_en="01XXXXXXXXX",
        input_mode="tel",
        max_length=20,
        skip_value="",
        skip_bn="নাম্বার দেব না",
        skip_en="No number",
    ),
    # R · after delivery
    QuestionDef(
        code="R1",
        kind="choose",
        family="R",
        bn="ভিডিওটা কেমন হয়েছে?",
        en="How did the video turn out?",
        options=(
            Option("up", "👍", "👍"),
            Option("down", "👎", "👎"),
            Option("change", "বদলাতে চাই", "I want changes"),
        ),
    ),
    QuestionDef(
        code="R2",
        kind="choose",
        family="R",
        bn="কোন দৃশ্যটা?",
        en="Which scene?",
        options=(
            Option("1", "১", "1"),
            Option("2", "২", "2"),
            Option("3", "৩", "3"),
            Option("all", "পুরোটা", "All of it", default=True),
        ),
    ),
)

QUESTIONS: dict[str, QuestionDef] = {q.code: q for q in _QUESTIONS}


def get_question(code: str) -> QuestionDef:
    return QUESTIONS[code]


# --- Routing (Q1 → group, Q1a → group/variant) ----------------------------------------

CATEGORY_TO_GROUP: dict[str, ProductGroup] = {
    "clothing": "G1",
    "cosmetics": "G2",
    "jewellery_watches": "G3",
    "electronics": "G3",
    "other": "G2",
}

FOOD_SUBTYPE_TO_GROUP: dict[str, tuple[ProductGroup, str | None]] = {
    "fresh": ("G5", None),  # wet or dry is asked (GQ5)
    "dry_goods": ("G5", "dry"),  # GQ5 is not asked: the answer is already known
    "flowing": ("G4", None),
    "prepared": ("G2", None),
}

GROUP_QUESTIONS: dict[ProductGroup, tuple[str, ...]] = {
    "G1": ("GQ1",),
    "G2": ("GQ2",),
    "G3": ("GQ3a", "GQ3b"),
    "G4": ("GQ4",),
    "G5": ("GQ5",),
}

SCENARIO_QUESTIONS: dict[ServiceScenario, tuple[str, ...]] = {
    "S1": ("SQ5", "SQ6"),
    "S2": ("SQ7",),
    "S3": ("SQ8",),
    "S4": (),
}

# Codes whose answers describe the product/service and feed the plan.
COLLECTION_CODES: frozenset[str] = frozenset(
    {"Q1", "Q1a", "Q2", "GQ1", "GQ2", "GQ3a", "GQ3b", "GQ4", "GQ5", "PH_GLARE"}
    | {"SQ1", "SQ2", "SQ3", "SQ4", "SQ5", "SQ6", "SQ7", "SQ8"}
)
BRAND_CODES: frozenset[str] = frozenset({"P1", "P1c", "P2", "P3", "P3n"})
FEEDBACK_CODES: frozenset[str] = frozenset({"R1", "R2"})
