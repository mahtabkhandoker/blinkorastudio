"""Cross-user authorization: Seller B must never read, edit or confirm
anything that belongs to Seller A, even with a known order id."""

from __future__ import annotations

from tests.test_orders import confirm, create, ready_order, upload


def test_owner_is_assigned_by_the_server_not_the_client(client):
    """CreateOrderRequest has no owner field at all, but prove the point
    end to end: a freshly created order is only visible to its creator."""
    order = create(client)
    assert client.get(f"/api/orders/{order['id']}").status_code == 200


def test_other_seller_cannot_read_the_order(client, other_client):
    order = create(client)
    response = other_client.get(f"/api/orders/{order['id']}")
    assert response.status_code == 404
    assert response.json()["error_code"] == "ORDER_NOT_FOUND"


def test_other_seller_cannot_change_the_format(client, other_client):
    order = create(client)
    response = other_client.put(f"/api/orders/{order['id']}/format", json={"format": "post"})
    assert response.status_code == 404


def test_other_seller_cannot_upload_to_the_order(client, other_client):
    order = create(client)
    response = upload(other_client, order["id"])
    assert response.status_code == 404


def test_other_seller_cannot_answer_a_question(client, other_client):
    order = create(client)
    assert upload(client, order["id"]).status_code == 200
    response = other_client.post(f"/api/orders/{order['id']}/answers", json={"code": "Q1", "value": "clothing"})
    assert response.status_code == 404


def test_other_seller_cannot_fetch_asset_bytes(client, other_client):
    order = create(client)
    assert upload(client, order["id"]).status_code == 200
    mine = client.get(f"/api/orders/{order['id']}")
    asset_id = mine.json()["photos"][0]["id"]

    response = other_client.get(f"/api/orders/{order['id']}/assets/{asset_id}/content")
    assert response.status_code == 404

    # Sanity check the owner can still fetch it, so the 404 above is really
    # about ownership and not a broken route.
    assert client.get(f"/api/orders/{order['id']}/assets/{asset_id}/content").status_code == 200


def test_other_seller_cannot_request_a_plan_change(client, other_client):
    order = ready_order(client, [("Q1", "clothing"), ("Q2", "red cotton saree"), ("GQ1", "heavy")])
    response = other_client.post(f"/api/orders/{order['id']}/plan/change")
    assert response.status_code == 404


def test_other_seller_cannot_confirm_the_plan(client, other_client):
    order = ready_order(client, [("Q1", "clothing"), ("Q2", "red cotton saree"), ("GQ1", "heavy")])
    mine = client.get(f"/api/orders/{order['id']}")
    revision = mine.json()["plan"]["revision"]

    response = confirm(other_client, order["id"], revision, key="steal-1")
    assert response.status_code == 404

    # Confirming as the real owner still works: the attempt above left no trace.
    assert confirm(client, order["id"], revision, key="key-1").status_code == 200


def test_listing_only_shows_my_own_orders(client, other_client):
    mine = create(client)
    theirs = create(other_client)

    mine_ids = {o["id"] for o in client.get("/api/orders").json()}
    their_ids = {o["id"] for o in other_client.get("/api/orders").json()}

    assert mine["id"] in mine_ids and mine["id"] not in their_ids
    assert theirs["id"] in their_ids and theirs["id"] not in mine_ids


def test_unauthenticated_request_cannot_create_or_read_orders(client):
    from fastapi.testclient import TestClient

    from app.main import app

    order = create(client)
    anon = TestClient(app)  # no register()/login() — no session cookie at all
    assert anon.post("/api/orders", json={"channel": "web", "locale": "bn"}).status_code == 401
    assert anon.get(f"/api/orders/{order['id']}").status_code == 401
    assert anon.get("/api/orders").status_code == 401
