---
name: oadp-backup-check
description: Check OADP / Velero backups of the hosted clusters on the MCE clusters - Schedules (hourly, TTL 48h), the last Backups per hosted cluster, phase / errors / warnings, CSI snapshots of PowerFlex with the data mover (DataUploads, node-agent, Kopia BackupRepositories), BSL availability, the DPA and the hypershift plugin. Triggers - "are the hosted cluster backups ok", "OADP backup failed", "PartiallyFailed", "DataUpload stuck", "BSL unavailable", "velero"
---
# OADP backup check (MCE clusters)

Read-only: `oc get` / `describe` / `logs` only; never create, patch or delete a Backup, Restore, Schedule, DPA or BSL, and
never `oc login` or switch context unless the user asked for that MCE. Say which MCE (context) every result came from.
OADP version from `oc get csv -n openshift-adp`; docs `redhat` / `oadp-1.4|1.5|1.6` to match, plus `hypershift-oadp-plugin`.

1. **Configuration**: `oc get dpa -n openshift-adp -o yaml` (plugins include `openshift`, `aws`, `csi`, `kubevirt` when used, and
   the `hypershift-oadp-plugin` custom plugin; `nodeAgent.enable: true`, `uploaderType: kopia`; DPA status Reconciled),
   `oc get backupstoragelocations.velero.io -n openshift-adp` (phase Available, last validation time),
   `oc get volumesnapshotlocations.velero.io,volumesnapshotclasses -A` (the PowerFlex class carries the label
   `velero.io/csi-volumesnapshot-class: "true"`; its deletionPolicy and default-class annotation as the version's
   "Back up persistent volumes with CSI snapshots" page says).
2. **Schedules**: `oc get schedules.velero.io -n openshift-adp -o custom-columns=NAME:.metadata.name,CRON:.spec.schedule,TTL:.spec.template.ttl,PAUSED:.spec.paused,LAST:.status.lastBackup,PHASE:.status.phase`
   One per hosted cluster (`oc get hostedclusters -A`), cron hourly, TTL 48h, `snapshotMoveData: true`, included namespaces
   = the HostedCluster namespace and its `clusters-<name>` control plane namespace (compare with the plugin's example YAML).
3. **Backups**: per schedule the last ones (label `velero.io/schedule-name`): phase Completed vs PartiallyFailed / Failed /
   FailedValidation / InProgress for too long, errors / warnings counts, start-to-completion time, count kept (~48) and
   the oldest (TTL working). For a bad one: `oc describe backups.velero.io <name> -n openshift-adp` and
   `oc -n openshift-adp exec deployment/velero -c velero -- ./velero backup describe <name> --details` (read-only) and
   `... ./velero backup logs <name> | grep -iE 'error|warn' | head -50`.
4. **Data mover**: `oc get datauploads.velero.io -n openshift-adp -l velero.io/backup-name=<backup>` (phase Completed;
   Accepted / Prepared for long = node-agent or snapshot problem), `oc get pods -n openshift-adp -o wide | grep node-agent`
   (one per node, Running), `oc get backuprepositories.velero.io -n openshift-adp` (Ready), VolumeSnapshots in the
   control plane namespace and their VolumeSnapshotContents (readyToUse, the PowerFlex snapshot handle); CSI side:
   `k8s-volume-troubleshoot`, PowerFlex docs `dell` / `csi-powerflex`.
5. **Velero logs**: `oc logs -n openshift-adp deployment/velero --since=2h | grep -iE 'level=(error|warning)' | head -80`.
Every distinct message: search it in quotes (`redhat` / `oadp-<ver>` troubleshooting, `velero`, `openshift` / `oadp-operator-<ver>`).

## Output
| MCE | Hosted cluster | Schedule | Last Completed | Age vs RPO 1h | Kept | Last failed + reason | DataUploads |, findings by
severity with the documented meaning, fixes as steps for the user, and what was not checked.
