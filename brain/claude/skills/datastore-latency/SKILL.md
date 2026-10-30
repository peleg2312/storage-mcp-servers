---
name: datastore-latency
description: Find which layer (VMware, fabric, PowerMax or ONTAP) causes latency on a datastore, VM disk or RDM. Triggers - "datastore X is slow", "VM latency since 14:00", "high storage latency alert", "RDM slow"
---
# Datastore / VM storage latency

Ask (or infer) the time window. Use the same window on every layer; use max **and** avg.

## 1. VMware (Aria)
- datastore / VM disk latency, IOPS, throughput over the window; which VMs drive the I/O
- split the latency: **device latency** (time on the fabric + array) vs **kernel / queue latency**
  (time queued in ESXi). High kernel/queue latency with normal device latency = host side (queue depth,
  too many VMs on one LUN, outstanding I/O limits) → not the array.
- is it all hosts or one host? all datastores on an array or one?

## 2. Map to the array
`identify-lun` → array, device/LUN, storage group / volume, the hosts' paths.

## 3. Array
- **PowerMax**: `get_performance(category="StorageGroup", storage_group=<sg>, minutes_back=<window>)`, then
  `category="FEPort"` (director + port) for the port group's ports: response time
  read/write, IOPS, MB/s, I/O size; FA ports / directors used by the port group (utilization, queue);
  SRDF/Metro write latency if replicated (synchronous replication adds the link round trip).
- **ONTAP** (Harvest): LUN and volume latency (read/write/other), IOPS; node CPU / utilization;
  aggregate / disk utilization; FC port / LIF throughput; QoS throttling.
- Array latency ≈ VMware device latency → the array is the source. Array latency low but VMware device
  latency high → look at the fabric.

## 4. Fabric
On the paths of the affected hosts: slow drain / TxWait, errors, port-channel congestion (`fabric-health`
checks, only for the involved ports).

## Output
Answer first: "latency is in <layer> because <evidence>". Then a table per layer (metric, avg, max, time
of max, normal/abnormal), the top contributing VMs, and next steps. Explain every event or alert seen with the docs (storage.md S6; products: docs-lookup).
Charts: latency over the window per datastore with `report-export` (one file per measure).
