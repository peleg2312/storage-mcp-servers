---
name: explain-error
description: Explain an error, alert, event or log line (PowerMax, ONTAP EMS, PowerFlex, MDS, UCS, ESXi, Trident, CSM) and give its fix, from the docs and bug trackers; the live system is checked only when he asks. Triggers - "what does this error mean", "explain EMS ...", "what is SIO02...", a pasted alert or log line
---
# Explain an error

1. Extract the exact identifiers: event / EMS name (e.g. `callhome.*`, `scsiblade.*`), alert ID, error
   code, CSI error string, SCSI sense codes, log message text.
2. Docs MCP (docs-search or docs-local): an EMS name, SYMAPI / SIO code, CONTAP / DSA / KB number: `explain_code`
   first (severity, corrective action, KB sections in one call). Otherwise, or when not documented, the exact name / quoted string, filtered by vendor/product
   when known (names in `~/.claude/brain/library/MANIFEST.md`):
   - ONTAP EMS: product `ontap-ems-<version>` matching the cluster version (9.15.1 → `ontap-ems-9151`,
     `ontap-ems-9111` … `ontap-ems-9181`; `ontap-ems` when unknown); the symptom: `kb-ontap`
     (NetApp KB incl. CONTAP-* bugs; "Partial article" = solution needs a support login).
   - Trident: `trident-issues`, `trident-changelog`, `trident-<release>` of the installed version.
   - CSM / CSI: `dell/kb`, `dell/csm` (the url version matching the installed CSM), `csi-powermax`,
     `csi-powerflex`, `csi-powerscale`, `csm-replication`, `csm-operator` and their fixes: the `*-prs` products (see docs-lookup).
     Not explained there: the same quoted string over the driver / client / sidecar **source code**
     (`csi-*`, `goscaleio`, `gopowermax`, `gobrick`, vendor `kubernetes`) shows the function that
     raises it and the condition behind it (code = current main, not the installed release; say so).
   - PowerScale / OneFS: `dell/kb`, `infohub-powerscale`, `csi-powerscale`.
   - PowerMax: `dell/powermax` (Events and Alerts guide, product / SRDF / SnapVX guides), `dell/kb`.
     PowerFlex: `dell/powerflex` (alerts-and-events reference, release notes per version), `dell/kb`.
   - ESXi: `vmware/kb`, `kb-ontap`. Harvest: `harvest`, `harvest-issues`. Pointers: `kb/kb`.
   - MDS / UCS: not in the library; explain from general knowledge and say so.
   Read the best hit fully (read_chunk) before answering; the next ones too when it does not fully explain the
   error, or another version or a KB may differ.
3. Live check: storage.md S7.
4. Answer: meaning · likely causes · fix (commands for him, placeholders + the read-only command that finds each value) · whether
   a known bug / fixed version applies · sources with versions. If the docs don't cover it, say so and
   suggest saving the relevant vendor KB into the local library once found.
