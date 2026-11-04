---
name: backup-morning-check
description: Daily backup health of every environment - the three Commvault CommCells (failed / missed jobs, SLA, libraries, MediaAgents, CommServe DR backup), Veeam (pasted sessions), OADP hosted-cluster schedules on the MCE clusters, NetApp SnapMirror / snapshots. Triggers - "morning check", "did last night's backups succeed", "backup status", "daily report"
---
# Backup morning check

Read-only. Cover every system below and say which were not reachable. Run the Commvault calls of the three CommCells
in parallel (or one `commvault-analyst` per CommCell); thresholds and RPOs from environment.md.

## 1. Commvault, per CommCell (commvault-env1 / -env2 / -env3)
- `get_failed_jobs` (jobLookupWindow 86400, raise `limit` until all are listed) and `get_jobs_list` (job_status All,
  job_filter `Backup,SNAPBACKUP,AUXCOPY,CSDRBKP`): failed, killed, "Completed w/ one or more errors", still running for
  more than its usual window, and pending / waiting jobs (their delay reason).
- `get_sla_status`: clients / subclients that missed their SLA (no good backup inside the RPO).
- `get_storage_space_utilization`, `get_library_list`, `get_mediaagent_list`: libraries over the warn %, offline
  mount paths, MediaAgents offline or not ready.
- CommServe DR backup (`CSDRBKP` jobs) in the last 24 h, and the CommServe DR / LiveSync state (environment.md).
- Every distinct error code: `get_job_detail` of one job per code, then its meaning from the docs (`commvault` /
  the CommCell's version).

## 2. Veeam (no MCP: to be run by you on the VBR server, PowerShell, then paste)
```powershell
Get-VBRBackupSession | Where-Object {$_.CreationTime -gt (Get-Date).AddDays(-1)} | Select-Object JobName, Result, State, CreationTime, EndTime | Sort-Object JobName | Format-Table -AutoSize
Get-VBRBackupRepository | ForEach-Object { [pscustomobject]@{Name=$_.Name; Path=$_.FriendlyPath; FreeGB=[math]::Round($_.GetContainer().CachedFreeSpace.InGigabytes,0); TotalGB=[math]::Round($_.GetContainer().CachedTotalSpace.InGigabytes,0)} }
```
Or the Veeam ONE "Backup Job Status" report / active alarms. Failed / warning jobs: `veeam-job-check`.

## 3. OADP, per MCE cluster (`oc` read commands, the user's current context; never `oc login` unasked)
`oc get schedules.velero.io,backupstoragelocations.velero.io -n openshift-adp` and the last backups per schedule:
`oc get backups.velero.io -n openshift-adp --sort-by=.status.startTimestamp -o custom-columns=NAME:.metadata.name,SCHEDULE:.metadata.labels.velero\.io/schedule-name,PHASE:.status.phase,START:.status.startTimestamp,ERRORS:.status.errors,WARNINGS:.status.warnings`
Each hosted cluster's Schedule: a Completed backup in the last hour (RPO 1 h), about 48 backups kept (TTL 48h), BSL
`Available`. Anything else: `oadp-backup-check`.

## 4. Storage-side protection (ontap / powermax / powerflex MCP)
SnapMirror relationships unhealthy or with lag over the RPO, SVM DR state; volumes whose snapshot policy made no new
snapshot; SRDF groups not Synchronized / Consistent; PowerFlex snapshot policies or RCGs in error (`snapshot-protection-check`).

## Output
One table per system: | System | Checked | OK | Failed / warning | Oldest missed RPO | Finding |, then findings by
severity (each with its documented meaning, title + url + version), what was not checked, and the commands for the user.
Over 15 rows: `report-export`.
