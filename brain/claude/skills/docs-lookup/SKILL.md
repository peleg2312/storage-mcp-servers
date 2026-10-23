---
name: docs-lookup
description: Playbook for answering any product question from the offline documentation library (docs MCP docs-search / docs-local, or search.py) - choosing vendor and product (versioned ontap-ems-<ver>, trident-<yymm>, dell/csm url version), exact-term search first, reading before answering, citing title + url + version, "Partial article", nothing found, and "is this a known bug / fixed in which version" via the bug trackers and release notes. Use whenever a question needs vendor documentation, a KB article, an error meaning, a procedure, a best practice or a known-bug check.
when_to_use: Trigger phrases - "what does the documentation say about", "find the KB article for", "is this a known bug", "which version fixes", "best practice for", "search the library for"
---
# Library lookup (how every docs answer is built)

Tools: docs MCP (`docs-search` on the cluster or `docs-local` on this VM; same four tools) or, without
MCP, `python3 ~/.claude/brain/library/search.py search "..." [--vendor v] [--product p] [--limit n]`,
`read-chunk <id> --context 1`, `read-doc --path <p>` / `--url <u>`, `sources`. Exact names of every
vendor / product: `~/.claude/brain/library/MANIFEST.md`. There is no internet; never cite anything else.

## 1. Pick vendor and product (product is a substring filter: use the full name when it matters)
| Question about | vendor / product |
|---|---|
| ONTAP EMS event | `netapp` / `ontap-ems-<ver>` of the cluster (9.15.1 → `ontap-ems-9151`, 9.11.1 … 9.18.1 exist); `ontap-ems` when unknown |
| ONTAP behaviour, commands, SAN hosts, MetroCluster, REST | `ontap`, `ontap-sanhost`, `ontap-metrocluster`, `ontap-restapi`, `ontap-systems-upgrade`, `ontap-tools-vmware-vsphere*` |
| ONTAP symptom, known bug (CONTAP-*) | `kb-ontap` |
| Trident | `trident-<yymm>` of the installed release (`trident-2307` … `trident-2510`; `trident` = latest), `trident-issues`, `trident-changelog`, `kb-trident` |
| Harvest | `harvest`, `harvest-issues`, `harvest-changelog` |
| PowerMax, SRDF, SnapVX, Solutions Enabler, Unisphere | `dell` / `powermax` (PDFs: Product Guide, Solutions Enabler CLI Reference, SRDF Introduction, Events and Alerts guide, Host Connectivity for ESXi), `kb` |
| PowerFlex | `dell` / `powerflex` (Technical Overview, Administration, CLI Reference and Install guides per version, release notes 3.6.x / 4.0.x / 4.5.x-5.1.x), `kb` |
| CSM / CSI drivers on OpenShift | `dell` / `csm` (url `content/docs/` = current, `content/v1..v3/` = older; pick the one matching the installed CSM), `csm-repo` (CHANGELOG-<ver>), `csi-powermax`, `csi-powerflex`, `csm-replication`, `csm-operator`, `csm-authorization`, `csm-resiliency`, `kb`; fixes: `csm-prs`, `csi-powermax-prs`, `csi-powerflex-prs`, `csi-powerscale-prs`, `csm-operator-prs`, `csm-replication-prs` |
| PowerScale / Isilon / OneFS | `dell` / `kb`, `infohub-powerscale`, `csi-powerscale` (driver docs + code), `gopowerscale`, `ansible-powerscale`, `terraform-powerscale` |
| A CSI / CSM error text, a sidecar (attacher, provisioner, resizer, snapshotter, registrar) | the error string in quotes over `dell` code (`csi-powermax`, `csi-powerflex`, `csi-powerscale`, `goscaleio`, `gopowermax`, `gobrick`, `csm-operator`, `csm-replication`) and `kubernetes` (sidecars, `csi-spec`, `csi-docs`) |
| Dell security advisories (DSA-*), PowerPath, Unisphere how-tos | `dell` / `kb` |
| ESXi storage | `vmware` / `kb`, `netapp` / `kb-ontap` |
| Cisco MDS / UCS, PowerMaxOS release notes, the CSM issue texts (use the `*-prs` fixes) | **not in the library**: say so; explain from general knowledge, clearly labelled |

## 2. Search: exact first, then wider
1. An error message or log line: its most specific part **in quotes** (quoted text must appear verbatim;
   drop variable parts such as volume names, IDs, timestamps). 2. The key technical words without quotes
   (EMS name, command, KB / CONTAP / DSA number, SIO / PFX code), with vendor + product when known.
   3. Drop the product filter, then the vendor filter. 4. Rephrase with the words the vendor would use
   (the symptom as a KB title would state it); old / new product names and common acronyms (Isilon /
   PowerScale, ScaleIO / VxFlex / PowerFlex, VMAX / PowerMax, RDP, SRDF, SDC / scini) already match.
Each hit has `matched` (query words found / total): prefer full matches; `match_mode: partial` means no
section holds every word, so treat the hits as leads, not answers. Max 2 hits per document: when one
document holds the answer, read it with `read_document`. Source-code hits (`.go`, `.yaml` paths) show where
an error is raised, not what to do about it. Use `limit` 10-20 when ambiguous and scan the titles first.

## 3. Read before answering
`read_chunk(chunk_id, context=1)` on the best 2-3 hits, `read_document(url or path)` when the answer is a
procedure or a table spanning sections. Never answer from snippets alone. PDF chunks carry the title
"pdf" or "View" plus a page number: cite the **file name from the url** (e.g.
`docu100386_Solutions_Enabler_9.2_CLI_Reference_Guide.pdf`, page 364) instead of the title.

## 4. Cite and version
Every statement: document title (or file name), url, and the product version it applies to (from the
product name, the url, or the document itself). A document for another version is a hint, not proof:
say "documented for 9.2; confirm for your version". Quote short passages verbatim when the wording matters
(state names, thresholds, limits).

## Special cases
- **Known bug / fixed in which version**: Trident → `trident-issues` (issue number, status, affected and
  fixed versions, workaround), `trident-changelog`, the `trident-<ver>` pages `trident-rn.html` and
  `known-issues.html`; Harvest → `harvest-issues`, `harvest-changelog`; ONTAP → `kb-ontap`
  CONTAP-* articles ("Fixed In Version" section; ranges like `9.15.1P3 to 9.15.1P20` mean affected);
  PowerFlex → the release notes PDFs in `dell/powerflex` ("fixed issues", "known issues"); CSM → the
  `dell/csm` `release/` and `csidriver/release/<driver>/` pages ("Fixed Issues" / "Known Issues": one line per
  bug, e.g. "PowerMax - Driver Crashes with Segmentation Fault ..."; older versions link `dell/csm#<n>`) and
  `csm-repo` CHANGELOG-<ver>, then search that title's key words, the `dell/csm#<n>` or the symptom over the `*-prs` products: the
  PR that fixes it; its "First release:" line is the first tag of that repo (driver, operator or client
  library) holding the fix - compare it with the installed version (CSM 1.18 ships csi-powermax 2.18 etc.:
  the `dell/csm` support matrix maps them);
  PowerMax → `dell/kb`
  (fix numbers and the PowerMaxOS level that carries them). Report: affected versions, fixed version,
  workaround, and whether the installed version (environment file / tool result) is inside the range.
- **Error text from a CSI driver, the operator or a sidecar**: search the exact text over the source code
  (table above). A code hit is a `.go` file whose section heading is the function that returns the error:
  read it (`read_chunk` with context 1) to explain **when** the error is raised (which array call, which
  check), then find the user-facing explanation in `dell/csm`, `dell/kb` or the sidecar CHANGELOG. The code is
  the current `main` branch, not necessarily the installed release: say so, and compare with the driver's
  release notes for the installed version.
- **"Partial article"** (NetApp KB): the symptom and cause are present but the solution needs a support
  login. Use what is there, say the solution is not in the library, and look for a sibling article or
  the CONTAP-* bug it refers to.
- **Nothing found**: say so plainly (which products and terms you searched); do not fill the gap with
  memory presented as a citation. Offer the general-knowledge explanation labelled as such, and name the
  vendor document to save into the local library (`library/README.md` explains the refresh).
- Two documents disagree (different versions): show both with their versions; prefer the one matching
  the installed version.
