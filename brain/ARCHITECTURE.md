# Brain architecture: checked against the Claude Code documentation (October 2026)

What the official docs (code.claude.com/docs: memory, skills, sub-agents, hooks, permissions, mcp,
best-practices) recommend, and where this brain stands. Re-check with `/brain-health` (step 5 runs
`/doctor prompt-audit`).

| Doc guidance | This brain |
|---|---|
| CLAUDE.md under 200 lines, imports do not save context | CLAUDE.md 133 lines + 3 imports (environment, notes, tool map); `/brain-health` warns above ~200 lines total |
| Rules, not prose: enforce with hooks, CLAUDE.md is only context | PreToolUse hook `block-write-tools.py` (matcher `mcp__.*`, exit 2) blocks every write-looking MCP call; allow-list file for false positives |
| SessionStart hooks inject fresh facts | `session-start.py` prints library version / document count, hook state, read-only mode at every start, resume and compaction |
| Skills: description + `when_to_use` drive auto-triggering (1,536-char cap) | all 23 skills carry trigger phrases; longest 747 chars |
| `disable-model-invocation` for user-run workflows | brain-setup, brain-health, morning-check, capacity-report, change-review, code-version-check |
| `context: fork` for long, self-contained work | unused-luns, zoning-audit, fabric-health, rdm-inventory (foreground, result returns to the chat) |
| Subagents: short descriptions, `memory`, preload `skills`, least privilege | 8 agents; 7 keep persistent memory (`memory: user`); research agents preload docs-lookup; infra writes are blocked by the hook, not by tool denial (agents still write reports and their memory) |
| Memory: auto memory + versioned project memory | `notes.md` (imported, versioned, shared) is the system of record; auto memory may exist beside it |
| MCP: project `.mcp.json` for a folder-scoped setup, pre-approved with `enabledMcpjsonServers` | `install-vm.sh --project <dir>` writes `.mcp.json` + `.claude/settings.json`; hooks via `$CLAUDE_PROJECT_DIR`; user install registers `docs-local` with `claude mcp add -s user` |
| Permissions: allow the MCP servers you trust to avoid prompts | `permissions.allow: mcp__<server>` for every server found by `claude mcp list` |
| Status line via `statusLine` command | `paas-statusline.py` (model, folder, context %) |

## Deliberate trade-offs

- **Retrieval is BM25 (SQLite FTS5), not embeddings.** Offline, no GPU, no model download: FTS5 with
  section chunks, near-miss fallback and alias/dedupe gives exact-term hits (EMS names, error codes, KB
  numbers), which is what storage troubleshooting needs. A hybrid (embeddings) layer would need a local
  model shipped in the library; it can be added later behind the same four tools.
- **Read-only by hook, not by permission rules.** Permission rules cannot express "read tools of this
  server only" (deny beats allow per server); a PreToolUse hook can, and its reason reaches Claude.
- **One CLAUDE.md for every project (user scope) by default**, project scope on request (`--project`).
  Both come from the same `brain/claude` tree; the installer rewrites paths.
- **Skills that need the user's pasted output (csm-health, powerflex-troubleshoot) are not forked**:
  a forked subagent cannot ask mid-way.

## Known limits

- `enabledMcpjsonServers` is honoured only after the folder is trusted: the first `claude` start in a
  `--project` folder shows the one-time trust dialog.
- `memory: user` agents write under `~/.claude/agent-memory/<name>/` even in project mode (Claude Code
  decides that location).
- The Cisco MDS / UCS documentation is not in the library (not published in a crawlable form).
