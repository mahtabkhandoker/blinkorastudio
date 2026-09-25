"""Server-side asset (image) quality validation.

Mirrors the frontend's client-side canvas heuristics
(`lib/chat/image-analysis.ts`) in Python using Pillow, for parity and so
the same checks can run server-side if/when uploads are proxied through
the backend. NOT currently wired to the frontend upload flow — the
existing client-side canvas validation already gives instant feedback
and matches the required copy exactly, so it remains the primary path
(see the integration report for details). This module exists so the
`/api/assets/{id}/validate` endpoint is real and testable, ready to
become the primary path later (e.g. if uploads move server-side for
storage reasons).
"""

from __future__ import annotations

import io

from PIL import Image, ImageFilter, ImageStat

from app.models.assets import AssetWarningCode

SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MIN_DIMENSION = 480
DARK_BRIGHTNESS_THRESHOLD = 55.0
BLUR_VARIANCE_THRESHOLD = 18.0
EXTREME_ASPECT_RATIO = 2.6


class AssetAnalysis:
    def __init__(self, width: int, height: int, warning_code: AssetWarningCode | None):
        self.width = width
        self.height = height
        self.warning_code = warning_code


def analyze_image_bytes(data: bytes, content_type: str) -> AssetAnalysis:
    if content_type not in SUPPORTED_CONTENT_TYPES:
        return AssetAnalysis(0, 0, "UNSUPPORTED")

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception:  # noqa: BLE001 - any decode failure is a corrupt upload
        return AssetAnalysis(0, 0, "CORRUPT")

    width, height = image.size
    if not width or not height:
        return AssetAnalysis(0, 0, "CORRUPT")

    grayscale = image.convert("L")
    brightness = ImageStat.Stat(grayscale).mean[0]

    # Downscale for a fast, resolution-independent sharpness estimate.
    thumb = grayscale.copy()
    thumb.thumbnail((256, 256))
    edges = thumb.filter(ImageFilter.FIND_EDGES)
    sharpness = ImageStat.Stat(edges).stddev[0]

    aspect_ratio = max(width / height, height / width)

    warning_code: AssetWarningCode | None = None
    if min(width, height) < MIN_DIMENSION:
        warning_code = "LOW_RESOLUTION"
    elif aspect_ratio > EXTREME_ASPECT_RATIO:
        warning_code = "CROPPED"
    elif brightness < DARK_BRIGHTNESS_THRESHOLD:
        warning_code = "TOO_DARK"
    elif sharpness < BLUR_VARIANCE_THRESHOLD:
        warning_code = "BLURRY"

    return AssetAnalysis(width, height, warning_code)


def status_for_warning(warning_code: AssetWarningCode | None) -> str:
    if warning_code is None:
        return "VALID"
    if warning_code in ("CORRUPT", "UNSUPPORTED"):
        return "REJECTED"
    return "WARNING"
