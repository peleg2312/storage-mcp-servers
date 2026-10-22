# MDS MCP server (read-only, token auth)

Packaging of the community [alecharn/mds-mcp](https://github.com/alecharn/mds-mcp) server (commit in
`UPSTREAM_COMMIT`, `main.py` unchanged, upstream docs in `README.upstream.md`) with:

- **Bearer-token auth** and `/healthz`, same as the PowerMax and UCS Central servers (`mcp_auth.py`).
- **Stricter command guard** on top of upstream's show-only check: rejects `;`, `|`, `>`, backticks
  and newlines, so only one plain `show` command can ever reach the switch.
- **Detailed instructions** for the connecting model (IDs, workflows, how to read CRC / optics /
  TxWait / B2B credit counters, cross-system WWPN tracing with UCS Central and PowerMax).
- **Prompts**: `fabric_health_check`, `check_host_connectivity`, `investigate_slow_drain`, `port_history`.
- 63 upstream tools (zoning, device-alias, FLOGI/FCNS, VSANs, interfaces, counters, transceivers,
  environment, logging) plus Generative UI charts in clients that support MCP Apps.
- **4 extra tools** (`mds_extra.py`), for 67 in total:
  - `run_show`: any single `show` command; JSON when the switch supports it, otherwise text
    (NX-API `cli_ascii`), with `grep` / `tail_lines` filtering. `show tech-support` is refused.
  - `show_logging_onboard`: OBFL history (error-stats, txwait, rxwait, credit-loss, datarate, ...),
    optionally per module.
  - `get_log_events`: syslog parsed into events (severity, facility, event code, interfaces, VSAN)
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
docker load -i mds-mcp-2.1.tar.gz
oc create secret generic mds-mcp-env --from-env-file=.env
oc apply -f openshift.yaml    # set the image first
claude mcp add --transport http mds http://HOST:8000/mcp --header "Authorization: Bearer $TOKEN"
```
`test_wrapper.py` runs the tools against a fake NX-API and checks that chained/non-show commands are blocked.
