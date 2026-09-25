"""Asset (uploaded image) state, mirroring `UploadedAsset` in the frontend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

AssetStatus = Literal["UPLOADING", "PROCESSING", "VALID", "WARNING", "REJECTED"]

AssetWarningCode = Literal[
    "BLURRY", "LOW_RESOLUTION", "TOO_DARK", "CROPPED", "CORRUPT", "UNSUPPORTED"
]


class AssetInfo(BaseModel):
    id: str
    filename: str
    mime_type: str = "image/jpeg"
    status: AssetStatus
    warning_code: AssetWarningCode | None = None
    warning_message: str | None = None
    width: int | None = None
    height: int | None = None


def has_usable_asset(assets: list[AssetInfo]) -> bool:
    """An asset the user has accepted (valid, or a warning they kept)."""
    return any(a.status in ("VALID", "WARNING") for a in assets)
