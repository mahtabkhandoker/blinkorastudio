"""Asset validation endpoint (server-side parity; not yet the primary path
— see services/assets/validator.py's module docstring).
"""

from __future__ import annotations

import re

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.assets import AssetInfo
from app.services.assets.validator import analyze_image_bytes, status_for_warning
from app.services.chatbot.system_prompt import ASSET_STATUS_MESSAGES

router = APIRouter(prefix="/api/assets", tags=["assets"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_filename(filename: str) -> str:
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return _UNSAFE_FILENAME_CHARS.sub("_", base)[:200] or "upload"


@router.post("/{asset_id}/validate", response_model=AssetInfo)
async def validate_asset(asset_id: str, file: UploadFile = File(...)) -> AssetInfo:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    content_type = file.content_type or "application/octet-stream"
    analysis = analyze_image_bytes(data, content_type)
    status = status_for_warning(analysis.warning_code)
    warning_message = None
    if analysis.warning_code:
        warning_message = ASSET_STATUS_MESSAGES[analysis.warning_code]["bn"]
    elif status == "VALID":
        warning_message = None

    return AssetInfo(
        id=asset_id,
        filename=sanitize_filename(file.filename or "upload"),
        mime_type=content_type,
        status=status,  # type: ignore[arg-type]
        warning_code=analysis.warning_code,
        warning_message=warning_message,
        width=analysis.width or None,
        height=analysis.height or None,
    )
