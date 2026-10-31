---
name: export-policy-check
description: Audit NFS exports and ONTAP export policies for open-to-all rules, root access, wrong read-write, orphaned policies and rule order. Triggers - "audit the NFS exports", "export policy review", "who has root on the export", "open exports"
---
# Export policy check

Read-only: never create, edit or delete an export, policy or rule. Say which clusters, zones and SVMs were covered.

## Collect
- **ONTAP (live, ontap MCP)**: per SVM the export policies, their rules (index order, client match, protocol,
  ro / rw / superuser rule, anon user), and which volumes and qtrees use each policy.
- **PowerScale (no MCP: he pastes)**, to be run by you: `isi nfs exports list --zone <zone> --verbose`,
  `isi nfs exports view <id> --zone <zone>`, `isi nfs settings export view --zone <zone>`.
- **VAST (no MCP: he pastes)**: the NFS view policies (host lists, read-write / read-only, root squash) from the VAST CLI / VMS.
- Compare in python when there are more than ~20 rules.

## Findings
| Check | Severity |
|---|---|
| client 0.0.0.0/0, `*` or a whole large subnet with read-write | **high** |
| root access for all clients (ONTAP superuser `any`; OneFS no root squash / map-root off; VAST root squash off) | **high** |
| read-write where the data is meant to be read-only (name, tier or environment file says so) | medium-high |
| rule order: a broad rule listed before a specific one so the specific never matches | medium |
| NFSv3 allowed where only v4 with Kerberos is intended | medium |
| orphaned policy or export: no volume, qtree or path uses it, or the path no longer exists | low |
| duplicate or overlapping client entries | low |

## Docs
Meanings of options (superuser, anon, map-root, security flavors): `netapp` / `ontap`, `dell` / `powerscale`
(OneFS 9.10), `vast` / `docs`. Say the document version against the cluster version.

## Output
Summary counts per cluster / zone, then the findings table (cluster, zone / SVM, export or policy, rule,
finding, severity), sources with versions, fixes as commands for him to run (with rollback), and what was not
checked (clients actually mounting, other zones, clusters not pasted). Nothing is "orphaned" without N3's list.
