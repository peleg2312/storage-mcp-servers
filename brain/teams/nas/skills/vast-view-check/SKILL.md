---
name: vast-view-check
description: Check VAST views, view policies, tenants, protection policies and quotas on a path. Triggers - "check the VAST view", "VAST view policy", "VAST tenant access", "why can't the host mount the VAST view"
---
# VAST view check

There is **no VAST MCP server yet**. Everything here comes from output he pastes or from the docs. Read-only:
never create or change a view, policy, tenant, quota or protection policy.

## Get the data (to be run by you)
Use the VAST CLI or VMS GUI (Views, View Policies, Tenants, Quotas, Protection) and paste the output. Or read-only
REST GET calls against the VMS (confirm the exact paths for his version in `vast` / `api-5-5`, N5):
- `GET https://<vms>/api/views/?path=<path>` and `GET https://<vms>/api/viewpolicies/?name=<policy>`
- `GET https://<vms>/api/tenants/`, `GET https://<vms>/api/quotas/?path=<path>`
- `GET https://<vms>/api/protectionpolicies/`
with a read-only token held by him (never paste it to me). Do not run POST, PATCH or DELETE.

## Steps
1. View: path, tenant, protocols (NFS / SMB / S3 flavours), bucket or share name, policy, state.
2. View policy: flavour, authentication (NFS version, Kerberos / AUTH_SYS, AD for SMB), host lists
   (read-write, read-only, none), root squash and the mapped user, SMB share-level settings.
3. Tenant: its VIP pool, identity provider (AD / LDAP / NIS), and whether the client address can reach the pool.
4. Quota on the path: hard and soft limits, used (the same view can sit under a parent quota).
5. Protection policy / replication for the path: schedule, retention, peer, last snapshot.
6. Host side for a failed mount: the client address against the host lists, protocol version, DNS of the VIP name.

## Output
| Layer | Setting | Effect | Source |
|---|---|---|---|
Then answer first, findings by severity (open host list, root squash off, no protection policy, quota near
limit), sources: pasted command + time, doc title, url, version (`vast` / `docs`, `kb`, `api-5-5`), fixes as
commands for him to run, and what was not checked (other tenants, other clusters, live client state).
