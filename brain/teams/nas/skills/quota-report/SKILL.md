---
name: quota-report
description: Report NAS quotas near or over their limits across PowerScale, ONTAP and VAST, with growth when history exists. Triggers - "which quotas are full", "quota report", "who is over quota", "quota usage on"
---
# Quota report

Read-only: never create, change or remove a quota or its limits. Thresholds come from environment.md (My
thresholds); none set there: ask, do not guess.

## Collect
- **ONTAP (live, ontap MCP)**: the quota report per SVM (tree, user and group quotas on volumes and qtrees:
  used, hard limit, soft limit, files) and whether quota is enabled on the volume. Growth: harvest MCP volume
  space history, if present.
- **PowerScale (no MCP: he pastes)**, to be run by you: `isi quota quotas list --zone <zone> --verbose`
  (directory, user, group; hard, soft, advisory, grace), `isi quota quotas view <type> --path <path>`.
- **VAST (no MCP: he pastes)**: quotas on paths from the VAST CLI / VMS (hard and soft limit, used).
- Docs for the type and state meanings: `dell` / `powerscale`, `netapp` / `ontap`, `vast` / `docs`; cite versions.

## Steps
1. Normalise every row to: cluster, path, type, used, hard, percent, state. Quote paths exactly.
2. Mark rows at or above the warn and critical thresholds, exceeded soft limits (with grace expiry), and
   hard limits that are hit (writes fail with a quota or "disk full" error: explain it from the docs, N6).
3. Quotas with no limit (accounting only), and paths with usage but no quota, when the paste includes them.
4. Growth: from harvest or from two pastes at known dates; state the period. No history: say none.
5. Compare lists above ~20 rows in python.

## Output
| Cluster | Path | Type | Used | Hard | % | State |
|---|---|---|---|---|---|---|
Over 15 rows: export with `report-export` and show the top ones. Then findings by severity, sources, fixes as
commands for him to run (raise a limit, clean up) with rollback, and what was not checked (clusters not pasted,
snapshot space counting, user quotas not listed).
