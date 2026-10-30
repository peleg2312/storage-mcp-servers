"""
Wrapper around the upstream mds-mcp server (alecharn/mds-mcp, main.py unchanged):
  - bearer-token auth + /healthz (mcp_auth, same as the PowerMax and UCS Central servers)
  - a stricter command guard on top of upstream's show-only check
  - detailed instructions and SAN troubleshooting prompts for the connecting model
  - extra tools (mds_extra.py): any show command incl. text-only ones (OBFL, port-monitor...),
    parsed syslog events, onboard failure logging, slow-drain bundle, clear error explanations
"""

import re

import requests
from mcp.types import ToolAnnotations
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import main  # upstream server: reads MDS_<N>_* at import and builds `main.mcp`
import mcp_auth
import mds_extra
import mds_san

# --- defence in depth: one plain `show` command, no chaining/pipes/redirection ---
_upstream_validate = main._validate_command
_FORBIDDEN = re.compile(r"[;|>\n\r`]")  # command chaining, pipes, redirection, newlines


def _strict_validate(cmd: str) -> str:
    c = _upstream_validate(cmd)
    if _FORBIDDEN.search(c):
        raise ValueError(f"Refusing command {cmd!r}: only a single plain `show` command is allowed")
    return c


main._validate_command = _strict_validate
# one pooled session: keep-alive instead of a TLS handshake per command; retry once on a stale kept-alive socket
main.requests = requests.Session()
for _p in ("https://", "http://"):
    main.requests.mount(_p, HTTPAdapter(pool_maxsize=8, max_retries=Retry(total=1, allowed_methods=None)))

_RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
mds_extra.register(main.mcp, _RO)
mds_san.register(main.mcp, _RO)
# Upstream tools hidden to save ~36 KB of tools/list per session: each is `show ...` and so reachable through
# run_show (mapping in README). Also the generative-UI (Prefab) tools: Claude Code shows no Prefab UI.
HIDDEN = {
    "show_zone", "show_zone_active", "show_zone_name", "show_zone_vsan", "show_zone_name_vsan", "show_zoneset",
    "show_zoneset_active_vsan", "show_zoneset_name", "show_zoneset_vsan", "show_zoneset_name_vsan",
    "show_device_alias_name", "show_device_alias_pwwn", "show_hardware", "show_inventory", "show_module_uptime",
    "show_boot", "show_switchname", "show_cdp_neighbors", "show_hosts", "show_interface_bbcredit",
    "show_interface_transceiver", "show_interface_transceiver_detail", "show_interface_description",
    "show_interface_mgmt", "show_port_channel_usage", "show_running_config_interface_for",
    "show_interface_brief_for", "show_interface_transceiver_for", "show_interface_description_for",
    "show_flogi_database_for", "show_flogi_database_vsan", "show_fcns_database_vsan",
    "show_fcns_database_detail", "show_vsan_id", "show_vsan_usage", "show_vsan_membership",
    "show_vsan_membership_for", "show_interface_counters", "show_interface_counters_for",
    "show_interface_counters_brief_for", "show_interface_aggregate_counters_for", "show_users", "show_logging"
}
main.mcp.disable(names=HIDDEN | {"generate_prefab_ui", "search_prefab_components"}, components={"tool"})

INSTRUCTIONS = """\
READ-ONLY gateway to Cisco MDS Fibre Channel switches (NX-OS via NX-API): every tool runs one `show`
command, nothing can change the fabric. Never say you changed, cleared or fixed anything.

== IDENTIFIERS ==
- switch: name from list_switches (e.g. mds-fab-a, mds-fab-b); several switches usually = fabrics A and B:
  always say which switch a result came from. Switch logs use the switch's own clock / time zone.
- interface fc1/1, fc1/1/1 or port-channel10 (po10 ok); vsan 1-4094; pwwn 50:00:09:73:00:12:34:56.
- Output is NX-API JSON (TABLE_x / ROW_x; a single row may be an object, not a list) or plain text.

== START HERE (composites, all switches in one call) ==
- trace_wwpn(pwwn): FLOGI (switch / interface / VSAN / FCID), FCNS, aliases, every ACTIVE zone with it and
  its partners' login state, the login port's health (+ port-channel members for a UCS FI F-port-channel)
  and warnings (not logged in, not zoned, partner offline, VSAN mismatch, port errors).
- zone_check(a, b): are two WWPNs / aliases zoned together (active zoneset, per VSAN) and both logged in.
- port_channel_health: state, speed, trunk VSANs, per-member state / speed / B2B / errors; flags down,
  mismatched and erroring members. scan_port_errors: ports ranked by error / discard / CRC / link-failure /
  credit counters, plus ports down or errDisabled. flogi_summary: logins per interface / VSAN (many = NPV
  uplink, e.g. a UCS FI port-channel: where each UCS fabric attaches).
- slow_drain_check: OBFL txwait / rxwait / credit-loss / error-stats, port-monitor policy and warning log
  events per interface. get_log_events: syslog parsed into events (time, severity, code, interface,
  VSAN, message), newest first, with a summary; prefer it to `show logging` (max_severity=4 since_hours=24, or
  interface="fc1/5"). show_logging_onboard(section): OBFL history that survives reboots (error-stats,
  txwait, rxwait, credit-loss, datarate, environmental-history, exception-log; module=).
- run_show(command): ANY single show command (port-monitor, rdp, fcs ie, topology, counters detailed...);
  grep= instead of `| include`, tail_lines= for long output; pipes and tech-support are refused. Errors are
  explained in plain words; if a command is invalid on this NX-OS, try the closest variant. Parsed
  results keep the raw lines: confirm odd ones with run_show.

== WORKFLOWS (check both fabrics) ==
Health: list_switches -> show_version / show_module / show_environment -> show_interface_brief ->
  get_log_events. Zoning: show_zoneset_active (enforced) vs run_show "show zoneset vsan N" (configured),
  run_show "show zone name X vsan N"; devices talk only when both WWPNs (or aliases) share a zone of the
  ACTIVE zoneset in the same VSAN. Other show variants (vsan N, name X, detail, users, accounting,
  running-config interface ...) go through run_show. One port: show_interface_for -> show_interface_counters_detailed_for,
  show_interface_bbcredit_for -> show_interface_transceiver_detail_for -> OBFL -> get_log_events
  interface=; compare the ports of the same path. UCS FIs run NPV: server vHBAs log in on the MDS
  F-port(-channel) of that FI (FI A -> fabric A MDS).

== READING THE NUMBERS (rules of thumb) ==
- CRC / invalid CRC / link failures / sync loss growing -> physical: SFP, cable, patch panel. Short-wave Rx
  power below about -7 dBm is marginal, below the transceiver's low alarm a fault.
- TxWait, credit loss, B2B credit at 0, timeout discards: on an F-port -> slow-drain device (host / HBA
  behind it); on an ISL -> congestion spreading. Any OBFL txwait / rxwait entry on an F-port points to a
  slow device; entries at the same times on many ports -> fabric-wide congestion.
- Counters are cumulative since clear / boot: compare two readings before saying "increasing".
- Log events: PORT-*-IF_DOWN_* (LINK_FAILURE, NOS, OLS), *CREDIT_LOSS*, *TXWAIT* / *SLOWDRAIN* / PMON-*,
  ZONE-* merge / changes, FCNS / FLOGI rejects, PLATFORM / ENVMON; repeated IF_DOWN / IF_UP = flap.
"""

main.mcp.instructions = INSTRUCTIONS


@main.mcp.prompt()
def fabric_health_check() -> str:
    """Health report for every configured MDS switch."""
    return ("Produce a SAN fabric health report. For every switch from list_switches: show_version, "
            "show_module and show_environment (failed modules, fans, PSUs), show_interface_brief (ports "
            "down/errDisabled), show_interface_counters_brief (ports with errors or discards), "
            "show_zone_status, scan_port_errors, port_channel_health, "
            "get_log_events max_severity=4 since_hours=24 (summarise by event and "
            "interface), and show_logging_onboard error-stats for ports that look bad. Present a table per switch and a "
            "ranked list of issues with the next action for each.")


@main.mcp.prompt()
def check_host_connectivity(pwwn: str, vsan: int = 0) -> str:
    """Is this WWPN logged in and zoned correctly on both fabrics?"""
    v = f" in VSAN {vsan}" if vsan else ""
    return (f"Check the SAN connectivity of WWPN {pwwn}{v}: run trace_wwpn. For each zone partner (array ports), "
            "check they are logged in. If it logs in through a port-channel, run port_channel_health for it; "
            "otherwise check the port with show_interface_counters_detailed_for and "
            "show_interface_transceiver_detail_for. Report per fabric (switch), one row per path, and flag "
            "anything missing or erroring.")


@main.mcp.prompt()
def investigate_slow_drain(switch: str = "") -> str:
    """Find slow-drain / congested ports."""
    target = f"switch {switch}" if switch else "every switch"
    return (f"Look for slow drain and congestion on {target}: start with slow_drain_check, then for the "
            "ports it names (and the worst in show_interface_counters_brief) run "
            "show_interface_counters_detailed_for and show_interface_bbcredit_for (TxWait, credit loss, "
            "timeout discards), get_log_events interface=<port> since_hours=72, and the FLOGI database to "
            "identify the device behind each port. Rank ports by severity, give the times congestion "
            "happened, and say whether each looks like a slow end device or an ISL bottleneck.")


@main.mcp.prompt()
def port_history(interface: str, switch: str = "") -> str:
    """Full history of one port: errors, congestion, flaps, optics."""
    return (f"Give the full history of port {interface}{(' on ' + switch) if switch else ''}: current state and "
            "counters (show_interface_for, show_interface_counters_detailed_for), optics "
            "(show_interface_transceiver_detail_for), get_log_events interface=<port> last=9999, and OBFL "
            "error-stats, txwait and credit-loss filtered with grep on the port. Build a timeline, say whether the "
            "problem is physical (CRC/optics), congestion (txwait/credit loss) or the attached device, and "
            "who is logged in on it (run_show \"show flogi database interface <port>\").")


if __name__ == "__main__":
    mcp_auth.run(main.mcp)
