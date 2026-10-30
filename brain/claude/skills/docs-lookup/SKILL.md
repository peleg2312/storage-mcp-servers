---
name: docs-lookup
description: How to answer from the offline documentation library - vendor / product names and versions, search method, reading, citing, known bug / fixed-in version. Use for any question about how a vendor product or library works. Triggers - "what do the docs say", "is this a known bug", "best practice for", "how does X work", "build / script something with ONTAP / PowerMax", "how do I do X in FastAPI / Pydantic / fastmcp"
---
# Library lookup (how every docs answer is built)

Tools: docs MCP (`docs-search` on the cluster or `docs-local` on this VM; same five tools) or, without
MCP, `python3 ~/.claude/brain/library/search.py search "..." [--vendor v] [--product p] [--limit n]`,
`read-chunk <id> --context 1`, `read-doc --path <p>` / `--url <u>`, `sources`, `explain-code <code>`. Exact names of every
vendor / product: `~/.claude/brain/library/MANIFEST.md`. There is no internet; never cite anything else.

## 1. Pick vendor and product (product is a substring filter: use the full name when it matters)
Exact names: `MANIFEST.md`. Anything else (Trident releases, PowerFlex API,
Nexus / NDFC, Terraform providers, SDKs, Kubernetes storage, concepts and best practices): read
`~/.claude/skills/docs-lookup/references/products.md` before searching.
| Question about | vendor / product |
|---|---|
| ONTAP EMS event | `netapp` / `ontap-ems-<ver>` of the cluster (9.15.1 → `ontap-ems-9151`); `ontap-ems` when unknown |
| ONTAP behaviour, commands, REST | `ontap`, `ontap-sanhost`, `ontap-metrocluster`, `ontap-restapi`; symptom or CONTAP-* bug: `kb-ontap` |
| Trident | `trident-<yymm>` of the installed release, `trident-issues`, `trident-changelog` |
| PowerMax, SRDF, SnapVX, Unisphere | `dell` / `powermax`, `kb` |
| PowerFlex | `dell` / `powerflex`, `kb`, `powerflex-api` |
| CSM / CSI drivers on OpenShift | `dell` / `csm` (url `content/docs/` = current, `content/v1..v3/` = older: match the installed CSM), `csm-repo`, `csi-powermax`, `csi-powerflex`, `kb`; fixes: the `*-prs` products (`csm-prs`, `csi-powermax-prs`, ...: every merged / open pull request with the `dell/csm#<n>` issues it fixes) |
| MDS / NDFC / Nexus | `cisco` / `mds`, `ndfc`, `nexus` |
| ESXi storage | `vmware` / `kb`, `netapp` / `kb-ontap` |
| UCS, PowerMaxOS release notes, CSM issue texts | **not in the library**: say so; explain from general knowledge, labelled |

## 2. Search: exact first, then wider
0. An EMS event name, SYMAPI / SIO code, CONTAP-* / DSA-* / KB number: `explain_code(code)` before any search
   (severity, corrective action, KB Symptoms / Cause / Resolution in one call). `documented: false` = search normally.
   A direct question: one `search_docs` with `read_top=2` (full text of the top 2 inline). First search partial
   or off-target: one call with `queries=[2-3 rephrasings]` (merged; `by_query` shows which found what).
1. An error message or log line: its most specific part **in quotes** (quoted text must appear verbatim;
   drop variable parts such as volume names, IDs, timestamps). 2. The key technical words without quotes
   (EMS name, command, KB / CONTAP / DSA number, SIO / PFX code), with vendor + product when known.
   3. Drop the product filter, then the vendor filter. 4. Rephrase with the words the vendor would use
   (the symptom as a KB title would state it; a general question: the topic in vendor terms, then with
   "best practices" / "considerations" / "overview", per vendor); old / new product names and acronyms
   (Isilon / PowerScale, ScaleIO / VxFlex / PowerFlex, VMAX / PowerMax, RDP, SRDF, SDC / scini) already match.
A hit with `matched` (e.g. 3/5 query words) is partial; reply `partial: true` = no section holds every word:
leads, not answers. `unmatched` = words no hit holds: replace exactly those with the vendor's term and
search again. A version in the query (`9.15.1`, `2.16.2`, `25.10`) ranks that version's documents first. Max 2 hits per document; code hits (`.go`, `.yaml`) show where an error is raised, not
what to do. Default 8 hits; raise `limit` only when the titles are all off-target.

## 3. Read, cite, version
`read_chunk(id, context=0)` on the best hit (context 1 when the section is cut off); read the next hits too when the
first does not fully answer, or when another version or a KB may change the answer; `read_document` only for a procedure or table spanning
sections. Never answer from snippets. Cite title (PDF titled "pdf" / "View": the file name from the url, with
the page) + url + the version it applies to; another version's document is a hint ("documented for 9.2;
confirm for yours"). Quote verbatim when wording matters (states, thresholds, limits). Two versions disagree:
show both, prefer the installed one.

## Special cases
- **Known bug / fixed in which version** - report affected versions, fixed version, workaround, and whether
  the installed version is in range:
  Trident: `trident-issues`, `trident-changelog`, `trident-<ver>` pages `trident-rn.html` / `known-issues.html`.
  Harvest: `harvest-issues`, `harvest-changelog`. ONTAP: `kb-ontap` CONTAP-* ("Fixed In Version";
  `9.15.1P3 to 9.15.1P20` = affected range). PowerFlex: release notes in `dell/powerflex`. PowerMax: `dell/kb`.
  CSM: "Fixed / Known Issues" in `dell/csm` `release/` and `csidriver/release/<driver>/` (one line per bug;
  older versions link `dell/csm#<n>`) and `csm-repo` CHANGELOG; then search that title's words or
  `dell/csm#<n>` over the `*-prs` products: the PR's "First release:" is the first tag of that repo with the
  fix (the `dell/csm` support matrix maps CSM to driver versions, e.g. CSM 1.18 = csi-powermax 2.18).
- **How a driver / client works** (what it runs on the node, which function does X): read the repo's
  `CODEMAP.md` first (search `code map <product>`: commands run and from which function, host paths, every
  file's functions), then search the function name with the product filter, and read it.
- **Error text from a CSI driver, operator or sidecar**: the quoted text over the code (table above); the hit's
  section heading is the function raising it - read it to say when it happens, then find the user-facing
  explanation in `dell/csm`, `dell/kb` or the CHANGELOG. Code is current `main`, not the installed release.
- **"Partial article"** (NetApp KB): cause present, solution behind the support login - say so, look for a
  sibling article or its CONTAP-* bug.
- **Nothing found**: say what you searched; label any general-knowledge answer as such; name the vendor
  document worth adding to the library.
