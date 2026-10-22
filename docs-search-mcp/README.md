# docs-search MCP server (read-only)

Gives Claude a searchable **documentation library**: all relevant NetApp documentation, Dell PowerMax and
PowerFlex official documents, curated KB pointers, and your own runbooks. BM25 full-text search
(SQLite FTS5): exact command names, EMS/event names, error text and KB numbers find the right page.
No data leaves the pod at query time. Same bearer-token auth as the other servers.

## What's in the library

| Source | How it gets there | Size (approx.) |
|---|---|---|
| **NetApp**: 28 doc repos from [github.com/NetAppDocs](https://github.com/NetAppDocs): ONTAP 9 (SAN admin, NVMe, data protection...), SAN host config (ESXi, Linux, Windows, AIX), ONTAP tools for VMware 9/10, SnapCenter + VMware plug-in, SnapMirror active sync, MetroCluster, EMS event reference (9.13/9.16/9.17), REST/automation, FLI, AFF/FAS/ASA hardware, ASA r2, technical reports, E-Series, StorageGRID, AIQUM | `sync/sync-netapp.sh` (git, **text only**) | ~20,500 pages, 160 MB text |
| **Dell PowerMax/VMAX**: everything linked from Dell's documentation hubs (product, Unisphere, Solutions Enabler, REST API, SRDF, SnapVX, eNAS, VMware/vVols/VAAI/SRDF-Metro papers) + key papers | `sync/sync_dell.py` crawls the hubs in `sources/dell-sources.txt` (one level, PDFs only) | ~60-80 PDFs |
| **Dell PowerFlex**: the PowerFlex documentation hub (3.6, 4.0, 4.5, 5.0, 5.1: guides, release notes, REST) | same | ~150 documents |
| **KB pointers** (`sources/kb/kb-pointers.md`): verified public KBs (NAA/EUI decoding, LUN detach order, APD/PDL...) with links, not copies | copied by the sync job | 1 file, grow it |
| **Your runbooks** | drop `.md/.txt/.pdf/.html` into `/data/docs/<folder>/<product>/` | - |

`sync-netapp.sh --all` pulls **every** public NetAppDocs repo (~2,000, cloud products included) if you want
everything; the curated list in `sources/netapp-repos.txt` is the SAN/VMware-relevant set.

**Licensing:** the content stays the vendors' copyright. It is fetched from the official sources into your
own volume for internal reference (NetApp's terms allow non-commercial internal use); it is not stored in
this Git repo or redistributed. Dell KBs are linked (KB pointers), not bulk-copied; add individual public KB
pages as `page` lines if you want them offline.

## Tools

| Tool | Purpose |
|---|---|
| `search_docs(query, vendor, product, limit)` | BM25 search; all words first, any-word fallback; snippet with matches marked « » |
| `read_chunk(chunk_id, context)` | the hit in full plus neighbouring sections |
| `read_document(path or url, start, max_sections)` | read a whole document in order (PDFs page by page) |
| `list_sources()` | what is indexed, per vendor/product, and when |

Prompts: `explain_error` (what does this error/event mean, how to fix), `how_to` (documented procedure).
The server instructions tell Claude to search with exact terms, read before answering, cite title + URL,
and state the version a statement comes from.

## Deploy (OpenShift)

```bash
cp .env.example .env && vi .env                 # MCP_AUTH_TOKENS (openssl rand -hex 32)
oc create secret generic docs-search-env --from-env-file=.env
# set <registry>/docs-search-mcp:1.0 in openshift.yaml (3 places), then:
oc apply -f openshift.yaml
oc create job docs-sync-now --from=cronjob/docs-sync     # first fill; afterwards nightly 02:17
oc logs -f job/docs-sync-now -c netapp-docs              # then -c dell-docs-and-index
claude mcp add --transport http docs http://<host>:8000/mcp --header "Authorization: Bearer <token>"
```

The sync job needs HTTPS to `github.com` and to `www.dell.com`, `dl.dell.com`, `www.delltechnologies.com`.
It uses the public `alpine/git` image for the NetApp clone (pin a tag you trust). Re-runs are incremental:
only new/changed documents are downloaded and re-indexed, and the new index is swapped in atomically.

## Run locally

```bash
sh sync/sync-netapp.sh ./data/docs/netapp
python3 sync/sync_dell.py --dest ./data/docs/dell
mkdir -p data/docs/kb && cp sources/kb/*.md data/docs/kb/
python3 docs_index.py --docs ./data/docs --db ./data/index/docs.db
MCP_AUTH_TOKENS=$(openssl rand -hex 32) INDEX_DB=./data/index/docs.db python3 server.py
```

## Tests

`test_search.py` (indexer + all tools + incremental update on a small corpus) and `test_sync_dell.py`
(hub parsing, allowed hosts only, de-duplication, login pages rejected, incremental). Verified on the
full NetApp library: 20,538 documents / 65,594 sections indexed in ~10 s, 108 MB index.
