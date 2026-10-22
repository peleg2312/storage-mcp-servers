# PowerMax MCP server (read-only)

MCP server for Dell PowerMax / VMAX through the Unisphere for PowerMax REST API: inventory,
host mapping, replication, **all performance metrics**, **alerts (events)** and the **audit log**.

## Read-only enforcement

Every HTTP request goes through one session object that refuses anything except:
- `GET` under `/univmax/restapi`
- `POST` to `/univmax/restapi/performance/<Category>/keys|metrics` (Unisphere uses POST for metric queries)

`PUT`, `PATCH`, `DELETE`, every other `POST`, and any URL outside the REST API are blocked before
they are sent. Also give the Unisphere user only the **Monitor** role.
`python3 test_readonly.py` exercises every tool against a fake Unisphere and proves writes never leave the process.

## Built-in guidance for the connecting Claude

- **Server instructions** (sent on connect): IDs and formats, the order to call tools, performance
  categories, how to read response time/busy %, and how to report findings.
- **Tool descriptions** with parameter formats and when to use each tool.
- **Prompts** the client can offer: `daily_health_check`, `troubleshoot_host_latency`, `what_changed`, `capacity_report`, `srdf_health`.
- Performance results come back **summarised** (avg/max/min/last, time of peak) so the model can
  reason over them; `raw=True` adds the time series.

## Tools (28)

| Area | Tools |
|---|---|
| Connection | `test_connection` (all Unispheres), `list_unispheres`, `list_arrays` |
| Array | `get_array`, `get_array_health`, `list_srps` |
| Storage | `list_storage_groups`, `get_storage_group`, `get_volume`, `find_volume_by_wwn` |
| Hosts/SAN | `list_hosts`, `get_host`, `find_wwpn`, `list_masking_views`, `get_masking_view`, `get_port_group`, `list_directors`, `get_port` |
| Replication | `get_replication` (SRDF groups, SnapVX snapshots) |
| Events | `get_alert_summary`, `get_alerts` |
| Logs | `get_audit_log` |
| Performance | `get_performance_overview`, `get_performance`, `list_performance_categories`, `list_performance_metrics`, `list_performance_keys` |
| Other | `unisphere_get` (any GET endpoint) |

`find_wwpn` traces WWPN → initiator → host → masking view → storage group / port group, so it pairs
with the MDS and UCS Central MCP servers for an end-to-end SAN path.

## Configuration (one Secret, any number of Unisphere servers)

| Variable | Required | Default |
|---|---|---|
| `MCP_AUTH_TOKENS` | yes | comma-separated bearer tokens (>= 24 chars) |
| `UNISPHERE_<N>_HOST` / `_USERNAME` / `_PASSWORD` | yes, per server | N = 1, 2, 3 ... |
| `UNISPHERE_<N>_NAME` | | the host |
| `UNISPHERE_<N>_PORT` | | `8443` |
| `UNISPHERE_<N>_VERIFY_SSL` | | `false` (`true`, or a CA bundle path) |
| `UNISPHERE_<N>_API_VERSION` | | auto-detected (`92`, `100`, `101` ...) |
| `POWERMAX_DEFAULT_ARRAY` | | used when `array_id` is omitted |
| `PERF_WORKERS` | | `8` parallel requests in `get_performance_overview` |

Arrays are routed automatically: the server asks every Unisphere which arrays it sees and sends each
array's calls to the Unisphere where it is **local** (where its performance data lives). Alerts and
alert summaries are merged across all Unispheres and tagged with the Unisphere name.

## Run

```bash
docker load -i powermax-mcp-2.0.tar.gz     # or: docker build -t powermax-mcp:2.0 .
docker run -d -p 8000:8000 --env-file .env powermax-mcp:2.0
```

OpenShift:
```bash
oc create secret generic powermax-mcp-env --from-env-file=.env
oc apply -f openshift.yaml    # set the image first
```
MCP endpoint: `http://<host>:8000/mcp` (in-cluster: `http://powermax-mcp.<ns>.svc:8000/mcp`).

## Connecting a client (token required)

Every request must carry `Authorization: Bearer <token>` (one of `MCP_AUTH_TOKENS`).
`/healthz` is open for probes and returns nothing sensitive. With no token configured the server
refuses to start (set `MCP_AUTH_DISABLED=true` only for a lab).

Claude Code:
```bash
claude mcp add --transport http powermax http://HOST:8000/mcp --header "Authorization: Bearer $TOKEN"
```
VS Code / Copilot (`mcp.json`):
```json
{ "servers": { "powermax": { "type": "http", "url": "http://HOST:8000/mcp",
  "headers": { "Authorization": "Bearer ${input:powermax_token}" } } },
  "inputs": [ { "id": "powermax_token", "type": "promptString", "password": true, "description": "powermax MCP token" } ] }
```

Rotate a token: put old and new in `MCP_AUTH_TOKENS=new,old`, update clients, then remove the old one
(`oc set env` or recreate the Secret and `oc rollout restart`).
Over a Route, use TLS (`oc create route edge ...`) so the token is never sent in clear text.
