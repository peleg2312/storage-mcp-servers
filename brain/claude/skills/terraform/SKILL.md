---
name: terraform
description: Write, review or plan Terraform for the user's platforms - PowerMax, PowerFlex, PowerScale, ONTAP, vSphere, Kubernetes / OpenShift, Cisco NDFC and NX-OS - and general HCL (modules, variables, state, backends, imports). Infrastructure is applied by the user, never by Claude. Triggers - "terraform", "HCL", ".tf", "provider", "module", "terraform plan", "import existing ... into terraform", "infrastructure as code", "IaC"
---
# Terraform (offline, read-only toward infrastructure)

## 1. Check before writing
- `terraform version` and the providers in use (`required_providers` / `.terraform.lock.hcl`): write for those
  versions. No terraform on the VM: say so (install from the internal repo / mirror); the code can still be written.
- Every resource and argument from the offline docs, version-matched (`docs-lookup`): language / CLI = vendor
  `hashicorp` product `terraform` (Terraform 1.17 docs); providers = `dell` `terraform-powermax` /
  `terraform-powerflex` / `terraform-powerscale`, `netapp` `terraform-ontap`, `vmware` `terraform-vsphere`,
  `hashicorp` `terraform-kubernetes`, `cisco` `terraform-dcnm` (NDFC) / `terraform-nxos`. Search
  `"<resource_type>" argument reference` with the product filter; never guess argument names.

## 2. Write it the maintainable way
- Layout: `versions.tf` (terraform + `required_providers` with `~>` pins), `providers.tf`, `variables.tf` (types,
  descriptions, validation; credentials `sensitive = true`, values from env `TF_VAR_*` or a git-ignored
  `*.auto.tfvars`, never in code), `main.tf` / per-area files, `outputs.tf`, a `README.md` with how to run it.
- Modules for anything repeated (a host + its storage group + masking view; a datastore per cluster); `for_each`
  over maps (stable keys: NAA / host name), not `count` over lists.
- State: a remote backend with locking when more than one person runs it; never edit state by hand; existing
  objects come in with `import` blocks (Terraform >= 1.5) - write the import, then `plan` must show no changes.
- `lifecycle { prevent_destroy = true }` on volumes, datastores, LUNs and anything holding data.
- Offline providers: `provider_installation { filesystem_mirror { path = ... } }` in the CLI config, with the
  provider zips mirrored by `terraform providers mirror` on a connected machine.

## 3. Check, never apply infrastructure
- Run `terraform fmt -recursive`, `terraform validate`, then `terraform plan -out=tfplan` (read-only: it refreshes
  and compares). Read the plan and summarize it: what is created / changed / DESTROYED, with the reason for each
  destroy or replace ("forces replacement").
- `terraform apply`, `destroy`, `import` (CLI), `state` and `taint` change real systems: for arrays, fabrics,
  vCenter and clusters give the exact command to the user, labelled "to be run by you" (CLAUDE.md rule 1), with
  the plan summary, pre-checks and rollback. The read-only guard asks before any of them runs. Applying to the
  user's own development resources (a dev namespace, a test VM) is fine once the user confirms.

## Output
The files (complete, formatted), how to run them (init / plan; apply for the user), the plan summary when one
ran, and the docs cited for each resource (title + url + provider version).
