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
2. **The brain** (`brain/claude/`): CLAUDE.md (107 lines, imports environment.md / notes.md / tool-map.md),
   24 skills (incl. Anthropic's skill-creator), 8 agents (sonnet), a PreToolUse hook that blocks write-looking MCP calls (read-only policy), a SessionStart
   hook, the "Peleg As A Service" banner and status line. Installed by `install-vm.sh` (user scope) or
   `install-vm.sh --project <dir>` (one folder only). Reviewed against the Claude Code docs: `brain/ARCHITECTURE.md`.

`RUNBOOK.md` has every command for the PC and the VM. `README.md` is the overview. The GitHub repository is
public by the user's decision (2026-10-23), although it carries vendor content. Tests: `cd docs-search-mcp &&
python3 test_search.py && python3 test_stdio.py && python3 test_sync_dell.py && python3 test_sync_issues.py && python3 ../brain/test_hook.py && python3 ../brain/test_docs_hints.py && python3 ../brain/test_docs_leads.py`;
search quality: `python3 eval_search.py` and `--cases tests/retrieval_heldout.json` (hit@5 >= 0.9).

## Where things stand (2026-10-23, night)

- Library 2026.10.23f: 53,111 files indexed. Recovered 786 pages the indexer used to skip (`_index.md` = the CSM
  install guides; KBs named after a quoted title). CODEMAP.md per code repository (`sync/codemap.py`, run by
  sync-git.sh: host tools / commands per function, host paths, functions). Added Kubernetes storage concepts,
  OpenShift storage docs, newer CSI sidecars, goiscsi / gonvme / csmlog / csm-metrics-common / csm-dr, and the
  Unisphere 10.3 HTML manual. Retrieval rebuilt and measured on blind test
  sets (brain/ARCHITECTURE.md): Dell KB sections fixed (Symptoms / Cause / Resolution), page chrome removed,
  PDF outline headings, version matching, `unmatched` hint. Six eval sets in `docs-search-mcp/tests/`
  (`retrieval_fresh_heldout` and `retrieval_general_heldout` are the blind ones); gate: hit@5 >= 0.9 on the
  first two. Bake-off against QMD (local BM25 + vectors + LLM rerank): this search wins on every set;
  no embeddings for now (`docs-search-mcp/bakeoff/` to re-run).
- Docs found unasked: `docs-leads.py` (library leads for every request that names the storage world, incl.
  design / best practice / automation questions) and `docs-hints.py` (meaning of EMS, alerts, codes and free-text
  errors in live MCP results); CLAUDE.md rule 8 says when to search. Seven eval sets incl. a blind best-practice set.
- Brain: memory catalog (notes.md + notes/<topic>.md), kuparashit documented as the snapshot inventory /
  join hub, installer always applies the look and feel, read-only hook catches SQL writes anywhere.
- Dell (done this evening): 1,654 KB articles, 234 Info Hub papers (PowerScale 90, CSM 58, PowerFlex 51,
  PowerMax 39), PowerFlex Rack HTML manual (64 pages; 17 retired "Sorry" pages removed, backup in
  work/backup-2026-10-23/sorry-pages). Unisphere 10.3 HTML manual: overview only (the PDF is in the library).
- **Dell PDFs of NEEDED.md**: refused for entitlement (account level 10 < 30) until the user's Dell account is
  linked to the company's PowerFlex site (the user asked for it); then `dell_browser.py needed --wait-login`.
  The PowerFlex HTML manuals are gated the same way (signed in, the page holds no content): their links
  (5.x release notes, Alerts and Events, security, 5.0 CLI) are in sources/dell-manuals.txt, from KB 000314729;
  after linking run `dell_browser.py manuals --wait-login` too. PowerMax alerts guide link: retired (commented out).
  PowerFlex 5.2 is not released (newest 5.1.0.2, Aug 2026; KB 000461757 in the library).
- **NetApp KB export is unfinished** (5,809 of 14,751 checked at 20:42, ~535 / hour, terminal tab; about
  17 hours left). Resumable; full articles need the kb.netapp.com cookie (NETAPP_KB_COOKIE, never in files).
  When it ends: re-index, eval gates, `LABEL=2026.10.24 sh bundle/pack-library.sh`, commit, push.

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
2. Dell: `python3 sync/dell_browser.py all --wait-login` (sign in inside the window it opens; the run goes on
   in that session; searches are cached a week), then `python3 sync/import_extra.py --dest work/docs`.
3. `GITHUB_TOKEN="$(gh auth token)" python3 sync/sync_github_issues.py --dest work/docs && python3 sync/pr_releases.py
   --dest work/docs` (Trident / Harvest issues; Dell CSM / CSI pull requests and their first release tags).
4. NetApp KB, continuing where the library stopped (one article per 5 s, resumable, Ctrl-C any time):
   `NETAPP_KB_COOKIE='authtoken=<value from the browser, kb.netapp.com cookie>' python3 sync/sync_netapp_kb.py --dest work/docs --refresh-partial --include on-prem/ontap/da/SAN on-prem/ontap/da/Host-Utilities on-prem/ontap/Perf Cloud/Astra/NetApp_Trident data-mgmt/OTV on-prem/Switches on-prem/ontap/mc on-prem/ontap/DP on-prem/ontap/OHW on-prem/ASAr2`
   (drop `--include` to export every area; it is a multi-day run at NetApp's rate).
5. Checkpoint: `sh sync/sync-git.sh work/docs && python3 docs_index.py --docs work/docs --db work/index/docs.db`,
   both eval_search checks, `sh bundle/pack-library.sh`, then from the repo root
   `git add -A library && git add -u docs-search-mcp/work/docs/dell && git add -f docs-search-mcp/work/docs/dell/kb
   docs-search-mcp/work/docs/dell/infohub-* docs-search-mcp/work/docs/dell/*/manual-* docs-search-mcp/extra/dell`
   (never `git add -f` the whole dell folder: the code clones carry their own .git), commit, push.
6. On the VM: `git pull && sh install-vm.sh` (or `--project <dir>`; add `--login-banner` for the banner at
   every login), then `/brain-setup` inside Claude.

## Pitfalls already met

- Dell returns a small PDF "Statement against modern slavery" instead of login-only documents; `is_redirect_pdf()`
  in `sync/sync_dell.py` detects it (text is inside the PDF, needs pypdf). Never index those.
- Dell's HTML manuals (`dell.com/support/manuals/...`) are sign-in gated for the PowerFlex alerts guide; the PDF link
  on those pages points to `dl.dell.com/content/manual<id>...pdf` and needs the browser session (identity-provider
  redirects), not a plain request.
- dell_browser outside the US: en-us pages set the `lwp=c=us` cookie, the IP sends en-us to the country site
  (he-il), and Chrome caches both 301s -> ERR_TOO_MANY_REDIRECTS on the support home. `unloop()` clears the
  cookie and the cache at every start.
- Dell's sign-in cookies (DellCEMSession, di_dwa, dci_jwt) are session cookies: Chrome drops them when the
  window closes. `login` copies them to `work/browser-profile/session-cookies.json` (0600, git-ignored) and every
  run restores them. Run `login` from a terminal and press ENTER, or close the window; then run the other commands.
- `dl.dell.com` answering "Denied: Invalid Access Level U:10 =a:30" = signed in, but the Dell account is not
  entitled (level 30 = linked to the company's site / products). Only the account owner can fix that (My Account
  -> link site ID); then re-run `needed`. All 26 PDFs of NEEDED.md need level 30.
- Check `work/docs` against the library before indexing: a stale `work/docs` (older than `library/VERSION`)
  silently drops what the library has. Merge with `rsync -a work/docs-library/docs/ work/docs/` after join.sh.
- `!cmd` in Claude Code has no keyboard: `read -s` for a cookie fails there; use a real terminal tab.
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
