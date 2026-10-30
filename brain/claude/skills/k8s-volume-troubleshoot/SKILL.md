---
name: k8s-volume-troubleshoot
description: Troubleshoot an OpenShift / Kubernetes volume on Trident or Dell CSM - PVC pending, attach / mount / resize failures, multipath - from the error text, bugs, docs and the array and fabric state. Triggers - "PVC stuck pending", "pod cannot mount the volume", "CSI error", "map this PV to the array"
---
# Kubernetes volume troubleshooting (Trident / CSM)

There is no Kubernetes MCP: ask the user for (read-only commands he runs):
`oc describe pvc <pvc> -n <ns>`, `oc describe pod <pod> -n <ns>` (events),
Trident: `tridentctl -n trident get backend`, `tridentctl -n trident logs` (or the trident controller /
node pod logs); CSM: the driver controller + node pod logs; the node: `oc debug node/<node>` then
`chroot /host multipath -ll` and `chroot /host lsblk`.

1. Take the **exact error string** and search the docs MCP: Trident → `trident-issues` (bug reports with
   workarounds and fixed versions), `trident-changelog`, then the `trident-<release>` docs of the installed
   version (`trident-2307` … `trident-2510`; `trident` = latest) and `kb-ontap`; CSM → `dell/kb` (CSM /
   CSI articles), `dell/csm` (use the page whose url version matches the installed CSM, see docs-lookup), `csi-powermax` / `csi-powerflex`, `csm-replication`, `csm-operator`
   fixes in the `*-prs` products (see docs-lookup), `csi-powerscale` for PowerScale. Sidecar messages
   (external-attacher / provisioner / resizer / snapshotter, node-driver-registrar): vendor `kubernetes`
   (code + CHANGELOG of each sidecar, `csi-spec`). Still unexplained: search the exact string over the driver
   and client source code (`csi-*`, `goscaleio`, `gopowermax`, `gobrick`) to see which check
   or array call produces it. Note the driver version the user runs and whether a fix exists in a later version.
2. Find the backing volume on the array: PV volumeHandle / internal name → ONTAP volume / LUN (Trident
   prefix) or PowerMax / PowerFlex volume (CSM prefix). Check it exists, its size, its mapping to the
   node's igroup / host, replication state.
3. Node connectivity: the worker node's WWPNs/IQNs: logged in, zoned (`trace-path` from the WWPN),
   mapped on the array; multipath shows all paths active.
4. Classify: provisioning (backend / capacity / credentials), attach (mapping, zoning, igroup), mount
   (filesystem, multipath, stale devices), resize, replication.

Output: cause (with evidence), fix steps for him to run, and the bug / doc references with versions.
