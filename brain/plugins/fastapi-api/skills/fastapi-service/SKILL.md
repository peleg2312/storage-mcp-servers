---
name: fastapi-service
description: Use when building or changing a Python REST API / web service / backend (FastAPI, uvicorn, pydantic, SQLAlchemy, alembic, pytest) on this air-gapped VM - new project, new endpoint, database model, settings, tests, or a container for OpenShift. Holds the offline setup (paas-kit venv), the project layout and the rules.
---
# FastAPI services on this VM (offline)

Nothing is downloaded here: packages come from the VM's wheels.
- New project: `/fastapi-api:new <name>` (copies the template, makes `.venv`, runs the tests).
- Existing project: `paas-kit venv .` makes `./.venv` (Python 3.12, else 3.9) with FastAPI, uvicorn, pydantic v2,
  pydantic-settings, SQLAlchemy 2, alembic, psycopg 3, httpx, python-jose, passlib, python-multipart, pytest,
  pytest-asyncio, ruff, mypy. A `requirements.txt` there is used when everything in it is in the wheels.
- `pip install` of anything else fails offline: say which package is missing; do not invent a workaround.

## Layout (the template)
```
app/main.py          create_app(): FastAPI(), routers, exception handlers, lifespan
app/config.py        Settings(BaseSettings): every setting from the environment (APP_ prefix), never in code
app/db.py            engine + session (SQLAlchemy 2, sync; sqlite by default, postgres via APP_DATABASE_URL)
app/models.py        ORM tables          app/schemas.py   pydantic models in / out (never return ORM objects)
app/api/routes/*.py  one APIRouter per resource; health.py has /healthz and /readyz
tests/               pytest + fastapi.testclient (or httpx.AsyncClient); conftest.py gives a fresh database per test
```
Run: `.venv/bin/uvicorn app.main:app --reload --port 8000`; docs at /docs. Checks before you say done:
`.venv/bin/ruff check . && .venv/bin/mypy app && .venv/bin/pytest -q`.

## Rules
1. Code must run on Python 3.9 and 3.12: `Optional[X]` / `List[X]` from typing, not `X | None` in models or routes.
2. Every endpoint: `response_model` (or a typed return), explicit status codes (201 create, 204 delete, 404 not
   found via HTTPException), request bodies as pydantic models with limits (`Field(max_length=..., ge=...)`).
3. Lists are paged: `limit` (default 50, max 500) and `offset` or a cursor; never return a whole table.
4. Settings and secrets come from the environment (`app/config.py`); no URLs, passwords or tokens in code or tests.
5. `async def` only when every call inside awaits (httpx.AsyncClient, async drivers); blocking work (sync SQLAlchemy,
   requests, subprocess, file I/O) goes in plain `def` endpoints, which FastAPI runs in a thread pool.
6. Database changes go through alembic (`alembic init migrations`, `alembic revision --autogenerate -m ...`,
   `alembic upgrade head`); `create_all` only in tests and the sqlite quick start.
7. Auth when asked: OAuth2 bearer (`fastapi.security.OAuth2PasswordBearer`) + python-jose JWT, passlib bcrypt hashes;
   a dependency `current_user` on the routers that need it.
8. Errors return `{"detail": ...}` (FastAPI's shape); log with `logging`, never print; no stack traces to clients.
9. A test for each endpoint: success, validation error (422), not found; run them before you report.
10. Calling storage / infrastructure APIs from the service stays read-only unless the user asked for a change
    (the brain's golden rules apply).

## Container for OpenShift
A `Containerfile` from the internal registry's Python image (ask the user for its name; never a public registry):
copy the wheels the project needs into the image (`pip download` is impossible here; use
`pip wheel -w wheels -r requirements.txt --no-index --find-links /opt/paas-kit/kit/wheels/api-py312`), run as a
non-root user, `uvicorn app.main:app --host 0.0.0.0 --port 8080`, readiness probe `/readyz`, liveness `/healthz`.
