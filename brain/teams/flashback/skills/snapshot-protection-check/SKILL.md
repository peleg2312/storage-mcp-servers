---
name: snapshot-protection-check
description: Storage-side protection check - NetApp ONTAP snapshots and snapshot policies, SnapMirror and SVM DR relationships (lag, health), FlexClones; PowerMax SnapVX snapshots and SRDF; PowerFlex snapshots, snapshot policies and replication - against the RPO, and how to restore from a snapshot. Triggers - "snapshot policy", "are the snapshots running", "SnapMirror lag", "SVM DR state", "FlexClone", "restore from snapshot", "SnapVX", "PowerFlex snapshot"
---
# Snapshot and replication protection check

Read-only: never create, delete or restore a snapshot, change a policy, or break / resync / update a relationship, pair
or RCG. A restore from a snapshot is prepared with `restore-plan`. Replication states in depth: `replication-check`.

## NetApp ONTAP (ontap MCP; the user's CLI where the MCP has no tool)
- Policies: snapshot policies and their schedules / counts / labels, which volumes use which (`none` = a finding where
  environment.md requires snapshots). CLI: `volume show -fields snapshot-policy`, `volume snapshot policy show`.
- Snapshots: newest and oldest per volume, the count vs the policy, snapshot reserve and space used, busy snapshots
  (owners: SnapMirror, FlexClone, SnapCenter) that cannot be deleted. CLI: `volume snapshot show -volume <v> -fields create-time,owners`.
- SnapMirror / SVM DR: state, status, healthy, unhealthy-reason, lag-time vs the RPO, policy and type (async-mirror,
  vault, mirror-vault), last transfer error; SVM DR: `snapmirror show -destination-path <svm>:`, identity-preserve.
- FlexClone: clones and their parent volume / snapshot (`volume clone show`), split state; a clone pins its parent snapshot.
- Restore paths (docs `netapp` / `ontap`): single file / LUN restore from a snapshot, SnapRestore of the volume (reverts
  everything after it: say so), a FlexClone of the snapshot for out-of-place checks, restore from the SnapMirror / vault
  destination.
## PowerMax (powermax MCP)
SnapVX snapshots per storage group (name, generation, time, expiry, secure), snapshot policies, linked targets; SRDF
groups, mode and pair states. Restore: SnapVX restore / link to a new SG (docs `dell` / `powermax`).
## PowerFlex (powerflex MCP)
Snapshots per volume, snapshot policies (schedule, retention levels), replication consistency groups (state, RPO,
current lag). CSI: VolumeSnapshotContents whose handle is a PowerFlex snapshot (OADP data mover).

## Output
| System | Object | Policy | Newest | Count vs policy | Replication / lag vs RPO | Finding |, findings by severity
with the documented meaning, and what was not checked.
