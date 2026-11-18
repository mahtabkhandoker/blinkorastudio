"""Shared FastAPI dependencies: the authenticated-user resolver and the
CSRF guard, used by every customer-facing mutating route."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.auth.csrf import require_csrf as _require_csrf
from app.services.auth.service import AuthService, CurrentUser, get_auth_service


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    raw_token = request.cookies.get(settings.session_cookie_name, "")
    return auth_service.resolve_session(db, raw_token)


def require_csrf(request: Request, settings: Settings = Depends(get_settings)) -> None:
    _require_csrf(request, settings)
