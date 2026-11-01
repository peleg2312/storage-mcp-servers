# Runbook: from this repo to a working offline brain

Three places: **your PC** (has internet; pushes to GitHub), **GitHub**, **the offline VM** (runs Claude
Code). Every command you need, in order.

## 1. PC: complete the library (Dell PDFs, Dell KB, bug trackers, the rest of the NetApp KB)

Needs: `git`, `python3` (3.10+), a venv with `pip install pypdf cryptography fonttools` (macOS: `python3 -m venv work/venv && source work/venv/bin/activate` first), and for the bug trackers any read-only GitHub token.
Dell's site blocks cloud IPs, so this step has to run from a normal office/home PC.

```bash
cd storage-mcp-servers/docs-search-mcp

# a) start from the prebuilt library (fast, no re-download of what is already there)
sh ../library/join.sh work && mv work/docs-library/docs work/docs && mkdir -p work/index \
  && mv work/docs-library/docs.db work/index/docs.db && rm -rf work/docs-library

# b) Dell PowerMax / PowerFlex product PDFs + the Dell KB articles listed in sources/web-pages.txt
#    Many manuals need a Dell login: sign in to dell.com/support in your browser first and add
#    --browser-cookies (pip install browser-cookie3 in the venv); --retry replaces copies that came
#    back as Dell's redirect page instead of the document.
python3 sync/sync_dell.py --dest work/docs/dell --browser-cookies --retry
python3 sync/sync_web.py  --dest work/docs               # KB pages (Dell, VMware, NetApp) one URL per line
python3 sync/sync_dell_kb.py --dest work/docs --browser-cookies   # Dell KB articles of PowerMax / PowerFlex / CSM-CSI
                                                         #   (seed list + related-article links; login-only ones with your session)

# b2) login-only Dell documents (alert / event reference guides, release notes, support matrices): the
#     scripts get Dell's redirect page for them even with cookies. Download them in your signed-in browser
#     as listed in extra/dell/NEEDED.md (file name + link), save under extra/dell/<product>/, then:
python3 sync/import_extra.py --dest work/docs
cd .. && git add -f docs-search-mcp/extra/dell && git commit -m "Dell login-only docs" && git push origin main && cd docs-search-mcp

# b3) MOST Dell content comes from a real browser (Dell's bot check and sign-in stop the plain scripts):
#     sign in once, then the collector searches DuckDuckGo, Bing and Dell Support for every query in
#     sources/dell-kb-queries.txt and saves every KB article found (login-only ones too), downloads the login-only
#     PDFs of extra/dell/NEEDED.md through the signed-in browser, every Info Hub paper on PowerFlex / PowerMax / CSM,
#     and the HTML manuals in sources/dell-manuals.txt topic by topic.
pip install playwright && python3 -m playwright install chromium
python3 sync/dell_browser.py all --wait-login # a window opens on Dell sign-in: sign in there, the run continues in that
                                              # session (Dell's sign-in expires between runs). Hours; Ctrl-C any time,
                                              # re-run continues (search results are cached a week)
python3 sync/import_extra.py --dest work/docs
#     "access level 10 < 30" for the PDFs = your Dell account is not linked to an entitled site: My Account -> link the
#     company's site ID (or ask the Dell account team), then: python3 sync/dell_browser.py needed --wait-login

# c) Trident / Harvest issue trackers + Dell CSM / CSI pull requests (Dell disabled its issue trackers: the PRs are
#    the fixes, with the issues they name), then the first release tag of every PR (from git history)
GITHUB_TOKEN="$(gh auth token)" python3 sync/sync_github_issues.py --dest work/docs
python3 sync/pr_releases.py --dest work/docs

# d) NetApp KB: continues exactly where the session stopped (1 article / 5 s, resumable, Ctrl-C any time)
#    with your kb.netapp.com login (DevTools -> Application -> Cookies -> kb.netapp.com -> authtoken):
NETAPP_KB_COOKIE='authtoken=<value>' python3 sync/sync_netapp_kb.py --dest work/docs --refresh-partial
#    (omit --include to export every area; add --include on-prem/ontap/da/SAN ... to narrow it)

# e) refresh the git docs (NetApp docs, Trident, CSM...) - incremental
sh sync/sync-git.sh work/docs

# f) index, check search quality, pack -> library/ (45 MB parts), then commit and push
python3 docs_index.py --docs work/docs --db work/index/docs.db
python3 eval_search.py --min-hit5 0.9 && python3 eval_search.py --cases tests/retrieval_heldout.json --min-hit5 0.9
sh bundle/pack-library.sh
cd .. && git add library && git commit -m "Library $(cat library/VERSION)" && git push origin main
```
Monthly: repeat b-f (all incremental). `library/MANIFEST.md` shows what is inside after each pack.

Optional, for an OpenShift cluster instead of / in addition to the VM:
```bash
sh bundle/build-offline.sh --from-library     # needs podman or docker; no internet
# -> work/docs-search-offline-<date>.tar.gz : import into the internal registry, deploy openshift-offline.yaml
```

## 2. VM (offline): install everything

Needs: `python3` (3.9+, the OS one: RHEL 9 ships 3.9), `git`, Claude Code installed (`claude` in PATH).

```bash
git clone https://github.com/peleg2312/storage-mcp-servers.git     # or copy the folder in
cd storage-mcp-servers
sh install-vm.sh                    # add --login-banner for the Peleg As A Service banner at every VM login (sudo)
```
This installs into `~/.claude`: CLAUDE.md, the skills, agents and hooks (read-only guard, docs hints / leads), the
documentation library (`~/.claude/brain/library`), the MCP server **docs-local** (stdio, no dependencies),
the **Peleg As A Service** banner (`claude` wrapper in `~/.bashrc`) and the status line.

**Brain only inside one folder** (project mode): `sh install-vm.sh --project ~/san` writes `~/san/CLAUDE.md`,
`~/san/.claude/{skills,agents,hooks,brain,banner,settings.json}` and `~/san/.mcp.json` (docs-local) instead of
`~/.claude`; the library still goes to `~/.claude/brain/library`. Claude started in any other folder has no brain,
no hooks and no banner; `claude` need not be installed yet. On the first start inside the folder approve docs-local. Then:

```bash
. ~/.bashrc                 # or open a new terminal (the banner wrapper)
claude                      # banner, then Claude Code
/brain-setup                # inside Claude: tool map + environment draft; confirm the uncertain items
```
Add the live MCP servers (PowerMax, UCS Central, MDS, docs-search on the cluster) as in the top README:
`claude mcp add --transport http <name> http://<host>:8000/mcp --header "Authorization: Bearer <token>"`,
then run `/brain-setup` again so the tool map knows them.

Update later: `git pull && sh install-vm.sh` (your environment.md / tool-map.md are kept; the library is
re-extracted only when `library/VERSION` changed).

Try: `python3 ~/.claude/brain/library/search.py search "scsiblade.san.config.active"` or, inside Claude,
`explain EMS scsiblade.san.config.active`, `/zoning-audit fabric A`, `which KB covers FC link down after a switch reboot`.

## Sizing the VM for many people and teams

What one person costs while working: a Claude Code process (the bulk, 300 MB to 1 GB with a long context), the web UI
instance (100 to 150 MB), one `docs-local` process per Claude session (about 30 MB; the library file is mapped once by the
kernel for everyone), hook processes that live for tens of milliseconds, and on disk the team clone (a few MB), the chats
and reports. The library (1.3 GB), the team folders, the marketplace and the plugins exist once under `/opt/paas`.

The installer gives every person one budget: `install-shared.sh` writes `/etc/systemd/system/paas-ui@.service.d/limits.conf`
from `/etc/paas/limits.env`, sized from the VM's RAM and cores for `PAAS_PEOPLE` concurrent people (memory high =
(RAM - 3 GB) / people, at least 1.5 GB; max = 1.5 x high; equal CPU weight; 512 tasks). The UI instance and everything it
starts (Claude Code, hooks, docs-local, shells) live in that cgroup, so one person's runaway cannot starve the others:
above the soft limit their processes are slowed and reclaimed first, above the hard limit their largest process is ended,
nobody else notices. Edit `/etc/paas/limits.env` and re-run `install-shared.sh` to change it; `systemctl status paas-ui@<name>`
shows a person's use. Idle instances stop after `GATE_IDLE_MINUTES` (default 120), so RAM follows the people active now.

Rule of thumb: 1.5 to 2 GB of RAM per concurrent person plus 4 GB for the system, one core per two or three concurrent
people, 20 GB of disk plus 1 GB per person for chats and reports. Teams add nothing per person beyond a small clone: the
docs service keeps one knowledge index per team under `/var/lib/paas-docs` and a member's `docs-local` uses it when it is as
fresh as their clone, so twenty people on one team share one index instead of building twenty.

## Docs search: one library for every team, local or on OpenShift

There is one documentation library for everyone; a team changes which rules and skills point into it, not the library.
On the VM each Claude session searches it with `docs-local` (the team plugin's own stdlib server over the shared read-only
`docs.db`; the OS page cache is shared, so ten people cost one copy), plus the person's own `brain.db` with the active team's
notes pages and incidents, which the server rebuilds at start when they changed.

**The VM serves the same search to other machines over HTTPS** (`install-shared.sh` sets it up): the service `paas-docs`
runs the same dependency-free server in HTTP mode on port 8001 with the gate's certificate and a bearer token
(`/etc/paas/docs-token`; port and refresh interval in `/etc/paas/docs.env`). `https://<vm>:8001/mcp` is the library;
`https://<vm>:8001/mcp?team=nas` adds that team's knowledge: the service keeps its own clone of every team repository
under `/var/lib/paas-docs` (from the remote recorded in `/opt/paas/teams/<team>/team.json`), pulls it and rebuilds the
team's index every 10 minutes and at once when a member's notes hook pushes (it posts to `/refresh?team=<team>` with the
token from the team's `mcp.json`). `install-shared.sh` writes `docs-search` with its `?team=` url and the token into every team's `mcp.json`
when it publishes the teams; the plugin's `docs-local` uses it as a bridge on every machine without the library (a laptop),
and serves the library itself where it is installed (the VM), so there is one docs server name everywhere and one token. Health: `curl -k https://<vm>:8001/health`. The OpenShift
deployment of `docs-search` (`docs-search-mcp/bundle/build-offline.sh --from-library`, `openshift-offline.yaml`) remains an
option for a cluster-hosted copy; it serves the library only.

**Where the team knowledge index lives, per kind of user**

| Who | Knowledge clone | Index | Searched through | Fresh when |
|---|---|---|---|---|
| VM user (web UI or shell) | `~/.claude/brain/teams/<team>` (pulled at every session start and Brain tab opening) | `~/.claude/brain/brain.db`, rebuilt by `docs-local` at start when pages changed | `docs-local`: library + knowledge | next session start after a teammate pushed |
| Plugin user on a laptop or another VM | `~/.claude/brain/teams/<team>` (same clone, same pulls) | `~/.claude/brain/brain.db`, the same way (the plugin carries the server) | `docs-local`: knowledge; `docs-search` on the VM: the library | next session start after a teammate pushed |
| A client with neither (another tool, OpenShift) | none | `/var/lib/paas-docs/<team>.db` on the VM | `docs-search` with `?team=<team>` | seconds after a push (the notes hook asks the service to re-index); every 10 minutes otherwise |

All three read the same git repository, so what one person's Claude wrote down is what every other member searches,
whichever machine they sit at. A laptop with the library installed (`install-laptop.sh`) behaves like a VM user.

## Owner's checklist: the multi-user VM with teams, end to end

Three things are yours to do by hand; everything else is one command that you re-run for every update.

**Before the command**

1. Packages, as root, from your satellite / local repo: `dnf install git python3 openssl acl diffutils hostname sssd realmd oddjob
   oddjob-mkhomedir adcli samba-common-tools`, and Claude Code installed so that `claude` is in root's PATH.
2. Active Directory: join the VM (`realm join`, sssd settings, mkhomedir; the "Active Directory accounts" section below). The
   AD group(s) whose members may sign in must resolve: `getent group storage-san-team`.
3. GitLab: one empty project per team (default branch `main`, every member Developer), and one access token for the VM: in the
   project or the group, Settings, Access tokens, role Developer, scope `write_repository`. Copy the token; you paste it once.
   On GitLab Free a Developer can also change the plugin folder (CODEOWNERS gates merge requests only): keep publish.py as the
   only writer of `paas-brain-<team>/` by habit, or split the plugin into its own repository later.

**The command** (as root, from this checkout on the VM; it asks for the API key and the GitLab token when they are missing):

```sh
sh brain/multiuser/install-multiuser.sh --gitlab-host gitlab.example.com \
   --team san=https://gitlab.example.com/storage/brain-san.git --team nas=https://gitlab.example.com/storage/brain-nas.git \
   --groups "storage-san-team,storage-nas-team"
```
It runs, in order: `install-vm.sh` (root's brain, the library, the web UI), `install-shared.sh` (shared library and brain under
/opt/paas, every team under `/opt/paas/teams/<team>`, the per-person CPU / memory budget, the docs token), `install-gate.sh` (the
gate on 3001 with its certificate, one UI per signed-in person), the API key into `/etc/paas/api-key`, the groups into
`/etc/paas/allowed-groups`, the GitLab token (`paas-user git-token`) and each team's url (recorded in `/opt/paas/teams/<team>`),
`install-shared.sh` again (now with the certificate: the marketplace and the docs service start, each team repository is pushed
to GitLab with `docs-search` and the docs token in its `mcp.json`), `paas-user provision --all`, then checks: the three services,
the gate, the docs service and each team repository reachable with the token. It ends with "left for you" when something is
missing (the AD join, a GitLab project, the key). Flags are remembered in `/etc/paas/multiuser.conf`; `--people 8` sizes the
per-person budget; `--dry-run` prints the plan. Nothing in it needs the internet.

**After the command**

4. The teams' MCP servers: Brain tab, Team card, More, Edit a team (address and token per server; saved into the team repository's
   `mcp.json`, built into the plugin's `.mcp.json` and pushed, so every member's Claude connects them at the next session). A
   server left on its placeholders is not connected and is named in a note at a switch.
5. Try it: sign in at `https://<vm>:3001` as an AD member, pick a team in the Team card, start a new chat, ask one storage
   question, save one note and see the commit in GitLab with your name on it. Laptops: `claude plugin marketplace add <team url>
   && claude plugin install paas-brain-<team>@paas-brain-<team> && claude`, with the person's own GitLab login.

**Updates**: `git pull && sh brain/multiuser/install-multiuser.sh` (no flags). Members get the new plugin at their next session
start; laptops when Claude Code checks the marketplace. Nobody gets a team at sign-in; everyone picks one in the Brain tab.

## Teams: one brain per team, one account per person

1. Pick the team at install time: `sh install-vm.sh --team nas` (single VM; `san` is the default and needs no flag), `sh
   install-laptop.sh --team nas` (laptop). Everywhere the team is the Claude Code plugin `paas-brain-<team>`, installed
   from the person's clone of the team repository, so the VM and every laptop run the identical thing (skills are
   `/paas-brain-<team>:<skill>`). `paas-team` shows the state, `paas-team use san` switches (a few seconds; start a new
   Claude session or a new chat afterwards), `paas-team list` the teams available.
2. Publish each team's repository once in GitLab (an empty project, default branch `main`): `python3 brain/teams/publish.py
   nas --to git@gitlab.example.com:storage/brain-nas.git`. It holds the plugin (`paas-brain-nas/`) and `knowledge/` (notes/, captures/,
   incidents/, tool-map.md). Members join it with `paas-team remote nas <url>` (or `install.sh --team nas --brain-remote <url>`,
   or `--team-source <url>` to install straight from it); their notes hook pushes every saved note there and every session
   start pulls. Re-run the publish after a `git pull` of this repository: members get the new skills at their next sync.
3. Multi-user VM: `sh brain/multiuser/install-shared.sh` publishes every team into `/opt/paas/teams/<team>`, republishes
   each team that has a GitLab url recorded straight to that project (so `git pull && install-shared.sh` updates every
   member's plugin at their next sync), and installs `paas-team`. The managed settings run every brain hook for every
   account (enforced); the team plugin's own copies step aside on the VM, so a person has the same plugin as on a laptop and
   nothing runs twice. Record a team's GitLab url there: `python3 brain/teams/publish.py nas --to /opt/paas/teams/nas --remote <url>`
   (members then clone from GitLab, and fall back to the VM copy when it is unreachable). Nobody gets a team automatically:
   people pick one in the Brain tab (one click), or root sets it with `paas-user team dana nas` / `paas-user add dana --team nas`;
   a person is on one team at a time and changes at will.
4. Laptop without this repository: `claude plugin marketplace add <team url> && claude plugin install
   paas-brain-nas@paas-brain-nas` (the standard way; the plugin sets the team up at its first session: knowledge clone, rules,
   `paas-team`). No GitLab from the laptop: copy a clone of the team repository over and add its folder as the marketplace. The
   docs library is not part of it: the plugin's docs-local bridges to the VM's docs-search, or `install-laptop.sh` installs it.
5. Beyond the team: everyone adds skills and agents from the Market tab (`paas-market add skill/<name>`) or writes their own
   in the Brain tab; a team switch never removes or overwrites those. The Market tab shows what the team plugin already
   gives you as added ("from your team") and lists every team as a plugin item: turning one on switches your team, turning it
   off leaves the teams. A change someone pushes to the team repository reaches you at your next session start or Brain tab
   opening; nothing to re-add. `paas-team use none` (Brain tab: "No team") leaves
   the teams: the team's skills go, your own stay, the rules become your own editable copies.
6. MCP servers per team: root sets each server's address and shared token once in the Market tab; a switch adds the team's
   servers (`team.json` "mcp") for the person and drops the previous team's. A team skill edited in the Brain tab is pushed
   to the team repository and reaches every member at their next sync; `publish.py` then refuses to overwrite it until it is
   ported into `brain/teams/<team>` (or run with `--force`). The whole team memory (notes.md, environment.md, notes/,
   captures/, incidents/, tool-map.md) is shared; reports never go to git. The team editor in the Brain tab ("Edit team")
   changes title, persona, rules, environment template, skills, agents and the MCP servers with their tokens (stored in the
   team repository's mcp.json by your decision: read-only tokens, rotate when someone leaves).
7. Rolling the plugin out to many laptops without each person typing the two commands: put the team marketplace into the
   laptops' managed settings (`/etc/claude-code/managed-settings.json` on Linux, the equivalent path on macOS):
   `{"extraKnownMarketplaces": {"paas-brain-nas": {"source": {"source": "git", "url": "<team url>"}, "autoUpdate": true}},
   "enabledPlugins": {"paas-brain-nas@paas-brain-nas": true}}`. The plugin's version carries a fingerprint of its content, so a
   republish always reaches the laptops (Claude Code hands out a new copy only when the version string changes); people
   without auto-update run `claude plugin update paas-brain-nas@paas-brain-nas` or `/reload-plugins`. Each team repository
   also carries `check.py` and a `.gitlab-ci.yml` that runs it: JSON, plugin shape, skills, no secrets in knowledge, caps.
8. Pushing is automatic on every path (the notes hook after each saved file, the Brain tab after each save, every session
   start and Brain tab opening syncs); the shared GitLab repository is always current. Publish a new plugin version with
   `publish.py <team> --to <url>` after a `git pull` of this repository: members pick it up at their next sync.
9. A new team: a folder `brain/teams/<name>/` with `team.json` and `persona.md` (plus its own rules file, skills, agents),
   `python3 brain/test_budgets.py` and `python3 brain/test_teams.py` green, then publish. `brain/teams/README.md` has the schema.

## Active Directory accounts on the multi-user VM

Everyone signs in to the web UI with their own domain account; nothing is created by hand, and the audit log, the chats and
the notes stay per person.

1. Join the VM (as root, RHEL 9): `dnf install sssd realmd oddjob oddjob-mkhomedir adcli samba-common-tools`, `realm join
   <domain> -U <admin>`, then in `/etc/sssd/sssd.conf` under the domain: `use_fully_qualified_names = False`,
   `case_sensitive = False`, `override_homedir = /home/%u`, `fallback_homedir = /home/%u`; `systemctl restart sssd`.
   Home directories at first login: `authselect enable-feature with-mkhomedir && systemctl enable --now oddjobd`.
   Check: `id <someone>` prints the domain groups, `getent passwd <someone>` a home under /home.
2. Who may sign in: put the AD group(s) into `/etc/paas/allowed-groups` (one per line; `paas-users` stays for local
   accounts), then re-run `sh brain/multiuser/install-shared.sh`: it gives those groups read access (ACLs) to
   `/opt/paas/marketplace` and `/opt/paas/teams`, which are otherwise readable by `paas-users` only because they can hold
   MCP tokens. The gate lower-cases the typed name and checks membership with `id -nG`; the password check is `su` through
   PAM, so it works for AD and local accounts alike.
3. At a person's first sign-in the gate runs `paas-user provision <name>` (home, links to the shared brain, UI plugins,
   marketplace defaults). No team is switched on: the person picks one in the Brain tab, Team card (No team / SAN / NAS, one
   click, then a new chat), or root sets it with `paas-user team <name> <team>`. Nothing else to do per person.
4. RAM: the gate stops a person's UI instance after `GATE_IDLE_MINUTES` (default 120) without a request, an open WebSocket
   or a running `claude`; the next request starts it again within seconds and the sign-in cookie stays valid. So the VM
   carries the people active now (about 100-150 MB each), not the headcount. Set the minutes in `paas-gate.service`
   (`Environment=GATE_IDLE_MINUTES=60`; 0 disables). Local accounts keep working as before (`paas-user add`).

## Sharing the brain through GitLab (no team profile)

1. In GitLab create an **empty** project (default branch `main`, no README). Give everyone who should see the team knowledge the **Developer** role.
2. Install with its url: `sh install-vm.sh` then `sh brain/install.sh --brain-remote <url>` (or `BRAIN_REMOTE=<url>`; re-running is safe). Use an ssh url with the person's own key, or an https url with a token kept by git's credential helper (`git config --global credential.helper store`), never in the brain or the url written into notes.
3. Shared: `notes/<topic>.md`, `captures/`, `incidents/`, `tool-map.md`. Personal, never in the history: `notes.md` and `environment.md` (management IPs, owners). The library, inbox and plugins stay local.
4. Every saved note is committed and pushed (offline is fine, the next sync retries); every session start pulls with rebase and says `shared brain: in sync` or `N ahead, M behind`. By hand: `python3 ~/.claude/hooks/notes-check.py --sync`. The Status tab shows the same under Notes.
5. Conflict (two people changed the same line): the sync aborts and names the files. In `~/.claude/brain` run `git pull --rebase`, edit the marked files, `git add` them, `git rebase --continue`, then `notes-check.py --sync`.
6. The code repository itself: `git remote add gitlab <url> && git push --mirror gitlab`, or GitLab's pull mirroring from GitHub. It is about 10 GB because the library parts are in its history.

## 3. Afterwards

- Every suite: `sh scripts/run_tests.sh`. Installers end to end: `sh brain/e2e/run.sh` (Rocky Linux 9 containers, docker).
- Sign out of kb.netapp.com once the KB export is done (invalidates the token you used).
- Vendor content remains the vendors' copyright, kept for internal reference.
- The web UI is installed by `install-vm.sh` (`NO_UI=1` skips it). Multi-user VM: `sh brain/multiuser/install-multiuser.sh` runs every step in order (the "Owner's checklist" section); an update is `git pull` and the same command.
