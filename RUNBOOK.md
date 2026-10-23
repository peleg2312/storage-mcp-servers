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

Needs: `git`, `python3` (3.10+), a venv with `pip install pypdf cryptography fonttools` (macOS: `python3 -m venv work/venv && source work/venv/bin/activate` first), and for the bug trackers any read-only GitHub token.
Dell's site blocks cloud IPs, so this step has to run from a normal office/home PC.

```bash
cd storage-mcp-servers/docs-search-mcp

# a) start from the prebuilt library (fast, no re-download of what is already there)
sh ../library/join.sh work && mv work/docs-library/docs work/docs && mkdir -p work/index \
  && mv work/docs-library/docs.db work/index/docs.db && rm -rf work/docs-library

# b) Dell PowerMax / PowerFlex product PDFs + the Dell KB articles listed in sources/web-pages.txt
#    Many manuals need a Dell login: sign in to dell.com/support in your browser first and add
#    --browser-cookies (pip install browser-cookie3 in the venv); --retry replaces copies that came
#    back as Dell's redirect page instead of the document.
python3 sync/sync_dell.py --dest work/docs/dell --browser-cookies --retry
python3 sync/sync_web.py  --dest work/docs               # KB pages (Dell, VMware, NetApp) one URL per line
python3 sync/sync_dell_kb.py --dest work/docs --browser-cookies   # Dell KB articles of PowerMax / PowerFlex / CSM-CSI
                                                         #   (seed list + related-article links; login-only ones with your session)

# b2) login-only Dell documents (alert / event reference guides, release notes, support matrices): the
#     scripts get Dell's redirect page for them even with cookies. Download them in your signed-in browser
#     as listed in extra/dell/NEEDED.md (file name + link), save under extra/dell/<product>/, then:
python3 sync/import_extra.py --dest work/docs
cd .. && git add -f docs-search-mcp/extra/dell && git commit -m "Dell login-only docs" && git push origin main && cd docs-search-mcp

# b3) MOST Dell content comes from a real browser (Dell's bot check and sign-in stop the plain scripts):
#     sign in once, then the collector searches DuckDuckGo, Bing and Dell Support for every query in
#     sources/dell-kb-queries.txt and saves every KB article found (login-only ones too), downloads the login-only
#     PDFs of extra/dell/NEEDED.md through the signed-in browser, every Info Hub paper on PowerFlex / PowerMax / CSM,
#     and the HTML manuals in sources/dell-manuals.txt topic by topic.
pip install playwright && python3 -m playwright install chromium
python3 sync/dell_browser.py all --wait-login # a window opens on Dell sign-in: sign in there, the run continues in that
                                              # session (Dell's sign-in expires between runs). Hours; Ctrl-C any time,
                                              # re-run continues (search results are cached a week)
python3 sync/import_extra.py --dest work/docs
#     "access level 10 < 30" for the PDFs = your Dell account is not linked to an entitled site: My Account -> link the
#     company's site ID (or ask the Dell account team), then: python3 sync/dell_browser.py needed --wait-login

# c) Trident / Harvest issue trackers + Dell CSM / CSI pull requests (Dell disabled its issue trackers: the PRs are
#    the fixes, with the issues they name), then the first release tag of every PR (from git history)
GITHUB_TOKEN="$(gh auth token)" python3 sync/sync_github_issues.py --dest work/docs
python3 sync/pr_releases.py --dest work/docs

# d) NetApp KB: continues exactly where the session stopped (1 article / 5 s, resumable, Ctrl-C any time)
#    with your kb.netapp.com login (DevTools -> Application -> Cookies -> kb.netapp.com -> authtoken):
NETAPP_KB_COOKIE='authtoken=<value>' python3 sync/sync_netapp_kb.py --dest work/docs --refresh-partial
#    (omit --include to export every area; add --include on-prem/ontap/da/SAN ... to narrow it)

# e) refresh the git docs (NetApp docs, Trident, CSM...) - incremental
sh sync/sync-git.sh work/docs

# f) index, check search quality, pack -> library/ (45 MB parts), then commit and push
python3 docs_index.py --docs work/docs --db work/index/docs.db
python3 eval_search.py --min-hit5 0.9 && python3 eval_search.py --cases tests/retrieval_heldout.json --min-hit5 0.9
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
This installs into `~/.claude`: CLAUDE.md, the 23 skills, 8 agents, the read-only safety hook, the
documentation library (`~/.claude/brain/library`), the MCP server **docs-local** (stdio, no dependencies),
the **Peleg As A Service** banner (`claude` wrapper in `~/.bashrc`) and the status line.

**Brain only inside one folder** (project mode): `sh install-vm.sh --project ~/san` writes `~/san/CLAUDE.md`,
`~/san/.claude/{skills,agents,hooks,brain,banner,settings.json}` and `~/san/.mcp.json` (docs-local) instead of
`~/.claude`; the library still goes to `~/.claude/brain/library`. Claude started in any other folder has no brain,
no hooks and no banner; `claude` need not be installed yet. On the first start inside the folder approve docs-local. Then:

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
