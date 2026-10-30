---
name: powerflex-troubleshoot
description: Troubleshoot Dell PowerFlex (SDC / SDS / MDM, rebuild, rebalance, pool capacity, data unavailable, ESXi access) live through the powerflex MCP, with the PowerFlex docs, Dell KB and vCenter data. Triggers - "PowerFlex alert SIO...", "SDC disconnected", "rebuild is slow", "ESXi lost the eui devices"
---
# PowerFlex troubleshooting

**With the powerflex MCP connected** (read-only), collect live instead of asking: `get_health` (MDM
cluster, SDS / SDC states, device errors, degraded / failed / pending capacity, rebuild / rebalance,
alert counts), `get_alerts`, `get_capacity`, `get_performance_overview` and `get_statistics` with
`samples` (live rates only: two `get_storage_pool` calls a few minutes apart show a rebuild trend),
`get_sdc` / `get_volume` / `find_volume` for the `eui.` / `emc-vol-` ids, `get_replication`. Step 1 below
is then only for what the API does not show (`drv_cfg` on the SDC, ESXi paths).

Without it, evidence comes from (a) what the user runs and pastes, (b) vCenter-side data
(kuparashit `locate` / `related` on the `eui.` ids: ESXi hosts, datastores, VMs; Aria: latency, APD/PDL alerts), (c) the library per docs-lookup (dell/powerflex, dell/powerflex-api, dell/kb; release notes only for 3.6.x / 4.0.x); PDF titles are 'View': cite file + page.
Everything is read-only: only
`--query_*` commands, never `--set`, `--remove`, `--add` or anything in PowerFlex Manager that changes state.

## 1. Collect (commands for him; PowerFlex 3.x: on the primary MDM; 4.x / 5.x: `scli` on the MDM or
the PowerFlex Manager UI / REST API)
- Cluster: `scli --login --username <ro-user>` then `scli --query_cluster`, `scli --query_all`
  (summary of protection domains, pools, SDS/SDC counts, capacity, rebuild / rebalance state),
  `scli --query_all_sds`, `scli --query_all_sdc`, `scli --query_storage_pool --protection_domain_name
  <pd> --storage_pool_name <sp>`, `scli --query_all_volumes`, `scli --query_properties --object_type
  SDS --all_objects --properties STATE,RMCACHE_STATE` (property names: CLI Reference Guide).
- An SDC (ESXi host): `esxcli software vib list | grep -i scini` (SDC version),
  `/opt/emc/scaleio/sdc/bin/drv_cfg --query_mdms`, `drv_cfg --query_vols`, `drv_cfg --query_guid`;
  on Linux SDCs the same `drv_cfg`. Paths and devices on ESXi: `esxcli storage core device list | grep
  -A4 eui`, `esxcli storage core path list`.
- Alerts / events: PowerFlex Manager (Monitoring › Alerts / Events) or `scli --query_alerts` where the
  version has it; the SIO code and the exact event text.
- Versions: MDM / SDS / SDC / PowerFlex Manager (`scli --version`, `scli --query_all` header). They
  select the matching guide and release notes.

## 2. Classify and check (search `dell/powerflex` + `dell/kb` with the exact alert / event text first)
| Symptom | Look at | Library terms |
|---|---|---|
| SDC disconnected / ESXi APD on `eui.` devices | `drv_cfg --query_mdms` (MDM IPs reachable? data network VLAN / MTU), scini module loaded, SDC version vs MDM version | "SDC disconnected", "scini", "APD" (`dell/kb` ESXi SDC article) |
| SDS disconnected / failed | node up? both data NICs? SDS service; `query_all_sds` state | "SDS disconnected", SIO code |
| Rebuild / rebalance slow or stuck | `query_all` rebuild / rebalance counters over two samples, pool rebuild throttling policy, failed devices | "rebuild", "rebalance", "throttling", "forward rebuild", "backward rebuild" |
| Capacity: degraded / failed / unavailable, spare policy | `query_storage_pool`: spare %, capacity in use, "degraded", "failed", "unavailable"; thin vs thick | "spare policy", "degraded capacity", "data unavailable" |
| Performance | `query_properties` on SDS / SDC IOPS and bandwidth; Aria latency on the datastores; read RAM cache / NVDIMM state | "performance", "RMcache", "fine granularity" |
| MDM cluster | `query_cluster`: mode (3 / 5 nodes), tie breaker, replicas, "degraded" | "MDM cluster", "tie breaker" |

## 3. Correlate with VMware
kuparashit: which datastores / VMs sit on the affected `eui.` volumes and which ESXi hosts are SDCs
(identify-lun step 3: EUI ↔ volume ID format from `dell/powerflex`, "device identifier eui"). Aria:
latency and alerts of those datastores in the window.

## Output
Answer first (what is wrong, since when, blast radius: pools / volumes / datastores / VMs), evidence
table (command | object | value), findings by severity, the documented meaning and recommended action
with citations (guide file name + page or KB number, version), then the next read-only commands for him.
Say explicitly that the array side was not checked live if he could not run the commands.
