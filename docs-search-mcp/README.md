# docs-search MCP server (read-only, works fully offline)

Gives Claude a searchable **documentation and bug library** for NetApp ONTAP, Trident, Harvest, Dell PowerMax,
PowerFlex and CSM, plus your own runbooks and saved KB articles. BM25 full-text search (SQLite FTS5): exact
command names, EMS/event names, error text and KB numbers find the right page. **Nothing needs internet at
query time**: the index holds all the text. Same bearer-token auth as the other servers.

## Two ways to run it

| Your cluster | Use | How the content gets in |
|---|---|---|
| **Air-gapped** (no internet) | `openshift-offline.yaml` | build the image `docs-search-offline:<date>` on any machine **with** internet (`bundle/build-offline.sh`), import it like any other image. The library is inside the image. |
| Has internet | `openshift.yaml` | a nightly CronJob syncs and re-indexes on a PVC |

Both also support a **local library**: your own files (runbooks, KB articles saved from the vendor portals,
PDFs) dropped into `/data/local/docs/<folder>/<product>/`, indexed every 30 min, searched together with the
main library (results say `library: main|local`).

## What's in the library

| Source | Sync script | Approx. |
|---|---|---|
| **NetApp docs**: 28 NetAppDocs repos (ONTAP 9 incl. release notes, SAN host config, ONTAP tools for VMware, SnapCenter, MetroCluster, EMS reference 9.13/9.16/9.17, REST, FLI, hardware, ASA r2, TRs, E-Series, StorageGRID, AIQUM) | `sync/sync-git.sh` | 20,500 pages |
| **Trident** docs (incl. "What's new" = fixes per release) + `trident-changelog` (every fix with its issue number) | `sync/sync-git.sh` | 400 pages |
| **Harvest** docs + `harvest-changelog` | `sync/sync-git.sh` | 150 pages |
| **Dell CSM** docs (CSI PowerMax/PowerFlex/PowerScale/PowerStore/Unity, replication, Metro, observability, authorization, release notes, troubleshooting) + **PyU4V** guide | `sync/sync-git.sh` | 800 pages |
| **Bug trackers**: every GitHub issue (open + closed, with all comments/workarounds) of NetApp/trident, NetApp/harvest, dell/csm → products `trident-issues`, `harvest-issues`, `csm-issues` | `sync/sync_github_issues.py` (needs `GITHUB_TOKEN`) | thousands of issues |
| **Dell PowerMax/VMAX** (Unisphere, Solutions Enabler, REST, SRDF, SnapVX, VMware papers) and **PowerFlex** 3.6–5.x (guides, release notes with fixed/known issues) PDFs from Dell's documentation hubs | `sync/sync_dell.py` (`sources/dell-sources.txt`) | 200+ PDFs |
| **KB articles / pages you choose** (NetApp KB, Dell KB, Broadcom KB, any vendor page): one URL per line in `sources/web-pages.txt` or a plain URL list (`URLS=file`) | `sync/sync_web.py` (one page per URL, robots.txt respected; login-only pages are reported, save those from the browser into `extra/`) | as many as you add |
| **KB pointers** (`sources/kb/kb-pointers.md`): verified public KBs with one-line answers | copied | grow it |
| Anything else: `extra/<vendor>/<product>/...` at build time, or the local library at run time | | |

Sources to add are one line each in `sources/git-repos.txt`, `sources/github-issues.txt`, `sources/dell-sources.txt`.
`sync-git.sh --netapp-all` adds every public NetAppDocs repo (~2,000).

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
| `search_docs(query, vendor, product, limit)` | BM25 search over all libraries; all words first, any-word fallback; snippet with matches marked « » |
| `read_chunk(chunk_id, context)` | the hit in full plus neighbouring sections |
| `read_document(path or url, start, max_sections)` | read a whole document in order (PDFs page by page) |
| `list_sources()` | per library: bundle date, documents per vendor/product |

Prompts: `explain_error`, `how_to`. The server instructions tell Claude it is offline, to search with exact
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

`test_search.py` (indexer, all tools, incremental update, two libraries), `test_sync_dell.py` (hub parsing,
allowed hosts, login pages rejected, incremental), `test_sync_issues.py` (pagination, comments, PRs skipped,
incremental). Verified: offline image with `--network none` answers searches; 21,540 documents / 74,055
sections index in seconds.
