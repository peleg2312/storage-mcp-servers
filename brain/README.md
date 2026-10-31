# Storage brain for Claude Code
See `brain/ARCHITECTURE.md` for how this brain follows the Claude Code documentation and the trade-offs taken.

Turns Claude Code on your VM into a SAN / storage operations assistant that knows your job, your
environment, how to use each MCP server, and your procedures. Read-only by design.

| Part | File(s) | What it does |
|---|---|---|
| Instructions | `claude/CLAUDE.md` | role, golden rules (read-only, no invented IDs, both fabrics...), which MCP answers what, NAA / EUI / WWPN decoding, the ESX → FI → MDS → array path model |
| Your environment | `claude/brain/environment.md` | arrays, fabrics, vCenters, UCS domains, naming conventions, thresholds, ownership; you fill it in (or `/brain-setup` drafts it) |
| Tool map | `claude/brain/tool-map.md` | kuparashit / ONTAP usage notes and what `/brain-setup` records (Claude sees tool names in the MCP tool list) |
| Learned notes (memory catalog) | `claude/brain/notes.md` + `notes/<topic>.md` | `notes.md` (≤ 60 lines: names, prefixes, thresholds, owners) is read every session; everything else Claude learns goes to topic files (powermax, ontap, fabric, vmware, tools...) read only when a question needs them, so cost per session stays flat. Never overwritten by the installer |
| Skills | `claude/skills/*/SKILL.md` | the procedures, see `claude/skills/` (below); Claude uses them automatically or you call `/<name>` |
| Agents | `claude/agents/*.md` | see `claude/agents/` (incl. Explore on haiku) |
| Documentation library | `../library/` → `~/.claude/brain/library/` | NetApp ONTAP + Trident docs and KB (`kb-ontap`, `kb-san`), EMS references per ONTAP version, Harvest, Dell CSM / CSI / PowerMax / PowerFlex docs and Dell KB, VMware KB (exact names: `library/MANIFEST.md`); searched through the MCP server `docs-local` (this VM) or `docs-search` (cluster), or `python3 ~/.claude/brain/library/search.py search "..."` |
| Charts + Excel | `claude/tools/report.py`, skill `report-export` | any table from the MCPs (throughput / IOPS / latency over days, capacity per pool, unused LUNs...) as one sparkline line per series in the answer, `report.html` (charts with hover, light / dark, data tables) and `report.xlsx` (sheet per table with a native Excel chart + Summary) under `~/storage-reports/`. Pure-Python wheels in `claude/tools/vendor/` (openpyxl, plotext): nothing to pip install on the air-gapped VM. To the PC: in an SSH session each report is queued for `claude/tools/get-reports.ps1`, which runs on the Windows PC (one-time SSH key setup in its header), downloads it into Downloads\\storage-reports and opens it; without it, Claude's answer ends with a PowerShell line that copies and opens it. Check: `python3 brain/test_report.py` |
| Development tools | `devtools/` (ruff, basedpyright + node as offline wheels -> `~/.claude/devtools-venv`), `plugins/` (offline copy of Anthropic's official dev plugins, Apache-2.0: pr-review-toolkit, feature-dev, commit-commands, security-guidance in pattern-only mode, pyright-lsp, mcp-server-dev) + `dev-discipline` (test-driven-development, systematic-debugging and verification-before-completion skills from obra/superpowers, MIT, without its session hook), hook `py-lint.py` | for developing on the VM: ruff errors fed back after every .py edit, type diagnostics through the language server, review / feature workflows. Installed by default: pyright-lsp, security-guidance, dev-discipline, commit-commands (~300 tokens per session; not in `--project` installs). pr-review-toolkit, feature-dev and mcp-server-dev are opt-in: `claude plugin install <name>@brain-dev` (re-running the installer never removes a plugin you enabled; earlier installs keep theirs until `claude plugin uninstall <name>@brain-dev`) |
| Databases MCP | `claude/tools/db_mcp.py` (MCP server `databases`, drivers psycopg + pymongo in the dev tools) | PostgreSQL and MongoDB for development: schemas (tables / collections, columns or sampled field types, keys, indexes), queries, plans, find / aggregate / count (read-only: READ ONLY transactions rolled back, $out / $merge refused; use a read-only database account); writes with pg_execute / mongo_write only on connections marked `"write": true`, each confirmed by the user (the hook asks). Connections in `~/.claude/brain/databases.json` (example installed next to it); passwords in ~/.pgpass or env. Check: `brain/test_db_mcp.py` against real servers |
| Banner + status line | `claude/banner/paas-banner.py`, `paas-statusline.py` | "Peleg As A Service" in big coloured block letters every time `claude` is started, shown inside Claude Code under its header (a shell wrapper added to `~/.bashrc` / `~/.zshrc` writes it for the current window width as a `companyAnnouncements` settings file; Claude Code labels it "Message from … Organization"), and a styled status line (name · model · folder · context left, turning yellow / red · session cost) inside the UI |
| Login banner (optional) | `login-banner.sh` (`install-vm.sh --login-banner`, sudo) | the same "Peleg As A Service" logo at every login on the VM for every user (SSH, console, terminal windows) with a system card: host, user, OS, uptime, load, memory, disk, and "type claude". Once per session, interactive terminals only; `sudo sh brain/login-banner.sh --remove` undoes it |
| Look and feel | `claude/themes/paas.json`, `merge_settings.py` | "Peleg As A Service" colour theme (`/theme` to switch), storage spinner verbs, brain tips in the spinner, a terminal bell when Claude finishes, one colour per agent. UI only, no tokens; set only where you have not chosen your own |
| Safety hook | `claude/hooks/block-write-tools.py` | blocks any MCP call that looks like a change (create/delete/modify..., HTTP POST/PUT/PATCH/DELETE, non-show CLI, SQL writes) - protects you even if a third-party MCP has write tools |
| Web UI | `ui/` → `~/.claude/paas-ui` (service `paas-ui`) | Claude in the browser like Claude desktop: CloudCLI (siteboon/claudecodeui, AGPL-3.0) branded Peleg As A Service by `ui/brand/brand.py` (greeting, floating composer, gradient theme), offline bundle (`ui/build-bundle.sh` → `ui/bundle/`, Node.js included). `https://<vm>:3001` (self-signed certificate in `~/.claude/paas-ui-tls`), sign in with the VM's root account (`UI_LOGIN_USERS="root alice bob"` lets people use their own VM accounts; checked by `su`; 5 wrong from one computer = 10 min lock for that computer only; no sign-up). **New chat** on the welcome screen opens a plain chat in the built-in **Chats** space (`~/chats`, no folder or git to pick); projects are for work in a folder (code, git, files). A shared team workspace: everyone sees the same projects, chats and memory and works at the same time, each in their own chat (runs are per chat; a chat is answered one message at a time). Runs this user's real `claude`: skills, hooks, MCP servers and the library apply, and the read-only guard's asks always come to you as an approval, in every mode. Files Claude hands over (xlsx, pdf, csv, png, html, zip) get a **Report ready** card under the reply (Download, Open in Reports). The **Brain** chip next to the model in the message box: on (default) is the storage brain; **Plain chat** answers simple questions with no tools, no MCP servers and no settings files (about 1k tokens a turn instead of 35k and no MCP start-up) and sends storage or vendor questions back to the brain instead of inventing. Tabs **Brain** (docs search, add by URL / upload; skills: view, and create / edit / delete your own; agents; MCP & hooks with a connection check; memory: edit notes.md / environment.md / tool-map.md, CLAUDE.md read-only), Status (health, MCP check, token / cost usage), Reports, Schedule, Browser, Help (and Marketplace / Users on the multi-user VM) from `ui/plugins`. Test: `sh brain/ui/test-ui.sh` (Rocky 9). install-vm.sh installs it (`NO_UI=1` skips; `UI_PORT` changes the port) |
| Windows app icon | `ui/windows/Install-PaaS-App.ps1` (+ `paas.ico`) | on your PC, once: `powershell -ExecutionPolicy Bypass -File Install-PaaS-App.ps1 -Vm <vm> -TrustCert`: a desktop / Start-menu "Peleg As A Service" icon that opens the UI in its own app window (Chrome or Edge app mode); `-TrustCert` trusts the VM's certificate over ssh (no browser warning) |
| Your own documents | `claude/tools/add-docs` → `~/.local/bin/add-docs` | drop PDF / HTML / Markdown / text into `~/.claude/brain/inbox/<vendor>/<product>/` (loose files: `local/inbox`) and run `add-docs`, or fetch pages and PDFs the VM can reach: `add-docs <url> --to <vendor>/<product>` (the url is cited in results); indexed into the library `docs.db` in seconds; files removed from the inbox leave it; the library's own documents are never touched, and install.sh re-adds the inbox after every library update |
| Docs-hints hook | `claude/hooks/docs-hints.py` | after every live MCP call: EMS events, PowerMax alerts, PowerFlex dial-home codes, CONTAP bugs and DSA advisories in the result get their meaning from the offline library beside it (needs the library installed on this VM) |
| Docs-leads hook | `claude/hooks/docs-leads.py` | before Claude answers a request that names a vendor, product or storage term (troubleshooting, design, best practices, "an app like NetApp snapshots", automation): up to 4 matching library documents as leads; silent for anything else |
| Session-start hook | `claude/hooks/session-start.py` | prints the library version and document count, whether `environment.md` is filled, the notes count, whether the guard is active and a read-only reminder into every session |

Skills: `brain-setup`, `brain-health`, `docs-lookup`, `identify-lun`, `unused-luns`, `decommission-check`,
`trace-path`, `zoning-audit`, `fabric-health`, `datastore-latency`, `powermax-performance`,
`ontap-performance`, `capacity-report`, `rdm-inventory`, `k8s-volume-troubleshoot`, `csm-health`,
`powerflex-troubleshoot`, `replication-check`, `code-version-check`, `new-lun-checklist`, `morning-check`,
`explain-error`, `change-review`, `fastapi-service`, `report-export`, `skill-creator`, `terraform` (all in `claude/skills/`).

## Install (on the VM that runs Claude Code)

Needs: `python3` (and `claude`; the other MCP servers can be added before or after).
```bash
cd storage-mcp-servers              # your clone of this repo
sh install-vm.sh                    # = brain/install.sh + the documentation library + a smoke test
claude                              # then type:  /brain-setup
```
`install.sh` copies everything into `~/.claude/`, backs up an existing `CLAUDE.md` / `settings.json`,
adds the safety, docs-hints, docs-leads and session-start hooks, allows your MCP servers' tools without a prompt each time, extracts the
documentation library from `../library/` into `~/.claude/brain/library/` and registers it as the MCP
server **docs-local** (`mcp_stdio.py`, standard library only: no pip, no container). Re-run it after
every `git pull`; your `environment.md`, `tool-map.md`, `notes.md`, `notes/` and `allowed-tools.txt` are never overwritten (multi-user: root's list in `/opt/paas/hooks` is carried over by `install-shared.sh`, and each user's own `~/.claude/hooks/allowed-tools.txt` is read too); theme, status line, spinner, tips and bell are always reset to the brain's (settings.json is backed up first).
**Multi-user VM** (as root): `sh install-vm.sh`, then `sh brain/multiuser/install-shared.sh`, then `sh brain/multiuser/install-gate.sh`, then `install-shared.sh` again (the marketplace for other VMs starts once the gate made the certificate). Update: `git pull && sh install-vm.sh && sh brain/multiuser/install-shared.sh`. The key in `/etc/paas/api-key` is readable by every user in `paas-users` by design (managed settings deny Claude's Read tool there); a real boundary would need a local proxy that holds the key.
`sh install.sh --no-library` skips the library when docs-search runs on the cluster instead.
`sh install-vm.sh --project <dir>` (or `sh brain/install.sh --project <dir>`) installs the brain **only inside
that folder**: `<dir>/CLAUDE.md` (imports `@.claude/brain/...`), `<dir>/.claude/{skills,agents,hooks,brain,banner,
settings.json}` and `<dir>/.mcp.json` with the `docs-local` stdio server; the library stays shared in
`~/.claude/brain/library`, and the banner prints only when `claude` is started under `<dir>`.

`/brain-setup` makes Claude list every tool of every MCP (kuparashit, Aria, ONTAP, Harvest, MDS, UCSC,
PowerMax, docs) into `tool-map.md` and draft `environment.md` from what it sees; it asks you to confirm the
uncertain parts (fabric A/B, thresholds, prefixes). Run it again whenever you add or upgrade an MCP.

## Make it better over time
- Wrong or slow answer? Fix the skill's steps or add the fact to `environment.md`, then re-run install.
- A new procedure you repeat → a new folder `claude/skills/<name>/SKILL.md` (copy an existing one).
- The hook blocked a read-only tool by mistake → add its exact name to `~/.claude/hooks/allowed-tools.txt`.
- Keep your changes in this repo so the brain is versioned and can be rebuilt on a new VM.

## Try it
- `which LUNs on the PowerMax arrays are not used by any vCenter?`
- `trace naa.6000097000019790... end to end on both fabrics`
- `datastore DS_PROD_01 was slow yesterday 14:00-15:00, why?`
- `/zoning-audit fabric A`  ·  `/morning-check`  ·  `explain EMS scsiblade.san.config.active`
- `/replication-check`  ·  `/code-version-check`  ·  `/brain-health`  ·  `is CSI driver bug X fixed in our CSM?`
