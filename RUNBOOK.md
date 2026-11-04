# Runbook: from this repo to a working offline brain

Three places: **your PC** (has internet; pushes to GitHub), **GitHub**, **the offline VM** (runs Claude
Code). Every command you need, in order.

## 1. PC: complete the library (Dell PDFs, Dell KB, bug trackers, the rest of the NetApp KB, VAST, VMware)

The packed library in `library/` is what every VM installs. Its `library/VERSION` and `MANIFEST.md` say what is in it; a
document synced on the PC reaches the VMs only after step f repacks and the parts are committed.

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
python3 sync/sync_vast.py --dest work/docs               # VAST Data docs, KB and API reference (kb.vastdata.com, Markdown)
python3 sync/sync_techdocs.py --dest work/docs           # VMware vSphere guides from techdocs.broadcom.com (sources/techdocs-sections.txt)
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
sh ../scripts/run_tests.sh      # every retrieval set with its floor (VAST + VMware, PowerScale, NAS ... need the syncs above)
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
shows a person's use. Idle instances stop after `GATE_IDLE_MINUTES` (default 60, in `/etc/paas/gate.env`), so RAM follows the people active now.

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
runs the same dependency-free server in HTTP mode on port 8443 with the gate's certificate and a bearer token
(`/etc/paas/docs-token`; port and refresh interval in `/etc/paas/docs.env`). `https://<vm>:8443/mcp` is the library;
`https://<vm>:8443/mcp?team=nas` adds that team's knowledge: the service keeps its own clone of every team repository
under `/var/lib/paas-docs` (from the remote recorded in `/opt/paas/teams/<team>/team.json`), pulls it and rebuilds the
team's index every 10 minutes and at once when a member's notes hook pushes (it posts to `/refresh?team=<team>` with the
token from the team's `mcp.json`). `install-shared.sh` writes `docs-search` with its `?team=` url and the token into every team's `mcp.json`
when it publishes the teams; the plugin's `docs-local` uses it as a bridge on every machine without the library (a laptop),
and serves the library itself where it is installed (the VM), so there is one docs server name everywhere and one token. Health: `curl -k https://<vm>:8443/health`. The OpenShift
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

(A VM that already runs the 30.10 version: `UPGRADE.md`, which is this checklist plus moving the old team accounts' notes.)

Three things are yours to do by hand; everything else is one command that you re-run for every update.

**Before the command**

1. Packages, as root, from your satellite / local repo: `dnf install git python3 openssl acl diffutils hostname sssd realmd oddjob
   oddjob-mkhomedir adcli samba-common-tools`, and Claude Code installed so that `claude` is in root's PATH.
2. Active Directory: join the VM (`realm join`, sssd settings, mkhomedir; the "Active Directory accounts" section below). The
   AD group(s) whose members may sign in must resolve: `getent group storage-san-team`.
3. GitLab: one empty project per team (default branch `main`, every member Developer), and one access token for the VM: in the
   group that holds both projects, Settings, Access tokens, role Developer, scope `write_repository`: one group token covers
   every team repository and the installer asks for it once. Project tokens, one per team, work too: the installer asks per
   team (or `paas-user git-token gitlab.example.com/storage/brain-nas.git` by hand). Copy the token; you paste it once.
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

4. The teams' MCP servers: Brain tab, Team, More, Edit a team (address and token per server; saved into the team repository's
   `mcp.json`, built into the plugin's `.mcp.json` and pushed, so every member's Claude connects them at the next session). A
   server left on its placeholders is not connected and is named in a note at a switch.
5. Try it: sign in at `https://<vm>:3001` as an AD member, pick a team in the Brain tab, Team, start a new chat, ask one storage
   question, save one note and see the commit in GitLab with your name on it. Laptops: `claude plugin marketplace add <team url>
   && claude plugin install paas-brain-<team>@paas-brain-<team> && claude`, with the person's own GitLab login.

**Updates**: `git pull && sh brain/multiuser/install-multiuser.sh` (no flags). Members get the new plugin at their next session
start; laptops when Claude Code checks the marketplace. Nobody gets a team at sign-in; everyone picks one in the Brain tab.

## Teams: one brain per team, one account per person

Everywhere the team is the Claude Code plugin `paas-brain-<team>`, enabled from the person's clone of the team repository (the
plugin plus `knowledge/`), so the VM and every laptop run the identical thing: skills are `/paas-brain-<team>:<skill>`, the hooks
and `docs-local` come with the plugin, every saved note is committed and pushed, every session start pulls. A person is on one
team at a time; a switch takes seconds and never touches the skills and agents they added themselves (Market tab, Brain tab).
Only the way a machine gets the team differs:

| Machine | Get the team | Switch, state |
|---|---|---|
| Multi-user VM | the owner's checklist above; nobody has a team at sign-in | Brain tab, Team, one click (No team / SAN / NAS), then a new chat; root: `paas-user team dana nas` |
| Single VM from this repository | `sh install-vm.sh --team nas` (without `--team`: the SAN brain as plain files, no team repository); join the team's GitLab project with `paas-team remote nas <url>` | `paas-team` (state), `paas-team use san`, `paas-team list`, then a new Claude session |
| Laptop | `claude plugin marketplace add <team url> && claude plugin install paas-brain-nas@paas-brain-nas && claude`, with the person's own GitLab login; no GitLab there: copy a clone of the team repository over and add its folder instead of the url. `sh install-laptop.sh --team nas` from this repository adds the docs library; without it the plugin's `docs-local` bridges to the VM's `docs-search` | the same `paas-team` (copied to `~/.claude/tools` at the first session) |

**Publishing and updates.** Once per team: an empty GitLab project (default branch `main`, every member Developer) and
`python3 brain/teams/publish.py nas --to <url>`. After every `git pull` of this repository run it again (the multi-user installer
does it for every team): members get the new plugin at their next session start, laptops when Claude Code checks the marketplace
(by themselves: every session start pulls the team repository, and when it brought a new plugin the brain runs
`claude plugin marketplace update` + `claude plugin update` in the background, retried at the next start when GitLab did not
answer; the new version is active from the session after; by hand: the same two commands; the plugin's version carries a fingerprint
of its content, so every change is delivered). Many laptops without anyone typing: the team marketplace in the laptops' managed
settings (`/etc/claude-code/managed-settings.json` on Linux, the equivalent path on macOS):
`{"extraKnownMarketplaces": {"paas-brain-nas": {"source": {"source": "git", "url": "<team url>"}, "autoUpdate": true}},
"enabledPlugins": {"paas-brain-nas@paas-brain-nas": true}}`.

**Plain HTTP (no certificates on the PCs).** `sh brain/multiuser/install-multiuser.sh --plain-http` serves the docs MCP service
(8443) and the marketplace for other VMs (3443) as `http://` (remembered; `--https` goes back). The token is still required, but
nothing is encrypted: anyone who can capture traffic on that network can copy the docs token and read the docs and every team's
knowledge (notes, environment, incidents). The sign-in page stays HTTPS. Then a PC needs only `claude plugin marketplace add
<team url>` and `claude plugin install paas-brain-<team>@paas-brain-<team>` (and TCP 8443 open to the VM); other VMs connect
with `paas-market connect http://<vm>:3443 <token>`. Team repositories may be on an `http://` GitLab too.

**A new PC or laptop joins with one command** (Claude Code and git installed, the person's GitLab login): `git clone <team url>
brain-<team>` then `sh brain-<team>/join.sh` (Linux / macOS; sudo puts the certificate in the system store, `--no-sudo` uses
`NODE_EXTRA_CA_CERTS` in the shell profile) or `powershell -ExecutionPolicy Bypass -File .\brain-<team>\join.ps1` (Windows, no
admin): it trusts the VM's certificate, checks the docs port, installs the plugin and checks that Claude Code connects `docs-http`,
saying what to fix when a step fails. The docs port is 8443 (`/etc/paas/docs.env`); to change it: `sh brain/multiuser/install-multiuser.sh
--docs-port <port>` (the firewall, every team plugin's `docs-http` and the Market's docs items follow; PCs get the new address with
their next plugin update).

**Docs on a laptop.** The team plugin carries `docs-http`: the VM's docs service for the team (`https://<vm>:8443/mcp?team=<team>`:
its library and the team's knowledge), a native Claude Code connection, no Python needed, on Windows too. It is in the plugin when
the team was published with the VM's docs address (the multi-user installer does that; by hand: `publish.py <team> --to <url>
--docs-search https://<vm>:8443/mcp --docs-token-file /etc/paas/docs-token`). Once per laptop: TCP 8443 open to the VM, and the VM's
certificate trusted (Claude Code trusts the operating system's store): Windows, PowerShell `Import-Certificate -FilePath
paas-ui.crt -CertStoreLocation Cert:\CurrentUser\Root`; RHEL `cp paas-ui.crt /etc/pki/ca-trust/source/anchors/ && update-ca-trust`;
Ubuntu `cp paas-ui.crt /usr/local/share/ca-certificates/ && update-ca-certificates`; or `NODE_EXTRA_CA_CERTS=<path>` set before
`claude` starts (a settings.json `env` entry comes too late). The certificate: `/etc/paas/tls/paas-ui.crt` on the VM, also
`lib/paas-ui.crt` in the plugin. Check: `claude mcp list` shows `plugin:paas-brain-<team>:docs-http ... Connected`. The plugin's
`docs-local` serves the team knowledge from the person's clone (it needs Python 3; on the VM it has the library too, and the
VM's managed settings switch `docs-http` off there so the docs are not listed twice). Another team's docs on a laptop (the VM
Market's `docs-http-<other>`): `claude mcp add --transport http docs-http-<other> "https://<vm>:8443/mcp?team=<other>" --header
"Authorization: Bearer <docs token>"`.

**A team with its own documents** instead of the general library: `"library": "<name>"` in its `team.json`, then on the VM
`paas-library add <name> <folder of their documents> --to <vendor>/<product>` and the installer command (publishes the team,
adds its `docs-http-<team>` Market item). `brain/teams/README.md`, "A team with its own library".

**The team's MCP servers** are set once in the Brain tab, Team, More, Edit a team (address and token per server, into the team
repository's `mcp.json` and the plugin's `.mcp.json`; readable by the team's GitLab members by your decision, so read-only tokens,
rotated when someone leaves). **A new team**: a folder `brain/teams/<name>/` with `team.json` and `persona.md` (plus its own rules,
skills, agents), `python3 brain/test_budgets.py` and `python3 brain/test_teams.py` green, then publish. The team definition, the
Brain tab's team editor, what the Market tab shows, the CI gate and the knowledge flow: `brain/teams/README.md`.

## The Flashback team (backup and restore)

The team `flashback` (`brain/teams/flashback`): Commvault (three CommCells), Veeam 13 / Veeam ONE, OADP with the HyperShift
plugin on the MCE clusters, NetApp / PowerMax / PowerFlex snapshots and replication. Its own docs library `flashback`, not the
general one. Once, in this order:

1. **The library** (a machine with internet, from this repository): `sh docs-search-mcp/sources/flashback/build-library.sh`
   (Commvault 11.36 = `2024e`, 11.40, 11.42, 11.44; Veeam 13 guides; the OCP 4.18 / 4.20 / 4.22 backup and hosted control
   plane guides for OADP 1.4 / 1.5 / 1.6; oadp-operator, hypershift-oadp-plugin, HyperShift DR, Velero; the NetApp / Dell
   data-protection part of the general library; first run about two hours, then incremental) →
   `work/flashback/flashback-library-<date>.tar.gz` + `.sha256`. Carry both in. 11.38 is not fetched: the Commvault site's
   robots.txt disallows it.
2. **On the VM as root**: `paas-library import flashback flashback-library-<date>.tar.gz`, then `paas-library list`.
3. **The team**: an empty GitLab project, `python3 brain/teams/publish.py flashback --to <url>` (or the multi-user installer,
   which publishes every team; add the team's AD group to its `--groups`), members switch in the Brain tab (Team: Flashback).
4. **Commvault MCP** (Commvault's official server, one per CommCell, run where it reaches the CommServe; streamable-http):
   Brain tab, Team, More, Edit a team: `commvault-env1`, `-env2`, `-env3`: url `http://<host>:<port>/mcp`, the header
   `Authorization` = the secret the server's setup stored (no "Bearer"). Use a Commvault user with view-only rights: the guard
   blocks the job-control tools anyway (kill, suspend, resume, resubmit, schedule changes) and asks before a manual backup.
   Rename the three servers to your environments' names in team.json and the agents before the first publish, or keep env1-3
   and write which is which in environment.md.
5. **ontap / powermax / powerflex**: the same servers as the SAN team (addresses and read-only tokens in the editor).
6. **OADP**: no MCP: members run `oc` against the MCE clusters (their own kubeconfig; reads pass, `oc create` of a Restore
   asks). Veeam: no MCP: the skills give PowerShell to run on the VBR server and read the pasted output.
7. In a member's first chat: `/paas-brain-flashback:brain-setup`, then fill `environment.md` (CommCells, versions, MediaAgents,
   libraries, Veeam proxies / repositories, MCE clusters, RPO / RTO).

## Models and the context window (multi-user VM)

The default model is plain **Opus** (`"model": "opus"` in `/etc/claude-code/managed-settings.json`); **Opus (1M context)** stays
in the web UI's model picker and in `/model opus[1m]` for a chat that needs it. The installer no longer sets
`CLAUDE_CODE_DISABLE_1M_CONTEXT` (that variable hides the 1M variants) and removes it when an earlier update left it there.

Behind the gateway Claude Code does not recognise the model name, assumes a 200,000-token window and summarises a chat
(auto-compact) at about 160-170k. To give the regular model a larger window, as root: the **Users** tab, *Chat context
window*, or

```sh
paas-user context 300000      # 100000-1000000 (300k works too); `paas-user context` prints it; `default` goes back to 200000
```
It sets `CLAUDE_CODE_MAX_CONTEXT_TOKENS` in the managed settings (it applies to the gateway's model name without `[1m]`, so
Opus 1M keeps 1M), removes `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (it would shrink every model, 1M included) and gives the web UI's
context counter the same number. New sessions get it, terminal and web UI. Set it no higher than the model behind the gateway
really accepts, or long chats fail with a "prompt too long" error instead of being summarised.

## Active Directory accounts on the multi-user VM

Everyone signs in to the web UI with their own domain account; nothing is created by hand, and the audit log, the chats and
the notes stay per person.

1. Join the VM (as root, RHEL 9): `dnf install sssd realmd oddjob oddjob-mkhomedir adcli samba-common-tools`, `realm join
   <domain> -U <admin>`, then in `/etc/sssd/sssd.conf` under the domain: `use_fully_qualified_names = False`,
   `case_sensitive = False`, `override_homedir = /home/%u`, `fallback_homedir = /home/%u`; `systemctl restart sssd`.
   Home directories at first login: `authselect enable-feature with-mkhomedir && systemctl enable --now oddjobd`.
   Check: `id <someone>` prints the domain groups, `getent passwd <someone>` a home under /home.
   If the join fails, test the domain with `kinit` first (`dnf install krb5-workstation`; from a real terminal, not a
   script; the realm in capitals exactly as `realm discover <domain>` prints it): "KDC has no support for encryption type"
   means the domain controllers speak RC4 only and RHEL 9 refuses it: `update-crypto-policies --set DEFAULT:AD-SUPPORT-LEGACY`
   (`DEFAULT:AD-SUPPORT` on 9.0 / 9.1) and, if `/etc/crypto-policies/back-ends/krb5.config` still lists no `rc4-hmac`, a file
   `/etc/krb5.conf.d/00-ad-rc4.conf` with `[libdefaults]` / `permitted_enctypes = aes256-cts-hmac-sha1-96 aes128-cts-hmac-sha1-96
   rc4-hmac`; in FIPS mode RC4 is impossible and the AD team must enable AES on the domain. "KDC reply did not match
   expectations" means the realm is spelled differently: use the discovered spelling, or `kinit -C` and `canonicalize = true`
   under `[libdefaults]`. `KRB5_TRACE=/dev/stderr kinit ...` shows what was offered and what the KDC answered. Then
   `systemctl restart realmd` before `realm join`, and `kdestroy` afterwards.
   "Insufficient permissions to join the domain" means the account may not create or change the computer object (most
   domains set the join quota to 0; the OCUM / NetApp account is read-only). Best: the AD team pre-creates the object for
   this host in their OU with a one-time password, then `realm join <domain> --one-time-password='...'` needs no rights at all.
   Possible without any ticket: sssd without a join, as an LDAP directory plus a Kerberos password check, with the read-only
   account. `/etc/sssd/sssd.conf` (mode 600): `id_provider = ldap`, `auth_provider = krb5`, `ldap_uri = ldaps://<dc1>,
   ldaps://<dc2>`, `ldap_search_base = DC=...`, `ldap_schema = ad`, `ldap_id_mapping = True`, `ldap_referrals = False`,
   `ldap_default_bind_dn = <account>@<domain>` (or its full DN), `ldap_default_authtok_type = password`, `ldap_default_authtok =
   <its password>` (the file is root-only, mode 600; sssd's obfuscation is deprecated and only cosmetic), `ldap_tls_cacert = <the domain CA, from the AD team or openssl s_client -showcerts>`,
   `krb5_realm = <REALM>`, `krb5_server = <dc1>, <dc2>`, `krb5_canonicalize = true`, plus the same `use_fully_qualified_names`,
   `case_sensitive`, `override_homedir` / `fallback_homedir` lines as above; then `authselect select sssd with-mkhomedir --force`
   and `systemctl enable --now sssd oddjobd`. The gate needs only `id -nG` and `su`, which both work this way; what the join
   would add (site-based DC discovery, a computer identity) the brain does not use.
2. Who may sign in: put the AD group(s) into `/etc/paas/allowed-groups` (one per line; `paas-users` stays for local
   accounts), then re-run `sh brain/multiuser/install-shared.sh`: it gives those groups read access (ACLs) to
   `/opt/paas/marketplace` and `/opt/paas/teams`, which are otherwise readable by `paas-users` only because they can hold
   MCP tokens. The gate lower-cases the typed name and checks membership with `id -nG`; the password check is `su` through
   PAM, so it works for AD and local accounts alike.
3. At a person's first sign-in the gate runs `paas-user provision <name>` (home, links to the shared brain, UI plugins,
   marketplace defaults). No team is switched on: the person picks one in the Brain tab, Team (No team / SAN / NAS, one
   click, then a new chat), or root sets it with `paas-user team <name> <team>`. Nothing else to do per person.
4. RAM: the gate stops a person's UI instance after `GATE_IDLE_MINUTES` (default 60) without a request, an open WebSocket
   or a running `claude`; the next request starts it again within seconds and the sign-in cookie stays valid. So the VM
   carries the people active now (about 100-150 MB each), not the headcount. The minutes and the gate's port are in
   `/etc/paas/gate.env` (`GATE_IDLE_MINUTES`, 0 disables; `GATE_PORT`), kept across updates; `systemctl restart paas-gate`
   after a change. Local accounts keep working as before (`paas-user add`).

## 3. Afterwards

- Every suite: `sh scripts/run_tests.sh`. Installers end to end: `sh brain/e2e/run.sh` (Rocky Linux 9 containers, docker).
- Sign out of kb.netapp.com once the KB export is done (invalidates the token you used).
- Vendor content remains the vendors' copyright, kept for internal reference.
- The web UI is installed by `install-vm.sh` (`NO_UI=1` skips it). Multi-user VM: `sh brain/multiuser/install-multiuser.sh` runs every step in order (the "Owner's checklist" section); an update is `git pull` and the same command.
