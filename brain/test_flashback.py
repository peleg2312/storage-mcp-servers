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
import subprocess
import sys
import tarfile
import tempfile

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
