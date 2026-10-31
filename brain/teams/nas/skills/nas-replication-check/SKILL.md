---
name: nas-replication-check
description: Check NAS replication health and DR readiness - SyncIQ, ONTAP SnapMirror for NAS volumes, VAST replication. Triggers - "is SyncIQ healthy", "SnapMirror lag on NAS", "DR readiness for the file shares", "replication failed"
---
# NAS replication check

Read-only: never start, pause, resume, break, fail over, resync or edit a policy, relationship or job.
Cover every cluster and both directions; say which were not checked.

## ONTAP SnapMirror (live, ontap MCP)
Relationships for NAS volumes: source and destination path, type and policy, state, status, healthy,
unhealthy-reason, lag time, last transfer error and time; cluster and vserver peers. For him on the destination
cluster: `snapmirror show -fields state,status,healthy,unhealthy-reason,lag-time,last-transfer-error`.
Meanings: `netapp` / `ontap`, `kb-ontap`, EMS `snapmirror.*` in `ontap-ems-<version>`.

## PowerScale SyncIQ (no MCP: he pastes)
To be run by you: `isi sync policies list`, `isi sync policies view <policy>`, `isi sync jobs list`,
`isi sync reports list --policy <policy> --limit 5`, `isi sync target list`, `isi sync settings view`.
Look at: enabled, schedule, last success time vs RPO, last job state and errors, target host and path, source
and target access zone, whether the target is writable (failover state). Docs: `dell` / `powerscale` (OneFS 9.10), `kb`.

## VAST (no MCP: he pastes)
Replication peers and protected paths / protection policies from the VAST CLI / VMS: state, schedule, last
snapshot replicated, lag. Docs: `vast` / `docs`, `api-5-5` for the read-only GET calls.

## Checks
- Last success older than the RPO in environment.md (Replication table), or no RPO recorded: ask.
- Job or relationship in error, paused or unhealthy; peers unreachable; target out of space.
- DR readiness: target exists for every replicated path, the SMB shares / exports / quotas that clients need
  also exist on the target side (replication does not always carry them), DNS / SmartConnect failover plan.
- Policies that cover a path with no recent snapshots, and shares with no replication at all.

## Output
| Source | Target | Type | State | Last success | Lag vs RPO | Finding |
|---|---|---|---|---|---|---|
Findings by severity with the documented meaning of each state (title, url, version), commands for him to run
(never started by me), and what was not checked.
