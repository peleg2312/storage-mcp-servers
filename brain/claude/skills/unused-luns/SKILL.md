---
name: unused-luns
description: Find LUNs that exist on the arrays (PowerMax, ONTAP) but are not used in vCenter - unmapped devices, mapped but unseen, seen but not a datastore/RDM, empty datastores - with exclusions for OpenShift (Trident/CSM), non-VMware hosts, gatekeepers and replicas. Use for cleanup, reclaim or "which LUNs are not used on VC".
---
# Unused LUNs

Work on files: `~/storage-reports/<date>-unused-luns/`. Compare in python, never by eye.

## 1. Collect (save each to CSV/JSON)
1. **Arrays**: every volume/LUN with: array, device ID or LUN path, wwn/NAA (build `naa.` + wwn for
   PowerMax; for ONTAP `naa.600a0980` + hex(serial)), size, SG / volume, masking view / igroup, host
   names + initiators, replication role, created date if available.
2. **VMware (kuparashit)**: every NAA seen by any ESX host in **every** vCenter, with: datastore or RDM,
   VMs, hosts. Note which vCenters kuparashit covers.
3. **Aria** (optional): datastores with zero VMs / zero I/O.

## 2. Classify each array LUN
| Class | Meaning |
|---|---|
| U1 unmapped | no masking view / igroup map at all |
| U2 mapped, not seen | mapped to ESX initiators, but no ESX host sees the NAA |
| U3 seen, unused | ESX sees it, but it is neither a datastore extent nor an RDM |
| U4 empty datastore | datastore exists but has no VMs / files of VMs |
| IN USE | datastore extent with VMs, or RDM |

## 3. Exclusions (keep them in the report, in their own column, never silently drop)
- **OpenShift**: Trident (`trident*` names, OpenShift worker igroups) and Dell CSM volumes (CSM prefix,
  OpenShift host groups) - in use by Kubernetes even though vCenter doesn't see them
- mapped to **non-ESX hosts** (Linux/Windows/AIX/backup host groups)
- PowerMax **gatekeepers** (very small devices, a few MB) and devices in SRDF R2 / Metro / SnapVX
  link-target roles; ONTAP SnapMirror destinations / active sync
- vVols protocol endpoints, ESXi boot LUNs
- LUNs created in the last 7 days (probably being provisioned)
- vCenters **not covered** by kuparashit: everything mapped to their hosts is "unknown", not unused

## 4. Optional evidence of idleness
For U2/U3 candidates: array performance for the device/SG (PowerMax) or LUN (Harvest) over 30 days:
IOPS ~0 strengthens the case.

## Output
1. Summary: count + capacity per class per array.
2. Table: array | device / LUN | NAA | size | class | mapped to | exclusion | idle evidence | confidence.
3. Save `unused-luns.csv`.
4. State clearly: **candidates, not proven unused**. Next step for any removal: `decommission-check`.
