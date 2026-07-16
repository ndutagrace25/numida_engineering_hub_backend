# Numida Engineering Hub — Backend

Backend for the Numida internal engineering workspace: weekly standups, presence,
AOB items, PTO records, and outstanding pull-request links.

This repository currently contains only the **project skeleton and development
tooling**. No authentication, models, serializers, views, or business logic have
been implemented yet — this is the foundation future features will be built on.

## Architecture

```
config/                  Django project configuration (settings, root URLs, WSGI/ASGI)
  settings/
    base.py              Settings shared by every environment
    development.py        Local development overrides
    test.py              Settings used by the test suite
    production.py        Production hardening (HTTPS, HSTS, secure cookies)

apps/                    Domain apps, one per bounded context
  accounts/
  standups/
  presence/
  aob/
  pto/
  pull_requests/

  Each app follows the same internal layout:
    models.py            ORM models
    serializers.py        DRF serializers
    selectors.py          Read-side query logic
    services.py           Write-side business logic
    permissions.py         App-specific DRF permissions
    filters.py             django-filter FilterSets
    validators.py           App-specific validators
    views.py                Thin DRF views
    urls.py                 App-local URL routes
    admin.py                 Django admin registration
    tests/                    App-specific tests

common/                  Cross-app reusable infrastructure (responses, exceptions,
                         pagination, permissions, validators, constants). Currently
                         scaffolded as empty modules, to be implemented as a
                         follow-up task.

tests/                  Project-level test utilities
  factories/             Shared factory-boy factories
  integration/           Cross-app integration tests
```

## Project philosophy

Views stay thin: they authenticate, validate the request, delegate to a
selector/service, and return a response. Business logic lives in `services.py`
(writes) and `selectors.py` (reads), never in views.

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

Health check: `GET /health/` → `{"status": "ok"}`

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
configured via `pytest.ini`.

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

This repository currently provides only:

- Django + DRF project skeleton (`config/`)
- Empty domain app scaffolding (`apps/accounts`, `apps/standups`, `apps/presence`,
  `apps/aob`, `apps/pto`, `apps/pull_requests`)
- Empty `common/` infrastructure module placeholders
- Test utility scaffolding (`tests/`)
- Development tooling: pytest, coverage, Ruff, pre-commit
- Docker/Compose setup for the backend and PostgreSQL
- A single `/health/` endpoint

No authentication, models, serializers, views, APIs, or business logic exist yet.
Future work will implement the `common/` infrastructure (consistent response and
error formats, pagination, permissions, API versioning, logging, schema docs) and
then build out each domain app on top of it.

## Adding a new feature (future work)

1. Add models to the relevant app's `models.py` and generate migrations.
2. Add selectors/services for read/write logic.
3. Add serializers and thin views that delegate to selectors/services.
4. Wire the app's `urls.py` into `config/urls.py` under the API version prefix.
5. Add tests under the app's `tests/` package.
