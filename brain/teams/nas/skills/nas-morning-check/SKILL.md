---
name: nas-morning-check
description: Daily NAS health report - ONTAP NAS live (EMS, volumes and quotas over threshold, SnapMirror lag, LIFs, CIFS / name-mapping errors, Harvest latency peaks), PowerScale and VAST from pasted status output (events, pools, exceeded quotas, SyncIQ / replication, SmartConnect pools, VIP pools) - one page sorted by severity. Use for "morning check", "daily health", "anything wrong today".
disable-model-invocation: true
---
# NAS morning check

Read-only. Call the ONTAP and Harvest summary tools yourself, independent calls together in one turn; an agent only to
drill into a layer that is not OK. Window: last 24 h (or since the last check). PowerScale and VAST have no MCP
server: ask for the pasted output below in one message (placeholders in <>), then read it (python above ~20 lines; say
which cluster each block came from). Thresholds come from environment.md (My thresholds); none set: ask, do not guess.

| Layer | What |
|---|---|
| ONTAP (live, ontap MCP) | cluster and node health; EMS errors and alerts since 24 h; volumes and aggregates over the thresholds; quota report rows at or over a limit; SnapMirror lag against the RPO; LIFs down or not home; CIFS server and name-mapping errors in EMS |
| Harvest | latency peaks on the top NAS volumes overnight |
| PowerScale (pasted, to be run by you) | `isi status -q`; `isi event events list --begin <yesterday>`; `isi storagepool list`; `isi quota quotas list --exceeded`; `isi sync jobs list` and `isi sync reports list --state failed`; `isi network pools list` |
| VAST (pasted) | the VMS alarm list, cluster capacity, protection policy / replication status and VIP pool state (VMS, or a read-only REST GET; the exact call from the docs `vast` / `api-5-5`) |
| Changes | ONTAP configuration EMS events; PowerScale `isi_audit_viewer -t config` for the window; VAST audit log from VMS |

Explain every distinct event, alarm or failed state seen from the docs before concluding (N6): `ontap-ems-<version>`,
`dell` / `powerscale`, `vast` / `docs`; one lookup per distinct code, group repeats.

Output (one page):
1. Status line per layer: OK / WARNING / CRITICAL / NOT CHECKED (no paste, no tool).
2. Findings table sorted by severity: layer | cluster | object | finding | since | evidence | action / owner.
3. "Changed since yesterday": read the newest earlier `~/storage-reports/*-nas-morning-check.md` (Grep its findings
   table) and list what is new, what is gone and what got worse against it (capacity and quota numbers: the delta);
   none yet: say so.
4. Checks that could not run, and the pastes still missing.
Save as `~/storage-reports/<date>-nas-morning-check.md`.
