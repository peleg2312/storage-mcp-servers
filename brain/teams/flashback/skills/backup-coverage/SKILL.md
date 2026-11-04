---
name: backup-coverage
description: Find what is not protected - clients with no backup or no recent good backup, subclients without a plan or schedule, plans without a second copy, VMs in vCenter / hosted clusters / volumes missing from Commvault, Veeam, OADP schedules or snapshot policies, retention shorter than required. Triggers - "what is not backed up", "coverage report", "unprotected", "clients without backup", "audit our backup coverage"
---
# Backup coverage

Read-only. Compare lists in python, never by eye (rule 3); save them under `~/storage-reports/<date>-coverage/`.

1. **Commvault, per CommCell**: `get_client_list`, `get_subclient_list` per client (or the client groups), `get_sla_status`,
   `get_plan_list` / `get_plan_properties`, `get_schedules_list`. Findings: clients with no subclient, subclients with no
   plan / storage policy or no schedule, last good backup older than the RPO, plans with no aux copy, retention below
   environment.md, deconfigured / disabled clients still holding data.
2. **Veeam**: to be run by you: `Get-VBRJob | ForEach-Object { $j=$_; $j.GetObjectsInJob() | Select-Object @{n='Job';e={$j.Name}}, Name }`
   plus the vCenter VM list the user exports; VMs in neither Commvault nor Veeam are unprotected (VMs in both: double cost).
3. **OADP**: every HostedCluster on each MCE (`oc get hostedclusters -A`) has a Schedule (`oc get schedules.velero.io -n
   openshift-adp -o yaml` → includedNamespaces), the schedule is not paused, TTL 48h.
4. **Storage**: volumes with snapshot policy `none` (ontap), storage groups without SnapVX policy (powermax), PowerFlex
   volumes without a snapshot policy, and DR copies missing (no SnapMirror / SRDF / RCG) where environment.md requires one.
5. Inputs from other systems (vCenter inventory, database lists): ask the user for an export when no MCP has it, and say
   the result is only as complete as that list.

## Output
Answer first (how many unprotected, the worst), then | System | Object | Protected by | Last good backup | Gap |,
findings by severity, the fix per gap as steps for the user, and what was not compared.
