---
name: trace-path
description: Trace the SAN path end to end (VM / datastore / NAA / host, UCS vHBA, FI, MDS flogi / zone / port-channel, array port, masking or igroup) on both fabrics and flag broken or asymmetric hops.
when_to_use: Trigger phrases - "trace naa.xxx end to end", "is host X zoned to the array", "why does host Y have only 2 paths"
---
# Trace the SAN path

## 1. Starting point → host WWPNs
- Any starting identifier (VM, datastore, NAA, ESX, host pWWN, LIF) → one kuparashit SQL query for the
  rest: ESX host(s), vmhba pWWNs, NAAs, array targets it sees. Then confirm each hop live below.
- ESX host → UCS service profile: `ucsc` find_wwpn / trace_service_profile_san → vHBA name, fabric A/B,
  VSAN, WWPN, pinning (get_vhba_pinning) to FC uplink / SAN port-channel.

## 2. Fabric (per fabric A and B)
- MDS `trace_wwpn` / flogi: is each WWPN logged in, on which interface / port-channel, VSAN.
- FCNS: logged in and registered (FC4 type).
- Zoning: `zone_check` / active zoneset: zones containing the WWPN, the other members (array ports),
  device-alias names. Note zones in config but not active.
- The FI ↔ MDS link: `port_channel_health` and errors on that port-channel and its members
  (UCS side: list_fc_port_channels, get_fc_port_errors).

## 3. Array
- PowerMax: `find_wwpn` → host / initiator group → masking views → port group → FA ports (dir:port,
  WWPN, online). ONTAP: igroups containing the WWPN → LUN maps; SVM FC LIFs (WWPN, home/current port, up).
- Zoned array ports must be the ones in the port group / LIFs of the SVM.

## 4. Compare
Expected paths per LUN = (host vmhbas on fabric) × (array ports zoned and in the port group on that
fabric), per fabric. Flag:
- WWPN not logged in, not zoned, zoned but not masked, masked but not zoned
- only one fabric working, unequal path counts A vs B
- array port offline, port-channel member down, errors on any hop
- initiator on the array that never logs in (stale)

## Output
One table per fabric: hop | object | state | detail. Then findings by severity and what to fix (who
owns that layer). Mention which hops could not be checked (e.g. ESX path states without a vCenter tool).
