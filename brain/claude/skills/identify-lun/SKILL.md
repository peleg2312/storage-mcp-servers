---
name: identify-lun
description: Resolve any LUN identifier (naa., eui., PowerMax device ID, ONTAP serial or LUN path, datastore name, RDM, VM name) into the full picture - array, device, size, storage group / igroup, hosts, datastore or RDM, VMs, paths. Use when asked "what is naa.xxx", "where does this datastore live", "which LUN is this VM on".
---
# Identify a LUN

## 1. Classify the input
- `naa.60000970…` → PowerMax: decode serial + device ID (CLAUDE.md identifier rules)
- `naa.600a0980…` → ONTAP: decode the LUN serial
- `eui.…` → PowerFlex or NVMe namespace
- 5 hex chars (e.g. `003A5`) → PowerMax device ID: ask/find which array if several
- datastore / VM / RDM name → start on the VMware side (step 2)

## 2. VMware side (kuparashit; Aria for metrics)
- NAA → datastore or RDM, vCenter, ESX hosts that see it, VMs using it (and RDM mode if RDM)
- datastore/VM name → its NAA(s) (a datastore may span several extents: list all)

## 3. Array side
- **PowerMax**: `find_volume_by_wwn` (or `get_volume` with array + device) → size, emulation, storage
  group(s), masking view(s) → host/initiator group (initiator WWPNs) + port group (FA ports),
  replication (SRDF / SnapVX) state.
- **ONTAP**: LUN by serial → SVM, path, size, space reservation, igroup maps (LUN ID), igroup initiators
  (WWPNs), OS type, FC LIFs of the SVM.
- **PowerFlex**: no live MCP: report what VMware shows and say the array side was not checked (EUI ↔
  volume ID format: docs MCP `dell/powerflex`, "device identifier eui").

## 4. Consistency checks (report each as OK / finding)
- every ESX host that sees the LUN is in the array's host group / igroup and vice versa
  (extra initiators on the array = stale or non-VMware hosts; name them)
- same LUN ID to all hosts of a cluster (needed for RDMs / some setups)
- the device is in at most one masking view / igroup set you'd expect
- replication role (R1/R2, Metro, SnapMirror active sync) is mentioned

## Output
A card: identifier(s) · array + device/serial · size · SG / igroup · masking / mapping · hosts ·
datastore or RDM + VMs (with vCenter) · replication · findings · sources.
