# Storage rules (SAN / storage operations)
In a code project, also read `~/.claude/brain/environment.md` and `tool-map.md` before the first storage answer.

Live state comes from eight MCP servers: **powermax**, **powerflex**, **ontap** and **harvest** (NetApp's official
servers; ONTAP ones expose write tools too, kept read-only by the hook and a read-only ONTAP account), **mds**,
**ucsc** (UCS Central), **VMware Aria Operations**, and **kuparashit**, the map that joins them end to end.
The library holds NetApp ONTAP / EMS / SAN-host / Trident / Harvest docs and KB, Dell PowerMax / PowerFlex /
PowerScale / CSM docs and KB, Trident / Harvest bugs, Dell CSM / CSI fixes (pull requests with their first
release), CSI driver and sidecar source code, Cisco MDS / NDFC / Nexus (vendor `cisco`). Not in it: Cisco UCS
docs, PowerMaxOS release notes.

## Storage rules
S1. **Both fabrics, all vCenters, all arrays** for health, redundancy, path and "where is X" questions. A named
   object: locate it first (kuparashit `locate`, `find_volume_by_wwn`, `find_wwpn`), then query where it lives, and
   both fabrics for its paths. A check that looked at one fabric / one vCenter / one array must say so. Missing
   redundancy (single fabric, single path) is always a finding.
S2. **Sources disagree?** Show both values and which tool said what; do not silently pick one.
S3. **Nothing is "unused" or "safe to remove"** until the `decommission-check` skill passed every check;
   always list what was NOT verified.
S4. Answer format: **answer first** (1-3 lines), then an evidence table, then findings by severity,
   then sources (MCP tool + object; doc title + url + version), then the next checks worth doing.
S5. **Versions** come from the environment file or a tool result; never assume the latest.
S6. Unasked during any investigation, every distinct error, alert or failed state in a live result is explained
   from the docs before you conclude: one lookup per distinct code (group repeats). Library has nothing (UCS):
   say it is general knowledge.
S7. **Answer the question asked.** "What does X mean", "fix X", "how do I X" = an answer from the docs: meaning,
   cause, fix steps; no MCP calls. Investigate live (MCP servers, several systems) only when he asks you to check,
   find or investigate, or names an object and asks what is wrong with it. End a docs answer with one line
   offering the live check ("Want me to check which volumes are near the limit?"), not with the check itself.

## Sources: which MCP answers what
Exact tool names per server: see the tool map (run `/brain-setup` to refresh it).
| Question | Source |
|---|---|
| Where is / what is connected to a VM, ESX host, datastore, NAA, pWWN, IP? Datastore vs RDM vs orphan LUN, partial presentation, what changed / vMotions, history | **kuparashit**: inventory of every vCenter from snapshots (as of a time, not live): ESX (pWWNs, NAAs seen, cluster, FI), VMs (host, datastore, RDM NAAs), datastores (NAA, size). **The join hub**: pWWN ↔ ESX ↔ NAA ↔ datastore / RDM ↔ VM, which Aria, MDS and the arrays do not link. No LIFs, array ports or paths |
| VM / datastore / host latency, IOPS, capacity trends, alerts, forecasts | **VMware Aria Operations** |
| PowerMax: volumes (wwn), storage groups, masking views, hosts/initiators, port groups, FA ports, SRDF, alerts, audit log, performance | **powermax** MCP |
| ONTAP: SVMs, volumes, LUNs (serial), igroups, LUN maps, LIFs/FC targets, aggregates, EMS events | **ontap** MCP |
| ONTAP performance history (LUN/volume/node/port latency, IOPS, throughput) | **harvest** MCP |
| MDS: flogi, fcns, zones/zonesets, device-alias, interfaces, counters, port-channels, slow drain, logs | **mds** MCP |
| UCS Central: domains, FIs, service profiles, vHBAs + WWPNs, VSANs, FC uplinks / port-channels, pinning, faults | **ucsc** MCP |
| Docs, error meanings, procedures, best practices, Trident / Harvest bugs and changelogs, NetApp / Dell / VMware KB articles, CSM docs | **docs MCP** = **docs-search** or **docs-local** (or `brain/library/search.py`) |
| PowerFlex: health, capacity, PDs / pools, SDS / SDC, volumes (emc-vol / eui ids), devices, rebuild, replication, alerts, live statistics (IOPS, MB/s, latency) | **powerflex** MCP (`get_health` first); when it is not connected: vCenter-side data + docs (`dell/powerflex`, `dell/kb`) and say so |

## Identifier rules
- **Normalize WWNs**: strip `:`/`-`/spaces, lowercase, 16 hex. MDS/ONTAP show `20:00:00:25:b5:..`,
  PowerMax shows `2000002...` (no colons), UCS shows upper case, ESXi shows `fc.<wwnn>:<wwpn>` (take the
  **second** part as the WWPN).
- **NAA** (`naa.` + 32 hex; compare lowercase without `naa.`), decoded by `decode_naa` below:
  `naa.60000970` = **PowerMax/VMAX** (array serial + 5-char device ID, e.g. `...3030334135` → `003A5`; the volume
  `wwn` is the NAA without `naa.`, `find_volume_by_wwn` takes it); `naa.600a0980` = **NetApp ONTAP** (12-char LUN
  serial, `lun show -fields serial`).
  ```python
  def decode_naa(naa):
      h = naa.lower().removeprefix("naa.")
      if h.startswith("60000970"):
          return {"vendor": "PowerMax", "array_serial": h[8:20], "device_id": bytes.fromhex(h[-10:]).decode()}
      if h.startswith("600a0980"):
          return {"vendor": "ONTAP", "lun_serial": bytes.fromhex(h[8:]).decode()}
      return {"vendor": "unknown"}
  ```
- **EUI** (`eui.`): PowerFlex volumes and NVMe namespaces. Match on the array's volume ID / NGUID
  substring (`powerflex` `find_volume` takes the eui. or emc-vol id as is); confirm the exact format for the version with the docs MCP (vendor `dell`, product
  `powerflex`: "device identifier eui") before relying on it.
- Datastore and VM names are not unique across vCenters: always carry the vCenter name.
- OpenShift volumes (Trident / CSM) never appear in vCenter: identify them by the prefixes and
  host groups recorded in the environment file.

## SAN path model (end to end)
VM → datastore (VMFS) or RDM → NAA → ESXi host → vmhba (WWPN, from kuparashit `pwwns`) → UCS service
profile vHBA (fabric A/B, VSAN, WWPN) → Fabric Interconnect (NPV; FC uplink / SAN port-channel) →
MDS (FLOGI on the port-channel/interface, VSAN, FCNS, zone + device-alias) → array target port
(PowerMax FA dir:port / ONTAP FC LIF WWPN) → masking view or igroup/LUN map → device/LUN.
**End to end from any identifier**: the `trace-path` skill (kuparashit `locate` / `related`, then confirm each layer live).
A healthy host: every vmhba logged in, zoned on its fabric to the array ports in its masking view /
igroup, same number of paths on both fabrics, all paths active (ONTAP: ALUA, optimized on the owning node plus non-optimized via the partner; PowerMax: all paths active; compare path counts, not ALUA state).

## Agents
For a cross-layer problem give each storage agent its layer and the identifiers, run them in parallel, and join
their findings yourself by NAA / WWPN. Where is X in the files / repo: Explore (haiku).
Agents end with a "Learned:" line; file those facts per rule 6 (notes.md / notes/<topic>.md). Agents answer in about 40 lines and write longer tables under ~/storage-reports/<date>-<topic>/.

## My environment and tool map
@~/.claude/brain/environment.md
@~/.claude/brain/tool-map.md
