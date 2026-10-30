# MDS MCP server (read-only, token auth)

Packaging of the community [alecharn/mds-mcp](https://github.com/alecharn/mds-mcp) server (commit in
`UPSTREAM_COMMIT`, `main.py` unchanged, upstream docs in `README.upstream.md`) with:

- **Bearer-token auth** and `/healthz`, same as the PowerMax and UCS Central servers (`mcp_auth.py`).
- **Stricter command guard** on top of upstream's show-only check: rejects `;`, `|`, `>`, backticks
  and newlines, so only one plain `show` command can ever reach the switch.
- **Detailed instructions** for the connecting model (IDs, workflows, how to read CRC / optics /
  TxWait / B2B credit counters, cross-system WWPN tracing with UCS Central and PowerMax).
- **Prompts**: `fabric_health_check`, `check_host_connectivity`, `investigate_slow_drain`, `port_history`.
- 18 upstream tools kept visible (list_switches, version/module/environment, interface brief/counters,
  zone status, zoneset active, FLOGI/FCNS, device-alias, VSANs, port-channel summary, accounting log, per-port
  detail/bbcredit/transceiver); the other 43 and upstream's Prefab generative-UI tools are hidden with
  `main.mcp.disable(...)` (`HIDDEN` in `entry.py`) to save ~36 KB of tools/list per session. Each hidden
  tool is one `show` command, still reachable through `run_show`: `show_zone*`/`show_zoneset*` ->
  `show zone|zoneset [active] [name X] [vsan N]`; `show_device_alias_name|pwwn` -> `show device-alias name|pwwn X`;
  `show_flogi_database_for|vsan`, `show_fcns_database_vsan|detail` -> `show flogi|fcns database [interface X|vsan N|detail]`;
  `show_vsan*` -> `show vsan [N] [usage|membership [interface X]]`; `show_interface_*` hidden variants
  (`bbcredit`, `transceiver[ detail]`, `description`, `mgmt`, `counters[ brief]`, `*_for`, aggregate) ->
  `show interface [X] <same words>`; `show_running_config_interface_for` -> `show running-config interface X`;
  `show_hardware|inventory|boot|switchname|hosts|cdp_neighbors|module_uptime|port_channel_usage|users|logging`
  -> the same `show ...` words (for logging prefer `get_log_events`).
- **5 SAN troubleshooting composites** (`mds_san.py`):
  - `trace_wwpn`: one WWPN across all switches - FLOGI, FCNS, aliases, every active zone containing
    it with the other members and their login state, login-port health (and F-port-channel members
    for UCS FIs), and warnings (not logged in, not zoned, zone partner offline, VSAN mismatch).
  - `zone_check`: are two WWPNs/aliases zoned together in the active zoneset, and both logged in.
  - `port_channel_health`: per port-channel state, speed, trunk VSANs, and per member state, speed,
    B2B credits and error counters; flags down members, speed mismatch, erroring members.
  - `scan_port_errors`: ranks all interfaces by non-zero error/discard/CRC/credit counters; lists
    ports down or errDisabled.
  - `flogi_summary`: logins per interface/VSAN; shows which port-channels carry the UCS FIs.
- **4 extra tools** (`mds_extra.py`), for 27 tools in total:
  - `run_show`: any single `show` command; JSON when the switch supports it, otherwise text
    (NX-API `cli_ascii`), with `grep` / `tail_lines` filtering. `show tech-support` is refused, as are full `show running-config` / `startup-config` (a section such as `interface fc1/1` is fine) and snmp / tacacs / radius / aaa / user-account / crypto (secrets). A JSON body over `max_chars` (24000) is returned as text.
  - `show_logging_onboard`: OBFL history (error-stats, txwait, rxwait, credit-loss, datarate, ...),
    optionally per module.
  - `get_log_events` (default 50 events): syslog parsed into events (time, severity, event code, interfaces, VSAN)
    across all switches, newest first, with a summary by event and interface; filters for severity,
    time (switch clock), facility, text and interface.
  - `slow_drain_check`: OBFL txwait/rxwait/credit-loss/error-stats, port-monitor policy and
    warning-level log events by interface, in one call.
- **Plain-language errors**: role not allowed, command not valid on this NX-OS, switch unreachable,
  login refused - instead of raw NX-API JSON-RPC errors.

Requirements: NX-API enabled on each switch (`feature nxapi`), a **network-operator** (read-only)
account. Note `MDS_<N>_VERIFY_SSL` defaults to false.

## Run
```bash
docker load -i mds-mcp-2.2.tar.gz
oc create secret generic mds-mcp-env --from-env-file=.env
oc apply -f openshift.yaml    # set the image first
claude mcp add --transport http mds http://HOST:8000/mcp --header "Authorization: Bearer $TOKEN"
```
`test_wrapper.py` and `test_san.py` run the tools against fake NX-API output (realistic flogi/fcns/zoneset/port-channel/interface text) and check that chained or non-show commands are blocked.
