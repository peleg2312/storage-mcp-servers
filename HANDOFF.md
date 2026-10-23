# Handoff: continuing this project with Claude Code on the PC

Paste this to Claude Code running on the PC (it is also committed as `HANDOFF.md`; say "read HANDOFF.md").
It replaces the cloud session, which could not reach Dell (bot check) nor push to GitHub.

## What this repository is

An offline "brain" for Claude Code on an air-gapped VM for a SAN / storage operations team: Dell PowerMax,
Dell PowerFlex, NetApp ONTAP, NetApp Trident, Dell CSM / CSI, Cisco MDS / UCS, VMware. Two halves:

1. **The documentation library** (`library/`): every vendor document and KB article packed as 45 MB git parts
   plus a SQLite FTS5 full-text index (`docs.db`). Built from `docs-search-mcp/work/docs/<vendor>/<product>/...`
   by `docs-search-mcp/docs_index.py`, packed by `docs-search-mcp/bundle/pack-library.sh`. Served offline by
   `mcp_stdio.py` (stdio MCP server, standard library only) or `server.py` (HTTP, fastmcp) with four tools:
   search_docs, read_chunk, read_document, list_sources. Also `search.py` from the shell.
2. **The brain** (`brain/claude/`): CLAUDE.md (131 lines, imports environment.md / notes.md / tool-map.md),
   23 skills, 8 agents, a PreToolUse hook that blocks write-looking MCP calls (read-only policy), a SessionStart
   hook, the "Peleg As A Service" banner and status line. Installed by `install-vm.sh` (user scope) or
   `install-vm.sh --project <dir>` (one folder only). Reviewed against the Claude Code docs: `brain/ARCHITECTURE.md`.

`RUNBOOK.md` has every command for the PC and the VM. `README.md` is the overview. Keep the repo private
(vendor content). Tests: `cd docs-search-mcp && python3 test_search.py && python3 test_stdio.py && python3 test_sync_dell.py`.

## Where things stand (2026-10-23)

- Library 2026.10.23c: 39,681 files, 21,686 unique documents (identical copies across ONTAP versions are
  folded into aliases, shown as `also_in`). NetApp docs complete (ONTAP, EMS 9.11-9.18, REST, Trident, Harvest),
  Dell CSM docs site complete, Dell PowerMax/PowerFlex public PDFs, PowerMaxOS 10.x Events and Alerts guides,
  ~530 Dell KB articles, ~1,900 NetApp KB articles, Trident/Harvest issue trackers, VMware KB pages.
- **NetApp KB export is unfinished**: about 1,950 of 14,751 articles checked in the chosen areas (SAN, host utilities,
  performance, Trident, MetroCluster, DP, hardware, switches, ASA r2). It is resumable: manifests inside
  `work/docs/netapp/kb-*/` record what is done. Full articles need the kb.netapp.com login cookie.
- **Dell is the gap**: Dell's site blocks cloud addresses and needs sign-in for the best documents, so Dell
  collection runs from this PC with a real browser (`sync/dell_browser.py`, Playwright + a Chrome profile the
  user signs in to once). Not yet obtained: the PowerFlex Alerts and Events Reference Guides (4.5, 4.6, 4.8,
  5.0, 5.1), PowerFlex release notes / support matrices / security guides (26 PDFs listed in
  `docs-search-mcp/extra/dell/NEEDED.md`), the bulk of Dell KB (searches), Info Hub papers, dell/csm issues.
- The user's last run of the collector (before the lib7 fixes) got 14 KB articles and no PDFs; the fixed
  version has only been tested against a local fake of Dell's pages, never against the real site. Expect to
  adapt selectors / waits in `dell_browser.py` after watching one real run.

## Rules the user set

- Read-only toward infrastructure; the brain never changes anything on arrays, switches, vCenter.
- Never put tokens or cookies in files, logs or commits. Cookies go in env vars (NETAPP_KB_COOKIE,
  DELL_KB_COOKIE) or the browser profile (`work/browser-profile`, never committed). The user once pasted a
  GitHub token in chat: make sure it was revoked and a new one is used.
- `docs-search-mcp/work/` is git-ignored except what the user force-adds: `work/docs/dell` is tracked
  (`git add -f`), so Dell collections travel through git; NetApp KB content travels only inside the library parts.
- Commit messages: no model names. Keep `library/` at one version (old parts are removed by pack-library.sh).
- The user wants speed and completeness ("every bug and error" for PowerMax, PowerFlex, CSM/CSI), and asks
  for all Dell KB "like there is for NetApp".

## What to do next, in order

1. `cd docs-search-mcp && source work/venv/bin/activate` (venv has pypdf, cryptography, fonttools,
   browser-cookie3, playwright). If `work/docs` is missing, restore it from the library:
   `sh ../library/join.sh work && mv work/docs-library/docs work/docs && mkdir -p work/index && mv work/docs-library/docs.db work/index/docs.db && rm -rf work/docs-library`.
2. Dell, with the browser collector (watch the first run; fix what Dell's real pages need):
   `python3 sync/dell_browser.py login` (sign in, ENTER), then `python3 sync/dell_browser.py needed`,
   `python3 sync/dell_browser.py kb`, `python3 sync/dell_browser.py infohub`, `python3 sync/dell_browser.py manuals`,
   then `python3 sync/import_extra.py --dest work/docs`. Add queries to `sources/dell-kb-queries.txt` freely.
3. `rm -f work/docs/dell/csm-issues/.issues-state.json; GITHUB_TOKEN=<token> python3 sync/sync_github_issues.py --dest work/docs`
   (dell/csm has ~2,000 issues; the CSI driver repos have issues disabled, that is expected).
4. NetApp KB, continuing where the library stopped (one article per 5 s, resumable, Ctrl-C any time):
   `NETAPP_KB_COOKIE='authtoken=<value from the browser, kb.netapp.com cookie>' python3 sync/sync_netapp_kb.py --dest work/docs --refresh-partial --include on-prem/ontap/da/SAN on-prem/ontap/da/Host-Utilities on-prem/ontap/Perf Cloud/Astra/NetApp_Trident data-mgmt/OTV on-prem/Switches on-prem/ontap/mc on-prem/ontap/DP on-prem/ontap/OHW on-prem/ASAr2`
   (drop `--include` to export every area; it is a multi-day run at NetApp's rate).
5. Checkpoint whenever useful: `python3 docs_index.py --docs work/docs --db work/index/docs.db && sh bundle/pack-library.sh`,
   then from the repo root `git add -A library && git add -f docs-search-mcp/work/docs/dell docs-search-mcp/extra/dell && git commit && git push`.
   `library/MANIFEST.md` lists what is inside; the first line gives unique documents and folded copies.
6. On the VM: `git pull && sh install-vm.sh` (or `--project <dir>`), then `/brain-setup` inside Claude.

## Pitfalls already met

- Dell returns a small PDF "Statement against modern slavery" instead of login-only documents; `is_redirect_pdf()`
  in `sync/sync_dell.py` detects it (text is inside the PDF, needs pypdf). Never index those.
- Dell's HTML manuals (`dell.com/support/manuals/...`) are sign-in gated for the PowerFlex alerts guide; the PDF link
  on those pages points to `dl.dell.com/content/manual<id>...pdf` and needs the browser session (identity-provider
  redirects), not a plain request.
- NetApp KB: Cause / Solution sections need the login cookie; articles saved without it are flagged "Partial article"
  and refreshed by `--refresh-partial`. Sign out of kb.netapp.com when the export is done.
- Same KB saved twice under different names (sync_web vs sync_dell_kb naming): the indexer folds identical text;
  near-identical copies would show twice, so prefer one tool per source.
- zsh treats `#` in commands as arguments; macOS `split` has no `-d`; `shasum -a 256` instead of `sha256sum`;
  `pkill -f` can match your own shell (use an anchored `pgrep -f '^python3 ...'`).
- `git add .` adds nothing under `work/`; use `git add -f docs-search-mcp/work/docs/dell`.
- Index counts: "documents" in `docs_index.py` output counts files; MANIFEST.md gives the unique number.

## Ideas not done yet

- Hybrid retrieval (a local embedding model shipped in the library) behind the same four tools.
- A `dell-alerts` skill that walks the PowerMaxOS 10.x alert ID tables and the PowerFlex SIO/PFX codes once
  the PowerFlex guides are in.
- Cisco MDS / UCS documentation (not published in a crawlable form).
