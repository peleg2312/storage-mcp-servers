# Flashback pointers: short verified answers with their source

Each line was read in the source named on it when this library was built; open that source for the full procedure.

## OADP and hosted clusters (HyperShift / MCE)
- A hosted cluster backup must include both the HostedCluster namespace (e.g. `clusters`) and its hosted control plane
  namespace (e.g. `clusters-<name>`) in `includedNamespaces`. Source: openshift/hypershift-dr,
  docs/content/how-to/disaster-recovery/backup-and-restore-oadp-1-5.md, "Control Plane backup".
- `snapshotMoveData: true` with `datamover: "velero"` makes the CSI VolumeSnapshots be uploaded to the backup storage
  (the data mover). Source: the same page.
- A backup is complete when `status.phase` is `Completed`; watch it with `oc get backup -n openshift-adp <name> -o
  jsonpath='{.status}'` and the Velero logs `oc logs -n openshift-adp -ldeploy=velero -f`. Source: the same page, "Watching".
- Before restoring a hosted cluster into the same management cluster, the HostedCluster, its NodePools and the PVCs are
  deleted so no pod / PVC runs in the control plane namespace; on the Agent (bare metal) platform the InfraEnv is not
  deleted. Source: the same page, "Restore".
- The Restore of a hosted cluster uses `restorePVs: true` and `existingResourcePolicy: update` and excludes nodes, events,
  backups, restores and resticrepositories. Source: the same page, "Restore"; openshift/hypershift-oadp-plugin,
  examples/<platform>/04-restore-*.yaml.
- KubeVirt hosted clusters: restoring into another management cluster is not supported, and nodes are reprovisioned.
  Source: the same page, "Restore", KubeVirt tab.
- Modifying the folder structure of the backup bucket breaks `backuprepositories.velero.io`; delete backups with the
  velero CLI, not in the bucket. Source: the same page, "How to handle backups properly".
- The VolumeSnapshotClass used by OADP CSI backups carries the label `velero.io/csi-volumesnapshot-class: "true"`.
  Source: redhat/oadp-1.5, "Back up persistent volumes with CSI snapshots".
- OADP versions per library product: 1.4.x in redhat/oadp-1.4 (OCP 4.18 guide), 1.5.x in oadp-1.5 (4.20), 1.6.x in
  oadp-1.6 (4.22). Source: the release-notes sections of each guide.

## Commvault
- Always On availability groups: full and differential backups always run on the primary replica; log backups run on
  the primary when it is the preferred backup replica, else on the secondary with the highest backup priority; the
  master process logs to SQLBackupmaster.log. Source: commvault/11.40, "Always On Availability Groups for SQL Server".
- Version names in the library: 11.36 is the folder `2024e`; 11.38 is not in the library (the documentation site does
  not allow it to be fetched): use 11.36 or 11.40 and say so. Source: documentation.commvault.com robots.txt.
- The Commvault MCP server has job-control tools (kill, suspend, resume, resubmit, run backup, enable / disable
  schedule): the brain's read-only guard blocks them, a manual backup is asked first. Source:
  commvault/commvault-mcp-server README, brain/claude/hooks/block-write-tools.py.
