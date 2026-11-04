---
name: docs-lookup
description: How to answer from the Flashback backup library - Commvault, Veeam, OADP / Velero / HyperShift, NetApp, PowerMax and PowerFlex data protection docs - product names per version, search method, reading, citing. Use for any question about how a backup product works. Triggers - "what do the docs say", "how do I restore X in Commvault", "what does error code mean", "OADP hypershift backup", "Veeam PostgreSQL", "SnapMirror policy"
---
# Library lookup (the Flashback library)

Tools: docs MCP (`docs-local` on this VM, `docs-search` from a laptop; same tools) or, without MCP,
`python3 ~/.claude/brain/library/search.py --db ~/.claude/brain/libraries/flashback/docs.db search "..." [--vendor v]
[--product p] [--limit n]` (also `read-chunk <id>`, `read-doc --path <p>`, `sources`). What is inside: `~/.claude/brain/libraries/flashback/MANIFEST.md`.
This team's library is its own: the general SAN / NAS library is not searched. No internet; never cite anything else.

## 1. Pick vendor and product (product is a substring filter: give the full name when the version matters)
| Question about | vendor / product |
|---|---|
| Commvault (Command Center docs) | `commvault` / `2024e` (= 11.36), `11.40`, `11.42`, `11.44`: the CommCell's version from environment.md; 11.38 is not in the library (use 11.36 or 11.40 and say so) |
| Commvault REST API, PowerShell module, qcommands | `commvault` / `<version>` ("REST API", "Commvault PowerShell Module", "Command Line") |
| The Commvault MCP server's tools | `commvault` / `commvault-mcp-server` |
| Veeam B&R 13 (jobs, PostgreSQL, VMware, proxies, NFS / NetApp repositories, restores) | `veeam` / `vbr-userguide`; PowerShell `vbr-powershell`; event IDs `vbr-events`; `vbr-wn`, `vbr-permissions`, `vbr-qsg` |
| Veeam ONE, Veeam Agent for Linux | `veeam` / `one-userguide`, `agentforlinux-userguide` |
| OADP (DPA, BSL, Schedule, Backup, Restore, data mover, Kopia, CSI, troubleshooting, release notes) | `redhat` / `oadp-1.4` (OCP 4.18 guide), `oadp-1.5` (4.20), `oadp-1.6` (4.22): the MCE's OADP version |
| Hosted clusters (HyperShift / MCE) backup, restore, DR | `redhat` / `hosted-control-planes-4.18`, `-4.20`, `-4.22`; `openshift` / `hypershift-dr`, `hypershift-oadp-plugin` (README + example DPA / Backup / Restore YAML), `hypershift-oadp-plugin-1.5` |
| OADP operator internals, Velero | `openshift` / `oadp-operator-1.4|1.5|1.6`; `velero` / `velero-1.14` (OADP 1.4), `velero-1.16` (1.5), `velero-1.17` (1.6) |
| CSI snapshots (VolumeSnapshot, VolumeSnapshotContent, classes) | `kubernetes` / `external-snapshotter`; `openshift` / `storage`; PowerFlex CSI `dell` / `csi-powerflex`, `csm`; Trident `netapp` / `trident`, `kb-trident` |
| NetApp snapshots, policies, SnapMirror, SVM DR, FlexClone, SnapRestore | `netapp` / `ontap` (data-protection, volumes), `kb-ontap`, `ontap-ems` (EMS events), `ontap-restapi` |
| PowerMax SnapVX, SRDF, TimeFinder | `dell` / `powermax`, `kb` |
| PowerFlex snapshots, snapshot policies, replication | `dell` / `powerflex`, `kb`, `csm-replication` |
| Team pointers (verified one-line answers) | `flashback` / `pointers` |

## 2. Search: exact first, then wider
1. An error message, error code or event: its most specific part **in quotes** (Commvault `[19:1131]` style codes
   and their text, Veeam event ID, Velero `phase` / message, EMS name); drop variable parts (client, job ID, time).
2. The key technical words without quotes, with vendor + product. 3. Drop the product filter, then the vendor.
4. Rephrase with the vendor's words: Commvault "subclient", "storage policy copy", "aux copy", "data aging",
   "IntelliSnap", "CommServe LiveSync", "DDB"; Veeam "restore point", "backup copy job", "application-aware processing";
   OADP "DataProtectionApplication", "snapshotMoveData", "DataUpload", "BackupRepository".
Use `queries=[2-3 phrasings]` in one call when the first search is partial; `read_top=2` for a direct question.

## 3. Read, cite, version
`read_chunk` the best hit (never answer from snippets); `read_document` for a procedure spanning sections. Cite title +
url + version. Another version's page is a hint ("documented for 11.40; your CommCell is 11.36"). Two versions disagree:
show both, prefer the installed one. Procedures (restores, failover) are quoted step by step from the page.

## Nothing found
Say what you searched, label general knowledge as such, and name the vendor document to add
(`paas-library add flashback <file> --to <vendor>/<product>` as root, or `add-docs` for your own brain).
