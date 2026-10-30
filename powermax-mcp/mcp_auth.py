"""
Bearer-token authentication and HTTP runner shared by the MCP servers.

Tokens come from the environment (usually an OpenShift/Kubernetes Secret):
  MCP_AUTH_TOKENS   comma-separated list (lets you rotate: add new, update clients, remove old)
  MCP_AUTH_TOKEN    single token (used if MCP_AUTH_TOKENS is not set)
  MCP_AUTH_DISABLED=true   explicitly run without auth (not recommended)

Fail-closed: with HTTP transport and no token configured, the server refuses to start.
/healthz is unauthenticated (for probes) and returns no data.
"""

import hmac
import json
import logging
import os
import sys

log = logging.getLogger("mcp-auth")

MIN_TOKEN_LEN = 24


def load_tokens() -> list[bytes]:
    raw = os.getenv("MCP_AUTH_TOKENS") or os.getenv("MCP_AUTH_TOKEN") or ""
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if not tokens:
        if os.getenv("MCP_AUTH_DISABLED", "").lower() in ("1", "true", "yes"):
            log.warning("MCP_AUTH_DISABLED=true: the MCP endpoint is NOT protected")
            return []
        sys.exit("No MCP_AUTH_TOKEN / MCP_AUTH_TOKENS configured. Set a token "
                 "(e.g. `openssl rand -hex 32`) or MCP_AUTH_DISABLED=true to run without auth.")
    short = [t for t in tokens if len(t) < MIN_TOKEN_LEN]
    if short:
        sys.exit(f"Every MCP auth token must be at least {MIN_TOKEN_LEN} characters "
                 "(use `openssl rand -hex 32`).")
    return [t.encode() for t in tokens]


class BearerAuthMiddleware:
    """Pure ASGI middleware: requires `Authorization: Bearer <token>` on every HTTP request
    except the open paths. Constant-time comparison; failures are logged without the token."""

    def __init__(self, app, tokens: list[bytes], open_paths=("/healthz",)):
        self.app = app
        self.tokens = tokens
        self.open_paths = set(open_paths)

    def _ok(self, header: str) -> bool:
        if not header[:7].lower() == "bearer ":
            return False
        presented = header[7:].strip().encode()
        # check all tokens so timing does not reveal which one matched
        return any([hmac.compare_digest(presented, t) for t in self.tokens])

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.tokens or scope.get("path") in self.open_paths:
            return await self.app(scope, receive, send)
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        if self._ok(headers.get(b"authorization", b"").decode("latin-1")):
            return await self.app(scope, receive, send)
        client = (scope.get("client") or ("?", 0))[0]
        log.warning("Rejected unauthenticated request from %s to %s", client, scope.get("path"))
        body = json.dumps({"error": "unauthorized",
                           "detail": "Send Authorization: Bearer <token>"}).encode()
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json"),
                                (b"www-authenticate", b'Bearer realm="mcp"'),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


def run(mcp) -> None:
    """Run the FastMCP server: stdio (no auth needed) or streamable HTTP with bearer auth."""
    from starlette.middleware import Middleware
    from starlette.responses import JSONResponse

    transport = os.getenv("MCP_TRANSPORT", "http")
    if transport == "stdio":
        mcp.run(transport="stdio")
        return

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(request):  # noqa: ARG001
        return JSONResponse({"status": "ok"})

    tokens = load_tokens()
    app = mcp.http_app(path="/mcp", middleware=[Middleware(BearerAuthMiddleware, tokens=tokens)])

    import uvicorn
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    log.info("MCP endpoint http://%s:%s/mcp (auth: %s)", host, port,
             f"{len(tokens)} bearer token(s)" if tokens else "DISABLED")
    uvicorn.run(app, host=host, port=port, log_level=os.getenv("LOG_LEVEL", "info").lower(),
                proxy_headers=True, forwarded_allow_ips=os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"))
