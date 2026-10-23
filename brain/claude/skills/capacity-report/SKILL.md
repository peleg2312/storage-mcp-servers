---
name: capacity-report
description: Capacity report across datastores and arrays - datastore free space and overprovisioning, PowerMax SRP used / subscribed, ONTAP aggregates and volumes, data reduction, growth trend and days-to-full, reclaim candidates. Use for capacity reviews, "where is space running out", monthly reports.
when_to_use: Trigger phrases - "/capacity-report", "where is space running out", "monthly capacity report", "days to full", "SRP subscribed percent", "datastore overcommit"
disable-model-invocation: true
---
# Capacity report

Thresholds come from the environment file; ask once if they are empty.

1. **Datastores** (Aria; kuparashit has size and `trend` only): capacity, free %, provisioned (thin overcommit %), growth over
   30/90 days, Aria time-to-full forecast. Flag below thresholds and overcommit > 150 %.
2. **PowerMax** (`capacity_report`, `list_srps`): SRP usable / used / subscribed %, data reduction ratio,
   snapshot usage; top storage groups by allocated capacity.
3. **ONTAP**: aggregates used %, volumes used % incl. snapshot reserve / overflow, LUN space settings
   (thin vs reserved), efficiency savings; volumes with autosize limits close.
4. **Growth**: use Aria / Harvest history; days-to-full = free / avg daily growth (state the method).
5. **Reclaim**: link to `unused-luns` candidates and empty datastores (do not recompute here unless asked).

Output: one-line status per array and per cluster, then tables sorted by risk (days-to-full asc), and a
short "actions" list. Save CSVs under ~/storage-reports.
