# Storage MCP servers (read-only)

Three read-only MCP servers for the SAN/storage stack, all with bearer-token auth, multi-instance
config from one Secret, and built-in guidance so a connecting Claude knows how to use them.

| Server | Talks to | Tools | Image |
|---|---|---|---|
| [`powermax-mcp`](powermax-mcp/) | Dell PowerMax / VMAX via one or many Unisphere servers | 28 | `images/powermax-mcp-2.0.tar.gz` |
| [`ucsc-mcp`](ucsc-mcp/) | Cisco UCS Central (one or many): inventory, faults, service profiles, FI FC uplinks/port-channels/errors, vHBA pinning, per-host SAN trace | 26 | `images/ucsc-mcp-2.2.tar.gz` |
| [`mds-mcp`](mds-mcp/) | Cisco MDS switches via NX-API (wraps [alecharn/mds-mcp](https://github.com/alecharn/mds-mcp)): all show commands incl. text-only ones, parsed syslog, OBFL, WWPN trace, zone check, port-channel health, error scan | 72 | `images/mds-mcp-2.2.tar.gz` |

The three share one WWPN-based workflow, so Claude can trace a host's SAN paths end to end:

```
UCS  trace_service_profile_san   vHBA WWPN, fabric, VSAN, adapter link, FI uplinks / port-channel, errors
 -> MDS  trace_wwpn               FLOGI on the FI port-channel (NPV), active zones, partners logged in, port errors
        port_channel_health       FI <-> MDS port-channel members, speed, credits, errors
 -> PowerMax  find_wwpn           initiator -> host -> masking view -> storage group -> array ports
```

## Get the images

Each image is split into 45 MB parts (GitHub refuses files over 100 MB). Join and load:
```bash
git clone https://github.com/peleg2312/storage-mcp-servers.git && cd storage-mcp-servers
./images/join.sh                                  # rebuilds the .tar.gz files and checks SHA256
docker load -i images/powermax-mcp-2.0.tar.gz     # same for ucsc-mcp-2.2 and mds-mcp-2.2
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
