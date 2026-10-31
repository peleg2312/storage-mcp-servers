# My environment
<!-- Fill this in (or run /brain-setup and let Claude draft it from the MCP servers, then correct it).
     Claude reads this file every session. No passwords or tokens here. -->

## Clusters
| Name | Type (PowerScale / VAST / ONTAP) | Version | Site | Role / notes |
|---|---|---|---|---|
| | PowerScale | | | |
| | VAST | | | |
| | ONTAP | | | |

## Versions (they select the matching docs)
- OneFS per cluster (e.g. 9.10 -> docs `dell` / `powerscale`):
- VAST per cluster (-> `vast` / `docs`, REST `api-5-5`):
- ONTAP per cluster (e.g. 9.15.1 -> `ontap-ems-9151`, `netapp` / `ontap`):
- Trident / CSI PowerScale versions:

## Access zones / SVMs / tenants
| Cluster | Zone / SVM / tenant | SmartConnect zone or LIFs | Protocols | Notes |
|---|---|---|---|---|
| | | | | |

## AD domains and name mapping
| Domain | Clusters joined | Mapping rule | Notes |
|---|---|---|---|
| | | | |

## Replication
| Source | Target | Type (SyncIQ / SnapMirror / VAST) | Schedule / RPO |
|---|---|---|---|
| | | | |

## Naming conventions
- Shares:
- Exports / export policies:
- Quotas:
- Paths (/ifs/..., junction paths, VAST view paths):
- Kubernetes CSI prefixes (Trident storagePrefix, CSI PowerScale isiPath / volume prefix):

## My thresholds
- Quota warn __ %, critical __ %
- Cluster used: warn __ %
- SMB / NFS latency: warn __ ms
- SyncIQ / SnapMirror lag: warn __

## What is mine / not mine
- Mine: clusters, access zones / SVMs / tenants, shares, exports, quotas, replication.
- Not mine (read, report, hand over): AD / DNS, client hosts, Kubernetes.
- Hand-over teams / contacts:
