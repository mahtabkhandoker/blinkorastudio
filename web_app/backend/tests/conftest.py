from __future__ import annotations

import itertools
import os

os.environ.setdefault("CHATBOT_PROVIDER", "mock")
os.environ["ORDER_STORE"] = "memory"
os.environ["MOCK_GENERATION_SECONDS"] = "0"
# Auth always lives in Postgres regardless of ORDER_STORE; point tests at a
# dedicated database so repeated runs never collide with dev data or each
# other (see "CREATE DATABASE blinkora_test" in the P0.5 README).
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://blinkora:blinkora_dev@localhost:55432/blinkora_test"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.routes.auth import _login_limiter, _register_limiter
from app.core.config import get_settings
from app.db import models  # noqa: F401 - registers tables on Base.metadata
from app.db.base import Base
from app.db.session import get_engine
from app.main import app
from app.services.orders.service import reset_order_service

Base.metadata.create_all(get_engine())

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_user_seq = itertools.count(1)


class AuthedTestClient(TestClient):
    """A `TestClient` that mirrors what the real frontend API client does:
    read the (non-httponly) CSRF cookie this session was issued and echo
    it back as a header on every state-changing request. Order-route
    tests below don't have to know CSRF exists; `register_user()` is the
    only thing that needs to think about auth."""

    def request(self, method: str, url, **kwargs):  # type: ignore[override]
        if method.upper() in _UNSAFE_METHODS:
            csrf_cookie = self.cookies.get(get_settings().csrf_cookie_name)
            if csrf_cookie:
                headers = dict(kwargs.get("headers") or {})
                headers.setdefault("X-CSRF-Token", csrf_cookie)
                kwargs["headers"] = headers
        return super().request(method, url, **kwargs)

    def register_user(self, display_name: str = "Test Seller") -> dict:
        email = f"user{next(_user_seq)}-{id(self)}@test.local"
        response = self.post(
            "/api/auth/register",
            json={"email": email, "password": "test-pass-123", "display_name": display_name},
        )
        assert response.status_code == 201, response.text
        return response.json()


@pytest.fixture(autouse=True)
def _clear_settings_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    reset_order_service()
    # The auth rate limiters are process-global and key on client IP; every
    # TestClient in this suite looks like the same host ("testclient"), so
    # without a reset the fixed window fills up after a handful of tests.
    _login_limiter.reset()
    _register_limiter.reset()
    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE auth_sessions, identity_links, orders, users, order_sequence RESTART IDENTITY CASCADE"))
    yield
    get_settings.cache_clear()
    reset_order_service()


@pytest.fixture
def client() -> TestClient:
    """A logged-in seller. Every order-route test that predates P0.5 uses
    this fixture unchanged: it is now also an authenticated session, so
    those tests exercise the real auth+ownership path without having to
    mention it."""
    c = AuthedTestClient(app)
    c.register_user()
    return c


@pytest.fixture
def other_client() -> TestClient:
    """A second, different seller — for cross-user authorization tests."""
    c = AuthedTestClient(app)
    c.register_user("Other Seller")
    return c
