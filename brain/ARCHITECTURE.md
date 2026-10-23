# Brain architecture: checked against the Claude Code documentation (October 2026)

What the official docs (code.claude.com/docs: memory, skills, sub-agents, hooks, permissions, mcp,
best-practices) recommend, and where this brain stands. Re-check with `/brain-health` (step 5 runs
`/doctor prompt-audit`).

| Doc guidance | This brain |
|---|---|
| CLAUDE.md under 200 lines, imports do not save context | CLAUDE.md 107 lines + 3 imports (environment, notes, tool map), ~3,300 tokens; no inventories or lists Claude already sees (skills, tool schemas, library contents live in docs-lookup / MANIFEST.md); `/brain-health` warns above ~200 lines total |
| Rules, not prose: enforce with hooks, CLAUDE.md is only context | PreToolUse hook `block-write-tools.py` (matcher `mcp__.*`, exit 2) blocks every write-looking MCP call; allow-list file for false positives |
| PostToolUse hooks add context next to a tool result (`additionalContext`) | `docs-hints.py` (matcher `mcp__.*`): an EMS name, PowerMax SYMAPI alert, PowerFlex SIO code, CONTAP bug or DSA advisory in a live result gets its documented meaning + chunk id beside it, so errors are explained from the docs without a search round trip; only names the library documents (exact EMS heading match, cached name set), at most 4 lines + names per result, each once per session; 0.05 s on a 3,000-line result; 40 / 40 sampled EMS names explained, 0 false hits on 3,000 decoy names (`brain/test_docs_hints.py`) |
| SessionStart hooks inject fresh facts | `session-start.py` prints library version / document count, hook state, read-only mode at every start, resume and compaction |
| Skills: description + `when_to_use` drive auto-triggering (1,536-char cap) | one sentence + 3-4 trigger phrases each; all model-visible descriptions together ~1,600 tokens per turn (was ~2,800); verified by `claude plugin eval` (9/9) |
| `disable-model-invocation` for user-run workflows | brain-setup, brain-health, morning-check, capacity-report, change-review, code-version-check |
| `context: fork` for long, self-contained work | unused-luns, zoning-audit, fabric-health, rdm-inventory (foreground, result returns to the chat) |
| Subagents: short descriptions, `memory`, preload `skills`, least privilege | 8 agents; 7 keep persistent memory (`memory: user`); research agents preload docs-lookup; infra writes are blocked by the hook, not by tool denial (agents still write reports and their memory) |
| Memory: auto memory + versioned project memory; MEMORY.md as an index, topic files read on demand | a catalog: `notes.md` (imported, ≤ 60 lines: names, thresholds, owners) + `notes/<topic>.md` read only when a question touches it; the SessionStart hook lists the topic files with fact counts, so cost per session stays flat as memory grows; auto memory may exist beside it |
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
- **Clean input first.** Most misses traced to ingestion, not ranking: Dell KB pages draw Symptoms / Cause /
  Resolution as styled text (now split into real sections), page chrome (language and country menus, cookie
  banner, feedback forms, PR checklist template, license headers) is dropped, saved "page not found" pages are
  removed, and PDF pages carry their outline headings ("Chapter > Section (page N)").
- **Ranking details that measurably mattered:** versions match with and without `v` (`2.16.2` = `v2.16.2`)
  and lift documents of that exact version; rarity-weighted word coverage (IDF^0.25: "very" or "find" no
  longer weigh like "cpu"); document-type priors (REST API reference, 7-Mode / classic guides, pull requests
  and source code only when the question points there); short plurals (`logs` = `log`). The reply lists
  `unmatched` words so Claude rephrases exactly those.
- **Measured** (`eval_search.py`; hit@1 / hit@5). Sets written blind from random library sections are the
  honest ones (fresh, general); the older sets were written knowing the index:

  | Set | cases | before (Oct 23 morning) | now |
  |---|---|---|---|
  | `retrieval_eval` (tuned) | 45 | 0.71 / 0.78 | 0.89 / 1.00 |
  | `retrieval_heldout` | 20 | 0.60 / 0.65 | 0.90 / 1.00 |
  | `retrieval_hard` (paraphrased, dev) | 50 | 0.68 / 0.82 | 0.72 / 0.86-0.90 |
  | `retrieval_fresh_heldout` (blind, troubleshooting) | 36 | 0.72 / 0.89 (code before the tweaks) | 0.75 / 0.89 |
  | `retrieval_general_heldout` (blind, concepts / best practice) | 34 | - | 0.65 / 0.88 |

- **Bake-off against an off-the-shelf hybrid engine (QMD 2.8.3: BM25 + EmbeddingGemma vectors + LLM query
  expansion + Qwen3 reranker, all local), same cleaned documents, 2,919-document library with every gold
  document, every near miss of both engines and 1,500 random documents:**

  | hit@1 / hit@5 | fresh (blind) | general (blind) | hard | time / query |
  |---|---|---|---|---|
  | this search | **0.72 / 0.92** | **0.62 / 0.88** | **0.72 / 0.86** | 0.2-0.4 s |
  | QMD vectors only | 0.53 / 0.78 | 0.47 / 0.74 | 0.52 / 0.72 | 0.1 s |
  | QMD hybrid (expansion, no rerank) | 0.56 / 0.83 | 0.32 / 0.76 | 0.42 / 0.74 | ~5 s |
  | QMD hybrid + LLM rerank | (0.49 / 0.69 on the tuned set) | - | - | ~28 s (Mac GPU) |
  | this search + QMD vectors fused (RRF 1:1) | 0.72 / 0.94 | 0.62 / 0.91 | 0.72 / 0.90 | +vectors |

- **No embeddings (decided on these numbers).** Fusing vectors adds 2-4 points of hit@5 and nothing at
  hit@1, for ~5 h of embedding per library build on the PC, ~0.5 GB more to ship and a model runtime on the
  VM; Claude's own rephrasing (docs-lookup step 4, `unmatched`) recovers the same cases. Re-run the bake-off
  (`docs-search-mcp/bakeoff/`, steps in `bench.mjs`) if the blind sets start failing on wording rather than on content.
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
  in the context on every turn. Included: `skill-creator` (Anthropic, Apache-2.0, bundled in
  `skills/skill-creator` with pure-Python PyYAML so every script runs offline; ~80 tokens per turn). Worth adding:
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
