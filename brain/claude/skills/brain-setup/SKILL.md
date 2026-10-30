---
name: brain-setup
description: Inventory the connected MCP servers and the environment, then write ~/.claude/brain/tool-map.md and draft ~/.claude/brain/environment.md. Use on first install, after adding or upgrading an MCP server, or when asked to refresh the tool map.
when_to_use: Trigger phrases - "/brain-setup", "refresh the tool map", "list every tool of every MCP server", "draft environment.md from what you see", "I added a new MCP server"
disable-model-invocation: true
---
# Brain setup

Goal: Claude knows the exact tool names of every storage MCP and the shape of the environment.
Read-only: only list/get/show tools.

## 1. Tool map
For every connected MCP server (kuparashit, Aria/vROps, ontap, harvest, mds, ucsc, powermax, the docs MCP
(docs-search or docs-local, whichever is connected) and any other), list its tools from your own tool list. The
map is loaded in every session of every user, and Claude Code already shows each tool's own description, so write
only what the descriptions do not say (about 3-6 lines per server, the whole file under ~60 lines):
- server name as used in tool names (`mcp__<server>__...`) and the full names of its 3-6 entry tools: the
  overview / health / locate / trace tool to start with, and which question from the "Sources" table each answers
- parameter quirks you found (exact formats, required ids, slow calls, limits)
- any tool that looks like it can change something (create/delete/modify/set/...): list those under
  "DO NOT USE" so they are never called
- MCP prompts (`/` recipes, not tools) under "Not tools", with the tools they call
Pay special attention to **kuparashit**: `overview` (vCenters covered, snapshot times, warnings) and
`fields` / `relationships`; record the real field names and one tested call each for pWWN → ESX → NAAs and
NAA → datastore / RDM / VM / ESX.

Write the result to `~/.claude/brain/tool-map.md` (replace the whole file).

## 2. Environment draft
Using only list tools, collect:
- arrays: PowerMax (list_arrays: serials, models), ONTAP clusters/SVMs, PowerFlex if visible anywhere
- fabrics: MDS switches (list_switches), VSANs, which switch is fabric A/B (ask if unclear)
- vCenters / clusters (kuparashit or Aria)
- UCS domains, FIs and VSANs (ucsc)
- naming patterns: sample 10-20 names each of ESX hosts, storage groups, igroups, zones, device-aliases,
  datastores, and describe the pattern you see
- Trident / CSM: look for volume / LUN names starting with `trident` or other CSI-looking prefixes and
  hosts/igroups named like OpenShift workers
- versions: ONTAP version per cluster, PowerMaxOS / Unisphere version (from the tools); ask for Trident,
  CSM / CSI driver, NX-OS and ESXi versions (no tool shows them) - they select the versioned doc products

Show the draft to the user, ask him to confirm or correct the uncertain items (fabric A/B, thresholds,
prefixes, ownership), then write `~/.claude/brain/environment.md`, keeping anything he already filled in.

## 3. Smoke test
Run one cheap call per server (e.g. list arrays, list switches, docs list_sources) and report a table:
server | reachable | tools | notes. Flag any server whose tools failed. For the docs MCP, note which server
answered (docs-search or docs-local) and that list_sources matches `~/.claude/brain/library/MANIFEST.md`.
