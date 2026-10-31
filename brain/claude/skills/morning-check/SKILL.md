---
name: morning-check
description: Daily storage health report across PowerMax, PowerFlex, ONTAP, Harvest, MDS, UCS Central and Aria - new alerts, faults, degraded paths and ports, capacity thresholds, replication, recent changes - in one page sorted by severity. Use for "morning check", "daily health", "anything wrong today".
disable-model-invocation: true
---
# Morning check

Call the layers' summary tools yourself, independent calls together in one turn; an agent only to drill into a layer
that is not OK. Window: last 24 h (or since the last check).

| Layer | What |
|---|---|
| PowerMax | `list_arrays`, then per array: `get_array_health(array_id)`, `list_srps(array_id)`, `get_replication(array_id=...)` (RDF group state); `get_alerts` since_hours=24 once |
| ONTAP | cluster / node health, EMS errors and alerts, aggregates / volumes over threshold, SnapMirror lag |
| Harvest | anomalies: latency peaks on top LUNs / volumes overnight |
| PowerFlex | `get_health`, `get_alerts`, `get_events` since_hours=24, `get_replication()` |
| MDS | per switch, both fabrics: `scan_port_errors`, `slow_drain_check`, `port_channel_health`, `get_log_events` max_severity=4 since_hours=24 |
| UCS | `get_domain_health` per domain, `list_faults` severity='critical,major' unacked_only=true, `list_fc_uplinks` problems_only=true |
| Aria | storage-related alerts: datastore latency, datastore space, host path issues |
| Changes | PowerMax `get_audit_log` + `get_alerts` (same window), UCS `get_audit_log`, MDS `show_accounting_log` |

Output (one page):
1. Status line per layer: OK / WARNING / CRITICAL.
2. Findings table sorted by severity: layer | object | finding | since | evidence | action / owner.
3. "Changed since yesterday": read the newest earlier `~/storage-reports/*-morning-check.md` (Grep its findings table)
   and list what is new, what is gone and what got worse against it (capacity numbers: the delta); none yet → say so.
4. Checks that could not run.
Save as `~/storage-reports/<date>-morning-check.md`.
