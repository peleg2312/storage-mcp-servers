# brain/teams: team profiles

One brain per team, switched in seconds. A team profile decides what a member's Claude gets: the persona ("who you
work for"), the storage rules, the skills, the agents, the MCP servers it starts with, and a knowledge folder the
team shares. Everyone keeps their own Linux account (Active Directory on the multi-user VM), their own chats and
their own audit trail; the team is a profile on top of the person, not a shared login.

| Team | Rules | Skills | Agents | Live MCP |
|---|---|---|---|---|
| `san` (default) | `brain/claude/brain/storage.md` | all of `brain/claude/skills` (28) | all of `brain/claude/agents` (9) | docs-local, powermax, powerflex, mds, ucsc |
| `nas` | `brain/teams/nas/storage-nas.md` | 12 shared + 6 NAS: share-access-check, export-policy-check, quota-report, nas-replication-check, smartconnect-check, vast-view-check | Explore, docs-researcher, ontap-analyst, nas-analyst | docs-local, ontap, harvest. **No PowerScale or VAST MCP exists yet**: those skills work from output the person pastes (isi, VAST CLI / VMS) and the docs library, and say so |

## Definition: `brain/teams/<team>/team.json`

```json
{"name": "nas", "title": "NAS / file storage", "description": "...",
 "persona": "persona.md", "rules": "storage-nas.md", "environment": "environment.md",
 "skills": ["brain-setup", "docs-lookup", "share-access-check", "..."],   "agents": ["Explore", "nas-analyst"],
 "mcp": ["docs-local", "ontap", "harvest"]}
```
`skills` / `agents`: names, looked up in `brain/teams/<team>/skills|agents` first, then in `brain/claude/skills|agents`
(so a team adds its own and reuses the shared ones), or `"all"`. File paths are relative to the team folder, or to the
repository when they start with `brain/`. A new team = a folder with `team.json` and `persona.md`; `python3
brain/test_budgets.py` then checks its budgets (rules + environment + tool map under 12 KB, skill frontmatter under
10.5 KB, agents under 3.6 KB) and `python3 brain/test_teams.py` builds it.

## What gets built

`python3 brain/plugin/build.py <out> --team nas` builds the plugin `paas-brain-nas/` (skills, agents, hooks with
`hooks.json`, `docs-local`, plus `brain/` with persona.md, storage.md and the environment / tool-map / notes templates,
and `team.json` with the resolved lists). `python3 brain/teams/publish.py nas --to <dir|git-url>` wraps it into the
**team repository**:

```
.claude-plugin/marketplace.json      paas-brain-nas/        knowledge/{notes,captures,incidents}/  knowledge/tool-map.md
knowledge/notes.md, environment.md   mcp.json (the team's live MCP servers with address and token)   team.json   README.md
```
One git repository per team, in GitLab: `python3 brain/teams/publish.py nas --to git@gitlab/storage/brain-nas.git`
(clone, rebuild the plugin, commit, push; the url is recorded as the team's remote). Members' brains push their notes,
captures and incidents into `knowledge/`. The repository also carries `install-team.sh` and `bin/paas-team`, so a laptop
needs nothing else: `git clone <url> brain-nas && sh brain-nas/install-team.sh` gives the plugin, the rules, the knowledge
folder synced with the repository and `paas-team`; the docs library is the one thing it lacks (`install-laptop.sh` of this
repository adds it). The standard Claude Code way is the whole install too:

```sh
claude plugin marketplace add <url> && claude plugin install paas-brain-nas@paas-brain-nas
```
At the first session the plugin's session-start hook sets the team up itself (`bin/paas-team bootstrap`): it clones the
team repository recorded in the plugin's `team.json` as `~/.claude/brain/teams/nas`, links the memory files into it, writes
persona.md and storage.md, puts the core rules in `~/.claude/brain/main.md` with one import line in your `~/.claude/CLAUDE.md`,
and copies `paas-team` to `~/.claude/tools`. From then on every note is committed and pushed to the team repository like on
the VM; `git clone` is not needed. When the repository is unreachable, the hook prints the persona and rules as context
instead and tries again next session. Plugins stay read-only content in Claude Code's cache; the hook is what lets this one
contribute.

## MCP servers per team

The team repository's `mcp.json` holds the team's live MCP servers with address and token (`{"powermax": {"type": "http",
"url": "http://...:8000/mcp", "headers": {"Authorization": "Bearer ..."}}}`), created from the catalog with HOST / TOKEN
placeholders at the first publish and filled in the Brain tab's team editor (or by hand). A switch registers every filled
server for the person with `claude mcp add-json` (VM or laptop alike) and removes the previous team's; a server not filled in
falls back to the VM's marketplace (`paas-market add mcp/<name>`, root's shared token from the Market tab); a server the
person added themselves is left alone. The Team card shows which servers are added. The owner's decision: the tokens in
`mcp.json` are readable by everyone with access to the team's GitLab project, so use read-only tokens for the read-only
servers and rotate them when someone leaves; the notes hook never asks to redact that file. The docs library is the
plugin's own `docs-local`.

## Editing a team in the Brain tab

The Team card's "Edit team" opens the team's definition: title, description, persona, rules, environment template, the
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

## Updates and the CI gate

The plugin's `version` is the library version plus a fingerprint of the plugin's content (`2026.10.25b-7cbc8a20`): Claude
Code hands a user a new copy from a git-hosted marketplace only when that string changes, so every publish with a change is
delivered, and an unchanged republish adds no commit. A marketplace added from a local path (the VM, `paas-team` in plugin
mode) loads the files in place at every session start. Every team repository carries `check.py` (JSON, plugin shape,
hooks.json and .mcp.json wrappers, skills and agents with frontmatter, team.json lists resolvable, no secrets in knowledge,
line caps on notes.md and tool-map.md) and a `.gitlab-ci.yml` that runs it on every push; the Brain tab's edits go through
the same file when they are committed, so a broken edit is caught at the push, not at everyone's next session.

## Everything is pushed, by every path

The notes hook commits and pushes each file Claude saves (notes, captures, incidents, tool map); the Brain tab pushes
after each save or restore; every session start and every opening of the Brain tab's Memory section pulls and pushes
(`paas-team sync`), and a plugin the team republished is re-applied at that moment. Offline is never an error: the next
sync retries. A conflict on the same line is aborted and named; `RUNBOOK.md` has the three git lines that resolve it.

## Switching: `paas-team`

`~/.claude/tools/paas-team` (laptop, single VM) or `/opt/paas/bin/paas-team` (multi-user VM; `paas-team` in PATH):

```
paas-team                   active team, mode, remote state, other teams
paas-team use nas           switch (clones the team first when needed; then start a new Claude session)
paas-team list [--json]     local teams and the ones the VM offers
paas-team sync              pull / push the team's knowledge; re-applies the plugin when the team updated it
paas-team remote nas <url>  the team's GitLab repository; paas-team off: back to plain files
```
`paas-team use none` leaves every team: the team's skills and agents go, the person's own and marketplace ones stay,
the memory files become plain files and persona.md / storage.md stay as editable copies. `paas-team export [team]`
writes a zip of the team repository (plugin, marketplace file, install-team.sh) into `~/storage-reports`, the Reports
tab, for a laptop without GitLab access.

A switch rewrites `~/.claude/brain/persona.md` and `storage.md`, repoints `notes.md`, `environment.md`, `tool-map.md`,
`notes/`, `captures/`, `incidents/` (symlinks into `~/.claude/brain/teams/<team>/knowledge/`), and swaps the skills and
agents: in **files mode** (VMs; hooks come from settings.json or the managed settings) they are copied into
`~/.claude/skills` and `agents` without a namespace; in **plugin mode** (laptops, `install-laptop.sh`) the team's plugin
is enabled and the other teams' disabled. Under a second. The first switch moves the person's existing notes into the
team's knowledge folder; a person's own skills (`.user-skill`, `agents/.user-agents`) and the skills and agents they
added from the marketplace (`paas-market add skill/<name>`, the Market tab; recorded in `~/.claude/paas-market.json`) are
never removed or overwritten, so everyone has the team's set plus their own choices. Each team has its own memory:
`notes.md`, `environment.md`, `notes/`, `captures/`, `incidents/`, `tool-map.md`, shared by every member (committed by the
notes hook, pushed to the team remote, pulled at every session start).

Cost: a team clone is about 0.5 MB plus the knowledge; a NAS member's context is smaller than a SAN member's (the
NAS rules and skill list are shorter, `test_budgets.py` prints both).

## Where the teams come from on each install

- `sh install-vm.sh --team nas` / `sh brain/install.sh --team nas`: every team of the clone is published into
  `~/.claude/brain/team-sources/` (so `paas-team use <other>` works offline), the chosen one is added and switched on.
  `--team-source <git-url>` takes the team repository from GitLab instead. Without `--team` the install is the SAN brain
  as before (plain files, no symlinks).
- `sh install-laptop.sh [--team nas] [--team-source <url>]`: plugin mode; the pre-team `paas-brain` plugin is removed.
- Multi-user VM: `install-shared.sh` publishes every team into `/opt/paas/teams/<team>` (plugins without hooks, the
  hooks are managed settings) and installs `paas-team`. `paas-user add dana --team nas`, `paas-user team dana nas`, or
  the AD mapping in `/etc/paas/team-groups` (`nas  storage-nas-team`) at the person's first sign-in. The Brain tab of
  the web UI has the same switch.
