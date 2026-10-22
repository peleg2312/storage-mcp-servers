---
name: explain-error
description: Explain an error, alert, event or log line from PowerMax, ONTAP (EMS), PowerFlex, MDS, UCS, ESXi, Trident or CSM using the offline docs and bug trackers, then check the live system for it. Use when the user pastes an error, alert or event name.
---
# Explain an error

1. Extract the exact identifiers: event / EMS name (e.g. `callhome.*`, `scsiblade.*`), alert ID, error
   code, CSI error string, SCSI sense codes, log message text.
2. docs-search: first the exact name / quoted string, filtered by vendor/product when known
   (ONTAP EMS: product `ontap-ems-9171` etc. matching the cluster version; Trident / CSM: the `*-issues`
   trackers and changelogs; PowerMax / PowerFlex: release notes and guides; `kb` pointers).
   Read the best 2-3 hits fully (read_chunk) before answering.
3. Live check with the matching MCP: is it still happening, since when, on which objects, how often.
4. Answer: meaning · likely causes in this environment · how to verify · fix (commands for him) · whether
   a known bug / fixed version applies · sources with versions. If the docs don't cover it, say so and
   suggest saving the relevant vendor KB into the local library once found.
