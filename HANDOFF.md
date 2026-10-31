# Handoff: continuing this project with Claude Code on the PC

Paste this to Claude Code running on the PC (say "read HANDOFF.md").

## What this repository is

An offline "brain" for Claude Code on an air-gapped VM for a SAN / storage operations team: Dell PowerMax,
Dell PowerFlex, NetApp ONTAP, NetApp Trident, Dell CSM / CSI, Cisco MDS / UCS, VMware. Two halves:

1. **The documentation library** (`library/`): every vendor document and KB article packed as 45 MB git parts
   plus a SQLite FTS5 full-text index (`docs.db`). Built from `docs-search-mcp/work/docs/<vendor>/<product>/...`
   by `docs-search-mcp/docs_index.py`, packed by `docs-search-mcp/bundle/pack-library.sh`. Served offline by
   `mcp_stdio.py` (stdio MCP server, standard library only) or `server.py` (HTTP, fastmcp) with four tools:
   search_docs, read_chunk, read_document, list_sources. Also `search.py` from the shell.
2. **The brain** (`brain/claude/`): CLAUDE.md (core rules) + `brain/storage.md` (storage rules; imports environment.md / notes.md / tool-map.md),
   skills and agents (count: `ls brain/claude/skills | wc -l`, `ls brain/claude/agents/*.md | wc -l`), scoped tools, a PreToolUse hook that blocks write-looking MCP calls (read-only policy), a SessionStart
   hook, the "Peleg As A Service" banner and status line. Installed by `install-vm.sh` (user scope) or
   `install-vm.sh --project <dir>` (one folder only). Reviewed against the Claude Code docs: `brain/ARCHITECTURE.md`.

`RUNBOOK.md` has every command for the PC and the VM. `README.md` is the overview. The GitHub repository is
public by the user's decision (2026-10-23), although it carries vendor content. All tests: `sh scripts/run_tests.sh` (PY=venv python; skips container-only suites
and prints SKIP; runs the search evals when `docs-search-mcp/work/index/docs.db` exists).

## Where things stand

- Library: version and counts are in `library/VERSION` and `library/MANIFEST.md` (do not copy numbers here).
  Dell (KB, Info Hub, PowerFlex REST API, PDFs), NetApp (docs, 12k+ KB articles), Cisco MDS / NX-OS / NDFC,
  Kubernetes / OpenShift storage, the Python backend stack. Search: `brain/ARCHITECTURE.md`; seven eval sets in
  `docs-search-mcp/tests/` (gates in `scripts/run_tests.sh`).
- Five MCP servers (PowerMax, PowerFlex, UCS Central, docs-search, MDS), all read-only; the PreToolUse hook also
  blocks write-looking calls of other MCP servers and shell changes.
- Team profiles (`brain/teams`: `san`, `nas`): one brain per team as a plugin + knowledge repository, `paas-team use <team>`
  switches a person; multi-user VM on Active Directory accounts with idle-stopped UI instances (`RUNBOOK.md`, `brain/teams/README.md`).
- Web UI (port 3001), multi-user gate (`brain/multiuser/install-gate.sh`) and marketplace are installed by
  `install-vm.sh` (`NO_UI=1` skips the UI).
- Dell PDFs of `NEEDED.md` and the PowerFlex HTML manuals stay refused until the Dell account is linked to the
  company's site (entitlement level 30); then `dell_browser.py needed --wait-login` and `manuals --wait-login`.
- `docs-search-mcp/work/docs` is also tracked in git (Dell collections, force-added). Dropping it from git is the
  owner's decision (not done); binaries in the tree were likewise left alone.
- NetApp KB: re-run the export command in step 4 to retry failed articles; sign out of kb.netapp.com afterwards.

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

- Archives packed on a Mac carry hidden `._*` AppleDouble files (70,005 in the library): GNU tar on Linux unpacks
  them and install-vm.sh stopped halfway. pack-library.sh now packs without macOS metadata; install / join delete
  any `._*`. Test every install change with `sh brain/e2e/run.sh` (Rocky 9 x86_64 + arm64, docker / colima).
- Claude Code's native binary crashes under x86 emulation on Apple silicon: the e2e test runs Claude Code only in
  the arm64 container (the x86 one tests the rest; the installer works without claude and skips registrations).

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

- Red Hat's kubernetes-mcp-server with `--read-only` and a cluster-reader account (live CSI / CSM data).
- A read-only vSphere MCP for live per-LUN path state (kuparashit is a snapshot, Aria has metrics only).
- Claude Code's built-in sandbox for shell commands on the VM (needs bubblewrap; settings `sandbox.enabled`).

- Hybrid retrieval (a local embedding model shipped in the library) behind the same four tools.
- A `dell-alerts` skill that walks the PowerMaxOS 10.x alert ID tables and the PowerFlex SIO/PFX codes once
  the PowerFlex guides are in.
- UCS documentation (not published in a crawlable form).
