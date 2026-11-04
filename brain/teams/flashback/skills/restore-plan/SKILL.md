---
name: restore-plan
description: Prepare a restore, step by step, for the user to run - PostgreSQL, SQL Server (standalone or Always On AG), Oracle RAC, VMware VM, Exchange (IntelliSnap), etcd, S3 bucket, OpenShift hosted cluster (OADP), NetApp snapshot / FlexClone, PowerMax SnapVX, PowerFlex snapshot - with the proven restore point, pre-checks, steps, post-checks and rollback. Triggers - "restore X to", "I need to recover", "point in time restore", "out of place restore", "how do I restore"
---
# Restore plan (prepared here, run by the user)

Never start the restore (B1). The output is a runbook "to be run by you". Ask only what changes the plan: which system,
in place or out of place (target name), point in time, what may be overwritten.

## 1. Prove the restore point (B3)
- Commvault: the subclient's jobs (`get_jobs_list(client_id=..., jobLookupWindow=...)`), the chosen job's
  `get_job_detail` (Completed, end time, size) and `get_retention_info_of_a_job`; which copy holds it
  (`get_storage_policy_copy_details`: primary on S3 / NetApp, aux copy done?). Databases: the full / differential and
  every log backup after it up to the target time, without a failed log job in between.
- Veeam: the restore points of the VM (to be run by you: `Get-VBRRestorePoint -Name <vm> | Sort-Object CreationTime | Select-Object -Last 10 Name, CreationTime, Type`).
- OADP: `oc get backups.velero.io -n openshift-adp -l velero.io/schedule-name=<schedule> --sort-by=.status.startTimestamp`
  (phase Completed, no errors, expiration after the restore window) → `oadp-restore-hosted-cluster`.
- Storage snapshots: the snapshot exists with its creation time (ontap / powermax / powerflex MCP).

## 2. The procedure from the docs, for this version
Search the library (`docs-lookup`) for the exact restore page and quote its steps; the usual pages:
| Workload | Commvault page to search ("restore" plus) | Key decisions |
|---|---|---|
| PostgreSQL | "PostgreSQL restore", "point-in-time", "out-of-place", block-level vs dump-based | data directory, WAL / archive path, service stopped |
| SQL standalone | "Restoring SQL Server databases", "step-by-step restore", "to a point in time" | recovery state, overwrite, file relocation |
| SQL Always On AG | "Restoring an Always On Availability Database" | remove the database from the AG first, restore on the primary, re-seed / re-join the secondaries |
| Oracle RAC | "Oracle RAC restore", "RAC restore to a point in time" | the RAC pseudo-client, instances down / mount, control file, RMAN catalog |
| VMware VM | "full VM restore", "out of place", "file-level restore", "live mount" | power on, new name / network, overwrite |
| Exchange IntelliSnap | "Exchange Database restore", "IntelliSnap restore", "revert" | from snapshot vs backup copy; dismount; recovery database |
| etcd (on VMs) | "Restoring a Kubernetes etcd Snapshot to a File System", or the file-system subclient | the snapshot file, then the etcd / cluster restore procedure of that platform |
| S3 bucket | "Amazon S3 restore", in place / out of place | versioning, overwrite, the target bucket |
Veeam: `veeam` / `vbr-userguide` ("Entire VM restore", "Instant recovery", "PostgreSQL restore"). NetApp: `ontap`
("restore a volume from a snapshot", "single file snapshot restore", "FlexClone"). PowerMax: SnapVX restore / link.
PowerFlex: "restore volume from snapshot".

## 3. Write the runbook
1. Pre-checks (read-only, with the command or screen): restore point (step 1), target free space, the application owner
   agreed, nothing else restoring, current state captured (row counts, VM snapshot, a SnapVX snapshot of the target).
2. Steps: numbered Command Center / console clicks or commands / YAML exactly as the docs give them, with every value
   filled in from the tool results and placeholders only where unknown (plus the read-only command that shows it).
3. Post-checks: job Completed, the application's own check (DB opens, AG synchronized, VM boots, hosted cluster
   Available), the next scheduled backup runs (a restore can break a log chain: plan a full backup after it).
4. Rollback: what to do if it fails half-way (the captured state from pre-checks).
5. Expected duration from the size and recent restore / backup throughput, against the RTO.
Save it to `~/storage-reports/<date>-restore-<target>/runbook.md` and give the path.
