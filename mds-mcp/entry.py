"""
Wrapper around the upstream mds-mcp server (alecharn/mds-mcp, main.py unchanged):
  - bearer-token auth + /healthz (mcp_auth, same as the PowerMax and UCS Central servers)
  - a stricter command guard on top of upstream's show-only check
  - detailed instructions and SAN troubleshooting prompts for the connecting model
"""

import re

import main  # upstream server: reads MDS_<N>_* at import and builds `main.mcp`
import mcp_auth

# --- defence in depth: one plain `show` command, no chaining/pipes/redirection ---
_upstream_validate = main._validate_command
_FORBIDDEN = re.compile(r"[;|>\n\r`]")  # command chaining, pipes, redirection, newlines


def _strict_validate(cmd: str) -> str:
    c = _upstream_validate(cmd)
    if _FORBIDDEN.search(c):
        raise ValueError(f"Refusing command {cmd!r}: only a single plain `show` command is allowed")
    return c


main._validate_command = _strict_validate

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
  an object instead of a list.

== WORKFLOWS ==
Fabric health: list_switches -> show_version / show_module / show_environment on each switch ->
  show_interface_brief (ports down or errDisabled) -> show_logging for recent events.
Where is a WWPN / host logged in: show_flogi_database (or _vsan) on each switch -> interface + VSAN
  + FCID; show_fcns_database_detail for the device type/features; show_device_alias_pwwn for its
  alias.
Zoning: show_zoneset_active_vsan (what is enforced) vs show_zoneset_vsan (configured);
  show_zone_name_vsan for one zone. A device can talk only if both WWPNs (or their aliases) are in
  the same zone of the ACTIVE zoneset in the same VSAN. Check both fabrics.
Port problems / slow drain: show_interface_for (state, speed, errors) ->
  show_interface_counters_detailed_for and show_interface_bbcredit_for (B2B credits, TxWait,
  timeouts/discards) -> show_interface_transceiver_detail_for (Rx/Tx power, temperature).
  Compare across the ports of the same path and both fabrics.
ISLs / port-channels: show_port_channel_summary, show_interface_for port-channelN.

== READING THE NUMBERS (rules of thumb) ==
- CRC / invalid CRC / link failures / sync loss growing -> physical layer: SFP, cable, patch panel.
- Optical Rx power below about -7 dBm on short-wave SFPs is marginal, below the transceiver's low
  alarm threshold is a fault; compare with the thresholds shown in the transceiver detail.
- TxWait, Tx credit-loss / B2B credit 0 time, timeout discards on an F-port -> slow-drain device
  (usually the host/HBA behind that port); on an ISL -> congestion spreading in the fabric.
- Counters are cumulative since last clear/boot; when possible compare two readings over time
  before calling something "increasing".

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
            "show_zone_status, and show_logging for recent errors. Present a table per switch and a "
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
    return (f"Look for slow drain and congestion on {target}: show_interface_counters_brief to find ports "
            "with discards or errors, then for the worst ports show_interface_counters_detailed_for and "
            "show_interface_bbcredit_for (TxWait, credit loss, timeout discards) and the FLOGI database to "
            "identify the device behind each port. Rank ports by severity and say whether each looks like a "
            "slow end device or an ISL bottleneck.")


if __name__ == "__main__":
    mcp_auth.run(main.mcp)
