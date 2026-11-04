---
name: commvault-infra-check
description: Health of the Commvault infrastructure per CommCell - MediaAgents, libraries (S3 cloud and NetApp CIFS / NFS), storage pools and deduplication, aux copies, CommServe DR backups and CommServe DR / LiveSync, security posture. Triggers - "are the MediaAgents ok", "library almost full", "S3 library offline", "DDB", "aux copy behind", "is the CommServe DR ok"
---
# Commvault infrastructure check

Read-only. Per CommCell (commvault-env1 / -env2 / -env3), in parallel; say which CommCells were checked.

| Layer | Calls | Look for |
|---|---|---|
| CommCell | `get_commcell_details`, `get_entity_counts` | version (matches environment.md?), counts vs last check |
| MediaAgents | `get_mediaagent_list` | offline / not ready / maintenance mode, per site: fewer than the 4-5 expected |
| Libraries | `get_library_list`, `get_library_properties` | S3 cloud libraries: offline mount paths, access errors; NetApp CIFS / NFS libraries: mount path offline, free space; used % over the threshold |
| Storage pools / dedup | `get_storage_pool_list` | pool offline, DDB status, space saved dropping |
| Copies | `get_storage_policy_list`, `get_storage_policy_copy_details`, `get_storage_policy_copy_size` | aux copies with jobs to be copied (behind), copies without a second site |
| Space | `get_storage_space_utilization` | growth vs capacity |
| Jobs | `get_jobs_list(job_filter="AUXCOPY,CSDRBKP,DDBOPS,DATA_VERIFICATION,PRUNE")` | aux copy failures, CommServe DR backup missing in 24 h, DDB verification / data aging errors |
| Security | `get_security_score`, `get_security_posture` | items that dropped |

CommServe DR: the DR backup destination (its library / share) and the standby CommServe (LiveSync) are recorded in
environment.md; their state is not in the MCP: ask the user for the Command Center "CommServe DR" page or the
"Disaster Recovery Backup" report, and explain each state from the docs ("CommServe LiveSync", "DR backup").
S3 libraries: the bucket, endpoint and access node come from the library properties; an access error is explained from
the cloud-storage troubleshooting pages. NetApp libraries: compare with the ontap MCP (volume space, the share / export).

## Output
| CommCell | Component | State | Value vs threshold | Finding |, findings by severity with the documented meaning, and what
was not checked (logs on the MediaAgents, the S3 service itself).
