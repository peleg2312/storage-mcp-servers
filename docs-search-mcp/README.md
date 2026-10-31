# docs-search MCP server (read-only, works fully offline)

Gives Claude a searchable **documentation and bug library** for NetApp ONTAP, Trident, Harvest, Dell PowerMax,
PowerFlex and CSM, plus your own runbooks and saved KB articles. BM25 full-text search (SQLite FTS5): exact
command names, EMS/event names, error text and KB numbers find the right page. **Nothing needs internet at
query time**: the index holds all the text. Same bearer-token auth as the other servers.

## Fastest: the prebuilt library in this repo

`../library/` holds the whole library (documents + index) as 45 MB git parts, so the air-gapped side needs
only the git clone. On the VM that runs Claude Code: `sh ../install-vm.sh` (brain + library + the MCP
server `docs-local`, standard library only). For a cluster: `sh bundle/build-offline.sh --from-library`
builds the dated image with no internet at all. `../library/MANIFEST.md` lists what is inside; to add the
parts that need an office/home IP (Dell PDFs and KB, bug trackers) or to continue the NetApp KB export
see [`../library/README.md`](../library/README.md).

## Three ways to run it

| Your cluster | Use | How the content gets in |
|---|---|---|
| **Air-gapped** (no internet) | `openshift-offline.yaml` | build the image `docs-search-offline:<date>` from the prebuilt library (`bundle/build-offline.sh --from-library`, no internet) or fresh from the vendor sites on a machine **with** internet (`bundle/build-offline.sh`), import it like any other image. The library is inside the image. |
| Has internet | `openshift.yaml` | a nightly CronJob syncs and re-indexes on a PVC |
| **A VM with Claude Code, no cluster** | `mcp_stdio.py` | `sh ../install-vm.sh`: the library goes to `~/.claude/brain/library`, `docs-local` is registered with `claude mcp add` (stdio, no pip, no container). Same four tools. `search_cli.py` = the same search from the shell. |

Both also support a **local library**: your own files (runbooks, KB articles saved from the vendor portals,
PDFs) dropped into `/data/local/docs/<folder>/<product>/`, indexed every 30 min, searched together with the
main library (results say `library: main|local`).

## What's in the library

| Source | Sync script | Approx. |
|---|---|---|
| **NetApp docs**: 36 NetAppDocs repos (ONTAP 9 incl. release notes, SAN host config, ONTAP tools for VMware, SnapCenter, MetroCluster, **EMS event reference for ONTAP 9.11 to 9.18** (meaning + corrective action of every event), REST API reference, FLI, hardware + upgrades, ASA r2, TRs, E-Series, StorageGRID, AIQUM) | `sync/sync-git.sh` | 33,000 pages |
| **Trident** docs for **every release 23.07 to 25.10** (`trident` = latest, `trident-2510` ...; incl. "What's new" = fixes per release) + `trident-changelog` (every fix with its issue number) | `sync/sync-git.sh` | 830 pages |
| **NetApp Knowledge Base** (kb.netapp.com, public articles from the site's sitemap: ONTAP SAN / performance / data protection / hardware / MetroCluster / OS, Trident, ONTAP tools for VMware, switches, SnapCenter, AIQUM...) → products `kb-ontap`, `kb-trident`, `kb-ontap-tools-vmware`, `kb-switches`... Articles whose Cause/Solution needs a NetApp Support login keep their public part, flagged "Partial article"; with `NETAPP_KB_COOKIE` (your own logged-in browser session) the full articles are saved. | `sync/sync_netapp_kb.py` (one article per 5 s, as the site's robots.txt asks) | up to 35,000 articles |
| **Harvest** docs + `harvest-changelog` | `sync/sync-git.sh` | 150 pages |
| **Dell CSM** docs, all versions (CSI PowerMax/PowerFlex/PowerScale/PowerStore/Unity, replication, Metro, observability, authorization, resiliency, operator, release notes, troubleshooting) + the CSI / CSM GitHub repos (READMEs, release notes, changelogs) + **PyU4V**, **PyPowerFlex**, **Ansible** and **Terraform** PowerMax / PowerFlex docs | `sync/sync-git.sh` | 1,000 pages |
| **Bug trackers**: every GitHub issue (open + closed, with all comments/workarounds) of NetApp/trident, NetApp/harvest, dell/csm → products `trident-issues`, `harvest-issues`, `csm-issues` | `sync/sync_github_issues.py` (needs `GITHUB_TOKEN`) | thousands of issues |
| **Dell PowerMax/VMAX** (Unisphere, Solutions Enabler, REST, SRDF, SnapVX, VMware papers) and **PowerFlex** 3.6–5.x (guides, release notes with fixed/known issues) PDFs from Dell's documentation hubs | `sync/sync_dell.py` (`sources/dell-sources.txt`) | 200+ PDFs |
| **KB articles / pages you choose** (NetApp KB, Dell KB, Broadcom KB, any vendor page): one URL per line in `sources/web-pages.txt` or a plain URL list (`URLS=file`) | `sync/sync_web.py` (one page per URL, robots.txt respected; login-only pages are reported, save those from the browser into `extra/`) | as many as you add |
| **Dell Knowledge Base** for PowerMax, PowerMaxOS, Unisphere, Solutions Enabler, SRDF, PowerPath, PowerFlex (software, appliance, rack, manager), CSM / CSI: every article of the per-product listings on the support site + a seed list → product `dell/kb` | `sync/sync_dell_kb.py` (office/home PC only: dell.com refuses cloud IPs) | hundreds |
| **VAST Data** (kb.vastdata.com: product documentation of VAST Cluster / AI OS 5.x incl. protocols, views, replication, hardware, release notes; the support knowledge base; the 5.5 REST API reference) → `vast/docs`, `vast/kb`, `vast/api-5-5`, one Markdown file per article from the site's own `llms.txt` index | `sync/sync_vast.py` | 6,700 articles |
| **VMware vSphere guides** (techdocs.broadcom.com: vSphere Storage 7.0 / 8.0 / 9.0, Monitoring and Performance 8.0, WSFC setup 8.0; one topic per page, navigation stripped) → `vmware/vsphere-7|8|9` | `sync/sync_techdocs.py` (`sources/techdocs-sections.txt`; the site asks for a 10 s crawl delay) | 1,600 pages |
| **VMware / Broadcom KB** about storage (VMFS, NFS, datastores, LUNs, naa, APD / PDL, multipathing, iSCSI, FC / HBA, vVols, VAAI, NVMe, esxcli, UNMAP, VMDK, RDM, vSAN...) → `vmware/kb` | `sync/broadcom_kb_list.py` (slug filter over the site's sitemap) then `sync/sync_web.py --urls` | 4,300 articles |
| **Dell PowerScale OneFS 9.10** manuals (CLI and Web Administration, CLI Command Reference, Event Reference, Security Configuration, Upgrade Planning, Supportability and Compatibility, Backup and Recovery, CloudPools, release notes; HTML topic by topic, the PDFs need a Dell login) → `dell/powerscale` | `sync/dell_browser.py manuals` (`sources/dell-manuals.txt`; a real browser, dell.com refuses plain clients) | 11 guides |
| **NetApp KB NAS and S3 areas** (NFS / SMB / CIFS, exports, shares, name services, locks) | `sync/sync_netapp_kb.py` (now in its default areas) | 5,600 articles |
| **Red Hat Enterprise Linux 9** storage guides (storage devices, dm-multipath, file systems, network file services, performance) → `redhat/rhel9` | `sync/sync_web.py` (`sources/web-pages.txt`) | 5 guides |
| **KB pointers** (`sources/kb/kb-pointers.md`): verified public KBs with one-line answers | copied | grow it |
| Anything else: `extra/<vendor>/<product>/...` at build time, or the local library at run time | | |

Sources to add are one line each in `sources/git-repos.txt`, `sources/github-issues.txt`, `sources/dell-sources.txt`,
`sources/web-pages.txt`. `sync-git.sh --netapp-all` adds every public NetAppDocs repo (~2,000).
`sync_netapp_kb.py --include <sitemap prefix>` chooses other KB areas (`--list` shows them).

**NetApp KB with your support login** (full articles instead of the public part): sign in to kb.netapp.com in
your browser, open the developer tools → Network → any request to kb.netapp.com → copy the request `cookie`
header value, and give it to the sync as the environment variable `NETAPP_KB_COOKIE` (never in a file you
commit). Then `python3 sync/sync_netapp_kb.py --dest work/docs --refresh-partial`. The session lasts a few
hours; just copy a fresh one and re-run (incremental). Keep the resulting library internal: the articles
are licensed to your support contract.

**Identical pages in several versions** (an EMS event unchanged from ONTAP 9.11 to 9.18, a CSM page present in
every doc version) are stored once: the indexer folds copies with identical text into one canonical document
(the unversioned or newest product), keeps the others as aliases, and every hit lists them as `also_in`.
Filtering by any of those products still finds the page; `read_document` on an alias path reads the canonical copy.

**Where the content comes from:** docs.netapp.com is generated from the NetAppDocs GitHub repos, so the
git sync *is* the NetApp documentation site; the Dell part is downloaded from dell.com /
delltechnologies.com. **Not downloadable in bulk:** the NetApp KB, NetApp Bugs Online, Dell KB and Dell
SolVe have no export and many articles need a login - add the articles you need by URL (`web-pages.txt`)
or save them from the browser into `extra/<vendor>/<product>/`. Their content reaches the library through the
release notes / fixed-issue lists (included), the KB pointers, and articles you save into the local library.

**Licensing:** the content stays the vendors' copyright, fetched for internal reference into your own
image/volume. It is not stored in this Git repo; don't publish the offline image outside your company.

## Air-gapped: step by step

On a machine **with internet** (Linux/WSL/Mac: `git`, `python3` + `pip install pypdf`, `docker` or `podman`):
```bash
git clone https://github.com/peleg2312/storage-mcp-servers && cd storage-mcp-servers/docs-search-mcp
export GITHUB_TOKEN=<any read-only GitHub token>      # for the bug trackers (60 req/h without it)
sh bundle/build-offline.sh                           # 1st run 1-3 h (issues + PDFs), later runs minutes
# -> work/docs-search-offline-YYYY.MM.DD.tar.gz + .sha256
```
Carry the tar.gz in, then inside:
```bash
sha256sum -c docs-search-offline-*.tar.gz.sha256
podman load -i docs-search-offline-YYYY.MM.DD.tar.gz
podman tag docs-search-offline:YYYY.MM.DD <registry>/docs-search-offline:YYYY.MM.DD && podman push <registry>/docs-search-offline:YYYY.MM.DD
oc create secret generic docs-search-env --from-env-file=.env    # MCP_AUTH_TOKENS=<openssl rand -hex 32>
# set the image tag in openshift-offline.yaml (2 places)
oc apply -f openshift-offline.yaml
claude mcp add --transport http docs http://<route-or-service>:8000/mcp --header "Authorization: Bearer <token>"
```
Monthly: re-run `build-offline.sh` (incremental), import the new dated image, change the tag. The local
library on the PVC is not touched.

Add your own documents (any time, no rebuild):
```bash
POD=$(oc get pod -l app=docs-search-mcp -o name | head -1)
oc cp ./saved-kb ${POD#pod/}:/data/local/docs/saved-kb      # .pdf .html .md .txt .adoc; found within 30 min
```
Tip: save a vendor KB as PDF/HTML ("Print → Save as PDF") whenever you open one, into
`saved-kb/<netapp|powermax|powerflex|trident|csm>/`; the library grows with what the team actually hits.

## Tools

| Tool | Purpose |
|---|---|
| `search_docs(query, queries, vendor, product, limit, read_top)` | BM25 search over all libraries; all words first, any-word fallback; snippet with matches marked « ». Lean reply: `matched` only on partial hits, `partial: true` when no section holds every word, `library` only with two libraries; every hit says `fetched` (YYYY-MM), `stale: true` after 18 months, and `note` when the document is for another version of a product than the one in `~/.claude/brain/environment.md` (backticked docs product names under Versions) |
| `explain_code(code)` | exact lookup of an ONTAP EMS event, PowerMax `SYMAPI_*` alert, PowerFlex `SIO*` code, `CONTAP-*` bug, `DSA-*` advisory or KB number: severity, description, corrective action, url, and the KB's Symptoms / Cause / Resolution; `documented: false` when absent |
| `read_chunk(chunk_id, context)` | the hit in full plus neighbouring sections |
| `read_document(path or url, start, max_sections)` | read a whole document in order (PDFs page by page) |
| `related_docs(chunk_id or path or url, limit)` | pages the document links to (`links_to`) and pages that link to it (`linked_from`), resolved inside the library; `unresolved` counts links pointing outside it |
| `list_sources(vendor)` | per library: bundle date, documents per vendor as `product count, ...` (~3 KB; `vendor` lists one) |

`read_top` (0-3) returns the full text of the best hits inline, so one call answers. `queries` (up to 5 phrasings, wins over `query`) are merged, with `by_query` showing which found what. Mutual synonyms cover plain-language words as well as product names.

`related_docs` uses the `links` table (`doc_id`, `href`: up to 200 normalized outgoing http(s) links per document, collected by `docs_index.py` from HTML `<a href>`, Markdown / AsciiDoc links and bare urls) joined to `docs.url`. An index built before this table has no links until a `--full` rebuild; the tool then returns empty lists.

Prompts: `explain_error`, `how_to`. The instructions and the `search_docs` text live in `docs_text.py`, shared by `server.py` and `mcp_stdio.py` (copy it with them). The server instructions tell Claude it is offline, to search with exact
terms, read before answering, cite title + URL and the version, and to check the bug trackers for errors.

## Connected cluster

```bash
oc create secret generic docs-search-env --from-env-file=.env    # MCP_AUTH_TOKENS, GITHUB_TOKEN
# set <registry>/docs-search-mcp:1.1 in openshift.yaml (3 places)
oc apply -f openshift.yaml && oc create job docs-sync-now --from=cronjob/docs-sync
```
Needs HTTPS to github.com, api.github.com, www.dell.com, dl.dell.com, www.delltechnologies.com.

## Run locally

```bash
sh sync/sync-git.sh ./data/docs
python3 sync/sync_dell.py --dest ./data/docs/dell
GITHUB_TOKEN=... python3 sync/sync_github_issues.py --dest ./data/docs
mkdir -p data/docs/kb && cp sources/kb/*.md data/docs/kb/
python3 docs_index.py --docs ./data/docs --db ./data/index/docs.db
MCP_AUTH_TOKENS=$(openssl rand -hex 32) INDEX_DB=./data/index/docs.db python3 server.py
```

## Tests

`eval_search.py` (hit@1/5/10 + MRR over every `tests/retrieval_*.json` set; `--dump` to diff replies before/after a change), `test_search.py` (indexer, all tools, incremental update, two libraries), `test_stdio.py` (the stdio MCP
server handshake + all tools, the CLI, NetApp KB extraction incl. login-gated articles), `test_sync_dell.py`
(hub parsing, allowed hosts, login pages rejected, incremental), `test_sync_issues.py` (pagination, comments,
PRs skipped, incremental). Verified: offline image with `--network none` answers searches; 21,540 documents / 74,055
sections index in seconds.
