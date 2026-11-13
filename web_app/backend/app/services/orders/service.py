"""Order workflow service: the one place that changes an order's state.

Channels (the web routes today, WhatsApp later) call these methods and
render the `OrderView` they get back. They never decide what comes next.

State transitions:

    DRAFT ──answers complete──▶ PLAN_READY ──confirm──▶ GENERATING ──▶ GENERATED
      ▲                            │   │                     └────────▶ FAILED
      └──────answer changed────────┘   └─confirm, nothing to generate─▶ CONFIRMED

Generation is only ever started by `confirm_plan`, which needs the plan
revision the customer saw and an idempotency key.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.orders import (
    AnsweredView,
    AssetView,
    BrandView,
    CreateOrderRequest,
    EligibilityCheckView,
    EligibilityView,
    EnvironmentView,
    FeedbackView,
    FormatOptionView,
    FormatView,
    Generation,
    GenerationShot,
    GenerationShotView,
    GenerationView,
    Order,
    OrderOptionsView,
    OrderView,
    PhotoStepView,
    StepView,
    StoredAsset,
    utcnow,
)
from app.repositories.orders import InMemoryOrderRepository, JsonFileOrderRepository, OrderRepository
from app.services.assets.intake import LocalAssetStorage, inspect_image
from app.services.generations.providers import (
    ShotGenerationRequest,
    VideoGenerationProvider,
    get_video_provider,
)
from app.services.orders import questions, texts
from app.services.orders.catalog import FORMAT_ASPECT, FORMAT_OPTIONS, QUESTIONS
from app.services.orders.errors import OrderError
from app.services.orders.plan_builder import (
    build_plan,
    plan_view,
    shot_negative_prompt,
    shot_prompt,
)

logger = get_logger(__name__)

PRE_CONFIRM = questions.PRE_CONFIRM_STATUSES
_TERMINAL = ("SUCCEEDED", "FAILED")


class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        storage: LocalAssetStorage,
        provider: VideoGenerationProvider,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._storage = storage
        self._provider = provider
        self._settings = settings
        # One process, one lock: enough to make confirm atomic here. A real
        # database would use a row lock or a unique constraint instead.
        self._lock = threading.RLock()

    # --- Loading ----------------------------------------------------------------

    def _load(self, order_id: str) -> Order:
        order = self._repo.get(order_id)
        if order is None:
            raise OrderError("ORDER_NOT_FOUND", "This order does not exist on the server.", 404)
        return order

    def _save(self, order: Order) -> None:
        order.updated_at = utcnow()
        self._repo.save(order)

    def get(self, order_id: str) -> Order:
        with self._lock:
            order = self._load(order_id)
            if self._refresh_generation(order):
                self._save(order)
            return order

    # --- Creation and format -------------------------------------------------------

    def _format_available(self, format_choice: str) -> bool:
        if format_choice != "both":
            return True
        return self._settings.both_formats_enabled and self._settings.both_formats_addon_bdt is not None

    def create(self, request: CreateOrderRequest) -> Order:
        with self._lock:
            format_choice = request.format or "reels"
            if not self._format_available(format_choice):
                raise OrderError("FORMAT_UNAVAILABLE", "This format is not available yet.", 422)
            known_phone = None
            if request.known_phone:
                known_phone = questions.normalize_phone(request.known_phone)
            order = Order(
                id=str(uuid.uuid4()),
                number=self._repo.next_number(),
                channel=request.channel,
                customer_ref=request.customer_ref,
                locale=request.locale,
                format=format_choice,
                known_phone=known_phone,
            )
            order.log("created", channel=order.channel, format=order.format)
            self._save(order)
            return order

    def set_format(self, order_id: str, format_choice: str) -> Order:
        with self._lock:
            order = self._load(order_id)
            self._require_pre_confirm(order)
            if not self._format_available(format_choice):
                raise OrderError("FORMAT_UNAVAILABLE", "This format is not available yet.", 422)
            if order.format != format_choice:
                order.format = format_choice  # type: ignore[assignment]
                order.log("format", value=format_choice)
                self._sync_plan(order)
            self._save(order)
            return order

    # --- Assets ---------------------------------------------------------------------

    def add_asset(self, order_id: str, purpose: str, filename: str, data: bytes) -> Order:
        if purpose not in ("product", "logo"):
            raise OrderError("INVALID_PURPOSE", "purpose must be 'product' or 'logo'.", 422)
        with self._lock:
            order = self._load(order_id)
            if purpose == "product":
                self._require_pre_confirm(order)
            elif "P2" not in questions.answerable_codes(order):
                raise OrderError("LOGO_NOT_REQUESTED", "The logo is asked for after the plan is confirmed.", 409)

            info = inspect_image(
                data,
                max_bytes=self._settings.max_upload_mb * 1024 * 1024,
                max_pixels=self._settings.max_image_pixels,
                quality_checks=purpose == "product",
            )
            asset_id = uuid.uuid4().hex
            key = f"uploads/{order.id}/{asset_id}.{info.extension}"
            self._storage.put(key, data)
            asset = StoredAsset(
                id=asset_id,
                purpose=purpose,  # type: ignore[arg-type]
                filename=filename,
                mime_type=info.mime_type,
                size_bytes=len(data),
                width=info.width,
                height=info.height,
                sha256=info.sha256,
                status="WARNING" if info.warning_code else "VALID",
                warning_code=info.warning_code,
                storage_key=key,
            )
            if purpose == "product":
                questions.on_product_photo_added(order, asset)
                self._sync_plan(order)
            else:
                previous = order.logo_asset()
                if previous is not None:
                    previous.superseded = True
                order.assets.append(asset)
                from app.models.orders import Answer  # local: only needed here

                order.answers["P2"] = Answer(code="P2", value="uploaded")
            order.log("asset_added", asset_id=asset.id, purpose=purpose, status=asset.status, warning=asset.warning_code)
            self._save(order)
            return order

    def asset_file(self, order_id: str, asset_id: str) -> tuple[Path, str]:
        order = self._load(order_id)
        for asset in order.assets:
            if asset.id == asset_id and self._storage.exists(asset.storage_key):
                return self._storage.path_for(asset.storage_key), asset.mime_type
        raise OrderError("ASSET_NOT_FOUND", "This file is not stored on the server.", 404)

    # --- Answers --------------------------------------------------------------------

    def answer(self, order_id: str, code: str, value: str | None, skip: bool = False) -> Order:
        with self._lock:
            order = self._load(order_id)
            self._refresh_generation(order)
            questions.apply_answer(order, code, value, skip)
            if order.status in PRE_CONFIRM:
                self._sync_plan(order)
            self._save(order)
            return order

    def request_plan_change(self, order_id: str) -> Order:
        """C1 → 'I want changes': opens C2."""
        with self._lock:
            order = self._load(order_id)
            if order.status != "PLAN_READY" or questions.next_step(order).kind != "plan":
                raise OrderError("PLAN_NOT_READY", "There is no plan waiting for confirmation.", 409)
            order.revision_flow = "C2"
            order.log("plan_change_requested", revision=order.plan.revision if order.plan else None)
            self._save(order)
            return order

    # --- Plan -----------------------------------------------------------------------

    def _require_pre_confirm(self, order: Order) -> None:
        if order.status not in PRE_CONFIRM:
            raise OrderError("ORDER_LOCKED", "This order is already confirmed and cannot be changed.", 409)

    def _sync_plan(self, order: Order) -> None:
        """Rebuilds (or drops) the plan after any pre-confirmation change."""
        if order.status not in PRE_CONFIRM:
            return
        if not questions.answers_complete(order):
            order.plan = None
            order.status = "DRAFT"
            return
        plan = build_plan(
            order,
            clip_seconds=self._settings.clip_seconds,
            resolution=self._settings.clip_resolution,
        )
        if order.plan is None or plan.revision != order.plan.revision:
            order.plan_revision_counter = plan.revision
            order.log("plan_built", revision=plan.revision, shots=[s.template_id for s in plan.shots])
        order.plan = plan
        order.status = "PLAN_READY"

    def eligibility(self, order: Order, locale: str) -> EligibilityView:
        plan_ready = (
            order.status == "PLAN_READY"
            and order.plan is not None
            and questions.next_step(order).kind == "plan"
        )
        checks = {
            "plan_ready": plan_ready,
            "photo_ready": len(order.product_assets()) >= questions.rooms_required(order),
            "not_submitted": order.generation is None,
            # Only a simulated provider may run: paid generation is not enabled.
            "provider_safe": self._provider.is_simulated,
        }
        views = [
            EligibilityCheckView(code=code, ok=ok, message=texts.pick(texts.ELIGIBILITY_MESSAGES[code], locale))
            for code, ok in checks.items()
        ]
        return EligibilityView(eligible=all(checks.values()), checks=views)

    def confirm_plan(self, order_id: str, plan_revision: int, idempotency_key: str) -> tuple[Order, bool]:
        """C1 → 'Yes, make it'. Returns (order, deduplicated)."""
        key = idempotency_key.strip()
        if not key:
            raise OrderError("IDEMPOTENCY_KEY_REQUIRED", "An Idempotency-Key header is required.", 400)
        with self._lock:
            order = self._load(order_id)

            # A repeat of an already-accepted confirmation returns the same
            # generation; it never submits a second one.
            if order.generation is not None:
                same = order.generation.idempotency_key == key or order.generation.plan_revision == plan_revision
                if same:
                    self._refresh_generation(order)
                    self._save(order)
                    return order, True
                raise OrderError("ORDER_LOCKED", "This order was already submitted.", 409)
            if order.status == "CONFIRMED":
                return order, True

            if order.plan is None or order.status != "PLAN_READY" or questions.next_step(order).kind != "plan":
                raise OrderError("PLAN_NOT_READY", "There is no plan waiting for confirmation.", 409)
            if plan_revision != order.plan.revision:
                raise OrderError(
                    "PLAN_REVISION_STALE",
                    "The plan changed after it was shown. Review the updated plan first.",
                    409,
                    extra={"current_revision": order.plan.revision},
                )
            eligibility = self.eligibility(order, "en")
            if not eligibility.eligible:
                failed = [c.code for c in eligibility.checks if not c.ok]
                raise OrderError("NOT_ELIGIBLE", "This order cannot be submitted yet.", 409, extra={"failed": failed})

            plan = order.plan
            order.log("plan_confirmed", revision=plan.revision)
            shots = plan.generated_shots
            if not shots:
                order.status = "CONFIRMED"
                order.log("order_line", line=self.order_line(order))
                self._save(order)
                return order, False

            generation = Generation(
                id=f"GEN-{uuid.uuid4().hex[:12].upper()}",
                order_id=order.id,
                plan_revision=plan.revision,
                idempotency_key=key,
                provider=self._provider.name,
                simulated=self._provider.is_simulated,
            )
            assets = {a.id: a for a in order.assets}
            for shot in shots:
                reference = f"{generation.id}:shot{shot.index}:try1"
                record = GenerationShot(shot_index=shot.index, template_id=shot.template_id, client_reference=reference)
                source = assets.get(shot.source_asset_id or "")
                try:
                    record.provider_job_id = self._provider.submit(
                        ShotGenerationRequest(
                            client_reference=reference,
                            prompt=shot_prompt(shot),
                            negative_prompt=shot_negative_prompt(shot),
                            image_storage_key=source.storage_key if source else None,
                            aspect_ratio=shot.aspect_ratio,
                            duration_seconds=shot.duration_seconds,
                            resolution=shot.resolution,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - a provider error must not lose the order
                    logger.exception("provider submit failed order=%s shot=%s", order.number, shot.index)
                    record.status = "FAILED"
                    record.error = type(exc).__name__
                generation.shots.append(record)

            order.generation = generation
            order.status = "GENERATING"
            self._refresh_generation(order)
            order.log("generation_submitted", generation_id=generation.id, provider=generation.provider, simulated=generation.simulated)
            line = self.order_line(order)
            order.log("order_line", line=line)
            logger.info("order line: %s", line)
            self._save(order)
            return order, False

    def _refresh_generation(self, order: Order) -> bool:
        generation = order.generation
        if generation is None or generation.status in _TERMINAL:
            return False
        before = (generation.status, [s.status for s in generation.shots])
        for shot in generation.shots:
            if shot.status in _TERMINAL or shot.provider_job_id is None:
                continue
            result = self._provider.get_status(shot.provider_job_id)
            shot.status = result.status  # type: ignore[assignment]
            shot.error = result.error
        statuses = [s.status for s in generation.shots]
        if any(s == "FAILED" for s in statuses):
            generation.status = "FAILED"
        elif all(s == "SUCCEEDED" for s in statuses):
            generation.status = "SUCCEEDED"
        elif any(s in ("RUNNING", "SUCCEEDED") for s in statuses):
            generation.status = "RUNNING"
        else:
            generation.status = "QUEUED"
        if generation.status in _TERMINAL:
            generation.completed_at = utcnow()
            order.status = "GENERATED" if generation.status == "SUCCEEDED" else "FAILED"
            order.log("generation_finished", generation_id=generation.id, status=generation.status)
        return before != (generation.status, statuses)

    # --- Operator record (never sent to a customer channel) --------------------------------

    def order_line(self, order: Order) -> str:
        """One log line per order (spec §2.8)."""
        plan = order.plan
        if plan is None:
            return f"{order.number} · no plan"
        route = f"{plan.category} → {plan.group or plan.scenario}"
        answers = " ".join(f"{code}={value}" for code, value in sorted(plan.group_answers.items())) or "-"
        shots = ", ".join(s.template_id for s in plan.shots)
        generation = order.generation
        model = generation.provider if generation else "none"
        tries = ",".join(str(s.tries) for s in generation.shots) if generation else "-"
        confirmed = "ok" if order.status not in PRE_CONFIRM else "pending"
        rating = order.feedback[-1].rating if order.feedback else "-"
        first = plan.shots[0]
        return (
            f"{order.number} · {route} · {answers} · shots {shots} · model {model} · "
            f"{first.resolution} {plan.aspect_ratio} · tries {tries} · C1 {confirmed} · R1 {rating}"
        )

    def operator_record(self, order: Order) -> dict:
        shots = []
        for shot in order.plan.shots if order.plan else []:
            shots.append(
                {
                    **shot.model_dump(mode="json"),
                    "prompt": shot_prompt(shot),
                    "negative_prompt": shot_negative_prompt(shot),
                }
            )
        return {
            "order_line": self.order_line(order),
            "order": order.model_dump(mode="json", exclude={"plan": {"shots"}}),
            "shots": shots,
            "post_production": {
                "shop_name": order.answer("P1") or None,
                "phone": questions.brand_phone(order),
                "logo_asset_id": order.logo_asset().id if order.logo_asset() else None,
                "service_text": order.answer("SQ2") or None,
                "price_text": order.answer("SQ3") or None,
                "location_text": order.answer("SQ4") or None,
            },
        }

    # --- Customer view -----------------------------------------------------------------------

    def _asset_view(self, order: Order, asset: StoredAsset, locale: str) -> AssetView:
        message = texts.asset_warning_text(asset.warning_code, locale) if asset.purpose == "product" else None
        return AssetView(
            id=asset.id,
            purpose=asset.purpose,
            filename=asset.filename,
            width=asset.width,
            height=asset.height,
            status=asset.status,
            warning_code=asset.warning_code,
            message=message,
            usable=asset.usable,
            content_path=f"/api/orders/{order.id}/assets/{asset.id}/content",
        )

    def options(self, locale: str, max_upload_mb: int) -> OrderOptionsView:
        locale = locale if locale in ("bn", "en") else "bn"
        return OrderOptionsView(
            format=self._format_options("reels", True, locale),
            max_upload_mb=max_upload_mb,
            accepted_mime_types=["image/jpeg", "image/png", "image/webp"],
            photo_prompt=texts.pick(texts.PHOTO_MESSAGES["initial"], locale),
            environment=self._environment_view(locale),
        )

    def _environment_view(self, locale: str) -> EnvironmentView:
        return EnvironmentView(
            video_provider=self._provider.name,
            simulated_generation=self._provider.is_simulated,
            storage=self._storage.name,
            notice=texts.pick(texts.ENVIRONMENT_NOTICE, locale),
        )

    def _format_view(self, order: Order, locale: str) -> FormatView:
        return self._format_options(order.format, order.status in PRE_CONFIRM, locale)

    def _format_options(self, value: str, editable: bool, locale: str) -> FormatView:
        options = []
        for option in FORMAT_OPTIONS:
            available = self._format_available(option.id)
            label = texts.pick((option.bn, option.en), locale)
            if option.id == "both" and available:
                label = f"{label} (+৳{self._settings.both_formats_addon_bdt})"
            options.append(
                FormatOptionView(
                    id=option.id,  # type: ignore[arg-type]
                    label=label,
                    aspect_ratio=FORMAT_ASPECT[option.id],
                    available=available,
                    unavailable_reason=None if available else texts.pick(("শীঘ্রই আসছে", "Coming soon"), locale),
                )
            )
        return FormatView(value=value, editable=editable, options=options)  # type: ignore[arg-type]

    def _step_view(self, order: Order, locale: str) -> StepView:
        step = questions.next_step(order)
        if step.kind == "question" and step.code:
            return StepView(kind="question", question=questions.question_view(order, step.code, locale))
        if step.kind == "photo":
            required = questions.rooms_required(order)
            have = len(order.product_assets())
            message = texts.pick(texts.PHOTO_MESSAGES[step.photo_reason or "initial"], locale)
            missing = str(max(required - have, 1))
            message = message.format(k=questions.to_bn_digits(missing) if locale == "bn" else missing)
            return StepView(
                kind="photo",
                message=message,
                photo=PhotoStepView(reason=step.photo_reason, required_count=required, have_count=have),  # type: ignore[arg-type]
            )
        return StepView(kind=step.kind)  # type: ignore[arg-type]

    def _answered_views(self, order: Order, locale: str) -> list[AnsweredView]:
        if order.status in PRE_CONFIRM:
            ordered = questions.collection_codes(order)
        else:
            ordered = (
                questions.collection_codes(order)
                + questions.brand_codes(order)
                + [c for c in ("R1", "R2") if c in order.answers]
            )
        editable = questions.editable_codes(order)
        views = []
        for code in ordered:
            answer = order.answers.get(code)
            if answer is None or code not in QUESTIONS:
                continue
            views.append(
                AnsweredView(
                    code=code,
                    question=questions.question_view(order, code, locale),
                    value=answer.value,
                    display=questions.display_value(order, code, answer.value, locale),
                    source=answer.source,
                    editable=code in editable,
                )
            )
        return views

    def _title(self, order: Order, locale: str) -> str:
        for code in ("Q2", "SQ2"):
            if order.answer(code):
                return order.answer(code) or order.number
        category = order.answer("Q1")
        if category:
            return questions.display_value(order, "Q1", category, locale)
        return order.number

    def view(self, order: Order, locale: str | None = None, *, deduplicated: bool = False) -> OrderView:
        locale = locale if locale in ("bn", "en") else order.locale
        generation = None
        if order.generation is not None:
            generation = GenerationView(
                id=order.generation.id,
                status=order.generation.status,
                simulated=order.generation.simulated,
                plan_revision=order.generation.plan_revision,
                shots=[GenerationShotView(index=s.shot_index, status=s.status) for s in order.generation.shots],
                message=texts.pick(texts.GENERATION_MESSAGES[order.generation.status], locale),
                deduplicated=deduplicated,
            )
        logo = order.logo_asset()
        last_feedback = order.feedback[-1] if order.feedback else None
        return OrderView(
            id=order.id,
            number=order.number,
            title=self._title(order, locale),
            channel=order.channel,
            locale=order.locale,
            status=order.status,
            format=self._format_view(order, locale),
            photos=[self._asset_view(order, a, locale) for a in order.product_assets(usable_only=False)],
            logo=self._asset_view(order, logo, locale) if logo else None,
            answered=self._answered_views(order, locale),
            step=self._step_view(order, locale),
            plan=plan_view(order, locale),
            eligibility=self.eligibility(order, locale) if order.status == "PLAN_READY" else None,
            generation=generation,
            brand=BrandView(
                shop_name=order.answer("P1") or None,
                phone=questions.brand_phone(order),
                has_logo=logo is not None,
            ),
            feedback=FeedbackView(
                rating=last_feedback.rating,
                scene=last_feedback.scene,
                generation_id=last_feedback.generation_id,
            )
            if last_feedback
            else None,
            environment=self._environment_view(locale),
        )


# --- Wiring ------------------------------------------------------------------------------------

_service: OrderService | None = None


def build_order_service(settings: Settings) -> OrderService:
    root = Path(settings.storage_dir)
    repository: OrderRepository
    if settings.order_store == "memory":
        repository = InMemoryOrderRepository()
    else:
        repository = JsonFileOrderRepository(root / "orders")
    return OrderService(repository, LocalAssetStorage(root), get_video_provider(settings), settings)


def get_order_service() -> OrderService:
    global _service
    if _service is None:
        _service = build_order_service(get_settings())
    return _service


def reset_order_service() -> None:
    global _service
    _service = None
