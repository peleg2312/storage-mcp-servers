---
name: oadp-restore-hosted-cluster
description: Prepare the restore of an OpenShift hosted cluster ("click cluster") on its MCE from an OADP Schedule backup with the hypershift-oadp-plugin and the CSI data mover - choose the backup, pre-checks, the objects to remove first, the Restore YAML, watching, post-checks - for the user to run. Triggers - "restore the hosted cluster", "recover click cluster", "OADP restore", "hosted cluster lost", "restore from the hourly backup"
---
# Restore a hosted cluster with OADP (prepared here, run by the user)

Read-only here: never create the Restore or delete anything; the plan is "to be run by you" (B1). Same management
cluster only unless the docs of the installed OADP / MCE version and the platform say otherwise (KubeVirt: same MCE
only; Agent: node readoption only under the documented conditions). Read first: `redhat` / `hosted-control-planes-<ocp>`
("Restoring a hosted cluster by using OADP"), `openshift` / `hypershift-dr` (`backup-and-restore-oadp-1-5.md`, the
platform guide), `hypershift-oadp-plugin` (`examples/<platform>/04-restore-*.yaml`), `oadp-<ver>` restore pages.

1. **Which backup** (read-only):
   `oc get backups.velero.io -n openshift-adp -l velero.io/schedule-name=<schedule> --sort-by=.status.startTimestamp -o custom-columns=NAME:.metadata.name,PHASE:.status.phase,START:.status.startTimestamp,EXPIRES:.status.expiration,ERRORS:.status.errors`
   The newest **Completed** with 0 errors before the incident; its expiration must leave time for the restore (TTL 48h:
   a backup near expiry can be aged away mid-restore). `velero backup describe <name> --details` (read-only, through
   `oc -n openshift-adp exec deployment/velero -c velero -- ./velero ...`): namespaces, resources, the DataUploads
   (every PVC Completed).
2. **Pre-checks**: BSL Available; node-agent pods Running; the HostedCluster / NodePool / control plane namespace state
   now (`oc get hostedcluster,nodepool -n <ns>`, `oc get pods,pvc -n <ns>-<name>`); for the Agent platform the InfraEnv
   namespace and the Assisted Installer database stay untouched; record the current state (`oc get ... -o yaml >` files).
3. **Remove before restoring** (same MCE, as the docs say; to be run by you, after the owner agreed): the HostedCluster,
   its NodePools, and the PVCs left in the control plane namespace, so no pod / PVC runs there. Never the InfraEnv
   (Agent platform).
4. **The Restore** (to be run by you: `oc create -f restore.yaml`), from the plugin's example, values filled in:
```yaml
apiVersion: velero.io/v1
kind: Restore
metadata:
  name: <hosted-cluster>-restore-<yyyymmddhhmm>
  namespace: openshift-adp
spec:
  backupName: <backup chosen in step 1>
  restorePVs: true
  existingResourcePolicy: update
  excludedResources:
  - nodes
  - events
  - events.events.k8s.io
  - backups.velero.io
  - restores.velero.io
  - resticrepositories.velero.io
```
   Compare every field with the example and the guide of the installed versions (some examples add
   `includedNamespaces`, `cleanupBeforeRestore`, `preserveNodePorts`); say which document each field came from.
5. **Watch** (read-only): `oc get restores.velero.io -n openshift-adp <name> -o jsonpath='{.status}'`,
   `oc get datadownloads.velero.io -n openshift-adp`, `oc logs -n openshift-adp deployment/velero -f`,
   `velero restore describe <name> --details`.
6. **Post-checks**: Restore phase Completed (PartiallyFailed: read every error before going on), HostedCluster
   Available and its version, NodePools ready (nodes readopted or reprovisioned, per platform), the hosted cluster API
   answers, PVCs Bound, the Schedule still active and its next backup Completed.
7. **Rollback / if it fails**: what the saved YAML of step 2 allows, and the troubleshooting pages for the phase seen.
Save the plan to `~/storage-reports/<date>-restore-<hosted-cluster>/runbook.md`.
