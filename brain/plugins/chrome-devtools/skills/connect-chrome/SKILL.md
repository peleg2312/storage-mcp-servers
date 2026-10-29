---
name: connect-chrome
description: Connect the Chrome on the person's Windows PC so Claude can open, test and debug their web app with the chrome-devtools tools. Use when a chrome-devtools tool says no Chrome is connected or several PCs are, or when the person asks how to connect Chrome / see their app in a real browser.
---

# Connect Chrome (Windows PC)

Claude runs on this server; the browser is the person's own Chrome on their Windows PC, reached through an SSH tunnel.

1. Run `paas-chrome windows` and give the person the PowerShell line it prints, in a code block. They paste it into
   PowerShell on their PC and sign in with their server password. It opens a separate Chrome window (its own empty
   profile, not their everyday Chrome) and keeps the tunnel open while that PowerShell window stays open.
2. `paas-chrome list` (or the `list_my_browsers` tool) shows the connected PCs. Several people may share one account
   from different PCs: when more than one PC is connected, ask the person which PC they are on and call `use_browser`.
3. Open their app (for example `http://<this server>:8000/docs`) or any page they ask for. Storage arrays, switches,
   UCS and vCenter / ESXi pages are refused on purpose (they stay read-only); do not try other addresses for them.
   The person can also switch the PC of a chat in the web UI: Browser tab, "Chrome on your PC".

If the tunnel fails with "remote port forwarding failed", another PC already uses that port: they change `$p` at the
start of the line to any free port 9300-9399. If ssh says forwarding is not allowed, root enables
`AllowTcpForwarding yes` in /etc/ssh/sshd_config. Root lists more infrastructure hosts to refuse in
/etc/paas/chrome-blocked-hosts (one per line).
