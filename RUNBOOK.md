# Runbook: from this repo to a working offline brain

Three places: **your PC** (has internet; pushes to GitHub), **GitHub**, **the offline VM** (runs Claude
Code). Every command you need, in order.

## 1. PC: push what Claude built (git bundle)

```bash
cd storage-mcp-servers                              # your clone, branch main, up to date (git pull)
git pull /path/to/storage-brain-<date>.bundle main  # the bundle file you downloaded from the session
git push origin main
```
If git refuses because the branches diverged: `git fetch /path/to/<file>.bundle main && git merge FETCH_HEAD`
then push. A later "incremental" bundle applies the same way, on top of the previous one.

## 2. PC: complete the library (Dell PDFs, Dell KB, bug trackers, the rest of the NetApp KB)

Needs: `git`, `python3` (3.10+), `pip install pypdf`, and for the bug trackers any read-only GitHub token.
Dell's site blocks cloud IPs, so this step has to run from a normal office/home PC.

```bash
cd storage-mcp-servers/docs-search-mcp

# a) start from the prebuilt library (fast, no re-download of what is already there)
sh ../library/join.sh work && mv work/docs-library/docs work/docs && mkdir -p work/index \
  && mv work/docs-library/docs.db work/index/docs.db && rm -rf work/docs-library

# b) Dell PowerMax / PowerFlex product PDFs + the Dell KB articles listed in sources/web-pages.txt
python3 sync/sync_dell.py --dest work/docs/dell          # hubs in sources/dell-sources.txt -> 200+ PDFs
python3 sync/sync_web.py  --dest work/docs               # KB pages (Dell, VMware, NetApp) one URL per line

# c) Trident / CSM / Harvest bug trackers (every issue with workaround + fixed version)
GITHUB_TOKEN=<read-only token> python3 sync/sync_github_issues.py --dest work/docs

# d) NetApp KB: continues exactly where the session stopped (1 article / 5 s, resumable, Ctrl-C any time)
#    with your kb.netapp.com login (DevTools -> Application -> Cookies -> kb.netapp.com -> authtoken):
NETAPP_KB_COOKIE='authtoken=<value>' python3 sync/sync_netapp_kb.py --dest work/docs --refresh-partial
#    (omit --include to export every area; add --include on-prem/ontap/da/SAN ... to narrow it)

# e) refresh the git docs (NetApp docs, Trident, CSM...) - incremental
sh sync/sync-git.sh work/docs

# f) index + pack -> library/ (45 MB parts), then commit and push
python3 docs_index.py --docs work/docs --db work/index/docs.db
sh bundle/pack-library.sh
cd .. && git add library && git commit -m "Library $(cat library/VERSION)" && git push origin main
```
Monthly: repeat b-f (all incremental). `library/MANIFEST.md` shows what is inside after each pack.

Optional, for an OpenShift cluster instead of / in addition to the VM:
```bash
sh bundle/build-offline.sh --from-library     # needs podman or docker; no internet
# -> work/docs-search-offline-<date>.tar.gz : import into the internal registry, deploy openshift-offline.yaml
```

## 3. VM (offline): install everything

Needs: `python3` (any 3.8+ from the OS), `git`, Claude Code installed (`claude` in PATH).

```bash
git clone https://github.com/peleg2312/storage-mcp-servers.git     # or copy the folder in
cd storage-mcp-servers
sh install-vm.sh
```
This installs into `~/.claude`: CLAUDE.md, the 17 skills, 6 agents, the read-only safety hook, the
documentation library (`~/.claude/brain/library`), the MCP server **docs-local** (stdio, no dependencies),
the **Peleg As A Service** banner (`claude` wrapper in `~/.bashrc`) and the status line. Then:

```bash
. ~/.bashrc                 # or open a new terminal (the banner wrapper)
claude                      # banner, then Claude Code
/brain-setup                # inside Claude: tool map + environment draft; confirm the uncertain items
```
Add the live MCP servers (PowerMax, UCS Central, MDS, docs-search on the cluster) as in the top README:
`claude mcp add --transport http <name> http://<host>:8000/mcp --header "Authorization: Bearer <token>"`,
then run `/brain-setup` again so the tool map knows them.

Update later: `git pull && sh install-vm.sh` (your environment.md / tool-map.md are kept; the library is
re-extracted only when `library/VERSION` changed).

Try: `python3 ~/.claude/brain/library/search.py search "scsiblade.san.config.active"` or, inside Claude,
`explain EMS scsiblade.san.config.active`, `/zoning-audit fabric A`, `which KB covers FC link down after a switch reboot`.

## 4. Afterwards

- Sign out of kb.netapp.com once the KB export is done (invalidates the token you used).
- Keep the repo private: the library is vendor content licensed to your support contracts.
