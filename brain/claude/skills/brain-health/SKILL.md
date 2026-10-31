---
name: brain-health
description: Self-check of the brain installation: MCP servers answer, docs MCP list_sources vs MANIFEST.md, library version, hooks in settings.json, environment.md / tool-map.md / notes.md, skills and agents installed; a table with what to fix. Use for "is the brain healthy", after install.sh or git pull, a missing tool, a stale answer, or an unresponsive docs MCP.
when_to_use: Trigger phrases - "is the brain healthy", "/brain-health", "the docs MCP does not answer", "check the brain installation", "why does the read-only hook not run"
disable-model-invocation: true
---
# Brain health

Read-only and cheap: one list call per server, local files read with the shell. Fix nothing yourself:
tell him what to run.

## 1. MCP servers
For each server in your tool list (`mcp__<server>__…`): one cheap call - powermax `test_connection` / powerflex `list_systems` /
`list_arrays`, ontap (cluster or SVM list), harvest (any list / metric-name call), mds `list_switches`,
ucsc `list_centrals`, kuparashit `overview` (snapshot age and warnings), Aria (any list), docs `list_sources`. Record:
reachable · answer time · tool count · the call that failed and its error. Servers named in the
"Sources" table of CLAUDE.md but absent from the tool list = missing (he adds them with `claude mcp add`).
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
  environment status). If not, the hook is not wired: he re-runs `sh brain/install.sh`.
- `permissions.allow` lists `mcp__<server>` for each connected server (otherwise every call prompts).
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
proposed edit; apply nothing (he decides). If the command is unavailable, say so and compare by hand the
rules in CLAUDE.md and brain/storage.md with the skills that cite them (read-only rule, answer format, notes.md as memory).

## 6. Context size
Two budgets: `wc -l ~/.claude/CLAUDE.md ~/.claude/brain/notes.md` (every session) <= 120 lines; plus
`storage.md environment.md tool-map.md` (plain chats, generated ~/chats/CLAUDE.md) <= 250 lines in total; notes.md <= 60.
Over that: WARN with the
file to trim (move notes.md facts most sessions do not need into `notes/<topic>.md`, which is read on demand;
shorten tool-map.md to the tools actually used). A topic file over ~150 lines: split it or drop stale facts.
Project install (`install-vm.sh --project <dir>`): the same files live in `<dir>/.claude/` and `<dir>/CLAUDE.md`;
only the library stays in `~/.claude/brain/library`.

## Output
Table: component | status (OK / WARN / FAIL) | detail | fix (command or skill for him: `/brain-setup`,
`sh brain/install.sh`, `claude mcp add …`, edit environment.md). Then the three most useful fixes first.
