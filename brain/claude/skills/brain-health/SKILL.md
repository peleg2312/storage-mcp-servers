---
name: brain-health
description: Self-check of the storage brain installation on this VM - which MCP servers answer, docs MCP list_sources versus MANIFEST.md, library version, read-only hook and session-start hook present in settings.json, environment.md and tool-map.md filled, notes.md present, skills and agents installed - as a table with what to fix. Use for "is the brain healthy", after install.sh or git pull, when a tool is missing or an answer looks stale, or when the docs MCP does not respond.
---
# Brain health

Read-only and cheap: one list call per server, local files read with the shell. Fix nothing yourself:
tell him what to run.

## 1. MCP servers
For each server in your tool list (`mcp__<server>__…`): one cheap call - powermax `list_unispheres` /
`list_arrays`, ontap (cluster or SVM list), harvest (any list / metric-name call), mds `list_switches`,
ucsc `list_centrals`, kuparashit (smallest query), Aria (any list), docs `list_sources`. Record:
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

## 3. Hooks and settings (`~/.claude/settings.json`)
- `hooks.PreToolUse` contains `python3 ~/.claude/hooks/block-write-tools.py` with matcher `mcp__.*`
  (the read-only guard) and `hooks.SessionStart` contains `python3 ~/.claude/hooks/session-start.py`.
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
Table: component | status (OK / WARN / FAIL) | detail | fix (command or skill for him: `/brain-setup`,
`sh brain/install.sh`, `claude mcp add …`, edit environment.md). Then the three most useful fixes first.
