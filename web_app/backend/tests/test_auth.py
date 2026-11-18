"""Registration, login, logout, session restore, CSRF and rate limiting."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from tests.conftest import AuthedTestClient


def _client() -> AuthedTestClient:
    return AuthedTestClient(app)


def _register(c: TestClient, email: str, password: str = "test-pass-123", name: str = "Seller") -> "object":
    return c.post("/api/auth/register", json={"email": email, "password": password, "display_name": name})


def test_register_sets_httponly_session_cookie_and_csrf_cookie():
    c = _client()
    response = _register(c, "alice@example.com")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert "password" not in body and "password_hash" not in body

    settings = get_settings()
    session_cookie = next(h for h in response.headers.get_list("set-cookie") if h.startswith(settings.session_cookie_name))
    assert "HttpOnly" in session_cookie
    assert "SameSite=lax" in session_cookie or "samesite=lax" in session_cookie.lower()

    csrf_cookie = next(h for h in response.headers.get_list("set-cookie") if h.startswith(settings.csrf_cookie_name))
    assert "HttpOnly" not in csrf_cookie  # must be JS-readable for the double-submit pattern


def test_duplicate_email_is_rejected():
    c = _client()
    assert _register(c, "dupe@example.com").status_code == 201
    second = _register(c, "dupe@example.com")
    assert second.status_code == 409
    assert second.json()["error_code"] == "EMAIL_TAKEN"


def test_email_is_case_insensitive_for_uniqueness_and_login():
    c = _client()
    assert _register(c, "Case@Example.com").status_code == 201
    assert _register(c, "case@example.com").status_code == 409

    login = c.post("/api/auth/login", json={"email": "CASE@EXAMPLE.COM", "password": "test-pass-123"})
    assert login.status_code == 200


def test_wrong_password_and_unknown_email_give_the_same_generic_error():
    c = _client()
    _register(c, "bob@example.com")

    wrong_password = c.post("/api/auth/login", json={"email": "bob@example.com", "password": "not-it-at-all"})
    unknown_email = c.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json()["error_code"] == unknown_email.json()["error_code"] == "INVALID_CREDENTIALS"
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


def test_me_requires_a_session_and_logout_revokes_it():
    c = _client()
    anon = c.get("/api/auth/me")
    assert anon.status_code == 401

    _register(c, "carol@example.com")
    assert c.get("/api/auth/me").status_code == 200

    logout = c.post("/api/auth/logout")
    assert logout.status_code == 204
    assert c.get("/api/auth/me").status_code == 401


def test_csrf_header_is_required_for_mutating_order_routes(client):
    """`client` (conftest) auto-attaches the CSRF header; bypass that here
    to prove the server actually enforces it rather than just trusting a
    well-behaved caller."""
    settings = get_settings()
    csrf_cookie = client.cookies.get(settings.csrf_cookie_name)
    assert csrf_cookie

    # super().request bypasses AuthedTestClient's auto-injection.
    response = TestClient.request(client, "POST", "/api/orders", json={"channel": "web", "locale": "bn"})
    assert response.status_code == 403
    assert response.json()["error_code"] == "CSRF_FAILED"

    with_header = TestClient.request(
        client, "POST", "/api/orders", json={"channel": "web", "locale": "bn"}, headers={"X-CSRF-Token": csrf_cookie}
    )
    assert with_header.status_code == 201


def test_login_is_rate_limited():
    c = _client()
    _register(c, "dave@example.com")
    settings = get_settings()

    for _ in range(settings.auth_rate_limit_attempts):
        c.post("/api/auth/login", json={"email": "dave@example.com", "password": "wrong"})

    blocked = c.post("/api/auth/login", json={"email": "dave@example.com", "password": "wrong"})
    assert blocked.status_code == 429
    assert blocked.json()["error_code"] == "RATE_LIMITED"
