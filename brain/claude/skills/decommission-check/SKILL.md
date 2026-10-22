---
name: decommission-check
description: Prove whether a specific LUN, datastore or RDM is safe to remove, with a pass/fail checklist across VMware, arrays, replication, OpenShift and fabrics, and the correct removal order for him to execute. Use before any unmap, delete, reclaim or datastore removal.
when_to_use: Trigger phrases - "is naa.xxx safe to remove", "can I delete datastore X", "before I unmap this LUN", "prove nothing uses this RDM", "decommission checklist"
---
# Decommission check

Input: one or more NAAs / devices / datastores. Run `identify-lun` first for each.

## Checklist (every line gets PASS / FAIL / NOT CHECKED with evidence)
1. Not a datastore extent and not an RDM in **any** vCenter (kuparashit; list vCenters covered)
2. No VM files on the datastore (if it is a datastore): VMs, templates, ISOs, logs (Aria / kuparashit)
3. No I/O for ≥ 30 days on the array (PowerMax perf on device/SG, Harvest for ONTAP LUN)
4. Not mapped to non-ESX hosts; not a Trident / CSM (OpenShift) volume
5. No replication: SRDF / Metro / SnapVX (PowerMax), SnapMirror / active sync (ONTAP); no snapshots
   or clones depending on it
6. Not an ESXi boot LUN, not a vVols PE, not a gatekeeper
7. No recent changes or open work on it (PowerMax `what_changed` / audit log; ONTAP events)
8. The owner/team named in the environment file agrees (ask the user)

Verdict: **SAFE CANDIDATE** only if 1-7 PASS. Any FAIL → NOT SAFE. Any NOT CHECKED → UNKNOWN, with what
is missing.

## Removal order (for him to execute; you never execute)
VMware side first (unmount datastore on all hosts → detach the device on every host that sees it),
then the array side (remove from masking view / unmap from igroup), then rescan HBAs on the hosts, then
delete/reclaim on the array after an agreed waiting period. Removing the array mapping before detaching
on ESXi can cause APD conditions: search the docs MCP for "APD PDL detach" / "unmount datastore" in
`vmware/kb` (detach a LUN device, unmount datastores), `netapp/kb-san` (APD after LUN unmap),
`netapp/ontap-sanhost` and `kb/kb`, and cite them.
Give exact commands with the real names, plus pre-checks and post-checks (path count, no dead paths).
