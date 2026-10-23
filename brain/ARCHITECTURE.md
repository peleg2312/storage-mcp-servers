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

## Retrieval (measured, October 2026)

Design, from Anthropic's guidance (contextual retrieval; agentic search over a vector index for Claude
Code; few high-signal tools) and measured with `docs-search-mcp/eval_search.py`:

- **Agentic lexical search, not a vector database.** Claude issues several targeted searches and reads the
  hits (the docs-lookup skill is the playbook); the tools make each search precise. Exact strings (EMS names,
  error text, KB / CONTAP / DSA numbers, SIO codes) are what storage troubleshooting turns on.
- **Contextual index.** The FTS title column of every chunk carries the document title plus its vendor,
  product, folders and file name: a page titled "Troubleshooting" under csm/.../replication/ or a PDF titled
  "pdf" is found by where it sits (the cheap, LLM-free form of contextual BM25).
- **Ranking.** Candidates = chunks with every word group + best any-word chunks; score = BM25 (title x6,
  section x3, text x1) x coverage² x (1 + coverage in title / heading) x 0.5 for source code; at most 2
  chunks per document; storage synonyms (Isilon / PowerScale / OneFS, ScaleIO / VxFlex / PowerFlex, VMAX /
  Symmetrix / PowerMax, RDP, SRDF, air-gapped / offline ...); "quoted" text is required; `matched` tells
  Claude how many query words a hit holds.
- **Measured** (45 tuned cases `tests/retrieval_eval.json`, 20 untuned `tests/retrieval_heldout.json`):

  | | hit@1 | hit@5 | MRR |
  |---|---|---|---|
  | before, tuned set | 0.71 | 0.78 | 0.746 |
  | after, tuned set | 0.91 | 0.98 | 0.941 |
  | before, held-out | 0.60 | 0.65 | 0.618 |
  | after, held-out | 0.90 | 1.00 | 0.950 |

- **No embeddings (decided on the numbers).** With hit@5 at 0.98-1.00 the headroom a local embedding model
  could add is small, while it would add a model file, numpy (not on the VM) and a second index. Revisit
  only if the eval sets, grown from real questions that failed, show semantic misses.
- **Bug knowledge.** Trident / Harvest issue trackers; for Dell (issues disabled) every merged / open PR of
  the CSM / CSI repos with the issues it names and its **first release tag** (`sync/pr_releases.py`, from
  git history), so "fixed in which version / am I affected" has an exact answer.
- **Source code** of the CSI drivers, array clients and Kubernetes CSI sidecars, one section per function:
  a quoted error message lands on the function that raises it.

## Packaging and plugins

- **Installer, not a marketplace plugin, delivers the brain.** A plugin cannot carry CLAUDE.md, the
  editable environment / notes files, the banner or the library, and would rename every skill
  (`/zoning-audit` -> `/storage-brain:zoning-audit`). `brain/claude/.claude-plugin/plugin.json` + `.mcp.json`
  only let the same folder load with `--plugin-dir` for `claude plugin validate` and `claude plugin eval`
  (`brain/claude/evals/`: skill-triggering cases, docs-local mocked).
- **Third-party plugins: curated, not "everything".** Every enabled plugin's skill / agent descriptions sit
  in the context on every turn. Worth adding on the VM: `skill-creator` (team writes / tests skills offline);
  `grafana-mcp` only if Harvest feeds an internal Grafana (live ONTAP performance). Not useful here: dev
  workflow plugins (code-review, feature-dev, commit-commands...), anything needing internet (context7).
  Offline install: clone the marketplace repo on the PC, copy it over, `/plugin marketplace add <path>`.

## Deliberate trade-offs

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
