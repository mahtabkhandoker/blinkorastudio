"""Server-side intake of uploaded images: validation and local storage.

Validation trusts the bytes, not the client. The type is taken from what
Pillow actually decodes; the browser's MIME type and the file name are
ignored for that decision.

`LocalAssetStorage` writes to disk under STORAGE_DIR. That is real
server-side storage for development, not production object storage.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.services.assets.validator import analyze_image_bytes
from app.services.orders.errors import OrderError

_FORMATS: dict[str, tuple[str, str]] = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


@dataclass(frozen=True)
class ImageInfo:
    mime_type: str
    extension: str
    width: int
    height: int
    sha256: str
    warning_code: str | None


def inspect_image(data: bytes, *, max_bytes: int, max_pixels: int, quality_checks: bool) -> ImageInfo:
    if not data:
        raise OrderError("EMPTY_FILE", "The uploaded file is empty.", 422)
    if len(data) > max_bytes:
        raise OrderError("FILE_TOO_LARGE", "The uploaded file is too large.", 413)

    try:
        with Image.open(io.BytesIO(data)) as probe:
            image_format = probe.format or ""
            width, height = probe.size
    except Exception as exc:  # noqa: BLE001 - not an image Pillow can read
        raise OrderError("UNSUPPORTED_IMAGE", "The file is not a supported image.", 422) from exc

    if image_format not in _FORMATS:
        raise OrderError("UNSUPPORTED_IMAGE", f"{image_format or 'This'} images are not supported.", 422)
    if width * height > max_pixels:
        # Checked from the header, before decoding, so a decompression bomb
        # is rejected without being expanded in memory.
        raise OrderError("IMAGE_TOO_MANY_PIXELS", "The image dimensions are too large.", 422)

    mime_type, extension = _FORMATS[image_format]
    analysis = analyze_image_bytes(data, mime_type)
    if analysis.warning_code == "CORRUPT":
        raise OrderError("CORRUPT_IMAGE", "The image could not be decoded.", 422)

    return ImageInfo(
        mime_type=mime_type,
        extension=extension,
        width=analysis.width,
        height=analysis.height,
        sha256=hashlib.sha256(data).hexdigest(),
        warning_code=analysis.warning_code if quality_checks else None,
    )


class LocalAssetStorage:
    name = "local_disk_dev"

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if self._root not in path.parents:
            raise ValueError("storage key escapes the storage root")
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def exists(self, key: str) -> bool:
        return self.path_for(key).is_file()
