---
name: smartconnect-check
description: Check SmartConnect zones, pools, IP allocation, DNS delegation and failover on PowerScale, with ONTAP LIF and VAST VIP equivalents. Triggers - "check SmartConnect", "clients all land on one node", "zone does not resolve", "pool IP failover"
---
# SmartConnect check

Read-only: never change a pool, zone, subnet, DNS record or LIF. Cover every cluster and access zone; say which
were not checked.

## PowerScale (no MCP: he pastes)
To be run by you, placeholders in <>:
- `isi network subnets list` and `isi network subnets view <groupnet>.<subnet>` (SSIP, SmartConnect service IP)
- `isi network pools list` and `isi network pools view <groupnet>.<subnet>.<pool>` (SmartConnect zone name, aliases,
  allocation method static / dynamic, IP ranges, access zone, rebalance policy, connection policy)
- `isi network interfaces list` (members per pool, status per node)
- DNS side, run on a client: `dig <zone-name> +short` several times, `dig NS <delegated-subdomain>`,
  `nslookup <zone-name>`.
Docs: `dell` / `powerscale` (OneFS 9.10), `infohub-powerscale`, `kb`; cite title, url and version.

## ONTAP and VAST equivalents
- ONTAP (live, ontap MCP): LIFs per SVM (home node and port, current node, is-home, status, failover group and
  policy, DNS load balancing zone). Docs: `netapp` / `ontap`.
- VAST (no MCP: he pastes): VIP pools, their ranges, tenant binding and CNodes from the VAST CLI / VMS.

## Findings
| Check | Severity |
|---|---|
| zone name does not resolve, or DNS not delegated to the SSIP (NS record missing / points elsewhere) | **high** |
| pool has fewer IPs than needed for failover (dynamic: fewer than members; static: no spare) | **high** |
| pool members all on one node, or one interface down | medium-high |
| zone bound to the wrong access zone, or two zones overlap | medium |
| repeated lookups always return the same IP (no distribution) | medium |
| ONTAP LIF not at home, or failover group with a single port | medium |

## Output
Table: cluster | pool or LIF | zone name | IPs | members | allocation | access zone / SVM | finding. Then answer first,
findings by severity, sources with versions, fixes as commands for him to run, and what was not checked
(clients behind other resolvers, nodes not pasted).
