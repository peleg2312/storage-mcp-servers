---
name: new-lun-checklist
description: Prepare a new LUN / datastore / RDM request read-only - verify hosts, WWPNs, zoning on both fabrics, masking / igroups, capacity headroom and naming, then produce the exact provisioning commands and post-checks for him to run. Use for "I need to give cluster X a new 2TB datastore", new RDM, or adding a host to a cluster.
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
   fabrics, multipathing policy per the vendor's ESXi host configuration guide (search docs-search:
   ontap-sanhost / PowerMax host connectivity guide), datastore created on the right NAA.
