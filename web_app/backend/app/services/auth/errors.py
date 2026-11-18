from __future__ import annotations

from typing import Any


class AuthError(Exception):
    def __init__(self, code: str, detail: str, status_code: int, extra: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code
        self.extra = extra or {}
