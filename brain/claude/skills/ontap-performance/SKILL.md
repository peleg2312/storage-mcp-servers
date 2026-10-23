---
name: ontap-performance
description: Analyse NetApp ONTAP performance with Harvest metrics plus the ONTAP MCP - LUN / volume latency, IOPS, throughput, node CPU and utilization, aggregate/disk busy, FC ports, QoS - with avg and max. Use for ONTAP / NetApp performance questions and reports.
when_to_use: Trigger phrases - "ONTAP latency on volume X", "node CPU on the NetApp", "LUN IOPS last week", "aggregate busy", "FC port throughput on the SVM", "NetApp performance report"
---
# ONTAP performance (Harvest + ONTAP)

1. Identify objects with the ONTAP MCP: cluster, node, SVM, volume, LUN path (serial ↔ NAA via the
   identifier rules), aggregate, FC LIFs/ports, QoS policy.
2. Use the Harvest MCP for history. Get the exact metric names from Harvest (or the docs MCP, vendor
   `netapp`, product `harvest`, "ontap metrics") instead of guessing; typical families: `lun_*` (avg read/write latency,
   ops), `volume_*` (avg_latency, read/write ops, throughput), `node_*` (cpu busy), `aggr_*` / `disk_*`
   (utilization), `fcp_*` (port throughput), `qos_*` (latency, throttling).
3. Read latency from the LUN and the volume, then the node and aggregate it lives on: high latency with
   high node CPU / disk utilization = controller or disk bound; high latency with QoS throttling = QoS
   policy; low ONTAP latency but high VMware device latency = fabric / host.
4. Report avg and max with the time of max, top volumes / LUNs by ops and latency at the peak.
5. Check EMS events in the window (ONTAP MCP) and explain any with the docs MCP (product
   `ontap-ems-<cluster version>`, e.g. `ontap-ems-9151`); for the symptom search `kb-ontap`.

Output: answer first, table per object, top talkers, events, sources (with ONTAP version).
