---
name: k8s-volume-troubleshoot
description: Troubleshoot OpenShift / Kubernetes persistent volumes on Trident (NetApp) or Dell CSM (PowerMax / PowerFlex) - PVC pending, attach / mount failures, multipath issues, resize, replication - using the error text, the bug trackers and docs, and the array and fabric state. Use for any PVC / CSI / Trident / CSM problem.
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
   CSI articles), `dell/csm` (use the page whose url version matches the installed CSM: `content/docs/` =
   current, `content/v1..v3/` = older), `csi-powermax` / `csi-powerflex`, `csm-replication`, `csm-operator`
   (there is no CSM issue tracker in the library). Note the driver version the user runs and whether a
   fix exists in a later version.
2. Find the backing volume on the array: PV volumeHandle / internal name → ONTAP volume / LUN (Trident
   prefix) or PowerMax / PowerFlex volume (CSM prefix). Check it exists, its size, its mapping to the
   node's igroup / host, replication state.
3. Node connectivity: the worker node's WWPNs/IQNs: logged in, zoned (`trace-path` from the WWPN),
   mapped on the array; multipath shows all paths active.
4. Classify: provisioning (backend / capacity / credentials), attach (mapping, zoning, igroup), mount
   (filesystem, multipath, stale devices), resize, replication.

Output: cause (with evidence), fix steps for him to run, and the bug / doc references with versions.
