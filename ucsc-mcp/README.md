# UCS Central MCP server (read-only)

MCP server for Cisco UCS Central, built on Cisco's `ucscsdk`. Works with **one or many UCS Central
instances** from one pod; nothing it does can change configuration.

## Read-only enforcement

1. **XML allowlist**: every request is checked before it leaves the process. Only
   `aaaLogin/Logout/Refresh/KeepAlive` and `configResolve*` (Dn, Dns, Class, Classes, Children,
   Parent) are sent. `configConfMo`, `configConfMos` and every other method are refused.
2. **SDK write helpers disabled**: `add_mo`, `set_mo`, `remove_mo`, `commit`, file upload/download raise.
3. **Query-only tools**, all marked `readOnlyHint`.
4. Also use a UCS Central user with only the **read-only** role.

`python3 test_readonly.py` runs every tool against two fake UCS Centrals and proves writes are blocked.

## Built-in guidance for the connecting Claude

- **Server instructions** (sent on connect): DN formats, domains and centrals, which tool to use for
  which question, how to read operability / association / fault states, and the cross-system SAN
  trace with the MDS and PowerMax MCP servers.
- **Prompts**: `ucs_health_check`, `troubleshoot_server`, `trace_san_path`.

## Tools (21)

| Area | Tools |
|---|---|
| Connection | `test_connection`, `list_centrals` |
| Inventory | `list_domains`, `list_fabric_interconnects`, `list_chassis`, `list_servers`, `get_server`, `list_firmware` |
| Health / events / logs | `get_domain_health`, `list_faults`, `get_events`, `get_audit_log` |
| Service profiles | `list_service_profiles`, `get_service_profile`, `get_service_profile_vhbas` |
| SAN | `find_wwpn`, `list_wwn_pools`, `list_vsans`, `list_fc_uplinks` |
| Generic | `get_object` (any DN), `query_class` (any class) |

List tools query every central in parallel and tag rows with `central`; DN tools find the central
that owns the object. Unreachable centrals are reported, not fatal.

## Configuration (one Secret, any number of UCS Centrals)

| Variable | Required | Default |
|---|---|---|
| `MCP_AUTH_TOKENS` | yes | comma-separated bearer tokens (>= 24 chars) |
| `UCSC_<N>_HOST` / `_USERNAME` / `_PASSWORD` | yes, per instance | N = 1, 2, 3 ... |
| `UCSC_<N>_NAME` | | the host |
| `UCSC_<N>_PORT` | | `443` |

Note: `ucscsdk` does not verify the UCS Central TLS certificate.

## Run

```bash
docker load -i ucsc-mcp-2.0.tar.gz     # or: docker build -t ucsc-mcp:2.0 .
docker run -d -p 8000:8000 --env-file .env ucsc-mcp:2.0
```

OpenShift:
```bash
oc create secret generic ucsc-mcp-env --from-env-file=.env
oc apply -f openshift.yaml    # set the image first
```
MCP endpoint: `http://<host>:8000/mcp` (in-cluster: `http://ucsc-mcp.<ns>.svc:8000/mcp`).

## Connecting a client (token required)

Every request must carry `Authorization: Bearer <token>` (one of `MCP_AUTH_TOKENS`).
`/healthz` is open for probes and returns nothing sensitive. With no token configured the server
refuses to start (set `MCP_AUTH_DISABLED=true` only for a lab).

Claude Code:
```bash
claude mcp add --transport http ucs-central http://HOST:8000/mcp --header "Authorization: Bearer $TOKEN"
```
VS Code / Copilot (`mcp.json`):
```json
{ "servers": { "ucs-central": { "type": "http", "url": "http://HOST:8000/mcp",
  "headers": { "Authorization": "Bearer ${input:ucs-central_token}" } } },
  "inputs": [ { "id": "ucs-central_token", "type": "promptString", "password": true, "description": "ucs-central MCP token" } ] }
```

Rotate a token: put old and new in `MCP_AUTH_TOKENS=new,old`, update clients, then remove the old one
(`oc set env` or recreate the Secret and `oc rollout restart`).
Over a Route, use TLS (`oc create route edge ...`) so the token is never sent in clear text.
