"""Registration, login, logout and session-restore endpoints.

Every response that establishes or confirms a session also (re)issues the
CSRF cookie, so the frontend always has a fresh token to echo back on the
next mutating request. See `app/services/auth/csrf.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_csrf
from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_db
from app.models.auth import LoginRequest, RegisterRequest, UserView
from app.services.auth.csrf import issue_csrf_cookie
from app.services.auth.errors import AuthError
from app.services.auth.rate_limit import RateLimiter
from app.services.auth.service import AuthService, CurrentUser, get_auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Dev-friendly single-process limiter; see rate_limit.py for the production note.
_login_limiter = RateLimiter(max_attempts=10, window_seconds=300)
_register_limiter = RateLimiter(max_attempts=10, window_seconds=300)


async def auth_error_handler(request: Request, exc: AuthError) -> Response:
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=exc.status_code, content={"error_code": exc.code, "detail": exc.detail, **exc.extra})


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, settings: Settings, raw_token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    issue_csrf_cookie(response, settings)


def _user_view(user) -> UserView:
    return UserView(id=user.id, email=user.email, display_name=user.display_name, created_at=user.created_at)


@router.post("/register", response_model=UserView, status_code=201)
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserView:
    if not _register_limiter.hit(_client_key(request)):
        raise AuthError("RATE_LIMITED", "Too many attempts. Try again in a few minutes.", 429)
    user = auth_service.register(db, body.email, body.password, body.display_name)
    raw_token = auth_service.create_session(db, user, request.headers.get("user-agent"), _client_key(request))
    _set_session_cookie(response, settings, raw_token)
    return _user_view(user)


@router.post("/login", response_model=UserView)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserView:
    if not _login_limiter.hit(_client_key(request)):
        raise AuthError("RATE_LIMITED", "Too many attempts. Try again in a few minutes.", 429)
    user = auth_service.authenticate(db, body.email, body.password)
    raw_token = auth_service.create_session(db, user, request.headers.get("user-agent"), _client_key(request))
    _set_session_cookie(response, settings, raw_token)
    return _user_view(user)


@router.post("/logout", status_code=204, dependencies=[Depends(get_current_user), Depends(require_csrf)])
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    raw_token = request.cookies.get(settings.session_cookie_name, "")
    auth_service.revoke_session(db, raw_token)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return Response(status_code=204)


@router.get("/me", response_model=UserView)
def me(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: CurrentUser = Depends(get_current_user),
) -> UserView:
    issue_csrf_cookie(response, settings)
    user = db.get(User, current_user.id)
    return _user_view(user)
