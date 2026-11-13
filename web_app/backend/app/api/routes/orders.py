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

from app.core.config import Settings, get_settings
from app.models.orders import (
    AnswerRequest,
    ConfirmPlanRequest,
    CreateOrderRequest,
    OrderOptionsView,
    OrderView,
    SetFormatRequest,
)
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
) -> OrderOptionsView:
    """What a client needs before an order exists: the F1 choices, upload
    limits and what is simulated. Also a cheap reachability check."""
    return service.options(locale, settings.max_upload_mb)


@router.post("", response_model=OrderView, status_code=201)
def create_order(
    body: CreateOrderRequest,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
) -> OrderView:
    order = service.create(body)
    return service.view(order, locale)


@router.get("/{order_id}", response_model=OrderView)
def get_order(
    order_id: str,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
) -> OrderView:
    return service.view(service.get(order_id), locale)


@router.put("/{order_id}/format", response_model=OrderView)
def set_format(
    order_id: str,
    body: SetFormatRequest,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
) -> OrderView:
    return service.view(service.set_format(order_id, body.format), locale)


@router.post("/{order_id}/assets", response_model=OrderView)
async def upload_asset(
    order_id: str,
    file: UploadFile = File(...),
    purpose: str = Form(default="product"),
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
    settings: Settings = Depends(get_settings),
) -> OrderView:
    data = await _read_capped(file, settings.max_upload_mb * 1024 * 1024)
    order = service.add_asset(order_id, purpose, (file.filename or "upload")[:200], data)
    return service.view(order, locale)


@router.get("/{order_id}/assets/{asset_id}/content")
def get_asset_content(
    order_id: str,
    asset_id: str,
    service: OrderService = Depends(get_order_service),
) -> FileResponse:
    path, mime_type = service.asset_file(order_id, asset_id)
    return FileResponse(path, media_type=mime_type, headers={"X-Content-Type-Options": "nosniff"})


@router.post("/{order_id}/answers", response_model=OrderView)
def post_answer(
    order_id: str,
    body: AnswerRequest,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
) -> OrderView:
    return service.view(service.answer(order_id, body.code, body.value, body.skip), locale)


@router.post("/{order_id}/plan/change", response_model=OrderView)
def request_plan_change(
    order_id: str,
    locale: str | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
) -> OrderView:
    return service.view(service.request_plan_change(order_id), locale)


@router.post("/{order_id}/plan/confirm", response_model=OrderView)
def confirm_plan(
    order_id: str,
    body: ConfirmPlanRequest,
    locale: str | None = Query(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: OrderService = Depends(get_order_service),
) -> OrderView:
    order, deduplicated = service.confirm_plan(order_id, body.plan_revision, idempotency_key or "")
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
    return service.operator_record(service.get(order_id))
