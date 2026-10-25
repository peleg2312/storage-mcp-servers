---
name: zoning-audit
description: Audit MDS zoning against logins and array masking - stale members, unzoned initiators, zoned but not masked, single-fabric hosts, alias mismatches, unactivated changes.
when_to_use: Trigger phrases - "audit the zoning", "stale zone members", "which initiators are not zoned"
context: fork
agent: fabric-investigator
background: false
---
You run in a forked context: gather everything, then return a complete answer (answer first, evidence table, findings, sources, next checks); the user cannot answer questions mid-way.

# Zoning audit

Scope: all VSANs on both fabrics unless the user narrows it. Save raw outputs to files, compare in python.

## Collect per fabric
- active zoneset per VSAN, full zone config (to spot unactivated differences), device-alias database
- FLOGI + FCNS (who is logged in now)
- array initiators: PowerMax hosts / initiator groups (WWPNs), ONTAP igroups (WWPNs)
- UCS vHBA WWPNs (ucsc) and ESX host WWPNs (kuparashit esx `pwwns`) for naming

## Findings
| Check | Severity |
|---|---|
| zone member WWPN not logged in anywhere (stale) | low (cleanup) unless it belongs to a live host |
| initiator logged in but in no zone | medium |
| zoned to array ports but not in any masking view / igroup | low-medium (leftover or pending) |
| in a masking view / igroup but not zoned on one fabric | **high** (no redundancy) |
| host zoned on fabric A only (or B only) | **high** |
| zone with more than one initiator | low (best practice: single-initiator zones) |
| device-alias name that doesn't match the host / vHBA it points to | medium |
| zone config differs from active zoneset (pending changes) | medium: someone forgot to activate |
| zones / aliases referencing WWPNs from retired UCS pools | low |

## Output
Summary counts per fabric/VSAN, then the table of findings (fabric, VSAN, zone/alias, WWPN, owner,
finding, suggested fix). Fix suggestions are commands for him to run, grouped per switch, with
`zone commit` / `zoneset activate` notes if enhanced zoning is used. Save the CSV.
