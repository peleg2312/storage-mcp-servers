# Upgrading the multi-user VM from the 30.10 version

This is for a VM installed from the repository as of 2026-10-30 (commit `c014fbf`: the web UI with Git settings, one
Linux account per team such as `san` and `nas`). It brings it to the current version: teams as plugins, one account per
person, shared team memory in GitLab, the docs service for laptops. One command does the upgrade; the only manual work
is moving the old team accounts' notes into the team repositories, and the things only you can do (AD join, GitLab).

## What changes for the people on the VM

- Everyone signs in with their own account (local or Active Directory). Nobody gets a team at sign-in; the Team card at
  the top of Brain, Memory switches between No team, SAN and NAS with one click, then a new chat.
- A team is a Claude Code plugin (`paas-brain-san`, `paas-brain-nas`) with its skills, agents, hooks, rules and the
  team's MCP servers. Its memory (notes, environment, tool map, captures, incidents) is shared by the whole team through a
  git repository; every saved note is committed with the person's name and pushed, every session start pulls.
- Idle web UI instances stop after 60 minutes and restart on the next request; each person has a CPU and memory budget.
- The docs library is unchanged (version 2026.10.25b), and so are the MCP server images.

## What you do not need to do

- No library rebuild or re-import: `library/` and `images/` did not change since 30.10. When you copy the repository to
  the VM instead of pulling, those two folders (1.3 GB) can be skipped.
- No account re-creation, no edits to hooks, managed settings or systemd units by hand: the installer regenerates them.
- No `claude mcp add` for anyone: the team's servers come with the plugin; servers an earlier version registered per
  person are removed automatically at the first team switch.
- No change on the OpenShift side.

## Before you start

1. Pick a quiet moment: the upgrade restarts the gate and every running UI instance, which ends the chats in progress.
2. Packages: `dnf install acl` (new requirement: the per-team ACLs). If people will sign in with AD accounts, also
   `dnf install sssd realmd oddjob oddjob-mkhomedir adcli samba-common-tools` and join the VM (RUNBOOK, "Active Directory
   accounts"). Local accounts keep working without it.
3. GitLab (recommended, can be done later): one empty project per team (branch `main`, members Developer) and one access
   token (project or group, role Developer, scope `write_repository`). Without GitLab the teams work on the VM only and the
   knowledge stays in `/opt/paas/teams/<team>`.
4. A backup of `/etc/paas`, `/opt/paas/brain` and the home directories is cheap insurance: `tar czf /root/paas-30.10.tgz
   /etc/paas /opt/paas/brain /home`.

## The upgrade

```sh
cd /path/to/storage-mcp-servers
git pull                                   # or copy the new checkout in (library/ and images/ may be skipped)
sh brain/multiuser/install-multiuser.sh --gitlab-host gitlab.example.com \
   --team san=https://gitlab.example.com/storage/brain-san.git \
   --team nas=https://gitlab.example.com/storage/brain-nas.git \
   --groups "storage-san-team,storage-nas-team"
```
Leave out `--gitlab-host` and `--team` if GitLab comes later, and `--groups` if only local accounts sign in. The command
asks once for the GitLab token (the API key is already in `/etc/paas/api-key`). On an existing install it: refreshes root's
brain and the web UI bundle; rebuilds the shared library links, the marketplace and `/opt/paas/teams/<team>` (new); writes
the per-person budget (`/etc/paas/limits.env`, edit and re-run to change); installs the docs service on 8001 with its
token; regenerates the managed settings with the two new hooks (notes scan, capture nudge); installs the new gate (idle
stop, allowed groups, first-sign-in provisioning); stores the GitLab token for every account; records each team's url and
pushes the team repositories; re-provisions every account (team tool, git credential helper, UI plugins); restarts the UIs;
then checks the services, the gate, the docs service and each team repository and prints what is left for you.

## Move the old team accounts' notes into the team repositories

The `san` and `nas` accounts hold the notes written so far. Switching each one onto its team moves them: the first switch
merges the account's own `notes.md`, `environment.md`, `tool-map.md`, `notes/`, `captures/` and `incidents/` into the team's
knowledge (anything that differs from the team's copy is kept beside it as `.pre-team`), commits and pushes.

```sh
paas-user team san san
paas-user team nas nas
```
Check the result in GitLab (the `knowledge/` folder of each project) or in `/opt/paas/teams/<team>/knowledge`. The accounts
can stay as shared sign-ins; once people have their own accounts, lock them: `paas-user lock san` (their home stays).

## Check

- `https://<vm>:3001` shows the sign-in page; sign in as a person, the Brain tab shows the Team card with No team pressed.
- Click SAN, start a new chat: the session-start line reads `Team: san (...)`; ask one storage question; save one note and
  see its commit in GitLab with that person's name.
- `systemctl is-active paas-gate paas-docs paas-market-serve` all `active`; `journalctl -u paas-gate -n 20` quiet.
- `sh scripts/run_tests.sh` passes on the VM (the retrieval evals run when the built index exists).

## Later, when you want

- AD accounts: join, then `sh brain/multiuser/install-multiuser.sh --groups "<AD groups>"` (the other flags are remembered).
- Laptops: the three `claude plugin` lines in README.md with the team's url, with the person's own GitLab login.
- The teams' MCP servers (address and token per server): Brain tab, Team card, More, Edit a team.

## Rollback

`git checkout c014fbf && sh install-vm.sh && sh brain/multiuser/install-shared.sh && sh brain/multiuser/install-gate.sh`,
then `systemctl disable --now paas-docs`. Accounts that switched onto a team should run `paas-team off` first (the memory
files become plain files again); the team clones under `/opt/paas/teams` and `~/.claude/brain/teams` are harmless leftovers.

## Files that land on the VM (for reference)

| Where | What is new or changed since 30.10 |
|---|---|
| `/opt/paas/teams/<team>` | each team as a repository: plugin, knowledge, mcp.json (new) |
| `/opt/paas/bin` | `paas-team` (new), `paas-git-credential` (new), `paas-user` (team, git-token, provision changes) |
| `/opt/paas/hooks` | `notes-check.py`, `capture-nudge.py` (new); the others step aside for their plugin twins |
| `/etc/paas` | `limits.env`, `docs.env`, `docs-token`, `git/<host>.token`, `multiuser.conf` (new); `allowed-groups` (gate) |
| `/etc/systemd/system` | `paas-docs.service` (new), `paas-ui@.service.d/limits.conf` (new), `paas-gate.service`, `paas-ui@.service` |
| `/etc/claude-code/managed-settings.json` | regenerated: the two new hooks, the same key helper |
| each home | `~/.claude/brain/teams/<team>` clone and memory links once a team is chosen; git config with the credential helper |
