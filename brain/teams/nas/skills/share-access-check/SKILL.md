---
name: share-access-check
description: Check whether a user or group can reach an SMB share or NFS export and which layer denies it. Triggers - "can X access share Y", "why access denied on", "who can reach this export", "permission denied on the mount"
---
# Share access check

Read-only: never change a share, ACL, export rule, mapping or user. Cover every access zone / SVM / tenant
and both protocols (storage-nas.md N1); say which were not checked.

## Inputs
User or group (name and, if known, SID / UID / GID), share or export path, cluster, protocol. Missing one: ask.

## Sources
- **ONTAP (live, ontap MCP)**: the SVM, CIFS share and its share ACL, volume/qtree security style, export policy
  and rules for the volume, name-mapping rules, the UNIX user, the junction path. The effective file ACL
  (`vserver security file-directory show`) may have no tool: then give it as a command "to be run by you".
- **PowerScale (no MCP: he pastes)**, to be run by you, placeholders in <>:
  `isi zone zones view <zone>`, `isi smb shares view <share> --zone <zone>`,
  `isi nfs exports view <id> --zone <zone>`, `isi auth users view <user> --zone <zone>`,
  `isi auth mapping token <user> --zone <zone>`, `ls -led /ifs/<path>` on the node.
- **VAST (no MCP: he pastes)**: the view, its view policy, tenant and the user / group from the VAST CLI or VMS.
- Docs: `dell` / `powerscale` (OneFS 9.10), `infohub-powerscale`, `vast` / `docs`, `netapp` / `ontap`, `kb`,
  `kb-ontap`. Cite title, url and version.

## Steps
1. Identity: resolve the user to SID and UID/GID; show the mapping and the group list (the token).
2. Access zone / SVM / tenant: the path is served there, and the user's domain is reachable from it.
3. SMB: share exists, share permissions allow the user or a group in the token, then the NTFS / mixed ACL.
4. NFS: the client address matches an export rule or policy, the access level, root squash / anon mapping,
   NFS version and pseudo-root path.
5. POSIX mode bits or ACL on the directory and every parent (traverse).
6. Stop at the first deny and name it; still list the layers after it as "not reached".

## Output
| Layer | Setting | Effect on X | Source |
|---|---|---|---|
Then the answer first (reachable or not, and why), findings by severity, the fix as commands for him to run
(pre-check, rollback, post-check), and what was not checked (other zones, the other protocol, clients not named).
