"""
Wrapper around the upstream mds-mcp server (alecharn/mds-mcp, main.py unchanged):
  - bearer-token auth + /healthz (mcp_auth, same as the PowerMax and UCS Central servers)
  - a stricter command guard on top of upstream's show-only check
  - detailed instructions and SAN troubleshooting prompts for the connecting model
  - extra tools (mds_extra.py): any show command incl. text-only ones (OBFL, port-monitor...),
    parsed syslog events, onboard failure logging, slow-drain bundle, clear error explanations
"""

import re

from mcp.types import ToolAnnotations

import main  # upstream server: reads MDS_<N>_* at import and builds `main.mcp`
import mcp_auth
import mds_extra

# --- defence in depth: one plain `show` command, no chaining/pipes/redirection ---
_upstream_validate = main._validate_command
_FORBIDDEN = re.compile(r"[;|>\n\r`]")  # command chaining, pipes, redirection, newlines


def _strict_validate(cmd: str) -> str:
    c = _upstream_validate(cmd)
    if _FORBIDDEN.search(c):
        raise ValueError(f"Refusing command {cmd!r}: only a single plain `show` command is allowed")
    return c


main._validate_command = _strict_validate

mds_extra.register(main.mcp, ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                                             idempotentHint=True, openWorldHint=True))

INSTRUCTIONS = """\
You are connected to a READ-ONLY gateway to Cisco MDS Fibre Channel switches (NX-OS via NX-API).
Every tool runs one `show` command; nothing can change the fabric. Never say you changed,
cleared or fixed anything.

== IDENTIFIERS ==
- switch: friendly name from list_switches (e.g. mds-fab-a, mds-fab-b). Several switches usually
  means two fabrics (A and B); always say which fabric/switch a result came from.
- interface: fc1/1, fc1/1/1 or port-channel10 (po10 is accepted).
- vsan: 1-4094. pwwn: 8 colon-separated hex bytes, 50:00:09:73:00:12:34:56.
- Output is the switch's NX-API JSON: tables are nested as TABLE_x / ROW_x; a single row may be
  an object instead of a list. Text-only commands come back as plain text.
- Switch log timestamps are in the switch's own clock/time zone.

== TOOLS BEYOND THE FIXED show_* SET ==
- run_show(command): ANY single `show` command, JSON when available, otherwise text. Use it whenever a
  dedicated tool doesn't exist (show port-monitor, show rdp fcid X vsan Y, show fcs ie, show topology,
  show interface fcX/Y counters detailed, show system internal ...). Use grep= instead of `| include`
  and tail_lines= for long output. Pipes and show tech-support are refused.
- get_log_events: syslog PARSED into events (severity, facility, event code, interfaces, VSAN), across
  all switches, newest first, with a summary by event and interface. Prefer it over show_logging.
  Typical: max_severity=4 since_hours=24; or interface="fc1/5" to see one port's history.
- show_logging_onboard(section): OBFL history that survives reboots: error-stats, txwait, rxwait,
  credit-loss, datarate, interrupt-stats, environmental-history, exception-log ... (module= for one
  line card). Use it to answer "has this port had errors/congestion before, and when".
- slow_drain_check: one call that gathers OBFL txwait/rxwait/credit-loss/error-stats, port-monitor
  policy and warning-level log events by interface, for one or all switches.
- Errors are explained in plain words (no permission for the role, command not valid on this NX-OS,
  switch unreachable, login refused). If a command is not valid, try the closest variant.

== WORKFLOWS ==
Fabric health: list_switches -> show_version / show_module / show_environment on each switch ->
  show_interface_brief (ports down or errDisabled) -> get_log_events max_severity=4 since_hours=24.
Where is a WWPN / host logged in: show_flogi_database (or _vsan) on each switch -> interface + VSAN
  + FCID; show_fcns_database_detail for the device type/features; show_device_alias_pwwn for its
  alias.
Zoning: show_zoneset_active_vsan (what is enforced) vs show_zoneset_vsan (configured);
  show_zone_name_vsan for one zone. A device can talk only if both WWPNs (or their aliases) are in
  the same zone of the ACTIVE zoneset in the same VSAN. Check both fabrics.
Port problems / slow drain: show_interface_for (state, speed, errors) ->
  show_interface_counters_detailed_for and show_interface_bbcredit_for (B2B credits, TxWait,
  timeouts/discards) -> show_interface_transceiver_detail_for (Rx/Tx power, temperature)
  -> show_logging_onboard error-stats / txwait for history -> get_log_events interface=... .
  Compare across the ports of the same path and both fabrics.
Congestion / slow drain: slow_drain_check first, then drill into the ports it names.
ISLs / port-channels: show_port_channel_summary, show_interface_for port-channelN.

== READING THE NUMBERS (rules of thumb) ==
- CRC / invalid CRC / link failures / sync loss growing -> physical layer: SFP, cable, patch panel.
- Optical Rx power below about -7 dBm on short-wave SFPs is marginal, below the transceiver's low
  alarm threshold is a fault; compare with the thresholds shown in the transceiver detail.
- TxWait, Tx credit-loss / B2B credit 0 time, timeout discards on an F-port -> slow-drain device
  (usually the host/HBA behind that port); on an ISL -> congestion spreading in the fabric.
- Counters are cumulative since last clear/boot; when possible compare two readings over time
  before calling something "increasing". OBFL gives the history with timestamps.
- OBFL txwait/rxwait entries are only written when waiting exceeded a threshold in the sample
  interval, so any entries at all on an F-port point to a slow device; many entries clustered at the
  same times across ports point to fabric-wide congestion.
- Log events to watch: PORT-*-IF_DOWN_* (LINK_FAILURE, NOS, OLS: physical/peer), *CREDIT_LOSS*,
  *TXWAIT*/*SLOWDRAIN*/PMON-* (port-monitor alerts), ZONE-*-*MERGE*/ZONE_* (zoning changes or merge
  failures), FCNS/FLOGI rejects, PLATFORM/ENVMON (hardware). Repeated IF_DOWN/IF_UP on one port = flap.

== CROSS-SYSTEM TRACING (if other MCP servers are connected) ==
UCS Central get_service_profile_vhbas / find_wwpn -> host WWPN, fabric, VSAN
-> here: FLOGI interface, zones in the active zoneset, port errors
-> PowerMax find_wwpn -> masking view, storage group, array ports (their WWPNs must log in to the
   same fabric and be in the same zone).
Use the same WWPN at every hop; present one row per path (fabric A and B).

== ANSWER STYLE ==
Lead with the conclusion, then the evidence (switch, interface, counters, zone names), then the
next check you recommend.
"""

main.mcp.instructions = INSTRUCTIONS


@main.mcp.prompt()
def fabric_health_check() -> str:
    """Health report for every configured MDS switch."""
    return ("Produce a SAN fabric health report. For every switch from list_switches: show_version, "
            "show_module and show_environment (failed modules, fans, PSUs), show_interface_brief (ports "
            "down/errDisabled), show_interface_counters_brief (ports with errors or discards), "
            "show_zone_status, get_log_events max_severity=4 since_hours=24 (summarise by event and "
            "interface), and show_logging_onboard error-stats for ports that look bad. Present a table per switch and a "
            "ranked list of issues with the next action for each.")


@main.mcp.prompt()
def check_host_connectivity(pwwn: str, vsan: int = 0) -> str:
    """Is this WWPN logged in and zoned correctly on both fabrics?"""
    v = f" in VSAN {vsan}" if vsan else ""
    return (f"Check the SAN connectivity of WWPN {pwwn}{v} on every switch: FLOGI (interface, VSAN, FCID), "
            "FCNS entry, device alias, and every zone of the ACTIVE zoneset that contains it (by pwwn or "
            "alias) together with the other members. Then check the interface it logs in on for errors, "
            "B2B credit problems and optical power. Report per fabric and flag anything missing.")


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
            "who is logged in on it (show_flogi_database_for).")


if __name__ == "__main__":
    mcp_auth.run(main.mcp)
