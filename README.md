# Storage MCP servers (read-only)

Five read-only MCP servers for the SAN/storage stack, all with bearer-token auth, multi-instance
config from one Secret, and built-in guidance so a connecting Claude knows how to use them.

| Server | Talks to | Tools | Image |
|---|---|---|---|
| [`powermax-mcp`](powermax-mcp/) | Dell PowerMax / VMAX via one or many Unisphere servers | 26 | `images/powermax-mcp-2.0.tar.gz` |
| [`powerflex-mcp`](powerflex-mcp/) | Dell PowerFlex 3.x Gateway / 4.x-5.x PowerFlex Manager (one or many): health, capacity, inventory, replication, alerts, events, SDS network latency, NVMe hosts, OpenShift CSI lookups, all statistics | 29 | `images/powerflex-mcp-1.0.tar.gz` |
| [`ucsc-mcp`](ucsc-mcp/) | Cisco UCS Central (one or many): inventory, faults, service profiles, FI FC uplinks/port-channels/errors, vHBA pinning, per-host SAN trace | 26 | `images/ucsc-mcp-2.2.tar.gz` |
| [`docs-search-mcp`](docs-search-mcp/) | Offline documentation + bug library: NetApp docs (ONTAP, SAN hosts, VMware tools, EMS...), Trident, Harvest, Dell CSM, PowerMax, PowerFlex, the Trident/Harvest/CSM bug trackers, KB pointers, your saved KBs and runbooks. Air-gapped mode: library baked into a dated image (`bundle/build-offline.sh`) | 4 | `images/docs-search-mcp-1.1.tar.gz` (base; build the offline image with the script) |
| [`brain`](brain/) | **Not a server**: the Claude Code "brain" for the VM: CLAUDE.md (role, rules, ID decoding, path model), skills (`ls brain/claude/skills`), agents (`ls brain/claude/agents`), read-only safety hook, `install.sh`; team profiles in [`brain/teams`](brain/teams/README.md) (`san`, `nas`) | - | - |
| [`library`](library/) | **Not a server**: the prebuilt documentation library (NetApp ONTAP + Trident docs and KB, EMS references, Dell CSM / CSI / PowerMax / PowerFlex docs, VMware KB pages) as 45 MB git parts + `MANIFEST.md`. `install-vm.sh` installs it with the brain and a dependency-free MCP server `docs-local`; `build-offline.sh --from-library` bakes it into the docs-search image | - | `library/docs-library-<date>.tar.gz.part-*` |
| [`mds-mcp`](mds-mcp/) | Cisco MDS switches via NX-API (wraps [alecharn/mds-mcp](https://github.com/alecharn/mds-mcp)): all show commands incl. text-only ones, parsed syslog, OBFL, WWPN trace, zone check, port-channel health, error scan | 27 (70 registered, 43 hidden: use `run_show`) | `images/mds-mcp-2.2.tar.gz` |

The three share one WWPN-based workflow, so Claude can trace a host's SAN paths end to end:

```
UCS  trace_service_profile_san   vHBA WWPN, fabric, VSAN, adapter link, FI uplinks / port-channel, errors
 -> MDS  trace_wwpn               FLOGI on the FI port-channel (NPV), active zones, partners logged in, port errors
        port_channel_health       FI <-> MDS port-channel members, speed, credits, errors
 -> PowerMax  find_wwpn           initiator -> host -> masking view -> storage group -> array ports
```

**Every command for your PC and the VM, in order: [`RUNBOOK.md`](RUNBOOK.md).**
**Continuing the work with Claude Code on a PC: [`HANDOFF.md`](HANDOFF.md).**

## Install the brain: three ways

| Where | Install | Update |
|---|---|---|
| Laptop with Claude Code (macOS or Linux, connected or not): a plugin + the rules + the library, no web UI ([`brain/plugin`](brain/plugin/README.md)) | `git clone https://github.com/peleg2312/storage-mcp-servers.git && cd storage-mcp-servers && sh install-laptop.sh` | `git pull && sh install-laptop.sh` |
| Single VM (python3 + the git clone, nothing else): brain, library, `docs-local`, web UI | `sh install-vm.sh` | `git pull && sh install-vm.sh` |
| Multi-user VM (shared `/opt/paas`, read-only guard enforced, one Linux or Active Directory account per person) | `sh install-vm.sh` then `sh brain/multiuser/install-shared.sh` (as root) | `git pull`, then the same two lines |

Then start `claude` and run `/brain-setup`. `install-laptop.sh --no-library` skips the library; `--brain-remote <url>` shares the brain's git history.

**Teams.** `--team san` (default) or `--team nas` on any install picks a team profile ([`brain/teams`](brain/teams/README.md)): its
persona, storage rules, skills, agents and a knowledge folder the team shares through one git repository per team
(`python3 brain/teams/publish.py nas --to <gitlab url>`; `claude plugin marketplace add <url>` installs the brain from it
anywhere). `paas-team use nas` switches a person's brain in a second (`use none` for no team; a new Claude session uses it), and
everyone adds their own or marketplace skills on top. A laptop installs a team from its repository alone, the standard way:
`claude plugin marketplace add <url> && claude plugin install paas-brain-nas@paas-brain-nas` (the plugin sets the team up at its
first session, notes flow back to the repository). The NAS team covers
PowerScale (OneFS), VAST and ONTAP NAS; PowerScale and VAST have no MCP server yet, so those skills work from pasted output
and the docs library. On the multi-user VM people are Active Directory accounts (`RUNBOOK.md`), the team comes from an
AD group (`/etc/paas/team-groups`), and idle web UI instances are stopped after two hours so RAM follows the people
signed in, not the headcount.
The MCP servers below (PowerMax, UCS, MDS, docs-search on OpenShift) are added on top with `claude mcp add`.

## Install a team's brain on any machine

Any VM or laptop that has Claude Code, git and python3 3.9 or newer, and can reach the team's GitLab project:

```bash
claude plugin marketplace add git@gitlab.example.com:storage/brain-nas.git        # the team repository (ssh or https url)
claude plugin install paas-brain-nas@paas-brain-nas
claude                                                                 # first session: the plugin sets the team up
```
That first session clones the team's knowledge into `~/.claude/brain/teams/nas`, links the memory files into it, writes the
persona, the storage rules and the core rules (one import line in your `~/.claude/CLAUDE.md`), copies `paas-team` to
`~/.claude/tools`, and from then on every note is committed and pushed to the team, every session start pulls. You get the
team's skills (`/paas-brain-nas:<skill>`), agents, the seven hooks (read-only guard, docs hints and leads, notes scan,
lint, capture nudge, session start), the coding rules as a skill, and the team's MCP servers from its mcp.json. Updates
arrive with `claude plugin update paas-brain-nas@paas-brain-nas` or auto-update. Not in the plugin: the documentation
library (`sh install-laptop.sh --team nas` from this repository adds it and docs-local), the web UI, the dev tools. The library
and the team's knowledge are still searchable from the VM's `docs-search` service over HTTPS (`?team=nas`), which the team's
`mcp.json` points at once filled in (RUNBOOK, "Docs search").
No GitLab access: `paas-team export nas` on the VM gives a zip; unzip and run `install-team.sh` inside it.

## Get the images

Each image is split into 45 MB parts (GitHub refuses files over 100 MB). Join and load:
```bash
git clone https://github.com/peleg2312/storage-mcp-servers.git && cd storage-mcp-servers
./images/join.sh                                  # rebuilds the .tar.gz files and checks SHA256
docker load -i images/<name>.tar.gz              # one per *.tar.gz that join.sh rebuilt
docker tag powermax-mcp:2.0 <registry>/powermax-mcp:2.0 && docker push <registry>/powermax-mcp:2.0
```
Images are linux/amd64, run as a non-root random UID (OpenShift restricted SCC) with a read-only
root filesystem. Or build them in-cluster from source with [`openshift/buildconfigs.yaml`](openshift/buildconfigs.yaml).

## Deploy (each server)

```bash
openssl rand -hex 32                                   # token -> MCP_AUTH_TOKENS in .env
cp <server>/.env.example .env && vi .env               # add every Unisphere / UCS Central / MDS switch
oc create secret generic <server>-env --from-env-file=.env
oc apply -f <server>/openshift.yaml                    # set the image first
claude mcp add --transport http <server> http://<host>:8000/mcp --header "Authorization: Bearer <token>"
```
Use a separate token per server, a read-only account on every backend (Unisphere **Monitor** role,
UCS Central **read-only**, MDS **network-operator**), and a TLS edge Route if you expose them.

Each server's README has the full tool list, configuration and client setup. Tests: `sh scripts/run_tests.sh` (all of them; the mds ones need fastmcp 3.x + prefab-ui, else SKIP).
Tool counts: `grep -c '@mcp.tool' <server>/*.py` (mds: 27 visible, 70 registered; see mds-mcp/README.md).

## Read-only guarantees

- **PowerMax**: only `GET` and the performance query `POST`s (`/performance/<cat>/keys|metrics`) can
  leave the process; every other method or URL is refused before it is sent.
- **PowerFlex**: only `GET` and the read-only `POST`s (sign-in, `querySelectedStatistics`,
  `queryMdmCluster`, `queryBySelectedIds` / `queryIdByKey`, the 4.x metrics query) leave the process;
  every `.../action/...` change, `PUT`, `PATCH`, `DELETE` and `..` is refused before it is sent.
- **UCS Central**: only `aaaLogin/Refresh/Logout/KeepAlive` and `configResolve*` XML methods are sent;
  SDK write helpers raise.
- **MDS**: only one plain `show` command per call (upstream show-only check plus a block on `;`, `|`,
  `>`, backticks and newlines); every tool argument is validated.

`mcp_auth.py` is identical in the five server folders so each image builds on its own.

## License

The code in this repository is Apache-2.0 (`LICENSE`). Vendored plugins and skills keep their own LICENSE files; the vendor documentation inside `library/` and `docs-search-mcp/work/docs` stays under its vendors' terms and is redistributed only for the team's own air-gapped use.
