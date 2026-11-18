"""Registration, login and session lifecycle.

Sessions are server-side rows (`AuthSession`); the cookie only carries a
random opaque token. Only `sha256(token)` is ever stored, so a stolen
database snapshot cannot be replayed as a live cookie, and revoking a
session (logout, or an admin action later) takes effect immediately
everywhere — unlike a signed/stateless token, which would stay valid
until it expired.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import AuthSession, User
from app.services.auth.errors import AuthError
from app.services.auth.passwords import hash_password, needs_rehash, verify_password

SESSION_TOKEN_BYTES = 32


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    display_name: str
    role: str


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # --- Registration / login --------------------------------------------------

    def register(self, db: Session, email: str, password: str, display_name: str) -> User:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise AuthError("EMAIL_TAKEN", "An account with this email already exists.", 409)
        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            role="customer",
            status="active",
        )
        db.add(user)
        db.flush()
        return user

    def authenticate(self, db: Session, email: str, password: str) -> User:
        """Raises AuthError with the same code/message whether the email is
        unknown or the password is wrong, so a client cannot enumerate
        accounts by comparing error responses."""
        generic = AuthError("INVALID_CREDENTIALS", "Invalid email or password.", 401)
        user = db.scalar(select(User).where(User.email == email))
        if user is None or user.status != "active":
            # Still runs a hash verification so the response time doesn't
            # leak whether the account exists.
            verify_password("$argon2id$v=19$m=65536,t=3,p=4$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", password)
            raise generic
        if not verify_password(user.password_hash, password):
            raise generic
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        return user

    # --- Sessions ---------------------------------------------------------------

    def create_session(self, db: Session, user: User, user_agent: str | None, ip_address: str | None) -> str:
        raw_token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
        session = AuthSession(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=utcnow() + timedelta(days=self._settings.session_ttl_days),
            user_agent=(user_agent or "")[:300] or None,
            ip_address=(ip_address or "")[:64] or None,
        )
        db.add(session)
        db.flush()
        return raw_token

    def resolve_session(self, db: Session, raw_token: str) -> CurrentUser:
        unauthorized = AuthError("UNAUTHORIZED", "Please log in to continue.", 401)
        if not raw_token:
            raise unauthorized
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == _hash_token(raw_token)))
        if session is None or session.revoked_at is not None:
            raise unauthorized
        now = utcnow()
        if session.expires_at <= now:
            raise unauthorized
        # Sliding expiry: once more than half the TTL has elapsed, push the
        # session's expiry back out so an active user is never logged out
        # mid-session, while an abandoned cookie still expires on schedule.
        ttl = timedelta(days=self._settings.session_ttl_days)
        if session.expires_at - now < ttl / 2:
            session.expires_at = now + ttl
        user = db.get(User, session.user_id)
        if user is None or user.status != "active":
            raise unauthorized
        return CurrentUser(id=user.id, email=user.email, display_name=user.display_name, role=user.role)

    def revoke_session(self, db: Session, raw_token: str) -> None:
        if not raw_token:
            return
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == _hash_token(raw_token)))
        if session is not None and session.revoked_at is None:
            session.revoked_at = utcnow()


_service: AuthService | None = None


def get_auth_service() -> AuthService:
    global _service
    if _service is None:
        from app.core.config import get_settings

        _service = AuthService(get_settings())
    return _service


def reset_auth_service() -> None:
    global _service
    _service = None
