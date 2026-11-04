---
name: brain-setup
description: Inventory the Flashback team's MCP servers (three Commvault CommCells, ontap, powermax, powerflex, docs) and environment (CommCells, MediaAgents, libraries, plans, MCE clusters with OADP, Veeam), then write ~/.claude/brain/tool-map.md and fill ~/.claude/brain/environment.md. Use once after the team's MCP servers are set, after adding or upgrading one, or when asked to refresh the tool map.
disable-model-invocation: true
---
# Brain setup (Flashback)

Goal: Claude knows the exact tool names of every MCP server and the shape of the backup environment. Read-only: only
list / get / show tools and `oc get`. Both files are the team's (committed and pushed for everyone): run this once per
team, not per person; a teammate's later run updates them.

## 1. Tool map
For every connected server (commvault-env1 / -env2 / -env3, ontap, powermax, powerflex, the docs MCP) list its tools
from your own tool list; plugin tools are named `mcp__plugin_paas-brain-flashback_<server>__<tool>`. Write only what the
descriptions do not say, 3-6 lines per server, the whole file under ~60 lines:
- the server name and its 3-6 entry tools, and which question each answers (Commvault: `get_failed_jobs`,
  `get_jobs_list`, `get_job_detail`, `get_retention_info_of_a_job`, `get_sla_status`, `get_library_list`,
  `get_mediaagent_list`; ontap: snapshots, policies, SnapMirror; powermax: SnapVX, SRDF; powerflex: snapshots, RCGs)
- parameter quirks found (Commvault `jobLookupWindow` in seconds, `limit` / `offset` paging, `job_filter` values)
- **DO NOT USE** (the guard blocks or asks, list them anyway): Commvault `kill_job`, `suspend_job`, `resume_job`,
  `resubmit_job`, `run_backup_for_subclient`, `enable_schedule`, `disable_schedule`, `set_user_enabled`,
  `create_send_logs_job_*`, the DocuSign / Salesforce setup and recover tools; any create / delete / modify tool of the others
- OADP and Veeam have no MCP: one line each ("OADP: oc read commands on the MCE clusters"; "Veeam: PowerShell the
  user runs on the VBR server")
Write `~/.claude/brain/tool-map.md` (replace the whole file).

## 2. Environment (fill ~/.claude/brain/environment.md, keep everything already filled in)
- **Commvault, per CommCell server**: `get_commcell_details` (CommServe name, version → docs product: 11.36 =
  `2024e`), `get_mediaagent_list` (names, OS, online; group them per site if the names show it, else ask),
  `get_library_list` (+ `get_library_properties` of a few: S3 bucket / endpoint or NetApp CIFS / NFS path),
  `get_storage_pool_list` (dedup pools), `get_plan_list` / `get_storage_policy_list` (retention, aux copies),
  `get_entity_counts`. Ask which environment each server is and its CommServe DR / Command Center url.
- **OADP**: ask which MCE clusters (kube contexts) to read; never `oc login` or switch context yourself. In the current
  context: `oc get csv -n openshift-adp` (OADP version → docs `oadp-1.4|1.5|1.6`), `oc get clusterversion`, `oc get
  dpa,backupstoragelocations.velero.io -n openshift-adp` (bucket, prefix, plugins), `oc get schedules.velero.io -n
  openshift-adp` (cron, ttl), `oc get hostedclusters -A` (names, namespaces, platform), `oc get volumesnapshotclass`.
- **Veeam**: ask the user (VBR and Veeam ONE names, proxies per site, NFS repositories) or for the output of
  `Get-VBRViProxy | Select Name, Host` and `Get-VBRBackupRepository | Select Name, Path`.
- **Storage**: ONTAP clusters and versions, snapshot policies in use and SnapMirror / SVM DR pairs (ontap); SnapVX
  policies and SRDF groups (powermax); snapshot policies and RCGs (powerflex).
- Ask for what no tool shows: RPO / RTO per tier, thresholds, naming conventions, owners.
Show the draft, ask the user to confirm the uncertain items, then write the file.

## 3. Smoke test
One cheap call per server (Commvault `get_commcell_details`, ontap / powermax / powerflex a list call, docs
`list_sources`) and report | server | reachable | tools | notes |. The docs answer must show the Flashback library
(`commvault`, `veeam`, `redhat` / `oadp-*` products; `~/.claude/brain/libraries/flashback/MANIFEST.md`); the general
SAN library instead means the team's library is not installed (root: `paas-library import flashback ...`).
