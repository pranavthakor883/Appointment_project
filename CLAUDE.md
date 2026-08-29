# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Appointment Booking API

## Project Purpose

A production-oriented appointment booking backend. Customers find service
providers, view genuinely available time slots, and book appointments.
Providers publish services, working hours, and manage their calendar.

The domain is deliberately generic: doctors, consultants, trainers, salons, and
any other provider whose product is *a block of their time*. Nothing in the
schema or the business logic may hardcode a single vertical (no `patient`,
no `haircut_type`) — use `customer`, `provider`, `service`.

## Roles

| Role | Can do |
|---|---|
| `customer` | Browse providers/services, book, cancel and reschedule own appointments, leave reviews |
| `provider` | Manage own profile, services, working hours; view and manage appointments booked with them |
| `admin` | Manage all users, providers, and appointments |

A role is a property of a user, never a separate table of users. Authorization
is checked on every protected endpoint — never assume a caller's role from the
request body.

## Tech Stack

- Python 3.11+
- FastAPI — API layer
- PostgreSQL — the only supported database
- SQLAlchemy (2.0 style) — ORM, all database access
- Pydantic v2 — request/response validation
- Alembic — schema migrations
- JWT — authentication
- Pytest — testing
- Docker, Redis, background jobs — later, not now

Do not add dependencies without being asked. If a task seems to need a new
package, say so and stop.

## Project Structure

```
appointment_booking_api/
├── app/
│   ├── main.py              # FastAPI app instance, router registration only
│   ├── config.py            # Pydantic Settings, reads .env — the ONLY place env vars are read
│   ├── api/
│   │   ├── deps.py          # shared dependencies: get_db, get_current_user, require_role
│   │   └── routers/         # one module per resource: auth, users, providers,
│   │                        # services, availability, appointments, reviews
│   ├── models/              # SQLAlchemy ORM models, one module per aggregate
│   ├── schemas/             # Pydantic models, mirrors models/ file-for-file
│   ├── services/            # business logic — the actual rules live here
│   ├── db/
│   │   ├── base.py          # DeclarativeBase + model imports for Alembic autogenerate
│   │   └── session.py       # engine + SessionLocal factory
│   └── core/
│       └── security.py      # password hashing, JWT encode/decode
├── alembic/
│   └── versions/
├── tests/
│   ├── conftest.py          # fixtures: test db, client, auth headers
│   └── ...                  # mirrors app/ layout
├── .env                     # NEVER committed
├── .env.example             # committed, placeholders only
├── alembic.ini
└── requirements.txt
```

**Why this shape.** The four-layer split (router → service → model → db) exists
because each layer has a different reason to change. Routers change when the
HTTP contract changes; services change when a business rule changes; models
change when the schema changes. Collapsing them means a pricing-rule change
forces you to edit an HTTP handler, and it makes business logic untestable
without spinning up a web request.

`schemas/` is separate from `models/` because the wire format and the storage
format are not the same thing and must be allowed to diverge — a `User` model
has `hashed_password`; a `UserOut` schema must not.

`config.py` is the single reader of the environment so that a missing or
malformed variable fails once, loudly, at startup — not at 3am inside a request.

Do not add layers beyond these. No repository pattern, no unit-of-work, no
generic `BaseService`. Add abstraction when a second concrete case demands it,
not in anticipation of one.

## Coding Conventions

- `snake_case` for functions, variables, modules; `PascalCase` for classes.
- Type-hint every function signature. Pydantic and FastAPI depend on them.
- Route handlers stay thin: validate input via a schema, call one service
  function, return a response schema. No queries, no `if` chains, no
  business rules in a router.
- Service functions take a `Session` as their first argument and plain
  arguments or Pydantic models after — never a `Request` object. Business
  logic must not know that HTTP exists.
- Raise `HTTPException` in routers and `deps`. In services, raise domain
  exceptions and translate them at the boundary — a service must stay callable
  from a background job or a CLI.
- All datetimes are timezone-aware UTC. Store UTC, convert at the edges.
  Naive datetimes are a bug.
- Prefer plain functions over classes for services.
- Keep modules under ~300 lines; split by resource, not by arbitrary size.

## Security Rules

- **Never hardcode passwords, secrets, tokens, or connection strings.** They
  come from `.env` via `app/config.py`, with no fallback default for
  `SECRET_KEY` or any credential.
- **`.env` is never committed.** It is in `.gitignore`. `.env.example` carries
  the variable names with placeholder values only.
- Passwords are hashed (bcrypt/argon2), never stored, logged, or returned.
- Never return `hashed_password`, raw tokens, or internal IDs of other users in
  a response. Response schemas are an allowlist — build them explicitly, never
  serialize a model wholesale.
- Never log secrets, tokens, request bodies containing credentials, or full
  connection strings.
- Every non-public endpoint requires authentication, and separately requires an
  authorization check that the caller may act on *this specific* resource. A
  valid token is not permission — a customer with a valid JWT must not be able
  to cancel another customer's appointment by guessing an ID.
- JWTs carry `sub` (user id), `role`, and `exp`. Keep access-token lifetime
  short. Validate signature and expiry on every request.
- Error responses must not leak whether an email exists, which query failed, or
  any stack trace. Generic message out, detail to the logs.
- All queries go through SQLAlchemy's parameter binding. No f-string SQL, ever.

## Database Rules

- PostgreSQL only. Do not write code that quietly falls back to SQLite.
- All access through the SQLAlchemy ORM and an injected `Session` — no module
  level connections, no connection created at import time.
- Sessions are per-request, provided by a `get_db` dependency that always
  closes. One transaction per request; commit in the service layer.
- Every table has an integer or UUID primary key and `created_at` /
  `updated_at` timestamps.
- Foreign keys are declared explicitly with intentional `ondelete` behavior.
  Prefer soft-deactivation over cascading deletes for users and providers —
  appointment history must survive.
- Money is `Numeric`, never `Float`.
- Index every foreign key and every column used for filtering — in particular
  `appointments(provider_id, start_time)`.
- Enum-like columns (appointment status, role) use a real constrained type,
  not a free-text string.

### Double-Booking Prevention — non-negotiable

An availability check followed by an insert is **not** sufficient. Two
concurrent requests both pass the check and both insert. Application-level
validation is a UX nicety; the database is what actually guarantees this.

The rule is enforced in two places:

1. **Database constraint** — a PostgreSQL exclusion constraint on the
   appointment time range per provider, so overlapping active appointments are
   rejected by the engine itself:
   `EXCLUDE USING gist (provider_id WITH =, tstzrange(start_time, end_time) WITH &&) WHERE (status IN ('pending','confirmed'))`
   (requires `btree_gist`). This is created in an Alembic migration.
2. **Service layer** — check availability first so the normal path returns a
   clean `409 Conflict`, and catch the `IntegrityError` from the constraint to
   return the same `409` when the race actually happens.

A booking path that relies only on step 2 is incorrect and must not be merged.
The same applies to rescheduling, which is a move within the same constraint.

Slot generation (working hours minus existing appointments minus blocked time)
lives in a service, is pure, and is unit-tested against boundary cases:
back-to-back slots, DST transitions, and appointments that end exactly when
another begins.

## API Design Conventions

- REST: plural nouns, resources not verbs.
  `POST /appointments`, `GET /providers/{id}/services`.
  Not `/createAppointment`.
- Actions that are genuinely not CRUD get a sub-resource:
  `POST /appointments/{id}/cancel`.
- Status codes carry meaning:
  - `200` OK · `201` created (with the created object) · `204` no content
  - `400` malformed · `401` unauthenticated · `403` authenticated but not allowed
  - `404` not found · `409` conflict (double booking) · `422` validation
    (FastAPI's default) · `500` unexpected
  - Never return `200` with an error body.
- Every list endpoint is paginated from day one — `limit` (default 20, max 100)
  and `offset` — and returns `{"items": [...], "total": n, "limit": l, "offset": o}`.
  Retrofitting pagination onto a live endpoint is a breaking change.
- Filtering and sorting via query parameters, validated by Pydantic. Never
  interpolate a sort field into SQL.
- Request and response models are explicit Pydantic schemas on every route, so
  the OpenAPI docs at `/docs` stay accurate for free.
- API is versioned under `/api/v1` from the start.
- Timestamps are ISO-8601 UTC in and out.

## Testing Expectations

- Pytest. Tests live in `tests/`, mirroring the `app/` layout.
- Run against a separate PostgreSQL test database — not SQLite, because the
  double-booking constraint is Postgres-specific and testing on SQLite would
  test the wrong thing.
- `conftest.py` provides: a transactional db fixture rolled back per test, a
  `TestClient`, and factories for authenticated customer/provider/admin.
- Required coverage before a feature is considered done:
  - Business logic in `services/` — unit tested directly, no HTTP.
  - Every endpoint — happy path, unauthenticated, wrong-role, and not-found.
  - Double booking — including a concurrent test that proves the database
    constraint fires, not just the pre-check.
  - Cancellation and rescheduling edge cases.
- Tests must not depend on execution order or on data left by another test.
- No network calls in tests; external services are stubbed.

## Migration Rules

- Every schema change ships as an Alembic migration. Never
  `Base.metadata.create_all()` outside of a throwaway experiment, and never
  edit a table by hand in psql.
- Generate with `alembic revision --autogenerate -m "short description"`, then
  **read and correct the generated file** — autogenerate misses constraint and
  index changes, and will not produce the exclusion constraint above. That one
  is written by hand with `op.execute()`.
- Every migration has a working `downgrade()`.
- One logical change per migration; give it a descriptive message.
- Never edit a migration that has already been applied anywhere but your own
  machine — write a new one.
- Data migrations are separate from schema migrations.
- Migrations must not import application models — they have to keep working
  when the model code moves on.

## Rules for Changing Code

- Change only what the current task requires. No drive-by refactors, no
  reformatting untouched files, no renaming things you happen to dislike.
- Do not delete or rewrite existing working code unless the task requires it.
  If existing code conflicts with these guidelines, **report the conflict and
  wait** rather than silently rewriting it.
- Do not add dependencies, config keys, endpoints, tables, or abstractions that
  the task did not ask for.
- No speculative generality. Build the case in front of you.
- When something is ambiguous, ask before building the wrong thing.
- Explain the reasoning behind non-obvious architectural decisions.
