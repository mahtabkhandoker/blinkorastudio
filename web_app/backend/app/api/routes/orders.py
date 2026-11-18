"""P0 order workflow API.

Every customer-facing route returns an `OrderView`: the current state of
the order plus the single next step. The client renders that and sends
back the customer's input; it does not decide the flow.

Errors are `{"error_code", "detail", "message"}`. `message` is a localized
sentence when one exists; `detail` is for developers.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.api.deps import get_current_user, require_csrf
from app.core.config import Settings, get_settings
from app.models.orders import (
    AnswerRequest,
    ConfirmPlanRequest,
    CreateOrderRequest,
    OrderOptionsView,
    OrderSummaryView,
    OrderView,
    SetFormatRequest,
)
from app.services.auth.service import CurrentUser
from app.services.orders import texts
from app.services.orders.errors import OrderError
from app.services.orders.service import OrderService, get_order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])
internal_router = APIRouter(prefix="/api/internal/orders", tags=["internal"])

_READ_CHUNK = 1024 * 1024


async def order_error_handler(request: Request, exc: OrderError) -> JSONResponse:
    locale = request.query_params.get("locale", "bn")
    message = None
    if exc.code in texts.UPLOAD_ERRORS:
        message = texts.pick(texts.UPLOAD_ERRORS[exc.code], locale).format(mb=get_settings().max_upload_mb)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.code, "detail": exc.detail, "message": message, **exc.extra},
    )


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Reads an upload without ever holding more than the cap in memory."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise OrderError("FILE_TOO_LARGE", "The uploaded file is too large.", 413)
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/options", response_model=OrderOptionsView)
def get_order_options(
    locale: str = Query(default="bn"),
    service: OrderService = Depends(get_order_service),
    settings: Settings = Depends(get_settings),
    _current_user: CurrentUser = Depends(get_current_user),
) -> OrderOptionsView:
    """What a client needs before an order exists: the F1 choices, upload
    limits and what is simulated. Also a cheap reachability check."""
    return service.options(locale, settings.max_upload_mb)


@router.get("", response_model=list[OrderSummaryView])
def list_my_orders(
    service: OrderService = Depends(get_order_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[OrderSummaryView]:
    """The signed-in seller's own orders, newest first — backs the "My
    Orders" dashboard. Never takes an owner id from the client: it is
    always the authenticated session's user."""
    orders = service.list_mine(current_user.id)
    return [
        OrderSummaryView(
            id=o.id,
            number=o.number,
            title=service.view(o).title,
            status=o.status,
            updated_at=o.updated_at,
        )
        for o in orders
    ]


@router.post("", response_model=OrderView, status_code=201, dependencies=[Depends(get_current_user), Depends(require_csrf)])
def create_order(
    body: CreateOrderRequest,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderView:
    order = service.create(body, current_user.id)
    return service.view(order, locale)


@router.get("/{order_id}", response_model=OrderView)
def get_order(
    order_id: str,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderView:
    return service.view(service.get(order_id, current_user.id), locale)


@router.put("/{order_id}/format", response_model=OrderView, dependencies=[Depends(get_current_user), Depends(require_csrf)])
def set_format(
    order_id: str,
    body: SetFormatRequest,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderView:
    return service.view(service.set_format(order_id, body.format, current_user.id), locale)


@router.post("/{order_id}/assets", response_model=OrderView, dependencies=[Depends(get_current_user), Depends(require_csrf)])
async def upload_asset(
    order_id: str,
    file: UploadFile = File(...),
    purpose: str = Form(default="product"),
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
    settings: Settings = Depends(get_settings),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderView:
    data = await _read_capped(file, settings.max_upload_mb * 1024 * 1024)
    order = service.add_asset(order_id, purpose, (file.filename or "upload")[:200], data, current_user.id)
    return service.view(order, locale)


@router.get("/{order_id}/assets/{asset_id}/content")
def get_asset_content(
    order_id: str,
    asset_id: str,
    service: OrderService = Depends(get_order_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> FileResponse:
    path, mime_type = service.asset_file(order_id, asset_id, current_user.id)
    return FileResponse(path, media_type=mime_type, headers={"X-Content-Type-Options": "nosniff"})


@router.post("/{order_id}/answers", response_model=OrderView, dependencies=[Depends(get_current_user), Depends(require_csrf)])
def post_answer(
    order_id: str,
    body: AnswerRequest,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderView:
    return service.view(service.answer(order_id, body.code, body.value, body.skip, current_user.id), locale)


@router.post("/{order_id}/plan/change", response_model=OrderView, dependencies=[Depends(get_current_user), Depends(require_csrf)])
def request_plan_change(
    order_id: str,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderView:
    return service.view(service.request_plan_change(order_id, current_user.id), locale)


@router.post("/{order_id}/plan/confirm", response_model=OrderView, dependencies=[Depends(get_current_user), Depends(require_csrf)])
def confirm_plan(
    order_id: str,
    body: ConfirmPlanRequest,
    locale: str | None = Query(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: OrderService = Depends(get_order_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderView:
    order, deduplicated = service.confirm_plan(order_id, body.plan_revision, idempotency_key or "", current_user.id)
    return service.view(order, locale, deduplicated=deduplicated)


@internal_router.get("/{order_id}")
def get_operator_record(
    order_id: str,
    operator_token: str | None = Header(default=None, alias="X-Operator-Token"),
    service: OrderService = Depends(get_order_service),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Full record including English prompts. Off unless OPERATOR_API_TOKEN
    is set; it must never be called from a customer-facing client."""
    expected = settings.operator_api_token
    if not expected or not operator_token or not hmac.compare_digest(operator_token, expected):
        raise OrderError("NOT_FOUND", "Not found.", 404)
    return service.operator_record(service.get_unchecked(order_id))
