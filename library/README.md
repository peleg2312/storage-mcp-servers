# Documentation library (prebuilt, offline)

The whole vendor knowledge the brain uses, packed so a plain `git clone` carries it into the air-gapped
site: `docs-library-<date>.tar.gz.part-*` (45 MB parts, GitHub's file limit), `SHA256SUMS`, `VERSION`,
and `MANIFEST.md` = exactly what is inside (every source with document counts).

Inside the tarball (`docs-library/`):

| | |
|---|---|
| `docs/<vendor>/<product>/...` | the documents themselves: NetApp docs (`.adoc`), NetApp KB articles (`.html`), Dell CSM / CSI / automation docs (`.md`), Dell PDFs, VMware KB pages, bug-tracker exports, KB pointers |
| `docs.db` | the full-text index (SQLite FTS5) with all the text: this is what the search uses |
| `search.py` | search from the shell, standard library only: `python3 search.py search "..."` |
| `mcp_stdio.py` | the same four tools as an MCP server over stdio, standard library only (what `install-vm.sh` registers as `docs-local`) |
| `server.py`, `mcp_auth.py` | the HTTP MCP server used in the container image (needs `fastmcp`) |
| `MANIFEST.md` | what is inside |

## Use it

**On the VM that runs Claude Code** (nothing else needed than python3):
```bash
sh install-vm.sh            # from the repo root: brain + library + MCP server "docs-local" + smoke test
python3 ~/.claude/brain/library/search.py search "scsiblade.san.config.active"
```

**On an OpenShift cluster** (the docs-search HTTP server with the library baked into the image):
```bash
cd docs-search-mcp && sh bundle/build-offline.sh --from-library    # any machine with podman/docker, no internet
# -> work/docs-search-offline-<date>.tar.gz ; then deploy openshift-offline.yaml (see docs-search-mcp/README.md)
```

**Just the files**: `sh library/join.sh /some/dir` extracts everything to `/some/dir/docs-library/`.

## Refresh it (on a machine with internet)

```bash
cd docs-search-mcp
GITHUB_TOKEN=<read-only token> sh bundle/build-offline.sh --from-library --sync   # adds what is new
python3 sync/sync_netapp_kb.py --dest work/docs      # continues the NetApp KB export where it stopped
python3 docs_index.py --docs work/docs --db work/index/docs.db
sh bundle/pack-library.sh                            # rewrites library/ ; commit and push
```
Everything is incremental: re-running only fetches what changed. Sources are one line each in
`docs-search-mcp/sources/*.txt`.

## Coverage notes

- **Dell PowerMax / PowerFlex PDFs, Dell KB, Trident / Harvest bug trackers** are in (synced from a PC;
  Dell's site refuses cloud IPs). Re-run `sync_dell.py`, `sync_dell_kb.py`, `sync_github_issues.py` from a
  PC to refresh them; the CSM issue tracker needs a `GITHUB_TOKEN` run.
- **NetApp KB**: exported at the rate the site asks for (one article per 5 s); the part done so far is in
  `MANIFEST.md` (`kb-*` products). Re-running `sync_netapp_kb.py` continues it. Articles whose Cause /
  Solution needs a NetApp Support login are kept with their public part and flagged "Partial article"
  unless the export ran with `NETAPP_KB_COOKIE`.
- **Login-only Dell documents** (PowerFlex alerts-and-events reference guides, release notes, support matrices,
  security guides): Dell serves a redirect PDF for them even to the sync with cookies. `docs-search-mcp/extra/dell/NEEDED.md`
  lists them with links; download them in a signed-in browser and run `sync/import_extra.py` (RUNBOOK step b2).
- **Not in the library**: Cisco MDS / UCS documentation, PowerMaxOS release notes (not published as PDFs).

Content stays the vendors' copyright, fetched for internal reference. Keep this repo private.
