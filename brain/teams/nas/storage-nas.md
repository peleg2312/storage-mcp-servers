# Storage rules (NAS / file storage)
In a code project, also read `~/.claude/brain/environment.md` and `tool-map.md` before the first storage answer.

Live state exists only for NetApp ONTAP NAS: the **ontap** and **harvest** MCP servers (NetApp's official servers;
the hook keeps them read-only). There is **no MCP server for Dell PowerScale (OneFS) or VAST Data yet**: for them
you work from output he pastes (isi CLI, OneFS WebUI, VAST CLI / VMS) and from the docs library, and you say so.

## Storage rules
N1. **Every access zone / SVM / tenant and both protocols** (SMB and NFS) for "who can reach X" questions. A named
   share or export: find where it lives first, then check each layer. A check that looked at one cluster, one zone
   or one protocol must say so.
N2. **Sources disagree?** Show both values and which source said what (tool, pasted output with its time, doc).
N3. **Nothing is "unused" or "safe to delete"** (shares, exports, quotas, snapshots) without a check that
   lists what was NOT verified (clients still mounting, open sessions, snapshots, replication, Kubernetes PVs).
N4. Answer format: **answer first** (1-3 lines), then an evidence table, then findings by severity, then
   sources (MCP tool + object, or pasted command; doc title + url + version), then the next checks worth doing.
N5. **Versions** come from the environment file or a tool result; never assume the latest.
N6. Unasked during any investigation, every distinct error, event or failed state seen is explained from the docs
   before you conclude: one lookup per distinct code (group repeats).
N7. **Answer the question asked.** "What does X mean", "how do I X" = a docs answer: no live checks. Check live
   (ONTAP) or ask for pasted output (PowerScale, VAST) only when he asks you to check, or names an object and
   asks what is wrong. End a docs answer with one line offering the check.

## Sources: which MCP answers what
Exact tool names: see the tool map (run `/brain-setup` to refresh it).
| Question | Source |
|---|---|
| ONTAP NAS objects: SVMs, volumes, junction paths, export policies and rules, CIFS shares, qtrees, quotas, LIFs, SnapMirror, EMS | **ontap** MCP (live) |
| ONTAP NAS performance (latency, IOPS, throughput history) | **harvest** MCP |
| PowerScale: zones, shares, exports, quotas, SyncIQ, SmartConnect, auth mapping | **no MCP yet**: output he pastes from `isi` / WebUI, plus docs (`dell` / `powerscale`, `infohub-powerscale`, `kb`) |
| VAST: views, view policies, tenants, quotas, protection, VIP pools | **no MCP yet**: output he pastes from the VAST CLI / VMS (or read-only REST GET), plus docs (`vast` / `docs`, `kb`, `api-5-5`) |
| Docs, error meanings, procedures, KB, EMS events | **docs MCP** = **docs-search** or **docs-local** (or `brain/library/search.py`) |

## Identifier rules
- **SID vs UID/GID**: Windows identities are SIDs (`S-1-5-21-...`), Linux ones UID / GID numbers. A user reaches
  a file through the mapping (OneFS ID mapping and the on-disk identity / ONTAP name-mapping and UNIX user);
  show both identities and the mapping used.
- **Four paths**: SMB share name (UNC form `\\host\share`), NFS export path, ONTAP junction path, and the real
  filesystem path (OneFS `/ifs/...`, VAST view path). Never assume they match; resolve each.
- **NFS**: v3 exports the real path; v4 uses a pseudo-root (ONTAP junction namespace, OneFS zone root); a client
  may need a different mount path per version.
- **SmartConnect zone name vs pool vs IP**: the zone name is a DNS name clients use; the pool holds the IPs.
- **Equivalents**: OneFS access zone ~ ONTAP SVM ~ VAST tenant; VAST view + view policy ~ share + export rules.
- **Quota paths**: OneFS directory / user / group quotas on a path; ONTAP tree / user / group quotas on volumes
  and qtrees; VAST quotas on a path. Quote the path exactly as the tool shows it.
- Share, export and cluster names can repeat across clusters: always carry the cluster and zone / SVM.
- Kubernetes volumes (Trident NAS, CSI PowerScale) are found by the prefixes in the environment file.

## NAS path model (end to end)
Client -> DNS / SmartConnect zone (or ONTAP LIF) -> access zone / SVM / tenant -> protocol: SMB share (share
permissions + NTFS ACL) or NFS export (export rule / policy, root squash) -> path / view -> quota ->
snapshot / replication (SyncIQ, SnapMirror, VAST replication).
A healthy path: the name resolves to an IP in the right pool, the identity maps, share and file permissions both
allow, the quota has room, and replication is within its RPO. Check in that order and stop at the first deny.

## Agents
Give each storage agent its layer and identifiers and run them in parallel: **nas-analyst** (PowerScale / VAST
from pasted output and docs, ONTAP NAS live), **ontap-analyst** (deep ONTAP), **docs-researcher** (docs only).
Where is X in the files / repo: Explore (haiku).
Agents end with a "Learned:" line; file those facts per rule 6 (notes.md / notes/<topic>.md; NAS topics:
powerscale, vast, ontap-nas, smb, nfs, general). Agents answer in about 40 lines and write longer tables under ~/storage-reports/<date>-<topic>/.

## My environment and tool map
@~/.claude/brain/environment.md
@~/.claude/brain/tool-map.md
