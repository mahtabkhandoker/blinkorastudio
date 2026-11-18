"""Integration tests against the real Postgres-backed order repository
(ORDER_STORE=postgres), not the in-memory one the rest of the suite uses.
Verifies: data survives a fresh `OrderService`/repository instance ("the
process restarted"), idempotent plan confirmation still holds there, and
the row-level lock in `PostgresOrderRepository.locked()` prevents a
double-submit when two confirmations race for the same order."""

from __future__ import annotations

import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.orders.service import build_order_service, get_order_service, reset_order_service
from tests.conftest import AuthedTestClient


@pytest.fixture
def pg_client(monkeypatch):
    monkeypatch.setenv("ORDER_STORE", "postgres")
    get_settings.cache_clear()
    reset_order_service()
    c = AuthedTestClient(app)
    c.register_user("Postgres Seller")
    yield c
    get_settings.cache_clear()
    reset_order_service()


def _create_and_ready(client: TestClient) -> dict:
    from tests.test_orders import GOOD, answer, upload

    created = client.post("/api/orders", json={"channel": "web", "locale": "bn"})
    assert created.status_code == 201, created.text
    order = created.json()
    assert upload(client, order["id"], GOOD).status_code == 200
    view = answer(client, order["id"], "Q1", "clothing")
    view = answer(client, order["id"], "Q2", "red cotton saree")
    view = answer(client, order["id"], "GQ1", "heavy")
    assert view["plan"] is not None
    return view


def test_order_survives_a_simulated_backend_restart(pg_client):
    order = _create_and_ready(pg_client)

    # "Restart": drop the process-wide singleton and every cached settings
    # value, then build a brand new OrderService/repository from scratch —
    # nothing here is reused in-process.
    reset_order_service()
    get_settings.cache_clear()
    fresh_service = build_order_service(get_settings())
    owner_id = fresh_service.get_unchecked(order["id"]).owner_user_id

    reloaded = fresh_service.get(order["id"], owner_id)
    assert reloaded.id == order["id"]
    assert reloaded.plan is not None
    assert reloaded.plan.revision == order["plan"]["revision"]
    assert reloaded.answer("Q2") == "red cotton saree"


def test_duplicate_idempotency_key_does_not_create_two_generations(pg_client):
    order = _create_and_ready(pg_client)
    revision = order["plan"]["revision"]

    first = pg_client.post(
        f"/api/orders/{order['id']}/plan/confirm",
        json={"plan_revision": revision},
        headers={"Idempotency-Key": "race-key"},
    )
    second = pg_client.post(
        f"/api/orders/{order['id']}/plan/confirm",
        json={"plan_revision": revision},
        headers={"Idempotency-Key": "race-key"},
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["generation"]["id"] == second.json()["generation"]["id"]
    assert second.json()["generation"]["deduplicated"] is True


def test_concurrent_confirm_requests_submit_exactly_one_generation(pg_client):
    """Several threads race to confirm the same plan revision. They share
    this process's `OrderService._lock`, which alone would serialize them
    — this test does not by itself prove the Postgres row lock in
    `PostgresOrderRepository.locked()` is what's doing the work (that
    needs two separate processes/workers, which pytest doesn't give us
    here). What it does prove: the end-to-end confirm flow stays correct
    under concurrent callers and ends with exactly one generation, no
    duplicated or orphaned submissions."""
    order = _create_and_ready(pg_client)
    revision = order["plan"]["revision"]
    order_id = order["id"]
    results: list[int] = []

    def _confirm(key: str) -> None:
        response = pg_client.post(
            f"/api/orders/{order_id}/plan/confirm",
            json={"plan_revision": revision},
            headers={"Idempotency-Key": key},
        )
        results.append(response.status_code)

    threads = [threading.Thread(target=_confirm, args=(f"thread-{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(code == 200 for code in results), results

    service = get_order_service()
    final = service.get_unchecked(order_id)
    assert final.generation is not None
    # Every shot in the one generation was submitted exactly once.
    assert len({s.client_reference for s in final.generation.shots}) == len(final.generation.shots)


def test_repository_row_lock_serializes_two_independent_sessions(pg_client):
    """Exercises `PostgresOrderRepository.locked()` directly, bypassing
    `OrderService._lock` entirely, so this is the one test that actually
    isolates the DB-level lock: a second `locked()` call for the same
    order id must block until the first one's `with` block exits."""
    from app.repositories.postgres_orders import PostgresOrderRepository

    order = pg_client.post("/api/orders", json={"channel": "web", "locale": "bn"}).json()
    repo = PostgresOrderRepository()

    entered_first = threading.Event()
    release_first = threading.Event()
    second_entered_at: list[float] = []

    def _hold_lock() -> None:
        with repo.locked(order["id"]) as (_loaded, _save):
            entered_first.set()
            release_first.wait(timeout=5)

    def _try_lock() -> None:
        entered_first.wait(timeout=5)
        start = time.monotonic()
        with repo.locked(order["id"]) as (_loaded, _save):
            second_entered_at.append(time.monotonic() - start)

    first = threading.Thread(target=_hold_lock)
    second = threading.Thread(target=_try_lock)
    first.start()
    second.start()
    entered_first.wait(timeout=5)
    time.sleep(0.2)  # give the second thread a chance to block on the row lock
    release_first.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert second_entered_at, "second lock() call never completed"
    assert second_entered_at[0] >= 0.15  # it waited for the first to release, not a coincidence
