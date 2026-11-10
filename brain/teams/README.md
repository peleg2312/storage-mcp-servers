# brain/teams: team profiles

One brain per team, switched in seconds. A team profile decides what a member's Claude gets: the persona ("who you
work for"), the storage rules, the skills, the agents, the MCP servers it starts with, and a knowledge folder the
team shares. Everyone keeps their own Linux account (Active Directory on the multi-user VM), their own chats and
their own audit trail; the team is a profile on top of the person, not a shared login.

| Team | Rules | Skills | Agents | Live MCP |
|---|---|---|---|---|
| `san` (default) | `brain/claude/brain/storage.md` | all of `brain/claude/skills` (28) | all of `brain/claude/agents` (9) | docs-local, powermax, powerflex, ontap, harvest, mds, ucs-central |
| `nas` | `brain/teams/nas/storage-nas.md` (installed as `storage.md`) | 12 shared + 7 NAS: nas-morning-check, share-access-check, export-policy-check, quota-report, nas-replication-check, smartconnect-check, vast-view-check | Explore, docs-researcher, ontap-analyst, nas-analyst | docs-local, ontap, harvest. **No PowerScale or VAST MCP exists yet**: those skills work from output the person pastes (isi, VAST CLI / VMS) and the docs library, and say so |
| `flashback` | `brain/teams/flashback/storage-flashback.md` (backup and restore rules B1-B9) | 11 shared + 11 backup: backup-morning-check, commvault-job-check, commvault-infra-check, backup-coverage, restore-plan, restore-drill, veeam-job-check, oadp-backup-check, oadp-restore-hosted-cluster, snapshot-protection-check, and its own docs-lookup | Explore, docs-researcher, commvault-analyst, veeam-analyst, oadp-analyst, storage-protection-analyst | docs-local, commvault-env1/2/3 (Commvault's official MCP server, one per CommCell), ontap, powermax, powerflex; OADP through `oc` read commands; **no Veeam MCP** (pasted PowerShell). Its own library `flashback` (Commvault 11.36-11.44, Veeam 13, OADP 1.4-1.6, HyperShift, Velero, NetApp / Dell data protection): `docs-search-mcp/sources/flashback/build-library.sh` |

## Definition: `brain/teams/<team>/team.json`

```json
{"name": "nas", "title": "NAS / file storage", "description": "...",
 "persona": "persona.md", "rules": "storage-nas.md", "environment": "environment.md",
 "skills": ["brain-setup", "docs-lookup", "share-access-check", "..."],   "agents": ["Explore", "nas-analyst"],
 "mcp": ["docs-local", "ontap", "harvest"]}
```
`library` (optional): the team's own documentation library instead of the general one (see "A team with its own library").
`skills` / `agents`: names, looked up in `brain/teams/<team>/skills|agents` first, then in `brain/claude/skills|agents`
(so a team adds its own and reuses the shared ones), or `"all"`. File paths are relative to the team folder, or to the
repository when they start with `brain/`. A new team = a folder with `team.json` and `persona.md`; `python3
brain/test_budgets.py` then checks its budgets (rules + environment + tool map under 12 KB, skill frontmatter under
10.5 KB, agents under 3.6 KB) and `python3 brain/test_teams.py` builds it.

## What gets built

`python3 brain/plugin/build.py <out> --team nas` builds the plugin `paas-brain-nas/` (skills, agents, hooks with
`hooks.json`, `docs-local`, plus `brain/` with the templates a new team repository starts from: CLAUDE.md, persona.md,
storage.md, coding.md and environment / tool-map / notes, and `team.json` with the resolved lists). `python3 brain/teams/publish.py nas --to <dir|git-url>` wraps it into the
**team repository**:

```
.claude-plugin/marketplace.json      paas-brain-nas/        knowledge/{notes,captures,incidents}/  knowledge/tool-map.md
knowledge/notes.md, environment.md   rules/{main,persona,storage,coding}.md   README.md
```
**One copy of everything, inside the plugin.** Claude Code installs only the plugin folder (`paas-brain-nas/`), so the team's
definition and servers live there and nowhere else: `paas-brain-nas/team.json` (lists, version, the `remote` a first session
clones from, `library`, and `mcp_pending`: servers still without an address or token) and `paas-brain-nas/.mcp.json` (the
connected servers, the only place their address and token are). The knowledge does not travel in the plugin: the plugin's
session-start hook clones the whole repository (knowledge, rules) from that `remote`. A repository from before this layout
(`mcp.json` and `team.json` at its root) is moved into the plugin by the next `publish.py` or team editor save.
**The team's rules live in its repository, next to its knowledge.** `rules/` is created from the brain's templates by the first
publish and is the team's own from then on: `main.md` (the golden rules, imported by every member's `~/.claude/CLAUDE.md`),
`persona.md`, `storage.md`, `coding.md`. Nothing writes into an existing file there: a later publish keeps the team's text and
only reports that the brain's template is newer (`git diff --no-index` shows what changed), `paas-team` links the files into
`~/.claude/brain` instead of copying them, the installers skip a rule file that is such a link, and the notes hook never commits
`rules/`. Claude cannot change them either: the read-only guard blocks its Edit / Write and shell writes there (a safety net, not
a sandbox). People change the rules in the repository (commit and push; protect `rules/` in GitLab for review) or with the Brain
tab's team editor; every member gets the change at the next session start. `check.py` keeps them short (main.md 120 lines,
persona.md 30, storage.md 150, coding.md 60) and free of secrets.
One git repository per team, in GitLab: `python3 brain/teams/publish.py nas --to git@gitlab.example.com:storage/brain-nas.git`
(clone, rebuild the plugin, commit, push; the url is recorded as the team's remote). Members' brains push their notes,
captures and incidents into `knowledge/`. The repository also carries `bin/paas-team`, so a clone of it is a complete install source: the standard Claude
Code way is the whole install (the plugin sets the team up at its first session; without GitLab, add the copied clone's folder
as the marketplace):

```sh
claude plugin marketplace add <url> && claude plugin install paas-brain-nas@paas-brain-nas
```
At the first session the plugin's session-start hook sets the team up itself (`bin/paas-team bootstrap`): it clones the
team repository recorded in the plugin's `team.json` as `~/.claude/brain/teams/nas`, links the memory files and the team's
`rules/` into it (main.md, persona.md, storage.md, coding.md) with one import line in your `~/.claude/CLAUDE.md`,
and copies `paas-team` to `~/.claude/tools`. From then on every note is committed and pushed to the team repository like on
the VM; `git clone` is not needed. When the repository is unreachable, the hook prints the persona and rules as context
instead and tries again next session. Plugins stay read-only content in Claude Code's cache; the hook is what lets this one
contribute.

## GitLab access from the VM

Nobody signs in to GitLab on the VM. Root stores one project (or group) access token per GitLab host with `paas-user git-token
<host>` (role Developer, scope write_repository); `paas-user provision` puts the shared credential helper
(`/opt/paas/bin/paas-git-credential`) into every account's git config, so the notes hook's pushes, `paas-team` and the Brain
tab's commits, and the docs service's pulls all authenticate with it (https urls). A person's own helper, listed first, wins.
Commits carry the person (`<login>@<vm>`, or their own git identity when configured), so GitLab history says who wrote each
note. A failed push leaves its reason in `.git/paas-push-failed`; `--sync` prints it, so the Team tab and session start show it.
Laptops use the person's own GitLab login.

## MCP servers per team

Each of the team's servers is in exactly one place in the plugin. At the first publish every server the team starts with
gets its catalog shape with HOST / TOKEN placeholders in `team.json`'s `mcp_pending`; the Brain tab's team editor fills in
the address and token, and a complete server moves into the plugin's `.mcp.json` (`{"mcpServers": {"powermax": {"type":
"http", "url": "http://...:8000/mcp", "headers": {"Authorization": "Bearer ..."}}}}`; `paas-team`'s `save_servers`, used by
publish.py and the editor), so Claude Code connects it wherever the plugin is enabled, VM or laptop, and nothing is
registered per person; a server still pending is named in a note at a switch; a server the person added themselves is
theirs. `check.py` fails a `.mcp.json` entry that still holds a placeholder. The Team tab
shows which servers the plugin connects. `docs-search` is not listed twice: its address and token ride in `docs-local`'s
environment, and `docs-local` bridges to it (stdio to HTTPS, the VM's certificate from `lib/paas-ui.crt`) on a machine without
the library. The owner's decision: the tokens in the plugin's `.mcp.json` are readable by everyone with access to the team's
GitLab project, so use read-only tokens for the read-only servers and rotate them when someone leaves; the notes hook never
asks to redact those files. Claude Code names a plugin's tools `mcp__plugin_paas-brain-<team>_<server>__<tool>`: `build.py` writes
that form into the agents' `tools:` lists for the team's servers, `paas-team use` puts the matching `permissions.allow` rules into the
person's settings.json (the previous team's go), and the read-only guard reads the form as the bare name, so a server added
to a team in the editor is usable by the agents and needs no permission prompt at the next session.

**Several servers of one kind** (three CommCells, two ONTAP clusters): name them `<catalog name>-<suffix>` in the team definition's team.json
(`commvault-env1`, `commvault-env2`): the first publish gives each the catalog entry's shape, and each gets its own address
and token in the team editor. Agents list each one in their `tools:` (`mcp__commvault-env1__*`).

## A team with its own library

By default every team searches the one general library, plus its own knowledge. A team that needs other documents, and none
of the general ones, names its own library in `team.json`: `"library": "ops"`. Then, for that team only:

- the docs service answers `https://<vm>:8443/mcp?team=<team>` from `/opt/paas/libraries/ops/docs.db` (plus the team's
  knowledge), never from the general library; a library that is named but not built yet gives a clear error, no fallback;
- the team plugin's `docs-local` opens `~/.claude/brain/libraries/ops/docs.db` (on the multi-user VM a link to
  `/opt/paas/libraries`); where that is not installed it bridges to the docs service, and without that it searches the team's
  knowledge alone, never the general library;
- the docs-leads and docs-hints hooks take their leads from the same library.

Fill it as root with `paas-library` (stdlib, on the VM in `/opt/paas/bin`):

```sh
paas-library add ops /path/to/their/documents --to <vendor>/<product>     # copies them in and indexes (PDF, HTML, Markdown, text)
paas-library build ops [--full]                                           # re-index after files changed in the folder
paas-library list                                                         # every library: documents, size, when built
```
A library built on a machine with internet (the Flashback one: `sh docs-search-mcp/sources/flashback/build-library.sh`)
comes in as one tarball: `paas-library import <name> <name>-library-<date>.tar.gz` (checked against its `.sha256`; the
products it carries are replaced, documents added on the VM stay, then the index is brought up to date).
The documents live in `/opt/paas/libraries/<name>/docs/<vendor>/<product>/`, the index next to them; a rebuilt index is
used at the next request, no restart. Single VM: `~/.claude/brain/libraries` instead.

**The Market** offers one docs item per team, `docs-http-<team>` (the docs service with `?team=<team>`, one token for all):
everyone sees every team's and may add another team's docs to their own Claude; a team's plugin carries only its own (as
`docs-local`), so the active team's item shows as "from your team". `install-shared.sh` (re)creates the items for every team
under `/opt/paas/teams` and removes those of teams that are gone.

## Editing a team in the Brain tab

The Team tab's "More, Edit a team" opens the team's definition: title, description, persona, rules, environment template, the
skills and agents (checkboxes over everything on this machine: your own, the marketplace's, the other teams'), and the MCP
servers with their tokens. Saving writes into the team repository (`paas-team edit <team>` with JSON on stdin), commits
`brain tab: team <team> edited`, pushes, and re-applies the team if it is the active one; every member picks the change up at
their next sync. `paas-team show <team> --json` prints the same definition. `publish.py` refuses to overwrite such edits
without `--force`.

## Edits from the Brain tab reach the team

Memory: `notes.md`, `environment.md`, `notes/`, `captures/`, `incidents/` and `tool-map.md` are all the team's (committed
and pushed after every save; the first switch merges a person's earlier notes into them). Reports under `~/storage-reports`
are never in git.
Skills and agents: an edit of a **team** skill or agent in the Brain tab is written into the team repository too
(`paas-brain-<team>/skills/<name>/SKILL.md`), committed as `brain tab: team skill <name>` and pushed; every teammate's
brain re-applies it at their next sync or session start. A person's own or marketplace skill stays theirs. Because such an
edit lives only in the team repository, `publish.py` refuses to overwrite it until it is ported into `brain/teams/<team>`
(or `brain/claude`) in this repository, or `--force` is given.

## In the marketplace

The Market tab lists the team plugins (`plugin/paas-brain-<team>`: added when the person has the team, on when it is
the active one; Turn on switches the team, Turn off leaves it) and marks every skill, agent and MCP server the active team's
plugin provides as added "from your team", so what a person has is visible in one place: the team's set plus what they added
themselves. `paas-market add` of such an item says it comes with the team; the team editor changes the team's set. The
multi-user VM shares one knowledge index per team (`/var/lib/paas-docs/<team>.db`, built by the docs service) that a member's
`docs-local` uses when it matches their clone, and one resource budget per person (`/etc/paas/limits.env`); `RUNBOOK.md`,
"Sizing the VM".

## Updates and the CI gate

The plugin's `version` is the library version plus a fingerprint of the plugin's content (`2026.10.25b-7cbc8a20`): Claude
Code hands a user a new copy from a git-hosted marketplace only when that string changes, so every publish with a change is
delivered, and an unchanged republish adds no commit. A marketplace added from a local path (the VM) loads the files in place at every session start. Every team repository carries `check.py` (JSON, plugin shape,
hooks.json and .mcp.json wrappers, skills and agents with frontmatter, team.json lists resolvable, no secrets in knowledge,
line caps on notes.md and tool-map.md) and a `.gitlab-ci.yml` that runs it on every push; the Brain tab's edits go through
the same file when they are committed, so a broken edit is caught at the push, not at everyone's next session.

## Knowledge and learning, end to end

1. **Load.** Every session starts with notes.md (core facts, under 60 lines) and a catalog of the topic files, pages,
   captures waiting and incidents; a topic file is read only when a question touches it. The session-start line also says
   when curation is due (5 captures or more, or one older than 14 days) and how many facts are older than 180 days, and
   lists what teammates changed in the last 14 days (notes, runbooks, rules; not your own commits nor publish.py's), so a
   fact someone learned yesterday is read when a question touches it. In the docs search every dated fact line is a hit of
   its own (not the whole topic file), and captures are found too, titled "Unverified capture" until curated.
2. **Look up.** Before answering, Claude searches the offline library (docs-lookup, docs-leads) and the team's own
   knowledge. The plugin's `docs-local` carries the docs server itself: at every start it indexes the brain folder's notes
   pages and incidents into a small per-person index, `~/.claude/brain/brain.db` (a second or two when pages changed,
   nothing otherwise; the shared library stays read-only), and searches it with the library, so a teammate's page is found
   by `search_docs` next to the vendor documents, marked `library: team knowledge`. On a laptop without the library the
   knowledge is the whole `docs-local` index and the VM's `docs-search` supplies the library. It follows the active team.
3. **Learn.** A solved problem, a quirk, a corrected assumption is written down (golden rule 6): a dated line with a
   confidence word (verified / observed / hypothesis) and its source into notes/<topic>.md, a capture under captures/ when
   the topic is unclear, a page notes/<topic>-<slug>.md when it needs sections, an incident postmortem under incidents/,
   and a **runbook** under runbooks/<topic>-<task>.md when a change procedure the person ran worked: Pre-checks, Procedure,
   Verification, Rollback (check.py requires these four), Scope, History; every command is for the person to run. Session
   start lists the runbooks and Claude follows a matching one before writing change steps of its own; they are searched
   with the notes (docs index, product `brain-runbooks`) and listed in INDEX.md.
   The stop hook asks once after a long session without a capture. Agents end with a Learned line the parent files.
4. **Guard.** The notes hook scans every save for secrets and private addresses and sends them back for redaction before
   anything is committed; the team repository's check.py runs the same patterns at every push, and notes fact lines
   without a date or confidence word.
5. **Share.** Each save is committed and pushed to the team repository; every session start and Brain tab opening pulls.
   `knowledge/INDEX.md` is regenerated at every commit: topics with their fact counts, pages, captures, incidents, so the
   team's brain is readable at a glance in GitLab. The Brain tab shows the files with history and restore.
6. **Curate.** `brain-learn` promotes captures into notes (merge, keep, discard, with the person's go-ahead), re-verifies
   stale facts and raises or lowers confidence only with new evidence. Memory stays small: caps on notes.md and topic
   files are reported by session start and check.py.
7. **Switch.** Each team has its own memory; a person moving between SAN and NAS carries their own notes with them on the
   first switch and sees the other team's knowledge immediately.

Compared with team-brain repositories that review every learning in a merge request: here the learning lands at once
and the review happens at curation and at the CI gate; a team that wants human review before merge can protect `main`
in GitLab and give members a branch, the sync reports the state either way.

## Everything is pushed, by every path

The notes hook commits and pushes each file Claude saves (notes, captures, incidents, tool map); the Brain tab pushes
after each save or restore; every session start and every opening of the Brain tab's Memory section pulls and pushes
(`paas-team sync`), and a plugin the team republished is re-applied at that moment. Offline is never an error: the next
sync retries. A conflict on the same line is aborted and named; `RUNBOOK.md` has the three git lines that resolve it.

## Switching: `paas-team`

`~/.claude/tools/paas-team` (laptop, single VM) or `/opt/paas/bin/paas-team` (multi-user VM; `paas-team` in PATH):

```
paas-team                   active team, remote state, other teams
paas-team use nas           switch (clones the team first when needed; then start a new Claude session)
paas-team list [--json]     local teams and the ones the VM offers
paas-team sync              pull / push the team's knowledge; re-applies the plugin when the team updated it
paas-team remote nas <url>  the team's GitLab repository; paas-team off: no team
```
`paas-team use none` leaves every team: the team's plugin is disabled (its skills, agents and MCP servers with it), the person's own and marketplace ones stay,
the memory files become plain files and the rules (main.md, persona.md, storage.md, coding.md) stay as plain copies of the team's.

A switch repoints `main.md`, `persona.md`, `storage.md`, `coding.md` (symlinks into the team's `rules/`; a CLAUDE.md that was
the brain's full text is kept as `CLAUDE.md.bak.<time>` and becomes the import line, so the rules load once) and `notes.md`,
`environment.md`, `tool-map.md`, `notes/`, `captures/`, `incidents/` (symlinks into `~/.claude/brain/teams/<team>/knowledge/`;
Windows without the symlink right: hard links, re-made after each pull), and swaps the team's
Claude Code plugin: `paas-brain-<team>` installed and enabled from the person's clone (a marketplace added from a local
path loads in place, so a sync brings new skills to the next session with no update step), the other teams' plugins
disabled. This is the same install on the VM and on every laptop: skills are `/paas-brain-<team>:<skill>`, the hooks and
`docs-local` come with the plugin. On the multi-user VM the managed settings run every brain hook for every account
(enforced, cannot be switched off) and the plugin's own copies step aside when they see that twin, so no hook runs twice
and an account without a team is covered too. A switch takes a few seconds. The first switch moves the person's existing notes into the
team's knowledge folder; a person's own skills (`.user-skill`, `agents/.user-agents`) and the skills and agents they
added from the marketplace (`paas-market add skill/<name>`, the Market tab; recorded in `~/.claude/paas-market.json`) are
never removed or overwritten, so everyone has the team's set plus their own choices. Each team has its own memory:
`notes.md`, `environment.md`, `notes/`, `captures/`, `incidents/`, `tool-map.md`, shared by every member (committed by the
notes hook, pushed to the team remote, pulled at every session start).

Cost: a team clone is about 0.5 MB plus the knowledge; a NAS member's context is smaller than a SAN member's (the
NAS rules and skill list are shorter, `test_budgets.py` prints both). What a session start costs, measured: the rules
(CLAUDE.md, persona, notes.md, storage.md, environment, tool map) and the skill and agent frontmatter are about 32 KB, about
8k tokens, for SAN; the MCP tool schemas of powermax, powerflex, ucs-central, mds and docs-local are about 13k tokens more
(`python3 scripts/mcp_context_size.py` on a machine with the servers' Python packages), which is why the installer sets
`ENABLE_TOOL_SEARCH=true`: Claude sees the tool names and the servers' instructions (about 4k tokens) and loads a tool's
schema when a task needs it. On the VM `python3 ~/.claude/tools/token-report.py` shows the real per-session numbers.

## Where the teams come from on each install

- `sh install-vm.sh --team nas` / `sh brain/install.sh --team nas`: every team of the clone is published into
  `~/.claude/brain/team-sources/` (so `paas-team use <other>` works offline), the chosen one is added and switched on.
  `--team-source <git-url>` takes the team repository from GitLab instead. Without `--team` the install is the SAN brain
  alone: plain files, no team repository, no plugin.
- `sh install-laptop.sh [--team nas] [--team-source <url>]`: the pre-team `paas-brain` plugin is removed.
- Multi-user VM: `install-shared.sh` publishes every team into `/opt/paas/teams/<team>` (plugins without hooks, the
  hooks are managed settings) and installs `paas-team`. Everyone starts without a team; the Team tab of the Brain tab
  switches with one click (No team / SAN / NAS), root can also set it with `paas-user team dana nas` or `paas-user add
  dana --team nas`.
