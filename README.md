# Storage MCP servers (read-only)

Four read-only MCP servers for the SAN/storage stack, all with bearer-token auth, multi-instance
config from one Secret, and built-in guidance so a connecting Claude knows how to use them.

| Server | Talks to | Tools | Image |
|---|---|---|---|
| [`powermax-mcp`](powermax-mcp/) | Dell PowerMax / VMAX via one or many Unisphere servers | 28 | `images/powermax-mcp-2.0.tar.gz` |
| [`ucsc-mcp`](ucsc-mcp/) | Cisco UCS Central (one or many): inventory, faults, service profiles, FI FC uplinks/port-channels/errors, vHBA pinning, per-host SAN trace | 26 | `images/ucsc-mcp-2.2.tar.gz` |
| [`docs-search-mcp`](docs-search-mcp/) | Offline documentation + bug library: NetApp docs (ONTAP, SAN hosts, VMware tools, EMS...), Trident, Harvest, Dell CSM, PowerMax, PowerFlex, the Trident/Harvest/CSM bug trackers, KB pointers, your saved KBs and runbooks. Air-gapped mode: library baked into a dated image (`bundle/build-offline.sh`) | 4 | `images/docs-search-mcp-1.1.tar.gz` (base; build the offline image with the script) |
| [`brain`](brain/) | **Not a server**: the Claude Code "brain" for the VM: CLAUDE.md (role, rules, ID decoding, path model), 17 SAN skills, 6 agents, read-only safety hook, `install.sh` | - | - |
| [`library`](library/) | **Not a server**: the prebuilt documentation library (NetApp ONTAP + Trident docs and KB, EMS references, Dell CSM / CSI / PowerMax / PowerFlex docs, VMware KB pages) as 45 MB git parts + `MANIFEST.md`. `install-vm.sh` installs it with the brain and a dependency-free MCP server `docs-local`; `build-offline.sh --from-library` bakes it into the docs-search image | - | `library/docs-library-<date>.tar.gz.part-*` |
| [`mds-mcp`](mds-mcp/) | Cisco MDS switches via NX-API (wraps [alecharn/mds-mcp](https://github.com/alecharn/mds-mcp)): all show commands incl. text-only ones, parsed syslog, OBFL, WWPN trace, zone check, port-channel health, error scan | 72 | `images/mds-mcp-2.2.tar.gz` |

The three share one WWPN-based workflow, so Claude can trace a host's SAN paths end to end:

```
UCS  trace_service_profile_san   vHBA WWPN, fabric, VSAN, adapter link, FI uplinks / port-channel, errors
 -> MDS  trace_wwpn               FLOGI on the FI port-channel (NPV), active zones, partners logged in, port errors
        port_channel_health       FI <-> MDS port-channel members, speed, credits, errors
 -> PowerMax  find_wwpn           initiator -> host -> masking view -> storage group -> array ports
```

## Offline VM in one command

On the VM that runs Claude Code (python3 + the git clone, nothing else):
```bash
git clone https://github.com/peleg2312/storage-mcp-servers.git && cd storage-mcp-servers
sh install-vm.sh        # brain (CLAUDE.md, skills, agents, hook) + documentation library + MCP server docs-local
claude                  # then:  /brain-setup
```
The MCP servers below (PowerMax, UCS, MDS, docs-search on OpenShift) are added on top with `claude mcp add`.

## Get the images

Each image is split into 45 MB parts (GitHub refuses files over 100 MB). Join and load:
```bash
git clone https://github.com/peleg2312/storage-mcp-servers.git && cd storage-mcp-servers
./images/join.sh                                  # rebuilds the .tar.gz files and checks SHA256
docker load -i images/powermax-mcp-2.0.tar.gz     # same for ucsc-mcp-2.2, mds-mcp-2.2, docs-search-mcp-1.1
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

Each server's README has the full tool list, configuration and client setup. Tests:
`powermax-mcp/test_readonly.py`, `ucsc-mcp/test_readonly.py`, `mds-mcp/test_wrapper.py` (run inside the image).

## Read-only guarantees

- **PowerMax**: only `GET` and the performance query `POST`s (`/performance/<cat>/keys|metrics`) can
  leave the process; every other method or URL is refused before it is sent.
- **UCS Central**: only `aaaLogin/Refresh/Logout/KeepAlive` and `configResolve*` XML methods are sent;
  SDK write helpers raise.
- **MDS**: only one plain `show` command per call (upstream show-only check plus a block on `;`, `|`,
  `>`, backticks and newlines); every tool argument is validated.

`mcp_auth.py` is identical in the three folders so each image builds on its own.
