# My environment
<!-- Pre-filled from what the team described; fill the blanks (or /brain-setup drafts it). Read every session. No secrets. -->

## Commvault (three environments, each its own CommCell)
| Environment | MCP server | CommServe | CommServe DR | Command Center url | Version (docs product) | Sites |
|---|---|---|---|---|---|---|
| env1 | commvault-env1 | | | | 11.__ (11.36 → `2024e`, 11.40 → `11.40`) | |
| env2 | commvault-env2 | | | | | |
| env3 | commvault-env3 | | | | | |
- Every site has 4-5 MediaAgents, most of them **physical Windows** servers. List per site:
| Environment | Site | MediaAgents | OS | Libraries they write to |
|---|---|---|---|---|
| | | | Windows | |
- Libraries: most are **S3 cloud storage libraries**; a few are **NetApp CIFS / NFS** network-share disk libraries.
| Environment | Library | Type (S3 / NetApp CIFS / NetApp NFS) | Bucket or share path | Deduplication (storage pool / DDB MA) | Copy (primary / aux) |
|---|---|---|---|---|---|
| | | S3 | | | |
| | | NetApp CIFS | `\\svm\share` | | |
- Workloads protected: PostgreSQL, SQL Server (standalone + Always On availability groups), Oracle RAC, VMware VMs,
  Exchange (IntelliSnap snapshot backups only), etcd (on VMs), S3 object storage.
- Plans / storage policies and their retention, aux copies (which site / library gets the second copy):

## Veeam (one environment)
- VBR server: ______ (Veeam Backup & Replication **13.0.1**, docs `veeam` / `vbr-userguide`); Veeam ONE: ______
- Proxies: 3-4 **Linux virtual** VMware proxies per site: names, transport mode (hot-add / NBD / direct NFS):
- Repositories: all backups on **NetApp NFS** backup repositories (SVM, volume, export, SOBR?):
- vCenters protected: ______; PostgreSQL protected by: (VM job with application-aware processing / Veeam Agent for Linux)
- Configuration backup of the VBR: target, schedule:

## OADP (one environment)
- The OADP operator is installed **only on the MCE (HyperShift) management clusters**; it backs up the hosted clusters
  ("click clusters") under each MCE with the **hypershift-oadp-plugin**.
| MCE cluster | OCP version | OADP version (1.4.3 / 1.5.4 / 1.6 → docs `oadp-1.4` / `oadp-1.5` / `oadp-1.6`) | MCE version | BSL bucket / endpoint |
|---|---|---|---|---|
| | | | | |
- One **Schedule per hosted cluster**, **every hour**, **TTL 48h** (≈ 48 backups kept per hosted cluster).
- Volumes: **CSI snapshots of PowerFlex** (csi-vxflexos, VolumeSnapshotClass ______) moved off the array by the **data
  mover** (`snapshotMoveData: true`, Kopia, node-agent). Trident (ONTAP) CSI snapshots: where used:
- Hosted cluster platform (Agent / KubeVirt / none): ______; HostedCluster namespace: `clusters`; InfraEnv namespace:

## Storage-side protection
- NetApp ONTAP clusters and versions (9.15.1 → EMS `ontap-ems-9151`): snapshot policies in use, SnapMirror / SVM DR pairs:
- PowerMax arrays: SnapVX policies, SRDF groups and modes:
- PowerFlex systems and versions: snapshot policies, replication consistency groups:

## Recovery objectives (my thresholds)
| Workload / tier | RPO | RTO | Copies required | Retention |
|---|---|---|---|---|
| Databases (log backups) | | | | |
| VMs | 24 h | | | |
| Hosted clusters (OADP) | 1 h | | | 48 h |
- A job "Completed w/ one or more errors" counts as: (failed / warning)
- Library / repository / bucket used: warn __ %, critical __ %

## Naming conventions
- Commvault clients / subclients / plans:
- Veeam jobs:
- OADP Schedules (per hosted cluster):
- Snapshot / SnapMirror policy names:

## What is mine / not mine
- Mine: Commvault, Veeam, OADP, backup storage targets, snapshot and replication policies, restores and restore tests.
- Not mine (read, report, hand over): databases (DBAs), vCenter / ESXi, the OpenShift clusters, array provisioning
  (SAN / NAS teams), the S3 service.
- Hand-over teams / contacts:
