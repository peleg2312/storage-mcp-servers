---
name: code-version-check
description: Compare the running versions of the stack (PowerMaxOS, Unisphere, Solutions Enabler, ONTAP, Trident, CSM / CSI drivers, PowerFlex, Harvest, NX-OS, UCS, ESXi) - from the environment file and live tools - with the release notes, changelogs, security advisories (DSA-*) and recommended-release guidance in the library, and produce a table component | running | recommended or latest in library | security advisories | notes. Use for "are we current", upgrade planning, "which version fixes X", security-advisory exposure, or a quarterly review.
when_to_use: Trigger phrases - "/code-version-check", "are we current", "which version fixes X", "upgrade planning", "are we exposed to DSA-2026-...", "quarterly version review"
disable-model-invocation: true
---
# Code version check

The library is a snapshot (version in `~/.claude/brain/library/VERSION`): "latest in library" means latest
**documented** there, not latest released. Say so in the output. Never invent a version number.

## 1. Running versions
From `~/.claude/brain/environment.md` first, then live where a tool exists (prefer live, note
disagreements): PowerMax `list_arrays` / `get_array` (PowerMaxOS / microcode), `list_unispheres`
(Unisphere); ONTAP cluster version (ontap MCP); Harvest (harvest MCP); MDS `run_show "show version"`;
UCS `list_centrals` / `list_domains`; ESXi / vCenter from Aria (kuparashit has no versions). Ask him for what no tool
shows: Solutions Enabler (`symcli -def`), Trident (`tridentctl -n trident version`), CSM
(`oc get csm -A`, driver image tags), PowerFlex (`scli --version`, `scli --query_all` header).

## 2. What the library can say (vendor / product; cite title or file name + url + version)
| Component | Reference in the library | Not in the library (say so) |
|---|---|---|
| PowerMaxOS, Unisphere, Solutions Enabler | `dell/kb`: DSA-* for "PowerMaxOS", "Unisphere for PowerMax", "Solutions Enabler" (affected and fixed versions), fix / "available in PowerMaxOS level" articles, "Solutions Enabler and Unisphere for PowerMax important documentation and downloads links"; `dell/powermax` guides name the version they document | PowerMaxOS release notes, Dell target-code / E-Lab matrix |
| PowerFlex | `dell/powerflex` release notes PDFs (3.6.x, 4.0.x, 4.5.x / 5.1.x: fixed and known issues, upgrade paths), upgrade guides; `dell/kb` DSA-* "PowerFlex" | newer releases than the PDFs |
| ONTAP | `netapp/ontap` "Choose a NetApp-recommended target ONTAP version for an upgrade" and the upgrade section; `ontap-systems-upgrade`; `kb-ontap` CONTAP-* "Fixed In Version" (your version inside an affected range = finding) | the live "minimum recommended release" table, NetApp security advisories (NTAP-*) |
| Trident | `trident-<yymm>` pages `trident-rn.html` (what's new, fixed, known issues) and `known-issues.html`; `trident-changelog`; `trident-issues` (open bugs by version) | - |
| CSM / CSI drivers | `dell/csm` `csidriver/release/powermax/` and `.../powerflex/` + `replication/release/` of the matching url version; `csm-repo` CHANGELOG-<ver>; `dell/kb` DSA-* "Container Storage Modules"; `*-prs` (merged fixes, dated, with the `dell/csm#<n>` they fix) | the CSM issue texts |
| Harvest | `harvest-changelog`, `harvest-issues` | - |
| NX-OS (MDS), UCS, ESXi | nothing (ESXi: a few `vmware/kb`, `netapp/kb-ontap`, `ontap-sanhost` host-support pages) | everything: general knowledge only, labelled |

Search pattern: `"<product> <running version>"`, then `DSA <product>`, then "fixed in" / "known issues"
with the product filter; read the hits (`docs-lookup`). For each DSA: affected range, fixed version,
whether the running version is inside.

## 3. Output
| component | running (source) | recommended / latest in library (source, version) | security advisories | notes |
Notes: known issues matching symptoms seen here, dependencies (Unisphere ↔ PowerMaxOS, CSM ↔ OpenShift
↔ array OS, Trident ↔ ONTAP ↔ OpenShift, ESXi ↔ array host-connectivity guide), and "not verifiable from
the library". Finish with the upgrade order that the documented dependencies impose, as a plan for him.
Save the table under `~/storage-reports/<date>-code-versions.md`.
