# Blinkora Studio backend

FastAPI backend for the P0 order workflow and P0.5 auth/persistence.

## Local setup

```bash
cd web_app/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # edit if needed; defaults work for local dev
```

### Database (Postgres via Docker Compose)

```bash
docker compose up -d        # Postgres on host port 55432 (not 5432, to
                             # avoid clashing with a native install)
.venv/bin/alembic upgrade head
```

No Docker? Point `DATABASE_URL` in `.env` at any Postgres 14+ instance you
run natively, create the database/user it names, then run the same
`alembic upgrade head`.

### Run

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Tests

```bash
.venv/bin/python -m pytest -q
```

Most tests use `ORDER_STORE=memory` (set by `tests/conftest.py`) and
never touch the order tables. Auth always uses Postgres, so tests point
`DATABASE_URL` at a separate `blinkora_test` database (create it once:
`docker exec blinkora_studio_postgres psql -U blinkora -d blinkora -c
"CREATE DATABASE blinkora_test OWNER blinkora;"`) and truncate its
tables between tests — it is never the dev database. A few tests in
`tests/test_postgres_persistence.py` switch `ORDER_STORE=postgres` for
the duration of the test to exercise the real repository, including a
direct test of the `SELECT ... FOR UPDATE` row lock used during plan
confirmation.

## Frontend

```bash
cd web_app
npm install
cp .env.example .env.local   # NEXT_PUBLIC_CHAT_API_URL=http://localhost:8000
npm run dev
```

## Auth architecture (P0.5)

- Registration/login hash passwords with **argon2id** (`argon2-cffi`),
  never store them plaintext, and never reveal via the login error
  whether an email exists (`INVALID_CREDENTIALS` either way).
- A session is a Postgres row (`auth_sessions`); the cookie
  (`blinkora_session`, httponly, `SameSite=Lax`, `Secure` when
  `COOKIE_SECURE=true`) carries only a random token — only its SHA-256
  hash is stored, so a DB dump can't be replayed as a live cookie.
  Sessions expire after `SESSION_TTL_DAYS` (sliding: refreshed once more
  than half the TTL has elapsed) and can be revoked (logout) immediately.
- CSRF: a second, readable cookie (`blinkora_csrf`) must be echoed back
  as `X-CSRF-Token` on every state-changing request once a session
  exists (double-submit pattern) — enforced on all order-mutating routes
  and on logout.
- Login/register are rate-limited (in-memory, per IP; see "Known
  limitations").
- `role` defaults to `"customer"` and is never settable from a request
  body — there is no API path to self-promote.

## Authorization strategy (ownership)

Every customer-facing order route resolves the signed-in user from the
session cookie (`get_current_user`) and the service layer checks
`order.owner_user_id` before returning or mutating anything
(`OrderService._check_owner`). A mismatch or a missing order both return
the same `404 ORDER_NOT_FOUND` — never `403` — so a seller can't learn
that a guessed order id belongs to someone else. The operator endpoint
(`/api/internal/orders/{id}`) is a separate, token-gated path
(`OPERATOR_API_TOKEN`) that bypasses ownership entirely by design, and is
not reachable from any customer-facing client.

## Data model

`users`, `auth_sessions`, `identity_links` (schema only — reserved for a
future verified WhatsApp-to-account link; nothing writes to it yet) are
real relational tables. `orders` keeps `owner_user_id`, `number`,
`channel`, `status` as indexed columns (what authorization and the "My
Orders" listing filter on) and stores the full order aggregate — answers,
creative plan, asset metadata, generation, feedback, event log — as one
JSONB document per row. That's an explicit simplification: the P0
business logic in `app/services/orders/*` already operates on the
`Order` Pydantic model in memory, and rewriting it onto five normalized
tables would mean re-deriving that logic rather than just persisting it.
Every nested piece still has a typed Pydantic schema
(`app/models/orders.py`) enforced at the application layer.

## Data migration

`ORDER_STORE=file` (pre-P0.5 behavior) is still available for a
no-database dev loop; it never touches Postgres. If you have old
JSON-file orders you want in Postgres, see
`scripts/migrate_json_orders.py` — dry-run by default, never deletes or
overwrites, `--apply` to commit:

```bash
.venv/bin/python -m scripts.migrate_json_orders \
  --owner-user-id <existing-user-uuid> \
  --storage-dir ./storage/orders \
  --apply
```

## Known limitations

- The rate limiter and the `OrderService` in-process lock are
  single-process, in-memory. Behind multiple uvicorn workers or
  instances, swap the limiter for a shared store (e.g. Redis) — the
  `OrderRepository.locked()` row lock (Postgres `SELECT ... FOR UPDATE`)
  is what actually protects plan confirmation across workers; the
  in-process lock is now a redundant fast-path, not the real guard.
- Local disk asset storage (`LocalAssetStorage`) is not suitable for a
  multi-instance deployment — a second instance can't see files the
  first one wrote. The storage interface (`app/services/assets/`) is
  already behind an abstraction so an S3-compatible backend can be
  substituted without touching `OrderService`.
- No password reset / email verification / social login yet — out of
  scope for this milestone, noted as a later requirement.
- WhatsApp identity linking has a reserved table (`identity_links`) and a
  verification requirement documented above, but no OTP flow is
  implemented — there is no WhatsApp integration in this milestone.
