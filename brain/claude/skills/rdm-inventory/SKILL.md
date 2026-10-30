---
name: rdm-inventory
description: Inventory and check all RDMs - mode, NAA, array device, size, sharing across VMs, consistent LUN IDs on all hosts, orphan pointers. Triggers - "list all RDMs", "which VMs share a LUN", "WSFC cluster disks", "orphan RDM pointers"
context: fork
agent: vmware-mapper
background: false
---
Forked: the user cannot answer mid-way; finish with a complete answer (storage.md S4).

# RDM inventory

1. kuparashit: every RDM (`query` on vms where `naas != not found`, fields name / hostname / naas / vc) and
   `luns(issues_only=True)` for `rdm_no_hosts` (stale RDM), `conflict` and RDMs not visible on the VM's
   host. Disk and compatibility mode are not in kuparashit: ask him or mark NOT CHECKED.
2. Resolve each NAA on the array (`identify-lun` steps, in bulk via files + python).
3. Checks:
   - the same NAA on several VMs = shared disk (cluster): all those VMs' hosts must see the LUN
   - LUN mapped to every host in the VMs' cluster (else vMotion / failover breaks): compare the cluster
     host list with the array host group / igroup
   - the same LUN ID on all hosts (if your standard requires it)
   - NAA not found on any array (orphan pointer, LUN removed or other array)
   - RDM LUN in a replication relationship (note role)
   - physical-mode RDMs shared in Windows clusters: ESXi hosts should mark those devices as perennially
     reserved (avoids slow boot / rescans) - report if this data is available, else list as "to verify"
4. Output a CSV and a summary: count per array / mode / cluster, then findings by severity.
