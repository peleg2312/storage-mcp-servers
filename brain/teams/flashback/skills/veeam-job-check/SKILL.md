---
name: veeam-job-check
description: Investigate Veeam Backup & Replication 13 jobs from pasted output - failed or warning sessions, a VM that failed, PostgreSQL application-aware / WAL backups, Linux VMware proxies, NetApp NFS repositories, Veeam ONE alarms - with the documented cause and fix. Triggers - "Veeam job failed", "VM backup warning", "Veeam PostgreSQL", "proxy", "repository full", "Veeam ONE alarm"
---
# Veeam job check (no MCP: the user runs, Claude reads)

Read-only: never start, stop, retry or edit a job, repository or proxy. Give the commands "to be run by you" on the VBR
server (Veeam PowerShell, `Import-Module Veeam.Backup.PowerShell`); check cmdlet names in `veeam` / `vbr-powershell`
for 13.0.1 before giving them. Parse pasted output of more than ~20 lines in python.

1. **The session**:
```powershell
$s = Get-VBRBackupSession | Where-Object {$_.JobName -eq '<job>'} | Sort-Object CreationTime -Descending | Select-Object -First 3
$s | Select-Object JobName, Result, State, CreationTime, EndTime
$s[0].GetTaskSessions() | Select-Object Name, Status, @{n='Reason';e={$_.Info.Reason}}
$s[0].Logger.GetLog().UpdatedRecords | Select-Object Status, Title | Format-Table -Wrap
```
2. **Per cause**:
   - VM: snapshot creation / removal, CBT, VMware Tools quiescence, transport mode the Linux proxy used (hot-add needs the
     proxy in the same cluster with access to the datastore; NBD fallback is slow), `Get-VBRViProxy | Select Name, Host, TransportMode, MaxTasksCount`.
   - PostgreSQL: application-aware processing settings of the job (guest credentials, the PostgreSQL instance and user,
     WAL / log shipping), the documented requirements for 13 ("PostgreSQL" pages in `vbr-userguide`).
   - Repository on NetApp NFS: free space (`Get-VBRBackupRepository` + `GetContainer()`), the NFS mount from the gateway
     / mount server, immutability; the NetApp side live with the ontap MCP (volume space, export policy, snapshots).
   - Event IDs from the Windows event log or Veeam ONE: meaning from `veeam` / `vbr-events`.
3. **Veeam ONE**: alarms and the "Backup Job Status" / "VMs with no backup" reports, pasted by the user (`one-userguide`).
4. Every distinct error text: search it in quotes in `veeam` (vbr-userguide, vbr-events) and quote cause and resolution.

## Output
Answer first, then | Job | Session | VM | Result | Reason | Proxy | Repository |, the fix as steps for the user (with the
doc citation), and what was not checked (the guest OS, the vCenter, the NFS server side when not looked at).
