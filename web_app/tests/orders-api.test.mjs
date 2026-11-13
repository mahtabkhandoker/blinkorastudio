// Unit tests for the order API client: what the web app does when the
// backend is missing, slow, or says no. Run with `npm run test:unit`.
import assert from "node:assert/strict";
import { test } from "node:test";

import { OrderApiError, confirmIdempotencyKey, createOrderApi, kindForStatus } from "../lib/api/orders.ts";

function jsonResponse(status, body) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

test("a network failure is reported as unavailable and never returns an order", async () => {
  const api = createOrderApi("http://backend.invalid", "bn", async () => {
    throw new TypeError("fetch failed");
  });
  await assert.rejects(api.createOrder({ format: "reels" }), (error) => {
    assert.ok(error instanceof OrderApiError);
    assert.equal(error.kind, "unavailable");
    return true;
  });
});

test("a timeout is reported as unavailable", async () => {
  const hang = (_url, init) =>
    new Promise((_resolve, reject) => {
      init.signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
    });
  const api = createOrderApi("http://backend.test", "bn", hang, 20);
  await assert.rejects(api.getOrder("abc"), (error) => error.kind === "unavailable");
});

test("a 5xx or an unreadable body is unavailable, not a success", async () => {
  const down = createOrderApi("http://backend.test", "bn", async () => new Response("Bad gateway", { status: 502 }));
  await assert.rejects(down.getOptions(), (error) => error.kind === "unavailable" && error.status === 502);

  const garbled = createOrderApi("http://backend.test", "bn", async () => new Response("<html>", { status: 200 }));
  await assert.rejects(garbled.getOptions(), (error) => error.kind === "unavailable");
});

test("backend error codes and localized messages are preserved", async () => {
  const api = createOrderApi("http://backend.test", "en", async () =>
    jsonResponse(422, { error_code: "UNSUPPORTED_IMAGE", detail: "nope", message: "Use a JPG, PNG or WebP image." }),
  );
  await assert.rejects(api.answer("id", "Q1", "x"), (error) => {
    assert.equal(error.kind, "invalid");
    assert.equal(error.code, "UNSUPPORTED_IMAGE");
    assert.equal(error.userMessage, "Use a JPG, PNG or WebP image.");
    return true;
  });
});

test("status codes map to the right kind", () => {
  assert.equal(kindForStatus(404), "not_found");
  assert.equal(kindForStatus(409), "conflict");
  assert.equal(kindForStatus(413), "invalid");
  assert.equal(kindForStatus(503), "unavailable");
});

test("confirm sends the plan revision and a stable idempotency key", async () => {
  const calls = [];
  const api = createOrderApi("http://backend.test/", "bn", async (url, init) => {
    calls.push({ url, init });
    return jsonResponse(200, { id: "order-1" });
  });
  await api.confirmPlan("order-1", 3);
  await api.confirmPlan("order-1", 3);

  assert.equal(calls[0].url, "http://backend.test/api/orders/order-1/plan/confirm?locale=bn");
  assert.deepEqual(JSON.parse(calls[0].init.body), { plan_revision: 3 });
  // A retried tap reuses the same key, so the backend can deduplicate it.
  assert.equal(calls[0].init.headers["Idempotency-Key"], calls[1].init.headers["Idempotency-Key"]);
  assert.equal(calls[0].init.headers["Idempotency-Key"], confirmIdempotencyKey("order-1", 3));
  assert.notEqual(confirmIdempotencyKey("order-1", 3), confirmIdempotencyKey("order-1", 4));
});

test("asset URLs point at the backend, not at a blob", () => {
  const api = createOrderApi("http://backend.test", "bn", async () => jsonResponse(200, {}));
  assert.equal(
    api.assetUrl({ content_path: "/api/orders/o/assets/a/content" }),
    "http://backend.test/api/orders/o/assets/a/content",
  );
});
