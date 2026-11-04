---
name: restore-drill
description: Plan and record a restore test (DR drill) - choose what to test per workload and environment, prepare each restore with restore-plan, then record the measured RTO / RPO, problems and evidence in a report. Triggers - "restore test", "DR drill", "prove we can restore", "audit evidence for restores", "quarterly restore test"
---
# Restore drill

Read-only on our side: every restore is run by the user (B1). This skill organises the test and writes the evidence.

1. **Scope**: one restore per workload type and environment that matters (environment.md recovery objectives):
   PostgreSQL, SQL standalone, SQL AG database, Oracle RAC, VMware VM (Commvault and Veeam), Exchange IntelliSnap, etcd,
   S3 bucket, one hosted cluster (OADP, same MCE), a NetApp volume from snapshot. Prefer out-of-place targets.
   Pick restore points of different ages (latest, a week, the oldest retained, the aux copy) to also prove retention.
2. **Prepare** each with `restore-plan` (restore point proven, runbook). List them in a table first and ask the user to
   confirm the scope and the targets.
3. **Record** as the user runs them (ask for the job ID / restore name, start and end time, result): look up each job
   read-only (`get_job_detail` / `oc get restores.velero.io`) for the real duration, size and errors.
4. **Report** `~/storage-reports/<date>-restore-drill/report.md` (+ `report-export` for the table):
   | Environment | Workload | Restore point (age) | Copy / library | Target | Started | Duration | RTO met | Data checked | Issues |
   then the issues with their documented cause and fix, follow-ups with owners, and what was not tested.
5. File what was learned (rule 6, topic `restores`): actual throughput per workload, steps that differed from the docs.
