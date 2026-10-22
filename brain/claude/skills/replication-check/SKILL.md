---
name: replication-check
description: Replication health across the arrays - PowerMax SRDF (pair states, invalid tracks, SRDF/Metro witness and bias, link status) from the powermax MCP / Unisphere / symrdf, ONTAP SnapMirror (state, status, lag, healthy, errors), PowerFlex replication consistency groups (RCG state, RPO compliance, journal) - with the library references that define each state. Use for "is replication healthy", "what does state X mean", DR readiness, SnapMirror lag, after a link or site event, or before a failover review.
---
# Replication check

Cover every array and both directions; say which were not checked. Read-only: never establish, split,
suspend, swap, failover, quiesce, break or resync anything.

## PowerMax SRDF
- Live: powermax MCP `srdf_health`, `get_replication` (per SG / RDF group), `get_alerts` (SRDF alerts),
  `what_changed`. If he is at the CLI: `symrdf -sid <sid> list` or `symrdf -sid <sid> -sg <sg> -rdfg <n>
  query [-rdf_metro]`, `symcfg -sid <sid> list -rdfg all` (RDF groups, link state), `symrdf -sid <sid>
  -rdfg <n> ping`, Unisphere › Data Protection › SRDF (groups, pairs, witness).
- Per RDF group: mode (Sync / Async / Metro), link status (Online / Offline), pairs by state, and for
  Metro the witness (Array / vWitness) and bias / preferred side.
- Per pair: R1 / R2 invalid tracks (zero and stable = good; non-zero and **falling** = sync in progress;
  non-zero and **stable** while the state says synchronizing = investigate), consistency enabled (Async),
  consistency exempt devices.
- States to explain only from the library: `Synchronized`, `SyncInProg`, `Consistent`, `Suspended`,
  `Split`, `Partitioned`, `TransIdle`, `Failed Over`, `R1 Updated`, `ActiveActive`, `ActiveBias`,
  `Invalid`, `Mixed`: search `dell/powermax` ("symrdf" + the state; Solutions Enabler 9.2 CLI Reference
  Guide, SRDF Introduction, SRDF/Cluster Enabler guide) and the Events and Alerts for PowerMax and VMAX
  9.2.1 User Guide for the alert text; `dell/kb` for SRDF / Metro / witness how-tos. Say the document
  version (9.2) when the array runs a newer PowerMaxOS.

## ONTAP SnapMirror (incl. SnapMirror active sync)
- Live: ontap MCP relationships; CLI for him: `snapmirror show -fields source-path,destination-path,
  type,policy-type,state,status,healthy,unhealthy-reason,lag-time,last-transfer-error,last-transfer-
  end-timestamp` on the destination cluster, `snapmirror show -expand` for SVM-DR, `snapmirror
  config-replication status show`, `cluster peer show`, `vserver peer show`.
- Checks: `state` Snapmirrored (Uninitialized / Broken-off are findings unless intended) · `status`
  Idle / Transferring (Quiesced, Queued for a long time = finding) · `healthy` true, else the
  `unhealthy-reason` · `lag-time` under the schedule / RPO (threshold from the environment file) · no
  `last-transfer-error` · peers available · for active sync: `InSync` / `OutOfSync`, mediator reachable.
- Meanings and procedures: `netapp/ontap` (data-protection and snapmirror sections), `kb-ontap`
  (symptoms, CONTAP-* bugs), EMS `snapmirror.*` / `smc.*` / `sms.*` events in `ontap-ems-<ver>` of the
  cluster; MetroCluster: `ontap-metrocluster`.

## PowerFlex replication
- No MCP: he runs (read-only) the RCG queries from the CLI Reference Guide of his version (search
  `dell/powerflex` "replication consistency group" / "RPO"), or reads PowerFlex Manager › Protection:
  per RCG the state (active / paused / failover / error), RPO and RPO compliance, journal capacity use,
  peer system connectivity, pairs. Dial-home codes from `dell/kb`.
- OpenShift volumes replicated through CSM: `oc get dellcsireplicationgroup -A` and the `dell/csm`
  `replication/` pages for the group states (`csm-health`).

## Output
Table: array / cluster | group (RDF group / SM relationship / RCG) | mode | state | status | lag or invalid
tracks | last change | OK or finding. Then findings by severity (with the documented meaning and its
source + version), what he should run next, and what was not checked.
