# Token efficiency and performance pass (2026-10-30)

Branch `token-perf` (off `fresh-main`). Every change came from a verified audit: 15 area finders, one verifier per
medium/high finding, a completeness critic (259 findings, 230 confirmed), then 14 fixers in isolated worktrees,
each reviewed, then merged. Tests: `sh scripts/run_tests.sh` (one command for every suite plus the seven retrieval
eval sets); budgets: `python3 brain/test_budgets.py`.

## What a session costs now (bytes the model reads; ~4 bytes per token)

| Context item | Before | After | Note |
|---|---|---|---|
| Core CLAUDE.md + notes.md (every session) | 8,063 | 7,482 | duplicated tool names, hook block list and rule repeats removed |
| Plain-chat extra (storage.md + environment + tool-map) | 12,082 | 10,028 | tool-map no longer lists 70 tool names Claude already sees |
| Generated `~/chats/CLAUDE.md` with an unfilled environment.md | 12,154 | 8,207 | the empty template is skipped until it is filled |
| Skill listing (name + description, every turn) | 11,682 | 9,682 | when_to_use merged into description, skill-creator moved to the marketplace (opt-in) |
| Agent descriptions (every turn) | 3,383 | 3,269 | 9 agents |
| Dev plugins installed by default | 7 plugins, 10.6 KB | 4 plugins, ~1.1 KB | pr-review-toolkit alone was 6.8 KB per turn; the rest stay opt-in in the marketplace |
| mds-mcp tools/list | 70 tools, ~60 KB | 27 tools, 25.7 KB | 43 upstream `show_*` tools hidden; every command still reachable via `run_show` |
| powermax-mcp tools/list | 28 tools, 19.0 KB | 26 tools, 18.1 KB | list_unispheres and list_performance_categories folded into neighbours; get_performance takes one `object_id` |
| docs-search HTTP INSTRUCTIONS | 3,291 | 1,260 | one shared text (`docs_text.py`) for HTTP and stdio |
| docs-local tools/list | 2,637 | 2,231 | |
| docs `list_sources` reply | 15,894 | 3,184 | per-vendor product line, `vendor` filter |
| docs `search_docs` reply (8 hits, MCP) | 4,451 | 4,252 | no query echo, `partial` flag, `matched` only when partial |
| databases MCP tools/list | 6,012 | 4,597 | |
| databases `pg_query` default reply (200x5 wide) | 161,763 | 20,110 | 20 KB reply cap, smaller defaults |
| `mongo_find` of 20 wide documents | 17,058,515 | 20,111 | same cap |
| report.py text chart (2 series) | 3,046 | 570 | one sparkline per series; `--text full` restores the plotext chart |
| Per agent spawn | CLAUDE.md hierarchy + up to 25 KB MEMORY.md | 3-line block | `omitClaudeMd`, no `memory: user`; agents answer in ~40 lines and end with a Learned line |

Server output caps that stop one call from costing 15k-100k tokens: ucsc `list_firmware` (grouped, was ~370 KB raw),
`query_class` / `get_object` (`props`, lower limits), `get_events` / `get_audit_log` (`since` window instead of the
whole class), `list_faults` (by_code); powerflex `list_volumes` 500 -> 100 rows and curated fields, `list_devices`
2000 -> 200, events/alerts curated; mds `get_log_events` 200 -> 50 events, `run_show` JSON capped at 24 KB, OBFL and
slow-drain defaults smaller; powermax audit log projected to the useful fields, masking view grouped by volume,
director ports summarized.

## Faster

- docs search: snippet computed only for returned rows, idf cache per connection, url index: the 45-case eval runs in
  2.7 s instead of 4.1 s; ranking byte-identical on all 241 eval queries.
- docs-leads hook: query capped at 30 words (0.54 s -> 0.25 s on a 90-word prompt); Hebrew prompts now get leads.
- ucsc: parallel domain FC health / test_connection / find_wwpn, no N+1 on WWN pools, retry only on dead sessions,
  SDK session auto-refresh (no failed call after 10 idle minutes).
- powermax: parallel volume / port / alert fetches, connect timeout (a dead Unisphere no longer stalls 2 minutes).
- powerflex: connect timeout, one login per token expiry, performance overview sampled once.
- mds: pooled NX-API session (no TLS handshake per call), port_channel_health reads one interface dump per switch.
- Web UI: usage parser reads only appended bytes; `/` command menu cached 1 h instead of 5 min; browser tab polls
  pause while hidden; market snapshot served with ETag/304 instead of 7 MB every 10 minutes.
- install.sh re-run starts `claude` 2-3 times instead of 10.

## Bugs and safety fixes

- Read-only guard: `sudo -u`, `bash -c` / `sh -c` / `eval` / `chroot` wrappers are now inspected; docs MCP searches
  that look like SQL are no longer blocked; project installs no longer report the guard as missing; hook timeouts set.
- databases MCP: multi-statement SQL (`SET TRANSACTION READ WRITE; DELETE ...`) is refused in `pg_query` / `pg_explain`.
- powerflex: read-only check survives HTTP redirects; `get_statistics` parameters visible again (docstring parser
  dropped them); events/alerts envelope of 4.x/5.x recognised.
- powermax: audit log filter names and ordering fixed; `Session.send` guarded; forwarded headers trusted only from
  127.0.0.1.
- ucsc: `post_xml` guarded; pool exhaustion gives a readable error.
- Skills and agents: PowerFlex no longer described as "no MCP" (identify-lun, replication-check, k8s-storage-analyst,
  capacity-planner, morning-check, capacity-report, decommission-check); `troubleshoot_host_latency` (a prompt) no
  longer called as a tool; marketplace registers UCS Central as `ucsc` like the agents' allow lists.
- get-reports.ps1 opens only allow-listed file types; HTML reports served with a sandboxing policy; gate lock revokes
  the session cookie; paas-user remove reports userdel failures; secrets not copied into every user's settings.
- report.py parses 1-9 digit fractional timestamps on Python 3.9; token-report counts each API response once.
- Docs: README, HANDOFF, RUNBOOK, ARCHITECTURE, library and server READMEs match the tree (5 servers, counts, no
  git-bundle step).

## Best practices now encoded in the repo

1. Nothing in always-loaded context that Claude already sees elsewhere: tool names live in tool schemas, product
   tables in `references/` files read on demand, trigger phrases in the skill description only.
2. One place per rule: CLAUDE.md states it, the hook enforces it, skills point to it instead of repeating it.
3. Every MCP tool caps and shapes its output (limits, `props` / `fields`, `since` windows, grouped summaries), and
   the server INSTRUCTIONS stay under Claude Code's 4,096-char limit.
4. Agents start lean (`omitClaudeMd`, explicit tool lists, no persistent memory injection) and return short answers;
   long tables go to `~/storage-reports/`.
5. Plugins are opt-in beyond a small default set; every enabled plugin's descriptions are paid on every turn.
6. Budgets are tested: `brain/test_budgets.py` fails when a core file or a skill/agent listing grows past its cap.
7. Measure before trusting: `brain/claude/tools/token-report.py` shows where a VM's tokens went per tool and per hook.

## Owner decisions (done after the pass, on the owner's go-ahead)

- Root `LICENSE` added (Apache-2.0, matching the vendored Anthropic plugins); README says what it covers.
- `git gc` run on the shared `.git` to drop the 276 MB of tmp_pack garbage and 18 packs.
- Not done, on purpose: moving library parts, images and UI bundles out of git (LFS / Releases) would change the
  air-gapped flow (`git clone` then `install-vm.sh` on the VM) and needs a history rewrite to shrink the clone; keep
  the current flow until the next planned history reset, and then start the new history without the bundle tarballs
  (build them on the PC, copy the tarball to the VM). The 6,614 force-tracked Dell HTML files stay (they travel through
  git by design, HANDOFF.md).
- Still needs the VM: `vmware-mapper` on haiku (run the evals on both models), and copying useful lines from
  `~/.claude/agent-memory/*/MEMORY.md` into `~/.claude/brain/notes/`. The library parts get `docs_text.py` at the next
  re-pack; `install.sh` copies the current server code over the extracted library until then.
