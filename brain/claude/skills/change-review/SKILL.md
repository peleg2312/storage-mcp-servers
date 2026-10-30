---
name: change-review
description: What changed recently across the storage stack - PowerMax audit log, ONTAP events/audit, MDS accounting log and zoning, UCS audit log, Aria alerts - on one timeline, correlated with a problem time. Use for "what changed", post-incident timelines, or "did someone touch X".
when_to_use: Trigger phrases - "/change-review", "what changed since yesterday", "did someone touch storage group X", "post-incident timeline", "who changed the zoning", "changes around 14:00"
disable-model-invocation: true
---
# Change review

1. Window: from the user, or 24-72 h before the problem started.
2. Collect: PowerMax `get_audit_log` + `get_alerts`; ONTAP audit / EMS events (ontap MCP; explain unknown
   EMS names with the docs product `ontap-ems-<cluster version>`); MDS `show_accounting_log` and
   `get_log_events` (zoning commits, interface shut / no shut); UCS `get_audit_log` + `get_events`;
   Aria alerts for the involved objects.
3. Merge into one timeline (UTC and local time), filter to objects related to the problem (the LUN, SG,
   hosts, WWPNs, ports from `identify-lun` / `trace-path`).
4. Output: timeline table (time | layer | who | what | object | related?), then the changes most likely
   connected to the problem and why.
