# Brain architecture: checked against the Claude Code documentation (October 2026)

What the official docs (code.claude.com/docs: memory, skills, sub-agents, hooks, permissions, mcp,
best-practices) recommend, and where this brain stands. Re-check with `/brain-health` (step 5 runs
`/doctor prompt-audit`).

| Doc guidance | This brain |
|---|---|
| Coding rules (think first, simplicity, surgical changes, checkable goals; after Karpathy's notes) live in `brain/coding.md`, read on demand by code work only: storage chats pay one pointer line |
| CLAUDE.md under 200 lines, imports do not save context | core CLAUDE.md 77 lines + `notes.md` import (7.5 KB, ~1,900 tokens every session); storage rules + environment + tool map (~2,500 tokens, environment left out while it is the blank template) only in plain chats, via the generated `~/chats/CLAUDE.md`; no inventories or lists Claude already sees (skills, tool schemas, library contents live in docs-lookup / MANIFEST.md); `/brain-health` checks two line budgets (core, plain chat) |
| Rules, not prose: enforce with hooks, CLAUDE.md is only context | PreToolUse hook `block-write-tools.py` (matcher `mcp__.*|Bash`, exit 2) blocks write-looking MCP calls and infrastructure shell commands, and asks before oc / kubectl / helm / curl / systemctl changes; allow-list file for false positives |
| PostToolUse hooks add context next to a tool result (`additionalContext`) | `docs-hints.py` (matcher `mcp__.*`): an EMS name, PowerMax SYMAPI alert, PowerFlex SIO code, CONTAP bug or DSA advisory in a live result gets its documented meaning + chunk id beside it, so errors are explained from the docs without a search round trip; only names the library documents (exact EMS heading match, cached name set), at most 4 lines + names per result, each once per session; 0.05 s on a 3,000-line result; 40 / 40 sampled EMS names explained, 0 false hits on 3,000 decoy names. Free-text errors (`desc = ...`, `error: ...`, `failed: ...`): the longest fixed run of words, shortened until found, points at the doc / KB or the CSI function raising it (`brain/test_docs_hints.py`) |
| UserPromptSubmit hooks add context for a request | `docs-leads.py`: every request that names the library's world (vendor, product or storage term - the product names are read from the library - or a pasted identifier) gets up to 4 matching documents (title :: section, chunk id) before Claude answers; silent otherwise. Measured: fires on 215 / 241 test questions with the right document among the leads in 189 of them (88 %); fires on 0 / 25 unrelated requests ("yes", "center a div", "summarize this meeting for my manager"); ~150 tokens when it fires, 0.14 s |
| SessionStart hooks inject fresh facts | `session-start.py` prints library version / document count, environment and memory state at every start, resume and compaction; the guard line only when the guard is not configured |
| Skills: `description` (with its trigger phrases) drives auto-triggering (1,536-char cap) | one sentence + 3-4 trigger phrases inside `description`; 27 skills, 11.6 KB of frontmatter together (~2,900 tokens per turn); verified by `claude plugin eval` (9/9) |
| `disable-model-invocation` for user-run workflows | brain-setup, brain-health, morning-check, capacity-report, change-review, code-version-check |
| `context: fork` for long, self-contained work | unused-luns, zoning-audit, fabric-health, rdm-inventory (foreground, result returns to the chat) |
| Subagents: short descriptions, preload `skills`, least privilege | 9 agents (8 storage + `Explore`, haiku); the 8 storage agents have `omitClaudeMd` (3-line read-only block; needs Claude Code >= 2.1.271) and end with a Learned line the parent files per rule 6; research agents preload docs-lookup; each agent has only its own MCP servers (`tools` / `disallowedTools`); infra writes are blocked by the hook (agents still write reports) |
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
  section x3, text x1) x coverage² x (1 + 1.5 x coverage in title / heading) x word proximity x question
  type = page type (a "what is / why / should I" question prefers concept / overview pages, "how to /
  configure" task pages; x1.3) x 0.5 for source code; at most 2
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
- **Oct 24: question type, title weight, proximity** (chosen on the dev sets, confirmed on the held-out ones:
  all 7 sets mean hit@1 0.72 -> 0.75, MRR 0.80 -> 0.83; held-out MRR 0.792 -> 0.816). Tried and dropped:
  concept pages by title, everyday-verb synonyms (neutral), document-level score aggregation (worse).
  Remaining misses are paraphrases far from the docs' words (in the candidates, ranked 11-47).
- **No wasted result slots** (Oct 24): the same page in another version or copy (same title and section,
  version numbers ignored) is one result, the others listed in `also_in` by path (10% of slots were such
  repeats: Trident 23.07-25.10, CSM v1-v3, PowerFlex API versions); Dell KB "Affected Products" / "Article
  Properties" and manual "Table of Contents" sections are dropped at indexing (keyword bait, no answers).
  Docs leads are limited to the vendor of a product the request names (a FastAPI question no longer gets
  ONTAP REST pages).
- **The MCP answer itself** (Oct 24, night): field weights, coverage exponent and candidate pool were swept
  (all at their best within one question; pool cut 300/400 -> 100/150 for 35% faster searches, same scores).
  Replies are 13-25% smaller (no internal score, path only without url, no title repeated in the snippet,
  inline HTML stripped from Markdown) and carry `by_product` (where the strong candidates are: the next
  filter). The server instructions tell Claude to send 2-3 rephrasings in parallel when a search misses:
  the model is the paraphrase engine, no embeddings needed.
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
  a quoted error message lands on the function that raises it. Each repository also has a generated
  `CODEMAP.md` (host tools each function runs - drv_cfg, mount, mkfs, nvme, iscsiadm, multipath -, host paths,
  every file's functions) so "how does the driver do X" starts from the architecture; questions saying
  code / function / implementation rank source files first.

## Packaging and plugins

- **Installer, not a marketplace plugin, delivers the brain.** A plugin cannot carry CLAUDE.md, the
  editable environment / notes files, the banner or the library, and would rename every skill
  (`/zoning-audit` -> `/storage-brain:zoning-audit`). `brain/claude/.claude-plugin/plugin.json` + `.mcp.json`
  only let the same folder load with `--plugin-dir` for `claude plugin validate` and `claude plugin eval`
  (`brain/claude/evals/`: skill-triggering cases, docs-local mocked).
- **Third-party plugins: curated.** Every enabled plugin's skill / agent / command descriptions sit in the
  context on every turn. Included: the 7 plugins `install.sh` installs from
  `brain/plugins` (marketplace `brain-dev`): pr-review-toolkit, feature-dev, commit-commands, security-guidance,
  pyright-lsp, mcp-server-dev, dev-discipline. The other 8 in `brain/plugins` (chrome-devtools, hookify,
  plugin-dev, session-report, frontend-design, ui-ux-pro-max, explanatory-output-style, learning-output-style)
  are available, not enabled; `skill-creator` is opt-in from `brain/marketplace/skills`. Not useful here: anything needing internet (context7), code-review (needs gh).
  Worth adding: `grafana-mcp` only if Harvest feeds an internal Grafana. Offline install: clone the
  marketplace repo on the PC, copy it over, `/plugin marketplace add <path>`.

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
- `omitClaudeMd` on the storage agents needs Claude Code >= 2.1.271; agents do not keep their own memory.
- The Cisco MDS / UCS documentation is not in the library (not published in a crawlable form).
