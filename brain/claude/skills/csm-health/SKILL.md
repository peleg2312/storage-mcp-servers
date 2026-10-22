---
name: csm-health
description: Health and known-issue check of Dell CSM / CSI on OpenShift - operator and driver versions (csi-powermax, csi-powerflex) against the CSM docs of that version, support matrix (OpenShift, array OS), csm-replication / csm-authorization / csm-resiliency state, Dell KB and DSA security advisories for CSM. Use for "is our CSM healthy / supported / vulnerable", before an OpenShift or array upgrade, or for a recurring CSI problem. One broken PVC is k8s-volume-troubleshoot instead.
---
# CSM / CSI health check (Dell on OpenShift)

Companion to `k8s-volume-troubleshoot` (one PVC / pod / mount problem): this skill checks the
**installation** - versions, support, modules, known issues. For a failing volume, run that skill and come
back here only for the version / known-issue part. No Kubernetes MCP: the user runs read-only `oc` commands.

## 1. Collect (commands for him)
- Operator and CSM CRs: `oc get csv -A | grep -i dell`, `oc get csm -A`, `oc get csm <name> -n <ns> -o yaml`
  (spec: driver type + configVersion, modules enabled; status: state, conditions).
- Driver: `oc get pods -n <driver-ns> -o wide`, `oc get deploy,ds -n <driver-ns> -o
  jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.containers[*].image}{"\n"}{end}'`
  (driver + sidecar image tags), `oc get csidriver`, `oc get csinodes -o yaml | grep -B2 -A4 dell`,
  `oc get storageclass`, `oc get secret -n <ns> <array-secret> -o jsonpath='{.data}' | wc -c` (exists only).
- Modules: replication `oc get dellcsireplicationgroup -A`, `oc get pods -n dell-replication-controller`;
  resiliency (podmon) sidecar present on node pods, node taints / labels; authorization proxy pods and
  `oc get csm ... -o yaml` module config; observability / metrics pods if deployed.
- Platform: `oc version` (OpenShift), and the array versions from the environment file / powermax MCP
  (PowerMaxOS, Unisphere) or the PowerFlex query output.

## 2. Compare with the library (vendor `dell`)
- `csm`: use the url version matching the installed CSM (`content/docs/` = current, `content/v1..v3/` =
  older). Pages: `csidriver/release/powermax/` and `csidriver/release/powerflex/` (new features, fixed and
  known issues per driver release), the driver's "Prerequisites" / "Supported" sections (OpenShift and
  array OS / Unisphere versions, sidecar images), `replication/`, `authorization/`, `resiliency/`,
  `getting-started/installation/operator/operatorinstallation_openshift/` (certified vs community operator).
- `csm-repo`: `CHANGELOG-<version>.md` (what changed, bugs fixed); `csm-operator`, `csi-powermax`,
  `csi-powerflex`, `csm-replication`, `csm-authorization`, `csm-resiliency`: READMEs with version tables.
- `kb`: search `"Container Storage Modules"`, `CSM`, `csi-powermax`, the driver error text; **DSA-\***
  articles for CSM ("DSA-2026-259", "DSA-2026-234", "DSA-2023-285", "DSA-2022-328" ...): affected CSM
  versions and the fixed version. There is no CSM issue tracker in the library: say so.
- Trident on the same cluster is `k8s-volume-troubleshoot` / `code-version-check` territory
  (`trident-<yymm>`, `trident-issues`).

## 3. Checks (OK / finding)
driver and operator versions documented together · OpenShift version in the driver's supported range ·
array OS / Unisphere / PowerFlex version in the range · controller and node pods ready on every worker
that mounts volumes · one StorageClass per intended array / pool / SRP, parameters match the docs ·
replication groups in their expected state and synchronized · authorization and resiliency configured as
intended · no DSA affecting the running version · known issues of this release that match a recurring
symptom · secrets / certificates (expiry if visible).

## Output
Table: component | running | documented for this CSM version | status | reference. Then findings by
severity (with the DSA / known-issue / changelog citations and versions), then the recommended target
version with its supported-OpenShift / array-OS constraints, as a plan for him (no commands that change
anything).
