---
name: fastapi-service
description: Build or change a backend service the way the storage-mcp-servers repos do - a FastAPI REST service or an MCP server (fastmcp) in front of a storage / infrastructure API. Config from an OpenShift Secret, bearer-token auth that fails closed, read-only enforced in the HTTP client, offline tests with a faked backend, a non-root image and an OpenShift Deployment with probes, shipped to the air-gapped cluster as an image tarball.
when_to_use: Trigger phrases - "build an API / service / backend", "FastAPI", "endpoint", "new MCP server", "add a tool to the powermax / ucsc / mds MCP", "pydantic model", "deploy it to OpenShift", "write tests for the service"
---
# Backend services (FastAPI / fastmcp), house style

Reference implementations, in the storage-mcp-servers clone install-vm.sh ran from (find it:
`find ~ -maxdepth 3 -type d -name powermax-mcp`): `powermax-mcp/` (server.py, mcp_auth.py, test_readonly.py, Dockerfile,
openshift.yaml), `ucsc-mcp/`, `mds-mcp/` (wraps an upstream server), `docs-search-mcp/`. Copy their
patterns before inventing new ones. **Check every library API in the offline docs before using it**
(`docs-lookup`; vendor `python`: `fastapi`, `pydantic`, `pydantic-settings`, `starlette`, `uvicorn`,
`httpx`, `pytest`, `pytest-asyncio`, `sqlalchemy`, `fastmcp`; vendor `mcp`: `python-sdk`,
`specification`) and match the version pinned in `requirements.txt`; your memory of an API may be a
different major version (Pydantic v1 vs v2, SQLAlchemy 1.x vs 2.0, fastmcp 2 vs 4).

## 1. Shape
- One service = one folder: `server.py` (or `main.py` + a few modules once it passes ~1,500 lines),
  `mcp_auth.py` (copied as is), `requirements.txt` **pinned with ==**, `test_*.py`, `Dockerfile`,
  `openshift.yaml`, `README.md` (what it does, env vars, deploy, test).
- Python 3.13, standard logging: `log = logging.getLogger("<service>")`, level from `LOG_LEVEL`.
  Never log tokens, passwords or full request headers.

## 2. Configuration (environment only, from one Secret)
- Every setting from env; secrets never in Git or in the image. One backend: `<SYS>_HOST`,
  `<SYS>_USERNAME`, `<SYS>_PASSWORD`, `<SYS>_VERIFY_SSL` (true / false / CA-bundle path), `<SYS>_TIMEOUT`.
  Several: numbered `<SYS>_<N>_HOST` ... plus `<SYS>_<N>_NAME`, discovered by regex (`_load_unispheres`).
- FastAPI service: a `pydantic-settings` `BaseSettings` class reading the same names; validate at start.
- Missing required config: exit at start with a message naming the variable (fail closed, never at the
  first request).

## 3. Auth and transport
- Bearer tokens from `MCP_AUTH_TOKENS` (comma list, for rotation) / `MCP_AUTH_TOKEN`, at least 24 chars,
  compared with `hmac.compare_digest` against every token; no token configured → refuse to start unless
  `MCP_AUTH_DISABLED=true` (logged as a warning). `/healthz` is the only open path and returns no data.
- MCP server: `mcp_auth.run(mcp)`: `MCP_TRANSPORT=stdio|http`, `/mcp` on `MCP_HOST:MCP_PORT` (0.0.0.0:8000),
  uvicorn with `proxy_headers=True`.
- FastAPI: the same `BearerAuthMiddleware` (pure ASGI, works for both) or a `Depends` using `HTTPBearer`
  with the same constant-time check; `/healthz` outside it.

## 4. Talking to the backend (read-only by construction)
- One client class per backend (`Unisphere`, `UcsCentral`): base URL, auth, `verify`, timeout, and a
  `_do()` that maps 404 → `LookupError`, 401/403 → `PermissionError`, other ≥ 400 → `RuntimeError` with the
  vendor's message (first 500 chars). Paging in one `iterate(resp, limit)` helper.
- **Read-only lives in the HTTP layer, not in the tools**: a session subclass whose `request()` calls
  `check_read_only(method, url)` (GET / HEAD, plus an explicit allow-list of read-only POSTs such as
  performance queries; the path must stay under the API root, no `..`) and raises `ReadOnlyViolation`
  before anything is sent. A write feature is a separate, reviewed decision.
- Sync `requests` in fastmcp tools / plain `def` FastAPI endpoints (run in the thread pool); `httpx.AsyncClient`
  only in `async def` code, created once in the app's lifespan with explicit timeouts.

## 5. MCP tools / API endpoints
- MCP: `@mcp.tool(annotations=RO)` with
  `RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)`.
  The docstring says what it returns and when to use it ("Start here", "Run this first when something
  fails"); always a `test_connection` tool. Narrow parameters first (one array / fabric / name), the full
  list second; return dicts with stable keys and normalised identifiers (WWN lowercase without colons).
- Several backends in one tool: try each, return `{"ok": false, "error": str(e)}` for the one that failed
  and the others' data (partial result, never all-or-nothing).
- FastAPI: an `APIRouter` per resource; Pydantic v2 request / response models (`model_config`,
  `Field(...)`), `response_model` on every route; exceptions from `_do()` mapped once (exception handlers)
  to 404 / 403 / 502; no business logic in the route function.

## 6. Tests (offline, plain asserts, no pytest plugins required)
- Fake the backend at the transport: replace `requests.Session.send` (or `httpx.MockTransport`) with a
  router returning canned JSON per path, recording every request in `SENT`.
- Call every tool / endpoint once (`fastapi.testclient.TestClient`; MCP: the tool functions or the
  fastmcp client in-process); check results and paging.
- Prove read-only: every write method / path, path traversal and a foreign host raise
  `ReadOnlyViolation`, and `SENT` did not grow. Auth: no token → 401, wrong token → 401, `/healthz` open.
- `python3 test_readonly.py` must print `ALL TESTS PASSED`; run it before every commit.

## 7. Image and OpenShift
- Dockerfile: `python:3.13-slim`, `PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`, `pip install
  --no-cache-dir -r requirements.txt`, copy only the service files, `chgrp -R 0 /app && chmod -R g=u /app`,
  `USER 1001`, `EXPOSE 8000`. No secrets, no test files in the image.
- `openshift.yaml`: Deployment (`envFrom: secretRef`), readiness + liveness on `/healthz`,
  `securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, runAsNonRoot: true,
  capabilities: {drop: [ALL]}}`, requests + memory limit, Service on 8000; header comments with the exact
  `oc create secret generic <name> --from-env-file=.env` and `oc apply` commands.
- Air-gapped delivery: build with podman on a connected machine, `podman save | gzip`, split into 45 MB
  parts under `images/` with `SHA256SUMS` (see `images/join.sh`), or an OpenShift `BuildConfig` from the
  repo (`openshift/buildconfigs.yaml`). Python dependencies on the VM come from bundled wheels, never pip.
- Version the image tag in the Deployment, the BuildConfig and the tarball name together.

## Quality loop (tools installed on the VM)
- After each edit the `py-lint` hook reports ruff errors: fix them before moving on. The pyright-lsp plugin
  (basedpyright) gives type diagnostics: resolve them, do not silence them with `# type: ignore`.
- Bigger features: `/feature-dev` (explore -> architecture -> implement -> review). Before a commit: run the
  tests, then `/code-review` on the diff (pr-review-toolkit's silent-failure-hunter and pr-test-analyzer for
  error handling and test gaps). `/commit` writes the commit (no PR on the VM unless `gh` is there).
- security-guidance warns on risky patterns as you write (yaml.load, pickle, shell=True, hardcoded secrets).

## Output
The code, the test run output, and for the user to run: the build / deploy commands (labelled "to be run
by you", rule 1), the Secret keys to create, and how to check it (`/healthz`, then `test_connection`).
