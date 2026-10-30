---
name: fabric-health
description: Health check of the MDS fabrics and UCS FC uplinks - down ports, error counters, flaps, slow drain, port-channels, optics, recent zoning changes.
when_to_use: Trigger phrases - "is the fabric OK", "slow drain on fabric B", "flapping port", "after the switch maintenance"
context: fork
agent: fabric-investigator
background: false
---
You run in a forked context: gather everything, then return a complete answer (answer first, evidence table, findings, sources, next checks); the user cannot answer questions mid-way.

# Fabric health

Run per switch, both fabrics. Prefer the summary tools (`scan_port_errors`, `slow_drain_check`,
`port_channel_health`, `show_logging_onboard`, `get_log_events`) and drill down with the `show_*` tools only for the
ports they flag.

## Checks
1. **Interfaces**: down / err-disabled / initializing ports that have a description (expected up);
   speed mismatches on ISLs and port-channel members.
2. **Errors** (counters; compare two samples a few minutes apart to get the *rate* - totals since the
   last clear say little): CRC / invalid CRC, invalid transmission words, link failures, sync / signal
   losses, discards. Rising CRC on one port = optics / cable / SFP: check transceiver Rx/Tx power.
3. **Slow drain**: TxWait, B2B credit transitions to zero, credit loss recovery, timeout discards.
   Find the *slow device* (an edge F-port whose TxWait is high) vs the victims (ISLs / port-channels
   carrying its traffic). Map the port to its WWPN → host (flogi + device-alias + kuparashit `locate` / ucsc).
4. **Port-channels**: all members up, balanced, same speed; FI uplink port-channels from both sides
   (ucsc list_fc_port_channels / get_fc_port_errors).
5. **Onboard logs**: link flaps and error events with timestamps (`show_logging_onboard`); correlate
   with the time of the user's problem.
6. **Changes**: zoning / config changes in the logs and accounting log in the last days.
7. UCS: FI FC faults (critical / major) via `get_domain_fc_health` / `list_faults`.

## Output
Per fabric: status line (OK / degraded / critical), then a severity-ordered table:
switch | interface | connected to (WWPN / alias / host / FI) | finding | evidence (counter, rate, time) |
suggested action and owner. Mention any check that failed to run.
