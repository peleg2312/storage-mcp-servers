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

## Docs search: one library for every team, local or on OpenShift

There is one documentation library for everyone; a team changes which rules and skills point into it, not the library.
On the VM each Claude session searches it with `docs-local` (a stdio process over the shared read-only `docs.db`; the OS
page cache is shared, so ten people cost one copy), plus the person's own `brain.db` with the active team's notes pages and
incidents. The HTTP server `docs-search` on OpenShift (`docs-search-mcp/bundle/build-offline.sh --from-library`,
`openshift-offline.yaml`) serves the same tools to laptops without the library and to other VMs; give it a bearer token
and a TLS edge route, put it into each team's `mcp.json` through the team editor, and keep `docs-local` on the VM (it alone
sees the team knowledge index). Both may be connected at once: the brain uses whichever answers.

## Teams: one brain per team, one account per person

1. Pick the team at install time: `sh install-vm.sh --team nas` (single VM; `san` is the default and needs no flag), `sh
   install-laptop.sh --team nas` (laptop, plugin mode). `paas-team` shows the state, `paas-team use san` switches (under a
   second; start a new Claude session or a new chat afterwards), `paas-team list` the teams available.
2. Publish each team's repository once in GitLab (an empty project, default branch `main`): `python3 brain/teams/publish.py
   nas --to git@gitlab/storage/brain-nas.git`. It holds the plugin (`paas-brain-nas/`) and `knowledge/` (notes/, captures/,
   incidents/, tool-map.md). Members join it with `paas-team remote nas <url>` (or `install.sh --team nas --brain-remote <url>`,
   or `--team-source <url>` to install straight from it); their notes hook pushes every saved note there and every session
   start pulls. Re-run the publish after a `git pull` of this repository: members get the new skills at their next sync.
3. Multi-user VM: `sh brain/multiuser/install-shared.sh` publishes every team into `/opt/paas/teams/<team>` and installs
   `paas-team`. Record a team's GitLab url there: `python3 brain/teams/publish.py nas --to /opt/paas/teams/nas --remote <url>`
   (members then clone from GitLab, and fall back to the VM copy when it is unreachable). Give a person a team with
   `paas-user add dana --team nas`, `paas-user team dana nas`, or by AD group (step 3 of the next section). The Brain tab of
   the web UI has the same switch; a person may belong to one team at a time and change at will.
4. Laptop without this repository: `claude plugin marketplace add <team url> && claude plugin install
   paas-brain-nas@paas-brain-nas` (the standard way; the plugin sets the team up at its first session: knowledge clone, rules,
   `paas-team`), or `git clone <team url> brain-nas && sh brain-nas/install-team.sh` for the same without a first session; `paas-team
   export nas` on the VM writes the same as a zip into the Reports tab for a laptop without GitLab access (unzip, run
   `install-team.sh` inside). The docs library is not part of it: `install-laptop.sh` adds it.
5. Beyond the team: everyone adds skills and agents from the Market tab (`paas-market add skill/<name>`) or writes their own
   in the Brain tab; a team switch never removes or overwrites those. `paas-team use none` (Brain tab: "No team") leaves
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
3. Which team: `/etc/paas/team-groups`, lines `<team> <AD group>`, e.g. `san storage-san-team` and `nas storage-nas-team`.
   At a person's first sign-in the gate runs `paas-user provision <name>` (home, links to the shared brain, UI plugins,
   marketplace defaults) and the team of the first matching group is switched on. Nothing else to do per person.
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

- Sign out of kb.netapp.com once the KB export is done (invalidates the token you used).
- Vendor content remains the vendors' copyright, kept for internal reference.
- The web UI is installed by `install-vm.sh` (`NO_UI=1` skips it); multi-user setup, as root, in this order: `sh install-vm.sh`, `sh brain/multiuser/install-shared.sh`, `sh brain/multiuser/install-gate.sh`, then `install-shared.sh` again (starts the marketplace for other VMs once the gate made the certificate). Update a multi-user VM: `git pull && sh install-vm.sh && sh brain/multiuser/install-shared.sh`.
