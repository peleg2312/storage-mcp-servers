---
name: commvault-job-check
description: Investigate a Commvault job or a client's failing backups - job details, task details, error codes, delay reasons, retention, the subclient, plan, storage policy copy, library and MediaAgent behind it, and the documented fix. Triggers - "why did job X fail", "backup failed for client Y", "error code [19:...]", "job stuck pending", "SQL / Oracle / PostgreSQL backup failed"
---
# Commvault job check

Read-only: never kill, suspend, resume, resubmit or start a job (the hook blocks those tools). Ask which CommCell when
the user did not say; a job ID means nothing on another CommCell.

1. **The job**: `get_job_detail(job_id)` (status, phase, failure reason and error code, client, agent, instance,
   subclient, backup level, start / end, size, MediaAgent, storage policy and copy), `get_job_task_details(job_id)`
   (the schedule or user that started it, options), `get_retention_info_of_a_job(job_id)` (when it ages).
   A client name instead: `get_client_list` → `get_jobs_list(client_id=..., jobLookupWindow=604800)` and look at the
   pattern (always the same phase, always at the same hour, only one subclient, after a change).
2. **The configuration**: `get_subclient_list` / `get_subclient_properties` (content, plan / storage policy, filters),
   `get_plan_properties` or `get_storage_policy_properties` + `get_storage_policy_copy_details` (copies, retention, aux
   copy), `get_library_properties` (mount paths, S3 bucket or NetApp share, space), `get_mediaagent_list` (online).
3. **Meaning**: every distinct error code and delay reason from the docs (`commvault` / the CommCell's version, the
   agent's troubleshooting pages: "SQL Server troubleshooting", "PostgreSQL troubleshooting", "Oracle RAC", "IntelliSnap
   troubleshooting", "cloud storage troubleshooting"). Quote the cause and the documented resolution.
4. **Logs** (not reachable from here): name the log and the machine for the user: e.g. `SQLBackupmaster.log` /
   `SQLBackup.log` (SQL client), `ClOraAgent.log` / `ORASBT.log` (Oracle), `PostGresBackupParent.log` (PostgreSQL),
   `CVMA.log` / `CloudActivity.log` (MediaAgent, cloud library), `JobManager.log` (CommServe), `vsbkp.log` (VSA proxy);
   ask for the lines around the job ID. Check the log names in the docs for the version.
5. **Per workload**: SQL Always On: backup preference and which replica ran it, log chain after a failover. Oracle RAC:
   every instance reachable, archive log destinations, RMAN channel errors. PostgreSQL: WAL archiving
   (`archive_command`) for log backups, block-level vs dump. Exchange IntelliSnap: the array snapshot job and the backup
   copy job are separate: check both. VMware: CBT, snapshot removal, the proxy / transport mode. S3: the bucket
   credentials and the access node. etcd on VMs: the pre / post scripts or the file-system subclient that copies the snapshot.

## Output
Answer first (why it failed, documented cause), evidence table (CommCell, job, client / subclient, phase, error code,
MediaAgent, library), the fix as steps "to be run by you" (with the doc citation), the next run to watch, and what was
not checked (logs, the client itself).
