# My environment
<!-- Fill this in (or run /brain-setup and let Claude draft it from the MCP servers, then correct it).
     Claude reads this file every session. No passwords or tokens here. -->

## Arrays
| Name | Type | Serial / cluster | Site | Role / notes |
|---|---|---|---|---|
| | PowerMax | | | |
| | ONTAP | | | |
| | PowerFlex | | | |

## Fabrics
| Fabric | Switches | VSAN(s) | Notes |
|---|---|---|---|
| A | | | |
| B | | | |

## vCenters and clusters
| vCenter | Clusters | Notes |
|---|---|---|
| | | |

## UCS domains
| Domain | FI-A / FI-B | VSAN A / B | Notes |
|---|---|---|---|
| | | | |

## Naming conventions
- ESXi hosts:
- PowerMax storage groups / masking views / initiator groups / port groups:
- ONTAP SVMs / volumes / LUN paths / igroups:
- Device-aliases and zones:
- Datastores:
- RDMs:
- OpenShift: Trident backend storagePrefix (default `trident`), CSM volume name prefix, OpenShift
  worker host groups / igroups:
- Non-VMware hosts on the arrays (Linux, Windows, AIX, backup):

## My thresholds
- Datastore free space: warn __ %, critical __ %
- VM / datastore latency (Aria): warn __ ms, critical __ ms
- PowerMax storage group response time: warn __ ms
- ONTAP LUN / volume latency: warn __ ms
- SRP / aggregate used: warn __ %
- A LUN counts as idle when IOPS < __ for __ days

## What is mine / not mine
- Mine: arrays, MDS fabrics, datastores, RDMs, LUN provisioning, zoning.
- Not mine (read, report, hand over): UCS / FI config, ESXi host config, VMs.
- Hand-over teams / contacts:
