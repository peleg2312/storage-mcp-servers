---
name: change-review
description: What changed recently across the storage stack - PowerMax audit log, ONTAP events/audit, MDS accounting log and zoning, UCS audit log, Aria alerts, OneFS / VAST audit from pasted output - on one timeline, correlated with a problem time. Use for "what changed", post-incident timelines, or "did someone touch X".
disable-model-invocation: true
---
# Change review

1. Window: from the user, or 24-72 h before the problem started.
2. Collect: PowerMax `get_audit_log` + `get_alerts`; ONTAP audit / EMS events (ontap MCP; explain unknown
   EMS names with the docs product `ontap-ems-<cluster version>`); MDS `show_accounting_log` and
   `get_log_events` (zoning commits, interface shut / no shut); UCS `get_audit_log` + `get_events`;
   Aria alerts for the involved objects. NAS team: PowerScale `isi_audit_viewer -t config` and VAST's VMS audit log from
   pasted output (no MCP); only the layers the team has.
3. Merge into one timeline (UTC and local time), filter to objects related to the problem (the LUN, SG,
   hosts, WWPNs, ports from `identify-lun` / `trace-path`).
4. Output: timeline table (time | layer | who | what | object | related?), then the changes most likely
   connected to the problem and why.
