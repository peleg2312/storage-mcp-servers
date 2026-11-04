"""The Flashback (backup and restore) team: python3 brain/test_flashback.py (stdlib)
- the team builds: its own docs-lookup wins over the shared one, agents' tools carry the plugin names of the three
  Commvault servers, team.json names the "flashback" library;
- publish.py makes one mcp.json entry per CommCell from the catalog's "commvault" shape;
- paas-library import: a prebuilt library tarball replaces the products it carries, documents added on the VM stay;
- sync_site.py's page parsers (Commvault, Veeam, Red Hat html-single) and copy_subset.py's stream over library parts."""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
B = os.path.join(R, "brain")
tmp = tempfile.mkdtemp()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# 1. the plugin
subprocess.run([sys.executable, os.path.join(B, "plugin", "build.py"), tmp, "--team", "flashback"], check=True, stdout=subprocess.DEVNULL)
P = os.path.join(tmp, "paas-brain-flashback")
meta = json.load(open(os.path.join(P, "team.json")))
assert meta["library"] == "flashback", meta
for s in ("restore-plan", "oadp-restore-hosted-cluster", "oadp-backup-check", "commvault-job-check", "veeam-job-check",
          "backup-morning-check", "snapshot-protection-check", "replication-check", "docs-lookup"):
    assert os.path.isfile(os.path.join(P, "skills", s, "SKILL.md")), s
assert "Flashback library" in open(os.path.join(P, "skills", "docs-lookup", "SKILL.md")).read()     # the team's own, not the shared
assert "Brain setup (Flashback)" in open(os.path.join(P, "skills", "brain-setup", "SKILL.md")).read()
cv = open(os.path.join(P, "agents", "commvault-analyst.md")).read()
for env in ("env1", "env2", "env3"):
    assert f"mcp__plugin_paas-brain-flashback_commvault-{env}__*" in cv, cv[:400]
assert "storage-side protection" in open(os.path.join(P, "brain", "persona.md")).read()
assert "Backup and restore rules" in open(os.path.join(P, "brain", "storage.md")).read()
print("flashback plugin ok")

# 2. one Commvault server per CommCell from the catalog shape
pub = load("publish", os.path.join(B, "teams", "publish.py"))
cat = json.load(open(os.path.join(B, "marketplace", "mcp.json")))
assert pub.shape(cat, "commvault-env2") is cat["commvault"] and pub.shape(cat, "commvault") is cat["commvault"]
assert pub.shape(cat, "ontap") is cat["ontap"] and pub.shape(cat, "nothing-like-this") is None
assert pub.shape(cat, "docs-search") is cat["docs-search"]
assert cat["commvault"]["server"]["headers"]["Authorization"] == "TOKEN"     # the server takes its secret as is (no Bearer)
print("commvault catalog ok")

# 3. paas-library import
libs = os.path.join(tmp, "libraries")
src = os.path.join(tmp, "built")
os.makedirs(os.path.join(src, "docs", "commvault", "11.40"))
open(os.path.join(src, "docs", "commvault", "11.40", "sql_ag.md"), "w").write(
    "# Always On availability groups\n\nRestoring an Always On availability database: remove it from the group first.\n")
open(os.path.join(src, "MANIFEST.md"), "w").write("# Flashback library\n")
sys.path.insert(0, os.path.join(R, "docs-search-mcp"))
import docs_index  # noqa: E402
docs_index.build(os.path.join(src, "docs"), os.path.join(src, "docs.db"), full=True, log=lambda *a: None)
tar = os.path.join(tmp, "flashback-library-test.tar.gz")
with tarfile.open(tar, "w:gz") as t:
    for n in ("docs", "docs.db", "MANIFEST.md"):
        t.add(os.path.join(src, n), arcname=n)
env = dict(os.environ, PAAS_LIBRARIES=libs)
lib = os.path.join(B, "claude", "tools", "paas-library")
os.makedirs(os.path.join(libs, "flashback", "docs", "acme", "runbooks"))
open(os.path.join(libs, "flashback", "docs", "acme", "runbooks", "ours.md"), "w").write("# Our runbook\n\nflashback drill steps\n")
os.makedirs(os.path.join(libs, "flashback", "docs", "commvault", "11.40"), exist_ok=True)
open(os.path.join(libs, "flashback", "docs", "commvault", "11.40", "old.md"), "w").write("# stale\n")
r = subprocess.run([sys.executable, lib, "import", "flashback", tar], env=env, capture_output=True, text=True)
assert r.returncode == 0, r.stdout + r.stderr
d = os.path.join(libs, "flashback")
assert os.path.isfile(os.path.join(d, "docs", "commvault", "11.40", "sql_ag.md"))
assert not os.path.exists(os.path.join(d, "docs", "commvault", "11.40", "old.md"))      # the product came whole with the tarball
assert os.path.isfile(os.path.join(d, "docs", "acme", "runbooks", "ours.md"))           # added here: kept
assert os.path.isfile(os.path.join(d, "MANIFEST.md")) and not os.path.exists(os.path.join(d, ".import"))
search = load("search_cli", os.path.join(R, "docs-search-mcp", "search_cli.py"))
con = search.connect(os.path.join(d, "docs.db"), True)
titles = {row[0] for row in con.execute("SELECT path FROM docs")}
assert any("sql_ag" in p for p in titles) and any("ours.md" in p for p in titles), titles
open(tar + ".sha256", "w").write("0" * 64 + "  x\n")
r = subprocess.run([sys.executable, lib, "import", "flashback", tar], env=env, capture_output=True, text=True)
assert r.returncode != 0 and "checksum" in (r.stdout + r.stderr), r.stdout + r.stderr
print("paas-library import ok")

# 4. page parsers
site = load("sync_site", os.path.join(R, "docs-search-mcp", "sync", "sync_site.py"))
cvp = ('<div class="breadcrumbs"><a class="breadcrumb breadcrumb-home" href="index.html"></a>'
       '<a class="breadcrumb breadcrumb-link" href="index.html">Software</a><a class="breadcrumb breadcrumb-link" href="x.html">Databases</a>'
       '<a class="breadcrumb breadcrumb-link" href="y.html">SQL Server</a></div><h1 class="heading">Always On</h1>'
       '<article class="article"><p>Back up the AG.</p></article>')
title, crumbs, art = site.commvault_parse(cvp)
assert title == "Always On" and crumbs == ["Software", "Databases", "SQL Server"] and "Back up the AG" in art, (title, crumbs)
vp = ('<ol class="breadcrumb js-breadcrumb"><li><span itemprop="name">Home</span></li><li><span itemprop="name">User Guide</span></li>'
      '<li><span itemprop="name">VMware vSphere</span></li><li><span itemprop="name">PostgreSQL WAL Files Backup</span></li></ol>'
      '<article class="js-page-article"><h1>PostgreSQL WAL Files Backup</h1><aside class="mini-toc__container">toc</aside>'
      '<p>WAL files are backed up.</p></article>')
title, crumbs, art = site.veeam_parse(vp)
assert title == "PostgreSQL WAL Files Backup" and crumbs == ["User Guide", "VMware vSphere"] and "toc" not in art, (title, crumbs, art)
rh = ('<title>Backup and restore | OpenShift Container Platform | 4.20</title><div class="rhdocs">'
      '<section class="chapter" id="oadp"><h2 class="title">Chapter 5. OADP Application backup and restore</h2><p>' + "x" * 50 + '</p>'
      '<section class="section" id="sched"><h3 class="title">5.1. Scheduling backups</h3><rh-tooltip>Copy link</rh-tooltip>'
      '<p>Create a Schedule CR with a cron expression and a ttl for the backups it makes.</p></section></section></article>')
parts = site.redhat_split(rh, "u")
assert [p[0] for p in parts] == ["oadp", "sched"], parts
assert parts[1][1] == "5.1. Scheduling backups" and parts[1][2] == ["Backup and restore", "OADP Application backup and restore"]
assert "Copy link" not in parts[1][3]
print("site parsers ok")

# 5. copy_subset over parts of a tarball
gl = os.path.join(tmp, "general")
os.makedirs(gl)
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as t:
    for name, data in (("docs-library/docs/netapp/ontap/data-protection/snapmirror.adoc", b"= SnapMirror\n"),
                       ("docs-library/docs/netapp/ontap/smb-admin/share.adoc", b"= SMB\n"),
                       ("docs-library/docs/netapp/ontap/.source_url", b"https://github.com/NetAppDocs/ontap\n"),
                       ("docs-library/docs/dell/powermax/manifest.json", b'{"snapvx.pdf": {"url": "u1"}, "other.pdf": {"url": "u2"}}'),
                       ("docs-library/docs/dell/powermax/snapvx.pdf", b"%PDF"), ("docs-library/docs/dell/powermax/other.pdf", b"%PDF")):
        ti = tarfile.TarInfo(name)
        ti.size = len(data)
        t.addfile(ti, io.BytesIO(data))
raw = buf.getvalue()
half = len(raw) // 2
open(os.path.join(gl, "docs-library-x.tar.gz.part-aa"), "wb").write(raw[:half])
open(os.path.join(gl, "docs-library-x.tar.gz.part-ab"), "wb").write(raw[half:])
sub = os.path.join(tmp, "subset.txt")
open(sub, "w").write("# test\nnetapp/ontap   (^|/)data-protection/\ndell/powermax  (?i)snapvx\n")
out = os.path.join(tmp, "fbdocs")
subprocess.run([sys.executable, os.path.join(R, "docs-search-mcp", "sources", "flashback", "copy_subset.py"),
                "--library", gl, "--subset", sub, "--dest", out], check=True, stdout=subprocess.DEVNULL)
assert os.path.isfile(os.path.join(out, "netapp", "ontap", "data-protection", "snapmirror.adoc"))
assert not os.path.exists(os.path.join(out, "netapp", "ontap", "smb-admin"))
assert open(os.path.join(out, "netapp", "ontap", ".source_url")).read().startswith("https://github.com/NetAppDocs")
assert json.load(open(os.path.join(out, "dell", "powermax", "manifest.json"))) == {"snapvx.pdf": {"url": "u1"}}
print("copy subset ok")

# 6. the team editor keeps each server's Authorization scheme (Commvault's MCP takes the bare secret); a laptop's plugin
#    update fetches the team's marketplace first and is retried when it fails; the session start pulls before it checks
work = os.path.join(tmp, "teamrepo")
bare = os.path.join(work, "brain-flashback.git")
os.makedirs(work)
subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
genv = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
subprocess.run([sys.executable, os.path.join(B, "teams", "publish.py"), "flashback", "--to", "file://" + bare],
               check=True, stdout=subprocess.DEVNULL, env=genv)
home = os.path.join(work, "home")
fake = os.path.join(work, "fakebin")
os.makedirs(fake)
open(os.path.join(fake, "claude"), "w").write('#!/bin/sh\necho "$@" >> "$HOME/claude.log"\n[ -f "$HOME/claude.fail" ] && exit 1\nexit 0\n')
os.chmod(os.path.join(fake, "claude"), 0o755)
henv = dict(genv, HOME=home, PATH=fake + os.pathsep + os.environ["PATH"], PAAS_TEAMS=os.path.join(work, "none"))
henv.pop("CLAUDE_HOME", None)
tool = os.path.join(B, "claude", "tools", "paas-team")
subprocess.run([sys.executable, tool, "add", "flashback", "file://" + bare], check=True, env=henv, stdout=subprocess.DEVNULL)
change = {"mcp_servers": {"commvault-env1": {"url": "http://cv1:8000/mcp", "token": "cv-secret"},
                          "ontap": {"url": "http://ontap:8000/mcp", "token": "on-tok"}}}
r = subprocess.run([sys.executable, tool, "edit", "flashback"], input=json.dumps(change), capture_output=True, text=True, env=henv)
assert r.returncode == 0, r.stdout + r.stderr
clone = os.path.join(home, ".claude", "brain", "teams", "flashback")
pm = json.load(open(os.path.join(clone, "paas-brain-flashback", ".mcp.json")))["mcpServers"]
assert pm["commvault-env1"]["headers"]["Authorization"] == "cv-secret", pm       # bare, as the catalog's shape says
assert pm["ontap"]["headers"]["Authorization"] == "Bearer on-tok", pm
subprocess.run([sys.executable, tool, "use", "flashback"], check=True, env=henv, stdout=subprocess.DEVNULL)
open(os.path.join(home, "claude.log"), "w").close()
assert subprocess.run([sys.executable, tool, "plugin-update"], env=henv, capture_output=True).returncode == 0
log = open(os.path.join(home, "claude.log")).read().splitlines()
assert log == ["plugin marketplace update paas-brain-flashback", "plugin update paas-brain-flashback@paas-brain-flashback"], log
open(os.path.join(home, "claude.fail"), "w").close()
r = subprocess.run([sys.executable, tool, "plugin-update"], env=henv, capture_output=True, text=True)
assert r.returncode != 0 and "retried at the next session start" in r.stdout, r.stdout
r = subprocess.run([sys.executable, tool, "needs-refresh"], env=henv, capture_output=True)
assert r.returncode == 0                                                           # the next session start tries again
src = open(os.path.join(B, "claude", "hooks", "session-start.py")).read()
order = src[src.index("order = ("):].split("\n", 1)[0]
assert order.index("shared_line") < order.index("team_line"), order
assert '"relink", "--background"' in src
print("team edits and laptop updates ok")

# 7. the plugin's docs: docs-local (knowledge; the library on the VM) and docs-http (the VM's docs service, native HTTPS: laptops,
#    Windows too); the VM's managed settings switch the plugins' docs-http off by its plugin-scoped name
import importlib.machinery
pt = importlib.machinery.SourceFileLoader("paas_team_mod", tool).load_module()
pdir = os.path.join(tmp, "plugmcp")
os.makedirs(pdir)
got = pt.plugin_mcp(pdir, {"docs-search": {"type": "http", "url": "https://vm:8001/mcp?team=flashback",
                                           "headers": {"Authorization": "Bearer docs-token-0123456789"}},
                           "commvault-env1": {"type": "http", "url": "http://cv1:8000/mcp", "headers": {"Authorization": "cv"}},
                           "ontap": {"type": "http", "url": "http://HOST:8000/mcp", "headers": {"Authorization": "Bearer TOKEN"}}})
pm = json.load(open(os.path.join(pdir, ".mcp.json")))["mcpServers"]
assert got == ["commvault-env1", "docs-http", "docs-local"], got
assert pm["docs-http"] == {"type": "http", "url": "https://vm:8001/mcp?team=flashback",
                           "headers": {"Authorization": "Bearer docs-token-0123456789"}}, pm
assert pm["docs-local"] == {"command": "${CLAUDE_PLUGIN_ROOT}/bin/docs-local"}, pm      # no bridge: docs-http is the way off the VM
assert "mcp__plugin_paas-brain-flashback_docs-http__*" in open(os.path.join(P, "agents", "commvault-analyst.md")).read()
ms = open(os.path.join(B, "multiuser", "managed_settings.py")).read()
assert '{"serverName": f"plugin:paas-brain-{t}:docs-http"}' in ms
print("plugin docs servers ok")

# 8. a new machine joins with one command: the team repository carries join.sh / join.ps1; the docs port is 8443 by default
#    and --docs-port changes it (the real run of join.sh against an HTTPS docs service is in the session log, not repeated here)
repo = os.path.join(tmp, "joinrepo")
subprocess.run([sys.executable, os.path.join(B, "teams", "publish.py"), "flashback", "--to", repo], check=True,
               stdout=subprocess.DEVNULL, env=genv)
for f in ("join.sh", "join.ps1"):
    assert os.path.isfile(os.path.join(repo, f)), f
assert os.access(os.path.join(repo, "join.sh"), os.X_OK)
assert subprocess.run(["sh", "-n", os.path.join(repo, "join.sh")]).returncode == 0
ps = open(os.path.join(repo, "join.ps1")).read()
for needle in ("Cert:\\CurrentUser\\Root", "Test-NetConnection", "claude plugin install", "docs-http"):
    assert needle in ps, needle
assert "join.sh" in open(os.path.join(repo, "README.md")).read()
shared = open(os.path.join(B, "multiuser", "install-shared.sh")).read()
assert "PAAS_DOCS_PORT=8443" in shared and "--remove-port" in shared
r = subprocess.run(["sh", os.path.join(B, "multiuser", "install-multiuser.sh"), "--dry-run", "--docs-port", "8443"], capture_output=True, text=True)
assert r.returncode == 0, r.stdout + r.stderr
r = subprocess.run(["sh", os.path.join(B, "multiuser", "install-multiuser.sh"), "--dry-run", "--docs-port", "x"], capture_output=True, text=True)
assert r.returncode != 0 and "port number" in r.stdout, r.stdout
print("join scripts and docs port ok")

# 9. --plain-http: the docs service's TLS arguments come from docs.env (empty = http), the market server reads market.env,
#    the clients take http:// addresses; a team note that holds every word of a question comes before the library
svc = open(os.path.join(B, "multiuser", "paas-docs.service")).read()
assert "$PAAS_DOCS_TLS_ARGS" in svc and "--tls-cert /etc/paas/market" not in svc
assert "PAAS_DOCS_TLS_ARGS=" in shared and 'SCHEME=http' in shared and "PAAS_MARKET_TLS=0" in shared
assert "EnvironmentFile=-/etc/paas/market/market.env" in open(os.path.join(B, "multiuser", "paas-market-serve.service")).read()
mu = open(os.path.join(B, "multiuser", "install-multiuser.sh")).read()
assert "--plain-http) SCHEME_SET=http" in mu and "--https) SCHEME_SET=https" in mu
js = open(os.path.join(B, "teams", "team-join.sh")).read()
assert "plain HTTP, no certificate needed" in js and "plain HTTP, no certificate needed" in ps
assert 'GIT_ALLOW_PROTOCOL="https:http:ssh:file"' in open(os.path.join(R, "docs-search-mcp", "mcp_stdio.py")).read()
kd = os.path.join(tmp, "rank")
os.makedirs(os.path.join(kd, "lib", "commvault", "11.40"))
for i in range(6):
    open(os.path.join(kd, "lib", "commvault", "11.40", f"t{i}.md"), "w").write(
        f"# Cloud library topic {i}\n\nA cloud storage library goes offline when the access node cannot resolve DNS {i}. " * 3)
docs_index.build(os.path.join(kd, "lib"), os.path.join(kd, "lib.db"), full=True, log=lambda *a: None)
os.makedirs(os.path.join(kd, "brain", "notes"))
open(os.path.join(kd, "brain", "notes", "commvault.md"), "w").write(
    "# commvault: known issues\n2026-11-04 · the S3 cloud library goes offline when the access node loses DNS; restore the DNS entry · verified · job 1\n")
msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "cloud library offline access node DNS", "limit": 3}}}]
r = subprocess.run([sys.executable, os.path.join(R, "docs-search-mcp", "mcp_stdio.py"), "--db", os.path.join(kd, "lib.db"),
                    "--knowledge", os.path.join(kd, "brain")], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                   capture_output=True, text=True, timeout=120, env=dict(os.environ, HOME=os.path.join(kd, "home")))
res = json.loads(json.loads(r.stdout.strip().splitlines()[-1])["result"]["content"][0]["text"])["results"]
assert res and res[0].get("library") == "team knowledge", [(x.get("library"), x.get("title")) for x in res]
print("plain http and team knowledge first ok")

# 10. any Python, Windows links, simultaneous notes: hooks start through hooks/pyrun (python3, python, py -3; without any the
#     guard fails closed except the docs servers); knowledge files can be hard links (Windows without the symlink right)
#     that are re-made after a pull; the team repository merges knowledge files with git's union driver
plug = os.path.join(tmp, "paas-brain-flashback")
hj = json.load(open(os.path.join(plug, "hooks", "hooks.json")))["hooks"]
cmds = {x["command"] for gs in hj.values() for g in gs for x in g["hooks"]}
assert cmds and all(c.startswith('sh "${CLAUDE_PLUGIN_ROOT}"/hooks/pyrun "${CLAUDE_PLUGIN_ROOT}"/hooks/') for c in cmds), cmds
pr = os.path.join(plug, "hooks", "pyrun")
nopy = os.path.join(tmp, "nopy")
os.makedirs(nopy)
for c in ("sh", "grep", "basename", "cat"):
    os.symlink(shutil.which(c), os.path.join(nopy, c))
def guard(tool, path):
    return subprocess.run([os.path.join(path, "sh"), pr, os.path.join(plug, "hooks", "block-write-tools.py")],
                          input=json.dumps({"tool_name": tool, "tool_input": {}}), capture_output=True, text=True, env={"PATH": path})
assert guard("mcp__plugin_paas-brain-flashback_commvault-env1__get_jobs_list", nopy).returncode == 2
assert guard("Bash", nopy).returncode == 2
assert guard("mcp__plugin_paas-brain-flashback_docs-http__search_docs", nopy).returncode == 0
r = subprocess.run([os.path.join(nopy, "sh"), pr, os.path.join(plug, "hooks", "session-start.py")], input="{}", capture_output=True, text=True, env={"PATH": nopy})
assert r.returncode == 0 and "Python 3 is not installed" in r.stdout, r.stdout
onlypy = os.path.join(tmp, "onlypy")
os.makedirs(onlypy)
for c in ("sh", "grep", "basename", "cat"):
    os.symlink(shutil.which(c), os.path.join(onlypy, c))
os.symlink(sys.executable, os.path.join(onlypy, "python"))
assert guard("mcp__plugin_paas-brain-flashback_commvault-env1__kill_job", onlypy).returncode == 2       # the real guard
assert guard("mcp__plugin_paas-brain-flashback_commvault-env1__get_jobs_list", onlypy).returncode == 0
attrs = open(os.path.join(repo, ".gitattributes")).read()
assert "knowledge/**/*.md merge=union" in attrs and "knowledge/INDEX.md -merge" in attrs
# hard links: paas-team with PAAS_NO_SYMLINKS=1 links the files by hard link, re-links after the clone's file was replaced
hl = os.path.join(tmp, "hlhome")
henv2 = dict(henv, HOME=hl, PAAS_NO_SYMLINKS="1")
subprocess.run([sys.executable, tool, "add", "flashback", "file://" + bare], check=True, env=henv2, stdout=subprocess.DEVNULL)
subprocess.run([sys.executable, tool, "use", "flashback"], check=True, env=henv2, stdout=subprocess.DEVNULL)
b = os.path.join(hl, ".claude", "brain")
k = os.path.join(b, "teams", "flashback", "knowledge")
for n in ("notes.md", "environment.md", "tool-map.md"):
    assert not os.path.islink(os.path.join(b, n)) and os.path.samefile(os.path.join(b, n), os.path.join(k, n)), n
t = open(os.path.join(k, "notes.md")).read()
os.remove(os.path.join(k, "notes.md"))                                  # what a git pull does: a new file, the link broken
open(os.path.join(k, "notes.md"), "w").write(t + "- teammate line\n")
time.sleep(1.1)
with open(os.path.join(b, "notes.md"), "a") as f:
    f.write("- my line written after the pull\n")
r = subprocess.run([sys.executable, tool, "link-files"], env=henv2, capture_output=True, text=True)
assert "re-linked notes.md" in r.stdout, r.stdout + r.stderr
merged = open(os.path.join(b, "notes.md")).read()
assert "- teammate line" in merged and "- my line written after the pull" in merged, merged
assert os.path.samefile(os.path.join(b, "notes.md"), os.path.join(k, "notes.md"))
print("pyrun, windows links and union merge ok")
