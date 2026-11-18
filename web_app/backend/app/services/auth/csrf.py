"""Double-submit-cookie CSRF protection for cookie-authenticated requests.

The session cookie is httponly (a cross-site page cannot read it, but the
browser still attaches it automatically to a forged request). The csrf
cookie is deliberately *not* httponly so same-origin JS can read it and
echo it back in a header; a cross-site attacker's forged request has no
way to read that cookie and so cannot set the matching header.
"""

from __future__ import annotations

import hmac
import secrets

from fastapi import Request, Response

from app.core.config import Settings
from app.services.auth.errors import AuthError

CSRF_HEADER = "X-CSRF-Token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def issue_csrf_cookie(response: Response, settings: Settings) -> None:
    response.set_cookie(
        settings.csrf_cookie_name,
        secrets.token_urlsafe(24),
        max_age=settings.session_ttl_days * 86400,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def require_csrf(request: Request, settings: Settings) -> None:
    if request.method not in UNSAFE_METHODS:
        return
    cookie_value = request.cookies.get(settings.csrf_cookie_name)
    header_value = request.headers.get(CSRF_HEADER)
    if not cookie_value or not header_value or not hmac.compare_digest(cookie_value, header_value):
        raise AuthError("CSRF_FAILED", "Missing or invalid CSRF token.", 403)
