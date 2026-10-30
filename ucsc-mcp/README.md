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

`python3 test_readonly.py` and `python3 test_san.py` run every tool against fake UCS Centrals (with server-side filter evaluation) and prove writes are blocked.

## Built-in guidance for the connecting Claude

- **Server instructions** (sent on connect): DN formats, domains and centrals, which tool to use for
  which question, how to read operability / association / fault states, and the cross-system SAN
  trace with the MDS and PowerMax MCP servers.
- **Prompts**: `ucs_health_check`, `troubleshoot_server`, `trace_san_path`, `domain_san_health`.

## Tools (26)

| Area | Tools |
|---|---|
| Connection | `test_connection`, `list_centrals` |
| Inventory | `list_domains`, `list_fabric_interconnects`, `list_chassis`, `list_servers`, `get_server`, `list_firmware` (grouped; `limit>0` adds raw rows) |
| Health / events / logs | `get_domain_health`, `list_faults`, `get_events`, `get_audit_log` (`since=7d` default, `30d` or `all`) |
| Service profiles | `list_service_profiles`, `get_service_profile`, `get_service_profile_vhbas` |
| SAN troubleshooting | `trace_service_profile_san` (one call: every vHBA's WWPN/fabric/VSAN/pinning, adapter FC link and bad frames, FI FC uplinks and port-channels with current errors, problems list, next hops for MDS/PowerMax), `get_domain_fc_health`, `list_fc_port_channels`, `get_fc_port_errors`, `get_vhba_pinning` |
| SAN | `find_wwpn`, `list_wwn_pools`, `list_vsans`, `list_fc_uplinks` |
| Generic | `get_object` (any DN), `query_class` (any class); both take `props=` to return only named properties |

List tools query every central in parallel and tag rows with `central`; DN tools find the central
that owns the object. Unreachable centrals are reported, not fatal.

## Configuration (one Secret, any number of UCS Centrals)

| Variable | Required | Default |
|---|---|---|
| `MCP_AUTH_TOKENS` | yes | comma-separated bearer tokens (>= 24 chars) |
| `UCSC_<N>_HOST` / `_USERNAME` / `_PASSWORD` | yes, per instance | N = 1, 2, 3 ... |
| `UCSC_<N>_NAME` | | the host |
| `UCSC_<N>_PORT` | | `443` |
| `UCSC_SESSIONS` / `UCSC_<N>_SESSIONS` | | `3` parallel logged-in sessions per UCS Central |
| `UCSC_CACHE_TTL` | | `120` seconds; identical queries inside this window are served from memory (`0` = off) |

Note: `ucscsdk` does not verify the UCS Central TLS certificate.

## Performance on large UCS Centrals

- **Filters run on UCS Central**, not in the pod: name, org, type, association, severity, ack,
  fault code, domain, serial, model, problems-only. Only matching objects are sent back.
- **Single-object tools read one subtree**: `get_server` / `get_service_profile` fetch only that
  object and its children (adapters, vHBAs, vNICs, faults) in one request, instead of scanning
  every fault in UCS Central.
- **Real parallelism**: the Cisco SDK serialises every request in the process with one global
  lock; this server replaces it with a per-session lock and keeps a small session pool, so
  parallel questions and multiple UCS Centrals run at the same time.
- **Short cache** for repeated identical queries, and list results are capped (default 200) with
  totals and counts (`list_faults` and `query_class` 50; `list_faults` adds `by_code`), so Claude doesn't receive tens of thousands of rows.
- If a UCS Central version rejects a filter, the server automatically falls back to an unfiltered
  query and filters in the pod (slower, still correct).

## Run

The marketplace package registers this server as `ucsc`; the examples below use `ucsc`, any name works.

Local / stdio (no token): `MCP_TRANSPORT=stdio python3.12 server.py` (fastmcp needs Python >= 3.10, so
not the VM's system Python 3.9; use the container there).

```bash
docker load -i ucsc-mcp-2.2.tar.gz     # or: docker build -t ucsc-mcp:2.2 .
docker run -d -p 8000:8000 --env-file .env ucsc-mcp:2.2
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
claude mcp add --transport http ucsc http://HOST:8000/mcp --header "Authorization: Bearer $TOKEN"
```
VS Code / Copilot (`mcp.json`):
```json
{ "servers": { "ucsc": { "type": "http", "url": "http://HOST:8000/mcp",
  "headers": { "Authorization": "Bearer ${input:ucsc_token}" } } },
  "inputs": [ { "id": "ucsc_token", "type": "promptString", "password": true, "description": "ucsc MCP token" } ] }
```

Rotate a token: put old and new in `MCP_AUTH_TOKENS=new,old`, update clients, then remove the old one
(`oc set env` or recreate the Secret and `oc rollout restart`).
Over a Route, use TLS (`oc create route edge ...`) so the token is never sent in clear text.
