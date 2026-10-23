---
name: brain-health
description: Self-check of the storage brain installation on this VM - which MCP servers answer, docs MCP list_sources versus MANIFEST.md, library version, read-only hook and session-start hook present in settings.json, environment.md and tool-map.md filled, notes.md present, skills and agents installed - as a table with what to fix. Use for "is the brain healthy", after install.sh or git pull, when a tool is missing or an answer looks stale, or when the docs MCP does not respond.
when_to_use: Trigger phrases - "is the brain healthy", "/brain-health", "the docs MCP does not answer", "check the brain installation", "why does the read-only hook not run"
disable-model-invocation: true
---
# Brain health

Read-only and cheap: one list call per server, local files read with the shell. Fix nothing yourself:
tell him what to run.

## 1. MCP servers
For each server in your tool list (`mcp__<server>__…`): one cheap call - powermax `list_unispheres` /
`list_arrays`, ontap (cluster or SVM list), harvest (any list / metric-name call), mds `list_switches`,
ucsc `list_centrals`, kuparashit `overview` (snapshot age and warnings), Aria (any list), docs `list_sources`. Record:
reachable · answer time · tool count · the call that failed and its error. Servers named in the
"Sources" table of CLAUDE.md but absent from the tool list = missing (he adds them with `claude mcp add`).
Note which docs server answered (docs-search or docs-local); if neither, test the shell fallback
`python3 ~/.claude/brain/library/search.py sources`.

## 2. Library
- `cat ~/.claude/brain/library/VERSION`; compare with the version line at the top of
  `~/.claude/brain/library/MANIFEST.md` and (if the repo is on this VM) `library/VERSION`.
- Compare `list_sources` (or `search.py sources --json`) with the MANIFEST table in code: every
  vendor/product present on both sides with the same document count; list the differences.
- One real search as a smoke test, e.g. `search_docs("scsiblade.san.config.active", vendor="netapp",
  product="ontap-ems")` must return hits with a chunk id you can `read_chunk`.
- Search quality: `python3 ~/.claude/brain/library/eval_search.py` and `... eval_search.py --cases
  ~/.claude/brain/library/tests/retrieval_heldout.json`: hit@5 should be 0.9 or more on both (the last line
  prints hit@1 / hit@5 / MRR); lower means a damaged or old library, or an old search.py.

## 3. Hooks and settings (`~/.claude/settings.json`)
- `hooks.PreToolUse` has a command ending in `hooks/block-write-tools.py` with matcher `mcp__.*` (the read-only
  guard) and `hooks.SessionStart` one ending in `hooks/session-start.py` (user install: `~/.claude/hooks/`;
  project install: `"$CLAUDE_PROJECT_DIR"/.claude/hooks/`).
- Both files exist in `~/.claude/hooks/` and `python3 -m py_compile` them; `allowed-tools.txt` exists
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

## Output
## 5. Prompt audit (built-in)
Run `/doctor prompt-audit` (Claude Code >= 2.1.283; audits CLAUDE.md, the imported brain files, skills
and agents under `~/.claude/`). Report its findings - contradictions between files, references to tools,
files or commands that do not exist, instructions written for older models - as WARN rows with the
proposed edit; apply nothing (he decides). If the command is unavailable, say so and compare by hand the
rules in CLAUDE.md with the skills that cite them (read-only rule, answer format, notes.md as memory).

## 6. Context size
Imports load at launch and do not save context: `wc -l ~/.claude/CLAUDE.md ~/.claude/brain/environment.md
~/.claude/brain/notes.md ~/.claude/brain/tool-map.md` must stay around 200 lines in total (the docs
recommend < 200 lines per file; `tool-map.md` is the usual offender), notes.md ≤ 60. Over that: WARN with the
file to trim (move notes.md facts most sessions do not need into `notes/<topic>.md`, which is read on demand;
shorten tool-map.md to the tools actually used). A topic file over ~150 lines: split it or drop stale facts.
Project install (`install-vm.sh --project <dir>`): the same files live in `<dir>/.claude/` and `<dir>/CLAUDE.md`;
only the library stays in `~/.claude/brain/library`.

Table: component | status (OK / WARN / FAIL) | detail | fix (command or skill for him: `/brain-setup`,
`sh brain/install.sh`, `claude mcp add …`, edit environment.md). Then the three most useful fixes first.
