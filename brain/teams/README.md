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
team.json (name, title, remote)      README.md              .gitignore (knowledge/notes.md and environment.md stay personal)
```
One git repository per team, in GitLab: `python3 brain/teams/publish.py nas --to git@gitlab/storage/brain-nas.git`
(clone, rebuild the plugin, commit, push; the url is recorded as the team's remote). Members' brains push their notes,
captures and incidents into `knowledge/`, and `claude plugin marketplace add <url>` installs the brain from it anywhere.

## Switching: `paas-team`

`~/.claude/tools/paas-team` (laptop, single VM) or `/opt/paas/bin/paas-team` (multi-user VM; `paas-team` in PATH):

```
paas-team                   active team, mode, remote state, other teams
paas-team use nas           switch (clones the team first when needed; then start a new Claude session)
paas-team list [--json]     local teams and the ones the VM offers
paas-team sync              pull / push the team's knowledge; re-applies the plugin when the team updated it
paas-team remote nas <url>  the team's GitLab repository; paas-team off: back to plain files
```
A switch rewrites `~/.claude/brain/persona.md` and `storage.md`, repoints `notes.md`, `environment.md`, `tool-map.md`,
`notes/`, `captures/`, `incidents/` (symlinks into `~/.claude/brain/teams/<team>/knowledge/`), and swaps the skills and
agents: in **files mode** (VMs; hooks come from settings.json or the managed settings) they are copied into
`~/.claude/skills` and `agents` without a namespace; in **plugin mode** (laptops, `install-laptop.sh`) the team's plugin
is enabled and the other teams' disabled. Under a second. The first switch moves the person's existing notes into the
team's knowledge folder; a person's own skills (`.user-skill`) are never touched. Each team has its own personal
`notes.md` and `environment.md` (never committed) and the team's shared `notes/`, `captures/`, `incidents/`,
`tool-map.md` (committed by the notes hook, pushed to the team remote, pulled at every session start).

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
