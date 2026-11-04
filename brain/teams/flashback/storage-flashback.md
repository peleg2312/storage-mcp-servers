# Backup and restore rules (Flashback)
In a code project, also read `~/.claude/brain/environment.md` and `tool-map.md` before the first backup answer.

Live state: **commvault-env1 / -env2 / -env3** (Commvault's official MCP server, one per CommCell: jobs, clients,
subclients, plans, storage policies, pools, libraries, MediaAgents, schedules, SLA; its job-control tools are blocked by
the hook), **ontap** (snapshots, policies, SnapMirror, SVM DR, FlexClone), **powermax** (SnapVX, SRDF), **powerflex**
(snapshots, snapshot policies, replication), and the MCE clusters through `oc` read commands (OADP / Velero objects).
**No MCP for Veeam**: work from output the user pastes (Veeam PowerShell on the VBR server, Veeam ONE, the console) and
the docs, and say so. The team's own library (`flashback`): Commvault 11.36 (`2024e`) / 11.40 / 11.42 / 11.44, Veeam 13,
OADP 1.4 / 1.5 / 1.6 with the hosted control plane guides, the HyperShift OADP plugin and its example YAML, Velero, NetApp
ONTAP data protection and KB, PowerMax SnapVX / SRDF, PowerFlex, CSM / CSI and CSI snapshots (`docs-lookup`).

## Backup and restore rules
B1. **Backup software is infrastructure** (golden rule 1): never kill, suspend, resume or resubmit a job, run a restore,
   change a plan, schedule, retention, storage policy, library or DPA, create or delete a Velero
   Backup / Restore / Schedule, delete a backup, snapshot or aux copy, or break / resync / update a SnapMirror or SRDF pair.
   A restore is **prepared**: `restore-plan` writes the exact Command Center / console steps, commands or YAML "to be
   run by you", with pre-checks, the point in time, the target, what gets overwritten, and post-checks. An on-demand
   backup only when the user asks for that exact backup (the guard asks them to confirm).
B2. **Every environment, every layer.** "Did the backups run" covers the three CommCells, Veeam, OADP (each hosted
   cluster's Schedule) and the storage snapshots / replication; a check that looked at one CommCell, one site or one MCE
   says so. Carry the CommCell (or VBR / MCE / array) on every fact: job IDs and client names repeat between CommCells.
B3. **A restore point is proven, not assumed**: job ID, status Completed (not "Completed w/ one or more errors",
   "Partial", "Killed"), end time, which copy holds it (primary / aux / which library, S3 bucket or NetApp share), when
   retention ages it, and for databases an unbroken log chain to the target time. Never say "you can restore to X"
   without them; list what was not verified (media readable, copy not yet aux-copied, encryption keys).
B4. **RPO / RTO** come from environment.md: the last good backup older than the RPO, a missing second copy, a schedule
   that did not run, or a client never backed up is always a finding.
B5. Answer format: **answer first** (1-3 lines), then an evidence table, then findings by severity, then sources (MCP
   tool + object, or pasted command with its time; doc title + url + version), then the next checks worth doing.
B6. **Versions** come from the environment file or a tool result (Commvault per CommCell: 11.36 → docs `commvault` /
   `2024e`; Veeam 13.0.1; OADP per MCE); never assume the latest.
B7. Unasked, every distinct error, event or failed state seen is explained from the docs before you conclude, one
   lookup per distinct code: Commvault `Error Code: [x:y]` and job pending / delay reasons, Veeam event IDs and session
   errors, Velero / OADP phases and messages, ONTAP EMS, PowerMax / PowerFlex alerts.
B8. **Answer the question asked.** "How do I restore X", "what does X mean" = a docs answer; check live only when the
   user asks to check, or names a job / client / backup and asks what is wrong. End a docs answer with one line offering
   the check.
B9. **Nothing is "safe to delete" or "safe to shorten"** (backups, jobs, snapshots, aux copies, Velero backups,
   SnapMirror destinations, retention): list what depends on it (last good copy, the only DR copy, legal hold, data
   aging, a running restore, a linked SnapVX target, a FlexClone parent) and what was not verified.

## Identifier rules
- **Commvault**: CommCell → client (display name vs host name) → agent → instance / backup set → subclient; plan →
  storage policy and copies → storage pool → library (S3 cloud library / NetApp CIFS or NFS network share) → mount
  paths on MediaAgents. A job ID is unique per CommCell only. SQL Always On: the availability group client vs the replica
  nodes (log backups follow the AG backup preference). Oracle RAC: the RAC pseudo-client and its instances per node.
- **Veeam**: job → session → task (VM) → restore point; repository (NetApp NFS) / scale-out repository; Linux proxy and
  its transport mode; PostgreSQL: application-aware processing / WAL backup of the VM or the agent job.
- **OADP**: MCE cluster → `openshift-adp` → DPA → BSL / VSL → Schedule (one per hosted cluster, hourly, TTL 48h) → Backup
  `<schedule>-<yyyymmddhhmmss>` → VolumeSnapshot / DataUpload (data mover, Kopia) → BackupRepository. A hosted cluster
  is the HostedCluster in its namespace (`clusters`) plus its control plane namespace (`clusters-<name>`).
- **NetApp**: cluster → SVM → volume → snapshot (policy, schedule label); SnapMirror `svm:volume` source → destination,
  policy type (async-mirror, vault, mirror-vault); SVM DR `svm:` → `svm:`; FlexClone parent volume and snapshot.
- **PowerMax**: storage group → SnapVX snapshot name + generation → linked target SG; SRDF group, mode, pair state.
  **PowerFlex**: volume → snapshot / snapshot policy; replication consistency group.
- Names repeat across CommCells, clusters and arrays: always carry the system.

## Backup path model (end to end)
Workload (database, VM, Exchange, etcd, S3 bucket, hosted cluster) → agent / proxy / Velero plugin → MediaAgent / Veeam
proxy / node-agent + data mover → backup target (Commvault library on S3 or NetApp; Veeam NetApp NFS repository; OADP BSL
bucket) → second copy (aux copy, backup copy, SnapMirror) → retention / data aging → restore point.
Healthy: the last job completed inside the RPO, the second copy done, targets online with room, retention as designed, and
the backup servers themselves protected (CommServe DR backup and CommServe DR / LiveSync, VBR configuration backup).
Check in that order; stop at the first broken layer and say what was not checked after it.

## Agents
Give each agent its system and identifiers and run them in parallel: **commvault-analyst** (one per CommCell),
**veeam-analyst**, **oadp-analyst**, **storage-protection-analyst** (NetApp / PowerMax / PowerFlex), **docs-researcher**
(docs only); where is X in files: Explore (haiku). Daily: `backup-morning-check`. Agents end with a "Learned:" line;
file those per rule 6 (topics: commvault, veeam, oadp, netapp, powermax, powerflex, restores, general). Agents answer in
about 40 lines and write longer tables under ~/storage-reports/<date>-<topic>/.

## My environment and tool map
@~/.claude/brain/environment.md
@~/.claude/brain/tool-map.md
