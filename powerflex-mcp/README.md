# PowerFlex MCP server (read-only)

MCP server for Dell PowerFlex (ScaleIO / VxFlex OS) through its REST API: the **Gateway (3.x)** or
**PowerFlex Manager (4.x / 5.x)**, detected at sign-in. Covers the whole system: health in one call,
capacity, inventory (PD, pools, SDS, SDC, volumes, devices, fault sets), replication, NVMe/TCP, alerts,
the event log, SDS network latency and **all statistics**, converted to IOPS, MB/s, latency ms and GB.

## Read-only enforcement

Every HTTP request goes through one session object that refuses anything except:
- `GET` under `/api/`, `/rest/`, `/dtapi/`
- the `POST`s that only read: sign-in (`/rest/auth/login|refresh`), `/api/instances/querySelectedStatistics`,
  `/api/instances/System/action/queryMdmCluster`, `Sds::<id>/action/querySdsNetworkLatencyMeters`,
  `ProtectionDomain::<id>/action/querySdsConnectivityStatus`, `.../instances/action/queryBySelectedIds|queryIdByKey`,
  and the 4.x metrics query `/dtapi/rest/v1/metrics/query`

Every other `POST` (all PowerFlex changes are `POST .../action/...`), `PUT`, `PATCH`, `DELETE`, any
`..` and any URL outside the API are blocked before they are sent. Also give the account only a
**Monitor** (read-only) role. `python3 test_readonly.py` runs every tool against a fake 3.x Gateway and
a fake 4.x Manager and proves writes never leave the process.

## Tools (28)

| Area | Tools |
|---|---|
| Connection | `test_connection` (every gateway: API kind, version, systems), `list_systems` |
| System | `get_system` (+ MDM cluster), `get_health` (one call: MDM, PDs, SDS, SDC, devices, pool degraded / failed / rebuild, used % vs thresholds, alert counts), `get_capacity` |
| Inventory | `list_protection_domains`, `list_storage_pools`, `get_storage_pool`, `list_sds`, `get_sds`, `list_sdc`, `get_sdc` (also NVMe/TCP hosts), `list_volumes`, `get_volume`, `find_volume`, `list_devices`, `list_fault_sets` |
| Protection | `get_replication` (peer systems, RCGs, SDRs, pairs), `list_snapshot_policies`, `list_nvme` (hosts, SDTs) |
| Events | `get_alerts` (active alerts), `get_events` (4.x+ event log, `since_hours`; 3.x: says where the MDM log is) |
| Network | `get_network_latency` (SDS-to-SDS latency meters, PD connectivity check) |
| Performance | `get_performance_overview` (system, pools, top / worst-latency volumes, SDCs, SDSs, NVMe hosts), `get_statistics` (any object, KPI / ALL / names, with sampling), `list_statistics_properties`, `metrics_query` (4.x metrics API) |
| Other | `powerflex_get` (any GET endpoint) |

Prompts: `daily_health_check`, `troubleshoot_volume_latency`, `openshift_volume_troubleshoot`, `capacity_report`, `rebuild_status`, `replication_health`.

Every tool takes object **names or ids**; `find_volume` also takes what a host shows
(`/dev/disk/by-id/emc-vol-<system>-<volume>`, an `eui.` / `nvme-eui.` id) and an OpenShift CSI PV
`volumeHandle` (`<systemId>-<volumeId>`). OpenShift workers are SDCs or NVMe hosts: `get_sdc <node name or IP>`;
CSI volumes: `list_volumes name_contains=k8s-` (the driver's default prefix).

**Statistics are live.** PowerFlex returns rates over the last few seconds; there is no history in the
API. `samples` + `interval_seconds` (up to 300 s) give avg / max / min / last. Longer history is in
PowerFlex Manager, CloudIQ or Grafana.

## Configuration (one Secret, any number of gateways)

| Variable | Required | Default |
|---|---|---|
| `MCP_AUTH_TOKENS` | yes | comma-separated bearer tokens (>= 24 chars) |
| `POWERFLEX_<N>_HOST` / `_USERNAME` / `_PASSWORD` | yes, per gateway | N = 1, 2, 3 ... |
| `POWERFLEX_<N>_NAME` | | the host |
| `POWERFLEX_<N>_PORT` | | `443` |
| `POWERFLEX_<N>_VERIFY_SSL` | | `false` (`true`, or a CA bundle path) |
| `POWERFLEX_<N>_TIMEOUT` | | `60` s |
| `POWERFLEX_DEFAULT_SYSTEM` | | system id or name used when `system_id` is omitted |

Each tool call goes to the gateway that manages that system. 4.x tokens last 5 minutes; the server
signs in again on its own.

## Run

```bash
docker load -i powerflex-mcp-1.0.tar.gz     # or: docker build -t powerflex-mcp:1.0 .
docker run -d -p 8000:8000 --env-file .env powerflex-mcp:1.0
```

OpenShift:
```bash
oc create secret generic powerflex-mcp-env --from-env-file=.env
oc apply -f openshift.yaml    # set the image first
```
MCP endpoint: `http://<host>:8000/mcp`. `/healthz` is open for probes.

## Connecting a client (token required)

```bash
claude mcp add -s user --transport http powerflex http://HOST:8000/mcp --header "Authorization: Bearer $TOKEN"
```
Over a Route, use TLS (`oc create route edge ...`) so the token is never sent in clear text.
