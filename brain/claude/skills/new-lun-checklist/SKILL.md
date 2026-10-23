---
name: new-lun-checklist
description: Prepare a new LUN / datastore / RDM or host addition read-only - verify hosts, WWPNs, zoning, masking, headroom, naming - and produce the commands and post-checks for him to run.
when_to_use: Trigger phrases - "I need a new 2TB datastore for cluster X", "add a host to the cluster", "new RDM for VM Y"
---
# New LUN checklist (preparation only)

Input: size, type (datastore / RDM / OpenShift), target cluster or hosts, array (or let you suggest one
by capacity and standards).

1. **Hosts**: the cluster's ESX hosts (kuparashit / Aria) and every vmhba WWPN.
2. **Fabric**: each WWPN logged in and zoned to the array ports on **both** fabrics (`trace-path` for one
   host, then compare all hosts). Missing zones → list them.
3. **Array access**: PowerMax host / initiator group + masking view + port group already covering all
   hosts? ONTAP igroup with all WWPNs, correct OS type (vmware), portset if used? Missing → list.
4. **Capacity**: SRP / aggregate headroom after the new LUN vs thresholds.
5. **Naming**: next name per the conventions in the environment file.
6. **Plan**: exact commands / steps for him (PowerMax: Unisphere or symcli; ONTAP: `lun create`,
   `lun mapping create`; MDS zoning if needed), each labelled "to be run by you", in order, with
   pre-checks.
7. **Post-checks** after he runs it: rescan, the new NAA visible on every host, path count equal on both
   fabrics, multipathing policy per the vendor's ESXi host configuration guide (docs MCP: netapp
   `ontap-sanhost`; `dell/powermax` "Host Connectivity Guide for VMware ESXi" and `dell/kb` "native
   multipathing round robin"), datastore created on the right NAA.
