# Numida Engineering Hub — Backend

A Django REST Framework backend for the Numida internal engineering workspace:
daily standups, presence tracking, AOB (any-other-business) items, PTO records,
shared pull-request links, and a read-only dashboard aggregating all of them
for a given week.

Version **1.0.0** — feature-complete, documented, performance-reviewed, and
cleaned up for release.

## Completed modules

| Module | Endpoints | What it does |
|---|---|---|
| **Accounts** | `/api/v1/auth/*`, `/api/v1/users/*` | Session login/logout, current user, read-only active-user directory |
| **Standups** | `/api/v1/standups/*` | Daily standup submissions with nested items (completed/current/planned/meetings), per-user and per-week views, search/filtering |
| **Presence** | `/api/v1/presence/*` | Heartbeat-based online/recently-active/offline tracking |
| **AOB** | `/api/v1/aob-items/*` | Any-other-business items scoped to a week, with search/filtering |
| **PTO** | `/api/v1/pto/*` | Paid-time-off entries, with date-range/overlap filtering and search |
| **Pull Request Links** | `/api/v1/pull-request-links/*` | Shared PR links scoped to a week, with status/search/filtering |
| **Dashboard** | `/api/v1/dashboard/` | Read-only aggregate of standup submission stats, weekly standups, presence, AOB, PTO, and PR links for one selected week |

Every mutable resource (standups, AOB items, PTO entries, pull-request links)
enforces object-level ownership: anyone authenticated can read, only the
owner/creator can update or delete. See [Ownership and permissions](#ownership-and-permissions).

## Architecture

```
config/                  Django project configuration
  settings/
    base.py              Settings shared by every environment
    development.py       Local development overrides (readable console logs)
    test.py              Settings used by the test suite (fast password hasher)
    production.py        Production hardening (HTTPS, HSTS, JSON logs)
  urls.py                Root URLconf: /admin/, /health/, /api/v1/, schema/docs
  api_v1_urls.py         Aggregates each app's urls.py under /api/v1/
  views.py                Health check view

apps/                    Domain apps, one per bounded context
  accounts/  standups/  presence/  aob/  pto/  pull_requests/  dashboard/

  Every app follows the same layering rules, but only has the files its own
  logic actually needs — there are no empty placeholder modules:
    models.py            ORM models (dashboard has none — it's a read-only
                          aggregator over the other apps' data)
    serializers.py        DRF serializers — validation and representation only
    selectors.py          Read-side query logic (select_related/
                          prefetch_related live here, not in views)
    services.py            Write-side business logic, wrapped in
                          transaction.atomic() (accounts/dashboard have none —
                          accounts writes go through Django's UserManager,
                          dashboard has no writes at all)
    permissions.py          App-specific object-level permission (only
                          present where a resource has an owner/creator to
                          enforce — standups/aob/pto/pull_requests)
    filters.py               django-filter FilterSets (only present on
                          apps with a filterable list endpoint)
    views.py                 Thin DRF views: authenticate → validate →
                          delegate to a selector/service → respond
    urls.py                   App-local routes, included under /api/v1/
    admin.py                   Django admin registration
    tests/                      App-specific tests (mirrors the app's own
                          module names: test_selectors.py, test_services.py,
                          test_list_view.py, etc.)

common/                  Cross-app reusable infrastructure every app sits on
  responses.py            success_response/created_response/deleted_response/
                          paginated_response — the one success envelope
  exceptions.py            custom_exception_handler — the one error envelope
  pagination.py            DefaultPagination (page_size=20, max=100)
  permissions.py            IsOwnerOrReadOnly — the base class every app's
                          own Is<Resource>Owner/Creator subclasses
  validators.py             validate_https_url, validate_monday
  schema.py                 drf-spectacular documentation helpers (error/
                          success response shapes, reused across every app's
                          @extend_schema declarations)
  constants.py              APPLICATION_NAME/VERSION, API_VERSION, pagination
                          defaults, URL schemes, date formats
  logging.py                JSONFormatter (used in production)
  middleware.py              RequestLoggingMiddleware
  utils/
    dates.py                is_monday
    urls.py                  get_scheme, is_https_url

tests/                  Project-level test utilities and cross-cutting tests
  base.py                 BaseAPITestCase
  auth.py                  authenticate(client, user) helper
  helpers.py               get_data(response), get_error(response)
  factories/               Shared factory-boy factories
  integration/             Cross-app integration tests
  test_openapi.py          /api/schema/, /api/docs/, /api/redoc/ smoke tests
  test_health.py            /health/ smoke tests
  test_exceptions.py         Direct unit tests for the shared exception handler
```

## Project philosophy

Views stay thin: they authenticate, validate the request, delegate to a
selector (reads) or service (writes), and return a response via
`common/responses.py`. Business logic never lives in views — it lives in
`services.py` (writes, always wrapped in `transaction.atomic()`) and
`selectors.py` (reads, always with `select_related()`/`prefetch_related()`
applied so list endpoints never do one query per result).

## Ownership and permissions

`common/permissions.py` provides one base class, `IsOwnerOrReadOnly`: safe
methods (GET/HEAD/OPTIONS) are allowed for any authenticated user, unsafe
methods (PATCH/DELETE) are restricted to whichever field `owner_field` names
on the object. Each app that has an owned resource subclasses it with a
one-line override:

- `apps.standups.permissions.IsStandupOwner` (`owner_field="user"`)
- `apps.aob.permissions.IsAOBItemCreator` (`owner_field="created_by"`)
- `apps.pto.permissions.IsPTOEntryCreator` (`owner_field="created_by"`)
- `apps.pull_requests.permissions.IsPullRequestLinkCreator` (`owner_field="created_by"`)

This is enforced server-side in every detail view's `permission_classes`
alongside `IsAuthenticated`, and checked explicitly via
`self.check_object_permissions()` even on the GET path that bypasses
`get_object()` in favor of an optimized selector. Ownership can never be
overridden by request data — every create/update service excludes the
owner/creator field from `validated_data` even though the serializer already
marks it read-only, as a second safeguard.

## Response format

Every successful response shares one envelope, built by `common/responses.py`:

```json
{
    "message": "Resource created successfully.",
    "data": {}
}
```

`success_response()` (200), `created_response()` (201), and `deleted_response()`
(200, with a message body — a 204 cannot carry one) all produce this shape.
Paginated list responses use the same envelope, with `data` holding
`count`/`next`/`previous`/`results`.

## Error format

Every error response — validation errors, auth failures, permission denials,
404s, 405s, and unhandled server errors — is normalized by
`common/exceptions.py` into one envelope:

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "...",
        "fields": {}
    }
}
```

`fields` is only populated for field-level validation errors; other error
types leave it empty. The handler is registered via `EXCEPTION_HANDLER` in
`REST_FRAMEWORK` settings.

## Pagination

`common/pagination.py` provides `DefaultPagination`, registered project-wide as
`DEFAULT_PAGINATION_CLASS`. Default page size is 20, maximum is 100
(`?page=2&page_size=50`). The weekly-standups endpoint is the one deliberate
exception (`pagination_class = None`) since a single week's standups is
already a small, intentionally-bounded result set.

## Performance

Every selector backing a list or detail endpoint uses `select_related()` for
forward FK/one-to-one relationships and `prefetch_related()` for reverse/
nested relationships, so no list endpoint executes one query per result.
Query-count tests (`assertNumQueries`, run at two different data volumes to
prove the count doesn't grow) exist at the selector level for every app and
at the endpoint level for the standup list, weekly standups, presence list,
AOB list, PTO list, pull-request-link list, and dashboard endpoints.

**Indexes.** Every field the codebase commonly filters or orders by is
indexed: `Standup.standup_date`, `StandupItem(standup, section, position)`
(covers ordering and the `section` filter), `UserPresence.last_seen_at`,
`AOBItem(-week_start, position)`, `PTOEntry.start_date` and `.end_date`,
`PullRequestLink(-week_start, group_name, position)` and `.status`. Every
`user`/`created_by` ForeignKey already gets an index automatically from
Django's `db_index=True` default — no app declares a redundant duplicate of
one.

**Notable optimizations:** the four owned-resource detail views'
`self.get_object()` queryset uses `select_related()` for their FK(s), so
PATCH/DELETE don't pay for a second query when the ownership check or
response serialization reads the owner field. `.distinct()` on list
endpoints is applied only where a filter/search field actually joins to a
to-many relation (standups' `items`) — AOB/PTO/pull-request-link lists only
ever join to forward to-one FKs, so `.distinct()` there would be pure
overhead and was removed.

## API versioning

All endpoints live under `/api/v1/`, aggregated in `config/api_v1_urls.py` —
one path segment per app (`/api/v1/standups/`, `/api/v1/pto/`, etc.), except
accounts, which owns both `/api/v1/auth/*` and `/api/v1/users/*` at the v1
root. Adding a v2 later means adding `config/api_v2_urls.py` and including it
alongside this one, without touching existing routes.

## Logging

`common/middleware.py`'s `RequestLoggingMiddleware` logs method/path/status/
duration for every request. It never logs headers, cookies, or bodies, so
passwords, tokens, and session cookies cannot leak through logs. Development
uses a readable console formatter; production switches to
`common/logging.py`'s `JSONFormatter` so log aggregators can parse entries
directly. Unhandled exceptions and 4xx/5xx responses are logged by
`common/exceptions.py`.

## Schema docs (Swagger / ReDoc)

drf-spectacular is fully configured (title, description, version, contact,
license, tags, Swagger UI settings). Every endpoint has a unique
`operation_id`, a tag, a summary/description, realistic request/response
examples, and documented 200/201/400/401/403/404 responses. With the server
running:

- OpenAPI schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`
- ReDoc: `GET /api/redoc/`

Validate the schema generates without warnings:

```bash
uv run python manage.py spectacular --validate --fail-on-warn
```

## Requirements

- Python 3.12
- PostgreSQL
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker (optional, for running Postgres/the backend in containers)

## Environment variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Which settings module to load | `config.settings.development` |
| `DJANGO_SECRET_KEY` | Django's cryptographic signing key — set a real value outside local dev | `django-insecure-change-me-in-env` |
| `DEBUG` | Django debug mode | `True` in development, `False` in test/production |
| `ALLOWED_HOSTS` | Comma-separated hostnames the app will serve | `localhost,127.0.0.1` in development |
| `DATABASE_URL` | Full Postgres connection string | `postgres://postgres:postgres@localhost:5432/numida_engineering_hub` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Used by `docker-compose.yml` to provision the Postgres container | `numida_engineering_hub` / `postgres` / `postgres` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API cross-origin | none set |

Production additionally reads `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE`, and `SECURE_HSTS_SECONDS` (see
`config/settings/production.py`); all default to secure values if unset.

## Running locally

```bash
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

The app reads `DJANGO_SETTINGS_MODULE` from the environment (see `.env.example`);
it defaults to `config.settings.development` if unset.

Health check: `GET /health/` →
```json
{
    "status": "ok",
    "application": "Numida Engineering Hub",
    "version": "1.0.0",
    "environment": "development",
    "server_time": "..."
}
```

## Migrations

Each app currently has exactly one migration (`0001_initial.py`) — no
accumulated migration history to squash. After changing any model:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

CI/reviewers can confirm no model change was left un-migrated with:

```bash
uv run python manage.py makemigrations --check --dry-run
```

## Running with Docker

```bash
cp .env.example .env
docker compose up --build
```

This starts two services: `backend` (Django) and `postgres` (PostgreSQL 16).

## Tests

```bash
uv run pytest
```

Test settings (`config.settings.test`) use a fast password hasher and are
configured via `pytest.ini`. Feature tests should subclass
`tests.base.BaseAPITestCase` to get consistent authentication and response
helpers. Read-side tests (selectors, endpoint list views) generally include
an `assertNumQueries` check at two different data volumes to guard against
N+1 regressions.

## Coverage

```bash
uv run coverage run -m pytest
uv run coverage report
```

Configured in `pyproject.toml`'s `[tool.coverage.*]` tables. Migrations,
tests, `manage.py`, deployment entrypoints (`config/asgi.py`/`wsgi.py`), and
environment-specific settings modules are excluded, since none of those are
meaningfully unit-testable application logic. `fail_under = 90` acts as a
regression floor, not a target — actual coverage is comfortably above it;
`coverage report` exits non-zero if it ever drops below.

## Linting and formatting

```bash
uv run ruff check .
uv run ruff format .
```

Pre-commit runs the same checks automatically:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## Adding a new feature

1. Add models to the relevant app's `models.py` and generate migrations.
   Index any field you know will be filtered or ordered on.
2. Add selectors/services for read/write logic — never in views. Selectors
   always specify `select_related()`/`prefetch_related()`; services always
   wrap writes in `transaction.atomic()` and exclude owner/creator fields
   from `validated_data` even when the serializer already marks them
   read-only.
3. Add serializers (validation/representation only — no `create()`/
   `update()` overrides; that logic belongs in the service) and thin views
   that delegate to selectors/services and return responses via
   `common/responses.py`.
4. Reuse `common/pagination.py`, `common/permissions.py`, and
   `common/validators.py` instead of writing new ones, unless the app has a
   genuinely new concern — don't add an app-local `filters.py`/
   `permissions.py`/`validators.py` file until there's real content for it.
5. Wire the app's `urls.py` into `config/api_v1_urls.py`.
6. Document the endpoint with `@extend_schema`/`@extend_schema_view`
   (operation_id, tags, summary, description, request/response examples,
   error responses) and confirm `manage.py spectacular --validate
   --fail-on-warn` stays clean.
7. Add tests under the app's `tests/` package, subclassing
   `tests.base.BaseAPITestCase`, including a query-count test for any new
   list endpoint.
