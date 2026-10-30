---
name: docs-lookup
description: How to answer from the offline documentation library - product names and versions, search method, reading, citing, known bug / fixed in which version. Use for any request that depends on how a vendor product works: errors, procedures, concepts, design, best practices, APIs and SDKs, known bugs.
when_to_use: Trigger phrases - "what do the docs say", "is this a known bug", "best practice for", "how does X work", "build / script something with ONTAP / PowerMax", "how do I do X in FastAPI / Pydantic / fastmcp"
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
| PowerFlex | `dell` / `powerflex` (Technical Overview, Administration, CLI Reference, Install / Upgrade guides per version up to 5.1.x; release notes 3.6.x / 4.0.x only), `kb` (dial-home `SIO…` codes, 5.x issues, release matrix 000461757, end-of-life dates 000305299), `infohub-powerflex`, `powerflex-api` (REST API guide pages per version 3.6-5.1; every endpoint with parameters, responses and errors for 5.1.0 and 4.5.5 / Manager 4.8). Not in the library (Dell entitlement): 4.5-5.1 release notes, Alerts and Events guides, security guides - say so |
| CSM / CSI drivers on OpenShift | `dell` / `csm` (url `content/docs/` = current, `content/v1..v3/` = older; pick the one matching the installed CSM), `csm-repo` (CHANGELOG-<ver>), `csi-powermax`, `csi-powerflex`, `csm-replication`, `csm-operator` (`operatorconfig/driverconfig/<driver>/<ver>/` = the exact manifests the operator deploys), `csm-authorization`, `csm-resiliency`, `csm-dr`, `infohub-csm`, `kb`; fixes: `csm-prs`, `csi-powermax-prs`, `csi-powerflex-prs`, `csi-powerscale-prs`, `csm-operator-prs`, `csm-replication-prs` |
| PowerScale / Isilon / OneFS | `dell` / `kb`, `infohub-powerscale`, `csi-powerscale` (driver docs + code), `gopowerscale`, `ansible-powerscale`, `terraform-powerscale` |
| A CSI / CSM error text, a sidecar (attacher, provisioner, resizer, snapshotter, registrar) | the error string in quotes over `dell` code (`csi-powermax`, `csi-powerflex`, `csi-powerscale`, `goscaleio`, `gopowermax`, `gobrick`, `csm-operator`, `csm-replication`) and `kubernetes` (sidecars, `csi-spec`, `csi-docs`); host-side errors (mount, multipath, iSCSI, NVMe): `gofsutil`, `gobrick`, `goiscsi`, `gonvme` |
| Kubernetes / OpenShift storage itself (PV / PVC, StorageClass, snapshots, expansion, topology, CSI on OpenShift, OpenShift Virtualization storage) | `kubernetes` / `k8s-storage-docs` (official concepts), `openshift` / `storage` (Red Hat storage chapters), `kubernetes` / `csi-docs` |
| Dell security advisories (DSA-*), PowerPath, Unisphere how-tos | `dell` / `kb` |
| ESXi storage | `vmware` / `kb`, `netapp` / `kb-ontap` |
| Concepts, architecture, design, best practices (incl. "build something like X") | `netapp`: `ontap` (concept pages), `ontap-technical-reports` (TRs), `ontap-apps-dbs` (VMware / databases), `ontap-sanhost`, `trident-<yymm>` (`trident-reco`); `dell`: `infohub-powermax` / `-powerflex` / `-powerscale` / `-csm` (white papers), `powermax` / `powerflex` product guides and technical overviews, `csm` (`concepts/`); `kubernetes`: `csi-spec`, `csi-docs` |
| Automation, APIs, SDKs, code that talks to the arrays | `netapp`: `ontap-restapi` (every endpoint), `ontap-automation`, `harvest` (metrics); `dell`: `pyu4v` (PowerMax Python), `gopowermax`, `goscaleio`, `gopowerscale`, `powerflex-api` (PowerFlex REST endpoints), `pypowerflex`, `ansible-*`, `terraform-*`, `csi-*` code; `kubernetes`: sidecars |
| Writing a backend: FastAPI, Pydantic v2, settings, Starlette middleware, uvicorn, httpx, pytest, SQLAlchemy 2, MCP servers (fastmcp, the MCP Python SDK, the MCP specification 2026-07-28) | `python` / `fastapi`, `pydantic`, `pydantic-settings`, `starlette`, `uvicorn`, `httpx`, `pytest`, `pytest-asyncio`, `sqlalchemy`, `fastmcp`; `mcp` / `python-sdk`, `specification`. House conventions: the `fastapi-service` skill |
| Cisco MDS 9000, NDFC (Nexus Dashboard Fabric Controller), Nexus 9000: configuration, zoning, VSANs, port-channels, NX-API / REST, automation | `cisco` / `mds` (NX-OS 9.x guides, command reference, system messages, release notes 9.4, NX-API reference 9.4), `ndfc` (SAN user content 12.2.2, SAN controller guide, install / upgrade, REST API SAN + LAN 12.2.2, Nexus Dashboard API), `nexus` (NX-OS 10.6 SAN switching, FC/FCoE-NPV, interfaces, L2, QoS, system messages, NX-API REST), `ansible-dcnm`, `ansible-nxos`, `terraform-dcnm`, `terraform-nxos`. The guides are hand-downloaded (extra/cisco/NEEDED.md): if a search finds only API pages, the guide may not be in yet - say so |
| Terraform: HCL language, CLI, state, modules; providers | `hashicorp` / `terraform` (1.17 docs), `terraform-kubernetes`; `dell` / `terraform-powermax`, `terraform-powerflex`, `terraform-powerscale`; `netapp` / `terraform-ontap`; `vmware` / `terraform-vsphere`; `cisco` / `terraform-dcnm`, `terraform-nxos`. Conventions: the `terraform` skill |
| UCS, PowerMaxOS release notes, the CSM issue texts (use the `*-prs` fixes) | **not in the library**: say so; explain from general knowledge, clearly labelled |

## 2. Search: exact first, then wider
1. An error message or log line: its most specific part **in quotes** (quoted text must appear verbatim;
   drop variable parts such as volume names, IDs, timestamps). 2. The key technical words without quotes
   (EMS name, command, KB / CONTAP / DSA number, SIO / PFX code), with vendor + product when known.
   3. Drop the product filter, then the vendor filter. 4. Rephrase with the words the vendor would use
   (the symptom as a KB title would state it; a general question: the topic in vendor terms, then with
   "best practices" / "considerations" / "overview", per vendor); old / new product names and acronyms
   (Isilon / PowerScale, ScaleIO / VxFlex / PowerFlex, VMAX / PowerMax, RDP, SRDF, SDC / scini) already match.
Each hit has `matched` (query words found / total); `match_mode: partial` = no section holds every word:
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
