# Numida Engineering Hub — Backend

Backend for the Numida internal engineering workspace: weekly standups, presence,
AOB items, PTO records, and outstanding pull-request links.

This repository contains the **project skeleton and reusable engineering
infrastructure**: response/error formats, pagination, permissions, logging, API
versioning, and schema docs. No authentication, models, serializers, views, or
business logic have been implemented yet — every future feature is built on top
of this foundation.

## Architecture

```
config/                  Django project configuration
  settings/
    base.py              Settings shared by every environment
    development.py        Local development overrides (readable console logs)
    test.py              Settings used by the test suite (fast password hasher)
    production.py        Production hardening (HTTPS, HSTS, JSON logs)
  urls.py                Root URLconf: /admin/, /health/, /api/v1/, schema/docs
  api_v1_urls.py           Aggregates each app's urls.py under /api/v1/
  views.py                 Health check view

apps/                    Domain apps, one per bounded context
  accounts/  standups/  presence/  aob/  pto/  pull_requests/

  Each app follows the same internal layout:
    models.py            ORM models
    serializers.py        DRF serializers
    selectors.py          Read-side query logic
    services.py           Write-side business logic
    permissions.py         App-specific DRF permissions
    filters.py             django-filter FilterSets
    validators.py           App-specific validators
    views.py                Thin DRF views
    urls.py                 App-local URL routes (included under /api/v1/<app>/)
    admin.py                 Django admin registration
    tests/                    App-specific tests

common/                  Cross-app reusable infrastructure — the platform every
                         feature app sits on:
  responses.py            success_response/created_response/deleted_response/
                          paginated_response — the one success envelope
  exceptions.py            custom_exception_handler — the one error envelope
  pagination.py            DefaultPagination (page_size=20, max=100)
  permissions.py            IsOwnerOrReadOnly, IsCreatorOrReadOnly
  validators.py             validate_https_url, validate_future_week,
                           validate_monday, validate_non_empty_string
  constants.py              API_VERSION, pagination defaults, URL schemes,
                           date formats, application name/version
  logging.py                JSONFormatter (used in production)
  middleware.py              RequestLoggingMiddleware
  utils/
    dates.py                today, is_monday, is_in_future
    strings.py               is_blank, truncate
    urls.py                  get_scheme, is_https_url

tests/                  Project-level test utilities future feature tests inherit
  base.py                 BaseAPITestCase
  auth.py                  authenticate(client, user) helper
  helpers.py               get_data(response), get_error(response)
  factories/               Shared factory-boy factories
  integration/             Cross-app integration tests
```

## Project philosophy

Views stay thin: they authenticate, validate the request, delegate to a
selector/service, and return a response via `common/responses.py`. Business
logic lives in `services.py` (writes) and `selectors.py` (reads), never in
views.

## Response format

Every successful response shares one envelope, built by `common/responses.py`:

```json
{
    "message": "Standup created successfully.",
    "data": {}
}
```

`success_response()` (200), `created_response()` (201), and `deleted_response()`
(200, with a message body — a 204 cannot carry one) all produce this shape.

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
(`?page=2&page_size=50`). Paginated responses reuse the same envelope, with
`data` holding `count`/`next`/`previous`/`results`.

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
one. This audit added no new indexes; everything the task asked to review
was already covered, so no migration was needed
(`manage.py makemigrations --check` reports no changes).

**Optimizations applied in this review:**

- The four detail views' (Standup/AOB/PTO/PullRequestLink) `queryset` class
  attribute — the plain, un-optimized queryset `self.get_object()` uses for
  PATCH/DELETE — now uses `select_related()` for their FK(s). This removes
  one avoidable query per PATCH/DELETE request (previously triggered when
  the owner/creator permission check or response serialization read the FK).
  GET was already optimal via each app's dedicated selector.
- Removed `.distinct()` from the AOB, PTO, and pull-request-link list views.
  Their filters and `search_fields` only ever join to forward to-one FKs
  (`created_by`/`user`), which can never multiply rows, so `distinct()` was
  pure overhead. `.distinct()` is kept on the standup list, since its
  `section` filter and `items__content` search field join to the reverse
  `items` relation, which genuinely can produce duplicate rows.

**Deferred, and why:** `.only()`/`.defer()` were considered but every field
currently returned by a list serializer is actually used by that serializer
— there's no heavy/unused column to trim. Redis, caching, Celery, background
jobs, and query result caching were explicitly out of scope for this pass.

## API versioning

All future endpoints live under `/api/v1/`, aggregated in `config/api_v1_urls.py`
— one path segment per app (`/api/v1/accounts/`, `/api/v1/standups/`, etc.).
Adding a v2 later means adding `config/api_v2_urls.py` and including it
alongside v1, without touching existing routes.

## Logging

`common/middleware.py`'s `RequestLoggingMiddleware` logs method/path/status/
duration for every request. It never logs headers, cookies, or bodies, so
passwords, tokens, and session cookies cannot leak through logs. Development
uses a readable console formatter; production switches to
`common/logging.py`'s `JSONFormatter` so log aggregators can parse entries
directly. Unhandled exceptions and 4xx/5xx responses are logged by
`common/exceptions.py`.

## Schema docs

drf-spectacular is fully configured (title, description, version, contact,
license). With the server running:

- OpenAPI schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`
- Redoc: `GET /api/redoc/`

## Requirements

- Python 3.12
- PostgreSQL
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker (optional, for running Postgres/the backend in containers)

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
helpers.

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

## Current project scope

This repository currently provides:

- Django + DRF project skeleton (`config/`)
- Reusable infrastructure (`common/`): response/error envelopes, pagination,
  base permissions, validators, constants, logging, request-logging middleware
- API versioning under `/api/v1/`, with OpenAPI schema/Swagger/Redoc docs
- Empty domain app scaffolding (`apps/accounts`, `apps/standups`, `apps/presence`,
  `apps/aob`, `apps/pto`, `apps/pull_requests`) — no models or endpoints yet
- Test utility scaffolding (`tests/`)
- Development tooling: pytest, coverage, Ruff, pre-commit
- Docker/Compose setup for the backend and PostgreSQL
- A `/health/` endpoint reporting status, application, version, environment,
  and server time

No authentication, users, models, serializers, views, APIs, or business logic
exist yet.

## Adding a new feature (future work)

1. Add models to the relevant app's `models.py` and generate migrations.
2. Add selectors/services for read/write logic — never in views.
3. Add serializers and thin views that delegate to selectors/services and
   return responses via `common/responses.py`.
4. Use `common/pagination.py`, `common/permissions.py`, and `common/validators.py`
   instead of writing new ones, unless the app has a genuinely new concern.
5. Wire the app's existing `urls.py` (already included from
   `config/api_v1_urls.py`) with real routes.
6. Add tests under the app's `tests/` package, subclassing
   `tests.base.BaseAPITestCase`.
