---
name: morning-check
description: Daily storage health report across PowerMax, ONTAP, Harvest, MDS, UCS Central and Aria - new alerts, faults, degraded paths and ports, capacity thresholds, replication, recent changes - in one page sorted by severity. Use for "morning check", "daily health", "anything wrong today".
---
# Morning check

Run the layers in parallel (agents if available). Window: last 24 h (or since the last check).

| Layer | What |
|---|---|
| PowerMax | `daily_health_check` / `get_array_health`, new alerts, SRDF health, SRP capacity |
| ONTAP | cluster / node health, EMS errors and alerts, aggregates / volumes over threshold, SnapMirror lag |
| Harvest | anomalies: latency peaks on top LUNs / volumes overnight |
| MDS | `fabric_health_check` both fabrics: ports down, error rates, slow drain, log events |
| UCS | `ucs_health_check` / `domain_san_health`: critical / major faults, FC uplinks |
| Aria | storage-related alerts: datastore latency, datastore space, host path issues |
| Changes | PowerMax `what_changed`, UCS audit log, MDS accounting log |

Output (one page):
1. Status line per layer: OK / WARNING / CRITICAL.
2. Findings table sorted by severity: layer | object | finding | since | evidence | action / owner.
3. "Changed since yesterday" list.
4. Checks that could not run.
Save as `~/storage-reports/<date>-morning-check.md`.
