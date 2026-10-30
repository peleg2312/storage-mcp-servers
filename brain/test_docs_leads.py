"""Check of the docs-leads hook on a tiny library built by docs_index.py: python3 brain/test_docs_leads.py"""
import json, os, subprocess, sys, tempfile

here = os.path.dirname(os.path.abspath(__file__))
lib = os.path.join(here, "..", "docs-search-mcp")
sys.path.insert(0, lib)
import docs_index  # noqa: E402

d = tempfile.mkdtemp()
pages = {"netapp/ontap/snapmirror-concept.adoc": "= SnapMirror replication overview\n\nSnapMirror replicates volume snapshots "
         "asynchronously between clusters; the destination is read-only until you break the relationship.\n",
         "dell/powermax/srdf-modes.md": "# SRDF modes\n\nSRDF/S is synchronous, SRDF/A is asynchronous with cycle-based "
         "delta sets.\n", "netapp/ontap-ems/wafl-vol-events.adoc": "= wafl.vol events\n\n== wafl.vol.full\n\n*Severity*:: "
         "ALERT *Description*:: This message occurs when the volume is full. *Corrective Action*:: Grow it.\n"}
for rel, text in pages.items():
    os.makedirs(os.path.join(d, "docs", os.path.dirname(rel)), exist_ok=True)
    open(os.path.join(d, "docs", rel), "w").write(text)
db = os.path.join(d, "docs.db")
docs_index.build(os.path.join(d, "docs"), db, full=True, log=lambda *a: None)
hook = os.path.join(here, "claude", "hooks", "docs-leads.py")
chats, code = os.path.join(d, "chats"), os.path.join(d, "code", "app")   # Chats imports the storage rules
os.makedirs(chats), os.makedirs(code)
open(os.path.join(chats, "CLAUDE.md"), "w").write("<!-- generated -->\n# Storage rules (SAN / storage operations)\n")


def run(prompt, sid, cwd=chats):
    env = {**os.environ, "DOCS_LEADS_LIB": lib, "DOCS_LEADS_DB": db, "DOCS_HINTS_DB": db}
    return subprocess.run([sys.executable, hook], input=json.dumps({"session_id": sid, "prompt": prompt, "cwd": cwd}),
                          capture_output=True, text=True, env=env).stdout


sid = f"l{os.getpid()}"
out = run("I want to build an app that replicates snapshots like netapp snapmirror between clusters", sid)
assert "- SnapMirror replication overview" in out and "[netapp/ontap, chunk" in out, out
assert run("I want to build an app that replicates snapshots like netapp snapmirror between clusters", sid) == ""  # once
assert "wafl.vol.full [ontap-ems, chunk" in run("cluster1 keeps logging wafl.vol.full, why?", sid + "b")
for p in ("yes, do it", "how do I center a div in css", "summarize this meeting for my manager",
          "Use ~/storage-mcp-servers for this", "/brain-health", "run the tests and fix the failing target", "add a python test for the disk usage function"):
    assert run(p, sid + "c") == "", p                                     # unrelated: silent
# a storage question in a code project: read storage.md, once per chat; coding asks there stay silent
out = run("cluster1 keeps logging wafl.vol.full, why?", sid + "d", code)
assert out.startswith("Storage question outside Chats: read ") and "storage.md (storage rules" in out and "wafl.vol.full" in out, out
assert "storage.md" not in run("is snapmirror async between clusters?", sid + "d", code)
assert run("run the tests and fix the failing target", sid + "e", code) == ""
assert "storage.md" not in run("in the app folder, find where the volume commands are validated", sid + "f", code)
for f in os.listdir(tempfile.gettempdir()):
    if f.startswith(("claude-docs-leads-l", "claude-docs-hints-l", "claude-storage-rules-l")):
        os.remove(os.path.join(tempfile.gettempdir(), f))
print("docs leads ok")
