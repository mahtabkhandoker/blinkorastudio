"""Order domain models for the P0 product-video order workflow.

Two families of model live here:

* **Stored** models (`Order` and its parts) are the server-side record.
  They hold everything, including internal prompt slots and template IDs.
* **View** models (`OrderView` and its parts) are what a customer channel
  receives. They never contain the English generation prompt, template
  internals or negative prompts.

Identifiers are channel-neutral: an order carries a `channel` and an opaque
`customer_ref`, so a WhatsApp order can use the same record shape later.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

Channel = Literal["web", "whatsapp"]
Locale = Literal["bn", "en"]
FormatChoice = Literal["reels", "post", "both"]
AspectRatio = Literal["9:16", "1:1"]

ProductGroup = Literal["G1", "G2", "G3", "G4", "G5"]
ServiceScenario = Literal["S1", "S2", "S3", "S4"]

OrderStatus = Literal[
    "DRAFT",  # collecting photo and answers
    "PLAN_READY",  # plan built, waiting for the customer's confirmation
    "CONFIRMED",  # confirmed, nothing to generate (post-production only)
    "GENERATING",  # confirmed, generation submitted
    "GENERATED",  # generation finished
    "FAILED",  # generation failed
]

AssetPurpose = Literal["product", "logo"]
StoredAssetStatus = Literal["VALID", "WARNING"]
AnswerSource = Literal["customer", "default"]
QuestionKind = Literal["choose", "type", "upload"]
GenerationStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Stored ---------------------------------------------------------------------


class StoredAsset(BaseModel):
    id: str
    purpose: AssetPurpose
    filename: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    sha256: str
    status: StoredAssetStatus
    warning_code: str | None = None
    accepted_with_warning: bool = False
    superseded: bool = False
    storage_key: str
    created_at: datetime = Field(default_factory=utcnow)

    @property
    def usable(self) -> bool:
        if self.superseded:
            return False
        return self.status == "VALID" or self.accepted_with_warning


class Answer(BaseModel):
    code: str
    value: str
    source: AnswerSource = "customer"
    answered_at: datetime = Field(default_factory=utcnow)


class SlotValue(BaseModel):
    value: str
    source: str  # e.g. "q2", "group_default", "GQ3a", "generic_default"


class Shot(BaseModel):
    """One planned clip. Prompt *parts* are stored, never the sentence."""

    index: int
    role: str  # main | closeup | wide | room | result | tools | hands | scene | poster
    template_id: str
    template_group: str  # the group/scenario whose template this shot uses
    framing: Literal["standard", "wider"] = "standard"
    readable_label: bool = True
    crop: Literal["standard", "tighter"] = "standard"
    slots: dict[str, SlotValue] = Field(default_factory=dict)
    subject_motion: str = ""
    camera_move: str = ""
    aspect_ratio: AspectRatio = "9:16"
    duration_seconds: int = 5
    resolution: str = "720p"
    negative_terms: list[str] = Field(default_factory=list)
    generates_video: bool = True
    max_tries: int | None = None
    source_asset_id: str | None = None
    change_note: str | None = None


class CreativePlan(BaseModel):
    revision: int
    kind: Literal["product", "service"]
    group: ProductGroup | None = None
    variant: str | None = None  # e.g. "dry", "pour", "closed", "both"
    scenario: ServiceScenario | None = None
    category: str
    product_description: str = ""
    group_answers: dict[str, str] = Field(default_factory=dict)
    format: FormatChoice
    aspect_ratio: AspectRatio
    deliverables: list[str] = Field(default_factory=list)
    shots: list[Shot] = Field(default_factory=list)
    operator_flags: list[str] = Field(default_factory=list)
    fingerprint: str = ""

    @property
    def generated_shots(self) -> list[Shot]:
        return [s for s in self.shots if s.generates_video]


class GenerationShot(BaseModel):
    shot_index: int
    template_id: str
    client_reference: str
    provider_job_id: str | None = None
    status: GenerationStatus = "QUEUED"
    tries: int = 1
    error: str | None = None


class Generation(BaseModel):
    id: str
    order_id: str
    plan_revision: int
    idempotency_key: str
    provider: str
    simulated: bool
    status: GenerationStatus = "QUEUED"
    shots: list[GenerationShot] = Field(default_factory=list)
    submitted_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class Feedback(BaseModel):
    rating: str  # up | down | change
    scene: str | None = None  # 1 | 2 | 3 | all
    generation_id: str | None = None
    plan_revision: int | None = None
    created_at: datetime = Field(default_factory=utcnow)


class OrderEvent(BaseModel):
    at: datetime = Field(default_factory=utcnow)
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class Order(BaseModel):
    id: str
    number: str  # human-readable, e.g. ORD-000142
    channel: Channel = "web"
    customer_ref: str | None = None
    locale: Locale = "bn"
    status: OrderStatus = "DRAFT"
    format: FormatChoice = "reels"
    known_phone: str | None = None  # e.g. the WhatsApp sender number
    assets: list[StoredAsset] = Field(default_factory=list)
    answers: dict[str, Answer] = Field(default_factory=dict)
    revision_flow: str | None = None  # None | "C2" | "C2N:<shot index>"
    change_notes: dict[int, str] = Field(default_factory=dict)
    plan: CreativePlan | None = None
    plan_revision_counter: int = 0
    generation: Generation | None = None
    feedback: list[Feedback] = Field(default_factory=list)
    events: list[OrderEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def answer(self, code: str) -> str | None:
        found = self.answers.get(code)
        return found.value if found else None

    def product_assets(self, usable_only: bool = True) -> list[StoredAsset]:
        items = [a for a in self.assets if a.purpose == "product" and not a.superseded]
        return [a for a in items if a.usable] if usable_only else items

    def logo_asset(self) -> StoredAsset | None:
        logos = [a for a in self.assets if a.purpose == "logo" and not a.superseded]
        return logos[-1] if logos else None

    def log(self, event_type: str, **data: Any) -> None:
        self.events.append(OrderEvent(type=event_type, data=data))


# --- Requests -------------------------------------------------------------------


class CreateOrderRequest(BaseModel):
    channel: Channel = "web"
    locale: Locale = "bn"
    format: FormatChoice | None = None
    customer_ref: str | None = Field(default=None, max_length=200)
    known_phone: str | None = Field(default=None, max_length=32)


class SetFormatRequest(BaseModel):
    format: FormatChoice


class AnswerRequest(BaseModel):
    code: str = Field(min_length=1, max_length=16)
    value: str | None = Field(default=None, max_length=500)
    skip: bool = False


class ConfirmPlanRequest(BaseModel):
    plan_revision: int


# --- Views (customer-safe) --------------------------------------------------------


class OptionView(BaseModel):
    id: str
    label: str
    default: bool = False


class QuestionView(BaseModel):
    code: str
    kind: QuestionKind
    text: str
    options: list[OptionView] = Field(default_factory=list)
    placeholder: str | None = None
    input_mode: Literal["text", "tel"] = "text"
    max_length: int | None = None
    skippable: bool = False
    skip_label: str | None = None
    upload_purpose: AssetPurpose | None = None
    upload_label: str | None = None


class AnsweredView(BaseModel):
    code: str
    question: QuestionView
    value: str
    display: str
    source: AnswerSource
    editable: bool


class AssetView(BaseModel):
    id: str
    purpose: AssetPurpose
    filename: str
    width: int
    height: int
    status: StoredAssetStatus
    warning_code: str | None = None
    message: str | None = None
    usable: bool
    content_path: str  # relative API path that serves the stored file


class FormatOptionView(BaseModel):
    id: FormatChoice
    label: str
    aspect_ratio: str
    available: bool
    unavailable_reason: str | None = None


class FormatView(BaseModel):
    value: FormatChoice
    editable: bool
    options: list[FormatOptionView]


class PhotoStepView(BaseModel):
    reason: Literal["initial", "more_photos"]
    required_count: int = 1
    have_count: int = 0


class StepView(BaseModel):
    kind: Literal["photo", "question", "plan", "generation", "done"]
    message: str | None = None
    question: QuestionView | None = None
    photo: PhotoStepView | None = None


class PlanShotView(BaseModel):
    index: int
    description: str
    note: str | None = None
    generates_video: bool


class PlanView(BaseModel):
    revision: int
    intro: str
    shots: list[PlanShotView]
    closing: str
    post_production_note: str
    confirm_label: str
    change_label: str
    confirmed: bool


class EligibilityCheckView(BaseModel):
    code: str
    ok: bool
    message: str


class EligibilityView(BaseModel):
    eligible: bool
    checks: list[EligibilityCheckView]


class GenerationShotView(BaseModel):
    index: int
    status: GenerationStatus


class GenerationView(BaseModel):
    id: str
    status: GenerationStatus
    simulated: bool
    plan_revision: int
    shots: list[GenerationShotView]
    message: str
    deduplicated: bool = False


class BrandView(BaseModel):
    shop_name: str | None = None
    phone: str | None = None
    has_logo: bool = False


class FeedbackView(BaseModel):
    rating: str
    scene: str | None = None
    generation_id: str | None = None


class EnvironmentView(BaseModel):
    """Tells the client what is real and what is a stand-in."""

    video_provider: str
    simulated_generation: bool
    storage: str
    notice: str


class OrderOptionsView(BaseModel):
    format: FormatView
    max_upload_mb: int
    accepted_mime_types: list[str]
    photo_prompt: str
    environment: EnvironmentView


class OrderView(BaseModel):
    id: str
    number: str
    title: str
    channel: Channel
    locale: Locale
    status: OrderStatus
    format: FormatView
    photos: list[AssetView]
    logo: AssetView | None = None
    answered: list[AnsweredView]
    step: StepView
    plan: PlanView | None = None
    eligibility: EligibilityView | None = None
    generation: GenerationView | None = None
    brand: BrandView
    feedback: FeedbackView | None = None
    environment: EnvironmentView
