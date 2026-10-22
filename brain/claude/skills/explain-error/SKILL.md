---
name: explain-error
description: Explain an error, alert, event or log line from PowerMax, ONTAP (EMS), PowerFlex, MDS, UCS, ESXi, Trident or CSM using the offline docs and bug trackers, then check the live system for it. Use when the user pastes an error, alert or event name.
---
# Explain an error

1. Extract the exact identifiers: event / EMS name (e.g. `callhome.*`, `scsiblade.*`), alert ID, error
   code, CSI error string, SCSI sense codes, log message text.
2. Docs MCP (docs-search or docs-local): first the exact name / quoted string, filtered by vendor/product
   when known (names in `~/.claude/brain/library/MANIFEST.md`):
   - ONTAP EMS: product `ontap-ems-<version>` matching the cluster version (9.15.1 → `ontap-ems-9151`,
     `ontap-ems-9111` … `ontap-ems-9181`; `ontap-ems` when unknown); the symptom: `kb-ontap`, `kb-san`
     (NetApp KB incl. CONTAP-* bugs; "Partial article" = solution needs a support login).
   - Trident: `trident-issues`, `trident-changelog`, `trident-<release>` of the installed version.
   - CSM / CSI: `dell/kb`, `dell/csm` (the url version matching the installed CSM), `csi-powermax`,
     `csi-powerflex`, `csm-replication`, `csm-operator` (no CSM issue tracker in the library).
   - PowerMax: `dell/powermax` (Events and Alerts guide, product / SRDF / SnapVX guides), `dell/kb`.
     PowerFlex: `dell/powerflex` (alerts-and-events reference, release notes per version), `dell/kb`.
   - ESXi: `vmware/kb`, `kb-san`. Harvest: `harvest`, `harvest-issues`. Pointers: `kb/kb`.
   - MDS / UCS: not in the library; explain from general knowledge and say so.
   Read the best 2-3 hits fully (read_chunk) before answering.
3. Live check with the matching MCP: is it still happening, since when, on which objects, how often.
4. Answer: meaning · likely causes in this environment · how to verify · fix (commands for him) · whether
   a known bug / fixed version applies · sources with versions. If the docs don't cover it, say so and
   suggest saving the relevant vendor KB into the local library once found.
