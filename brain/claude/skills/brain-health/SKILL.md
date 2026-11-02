---
name: brain-health
description: Self-check of the brain installation: MCP servers answer, docs MCP list_sources vs MANIFEST.md, library version, hooks in settings.json, environment.md / tool-map.md / notes.md, skills and agents installed, the team (clone in sync, plugin on, MCP servers filled in); a table with what to fix. Use for "is the brain healthy", after install.sh or git pull, a missing tool, a stale answer, or an unresponsive docs MCP.
disable-model-invocation: true
---
# Brain health

Read-only and cheap: one list call per server, local files read with the shell. Fix nothing yourself:
tell the user what to run.

## 1. MCP servers
For each server in your tool list (`mcp__<server>__…`, or `mcp__plugin_paas-brain-<team>_<server>__…` when the team plugin carries it): one cheap call - powermax `test_connection` / powerflex `list_systems` /
`list_arrays`, ontap (cluster or SVM list), harvest (any list / metric-name call), mds `list_switches`,
ucsc `list_centrals`, kuparashit `overview` (snapshot age and warnings), Aria (any list), docs `list_sources`. Record:
reachable · answer time · tool count · the call that failed and its error. Servers named in the
"Sources" table of CLAUDE.md but absent from the tool list = missing (the user adds them with `claude mcp add`).
Note which docs server answered (docs-search or docs-local); if neither, test the shell fallback
`python3 ~/.claude/brain/library/search.py sources`.

## 2. Library
- `cat ~/.claude/brain/library/VERSION`; compare with the version line at the top of
  `~/.claude/brain/library/MANIFEST.md` and (if the repo is on this VM) `library/VERSION`.
- `list_sources` (or `search.py sources --json`; takes a vendor filter) returns `by_vendor: {vendor: "product (docs), ..."}`:
  compare it with the MANIFEST table: every vendor/product on both sides with the same document count; list the differences.
- One real search as a smoke test, e.g. `search_docs("scsiblade.san.config.active", vendor="netapp",
  product="ontap-ems")` must return hits with a chunk id you can `read_chunk`.
- Search quality: `python3 ~/.claude/brain/library/eval_search.py` and `... eval_search.py --cases
  ~/.claude/brain/library/tests/retrieval_heldout.json`: hit@5 should be 0.9 or more on both (the last line
  prints hit@1 / hit@5 / MRR); lower means a damaged or old library, or an old search.py.

## 3. Hooks and settings (`~/.claude/settings.json`)
- `hooks.PreToolUse` has a command ending in `hooks/block-write-tools.py` with matcher `mcp__.*|Bash` (the read-only
  guard for MCP tools and shell commands; test: `echo '{"tool_name":"Bash","tool_input":{"command":"scli --add_volume"}}'
  | python3 ~/.claude/hooks/block-write-tools.py` must exit 2; matcher `mcp__.*` alone = old install, re-run it), `hooks.PostToolUse` one ending in `hooks/docs-hints.py` (docs meaning of EMS / alerts / errors in
  live results), `hooks.UserPromptSubmit` one ending in `hooks/docs-leads.py` (library leads per request) and `hooks.SessionStart` one ending in `hooks/session-start.py` (user install: `~/.claude/hooks/`;
  project install: `"$CLAUDE_PROJECT_DIR"/.claude/hooks/`).
- The four files exist in `~/.claude/hooks/` and `python3 -m py_compile` them; docs-hints check:
  `echo '{"session_id":"bh","tool_name":"mcp__x__y","tool_response":"wafl.vol.full"}' | python3 ~/.claude/hooks/docs-hints.py`
  prints the wafl.vol.full meaning (nothing = library missing on this VM); `allowed-tools.txt` exists
  (list its non-comment entries: each one is a tool the guard skips - are they really read-only?).
- The session-start lines appeared at the top of this session (library version, document count,
  environment status). If not, the hook is not wired: the user re-runs `sh brain/install.sh`.
- `permissions.allow` lists `mcp__<server>` for each server added by hand and `mcp__plugin_paas-brain-<team>_<server>` for each of the team's (paas-team writes those at a switch; otherwise every call prompts).
- Never test the guard by calling a write tool.

## 4. Brain files (`~/.claude/`)
`CLAUDE.md` present and identical to the repo copy (if the repo is here: `cmp`); `brain/environment.md`
filled (arrays, versions, fabrics, thresholds - count empty table rows and `__` placeholders);
`brain/tool-map.md` generated (not the "Not generated yet" stub); `brain/notes.md` present;
`skills/*/SKILL.md` and `agents/*.md` counts equal the repo's; the banner / status line files exist.

## 5. Prompt audit (built-in)
Run `/doctor prompt-audit` if this Claude Code has it (audits CLAUDE.md, the imported brain files, skills
and agents under `~/.claude/`). Report its findings - contradictions between files, references to tools,
files or commands that do not exist, instructions written for older models - as WARN rows with the
proposed edit; apply nothing (the user decides). If the command is unavailable, say so and compare by hand the
rules in CLAUDE.md and brain/storage.md with the skills that cite them (read-only rule, answer format, notes.md as memory).

## 6. Context size
Two budgets: `wc -l ~/.claude/CLAUDE.md ~/.claude/brain/notes.md` (every session) <= 120 lines; plus
`storage.md environment.md tool-map.md` (plain chats, generated ~/chats/CLAUDE.md) <= 250 lines in total; notes.md <= 60.
Over that: WARN with the
file to trim (move notes.md facts most sessions do not need into `notes/<topic>.md`, which is read on demand;
shorten tool-map.md to the tools actually used). A topic file over ~150 lines: split it or drop stale facts.
Project install (`install-vm.sh --project <dir>`): the same files live in `<dir>/.claude/` and `<dir>/CLAUDE.md`;
only the library stays in `~/.claude/brain/library`.

## 7. Team (when `~/.claude/brain/team` exists)
`paas-team` (in PATH, else `~/.claude/tools/paas-team`): the active team, its remote and the sync state (`in sync`, `N ahead,
M behind`, or a push failure with its reason from `.git/paas-push-failed`); `paas-team needs-refresh` says whether the clone
holds a newer plugin than the one applied. `claude plugin list`: `paas-brain-<team>` enabled, the other teams' plugins
disabled. `paas-team show <team> --json`: every MCP server with `configured: false` is still on its HOST / TOKEN placeholders
and is not connected; name them. Where `docs-local` bridges to the VM's `docs-search` (its env in the plugin's `.mcp.json`
has `PAAS_DOCS_URL`), `curl -sk <that url without /mcp>/health` must answer. Rows: WARN for a push failure, a pending
refresh or a placeholder server; FAIL for a disabled plugin or a team folder that is not a git clone.

## Output
Table: component | status (OK / WARN / FAIL) | detail | fix (command or skill for the user: `/brain-setup`,
`sh brain/install.sh`, `claude mcp add …`, edit environment.md). Then the three most useful fixes first.
