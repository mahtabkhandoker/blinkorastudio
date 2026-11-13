"""Typed errors for the order workflow. Routes turn these into JSON
`{"error_code": ..., "detail": ...}` responses with the given status."""

from __future__ import annotations


class OrderError(Exception):
    def __init__(self, code: str, detail: str, status_code: int = 400, extra: dict | None = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code
        self.extra = extra or {}
