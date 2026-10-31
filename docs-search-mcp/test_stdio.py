"""mcp_stdio.py: MCP handshake and the four tools over stdio against a tiny index; search_cli output;
sync_netapp_kb extraction (full and login-gated articles). Standard library only."""
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
root = tempfile.mkdtemp()
docs, db = os.path.join(root, "docs"), os.path.join(root, "docs.db")
os.makedirs(os.path.join(docs, "netapp", "ontap-ems-9171"))
open(os.path.join(docs, "netapp", "ontap-ems-9171", "scsiblade-san-events.adoc"), "w").write(
    "= scsiblade.san events\n\n== scsiblade.san.config.active\n*Severity*:: NOTICE\n"
    "This message occurs when the SAN active-active state has changed.\n")
import docs_index  # noqa: E402
assert docs_index.build(docs, db, log=lambda *_: None)["documents"] == 1

msgs = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "active-active state"}}},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "read_chunk", "arguments": {"chunk_id": 1}}},
    {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "read_document", "arguments": {"path": "netapp/ontap-ems-9171/scsiblade-san-events.adoc"}}},
    {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "list_sources", "arguments": {}}},
    {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "read_chunk", "arguments": {"chunk_id": 999}}},
    {"jsonrpc": "2.0", "id": 8, "method": "nope"},
    {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "active-active state", "read_top": 1}}},
    {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"queries": ["active-active state", "zzzunknown"]}}},
    {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "explain_code", "arguments": {"code": "scsiblade.san.config.active"}}},
    {"jsonrpc": "2.0", "id": 12, "method": "tools/call", "params": {"name": "explain_code", "arguments": {"code": "nothing.documented.here"}}},
]
env = dict(os.environ, BRAIN_DB=os.path.join(root, "none.db"))      # no team-knowledge index: the library alone
p = subprocess.run([sys.executable, os.path.join(here, "mcp_stdio.py"), "--db", db],
                   input="".join(json.dumps(m) + "\n" for m in msgs), capture_output=True, text=True, timeout=60, env=env)
out = {m["id"]: m for m in (json.loads(l) for l in p.stdout.splitlines() if l.strip())}
assert out[1]["result"]["serverInfo"]["name"] == "docs-search" and out[1]["result"]["instructions"]
assert [t["name"] for t in out[2]["result"]["tools"]] == ["search_docs", "explain_code", "read_chunk", "read_document", "related_docs", "list_sources"]
hits = json.loads(out[3]["result"]["content"][0]["text"])
assert hits["results"][0]["section"] == "scsiblade.san.config.active" and hits["results"][0]["chunk_id"] == 1, hits
assert "NOTICE" in out[4]["result"]["content"][0]["text"]
assert json.loads(out[5]["result"]["content"][0]["text"])["total_sections"] == 1
assert json.loads(out[6]["result"]["content"][0]["text"])["libraries"][0]["documents"] == 1
assert out[7]["result"]["isError"] is True
assert out[8]["error"]["code"] == -32601
assert len(out[1]["result"]["instructions"].encode()) < 1500
assert json.loads(out[6]["result"]["content"][0]["text"])["libraries"][0]["by_vendor"] == {"netapp": "ontap-ems-9171 1"}
assert len(out) == 12, "notification must not be answered"
top = json.loads(out[9]["result"]["content"][0]["text"])["results"][0]
assert "SAN active-active state" in top["text"] and "snippet" not in top, top            # read_top: text inline
assert "text" not in hits["results"][0]                                                  # and only when asked
multi = json.loads(out[10]["result"]["content"][0]["text"])
assert multi["results"][0]["chunk_id"] == 1 and len(multi["results"]) == 1, multi         # merged, de-duplicated
assert [(q["q"], q["hits"], q.get("partial")) for q in multi["by_query"]] == [("active-active state", 1, None), ("zzzunknown", 0, True)], multi
ems = json.loads(out[11]["result"]["content"][0]["text"])
assert ems["kind"] == "ontap-ems" and ems["severity"] == "NOTICE" and ems["chunk_id"] == 1 and "SAN active-active" in ems["description"], ems
assert json.loads(out[12]["result"]["content"][0]["text"]) == {"code": "nothing.documented.here", "documented": False}

real = next((p for p in (os.environ.get("INDEX_DB", "").split(",")[0], os.path.join(here, "work", "index", "docs.db")) if p and os.path.isfile(p)), None)
if real:                                  # the real library, when this checkout has it
    import search_cli as lib  # noqa: E402
    rc = lib.connect(real)
    e = lib.explain_code(rc, "wafl.vol.full")
    assert e["kind"] == "ontap-ems" and e["severity"] == "ALERT" and e["corrective_action"] and e["url"], e
    assert lib.explain_code(rc, "SYMAPI_AEVENT2_UID_EVT_RESTARTED")["kind"] == "powermax-alert"
    b = lib.explain_code(rc, "CONTAP-698579")
    assert b["kind"] == "ontap-bug" and "Issue" in b["sections"] and b["chunk_id"], b
    assert lib.explain_code(rc, "000446689")["kind"] == "kb"
    assert lib.explain_code(rc, "CONTAP-999999") == {"code": "CONTAP-999999", "documented": False}
    s2 = lib.search(rc, "lun mapping show", read_top=2)["results"]
    assert all("text" in r for r in s2[:2]) and "text" not in s2[2], "read_top=2"
    m = lib.search(rc, queries=["lun mapping show", "igroup create"], limit=6)
    assert len(m["by_query"]) == 2 and len({r["chunk_id"] for r in m["results"]}) == len(m["results"])
    import time  # noqa: E402
    lib.search_docs(rc, "lun mapping show", limit=8)
    t = time.perf_counter()
    lib.search_docs(rc, "lun mapping show", limit=8)
    assert time.perf_counter() - t < 0.001, "a repeated query is answered from the LRU"

c = subprocess.run([sys.executable, os.path.join(here, "search_cli.py"), "--db", db, "search", "san active"],
                   capture_output=True, text=True)
assert "scsiblade.san.config.active" in c.stdout and "chunk 1" in c.stdout, c.stdout

from sync import sync_netapp_kb as kb  # noqa: E402
full = (b'<html><head><title>How to map a LUN - NetApp Knowledge Base</title></head><body><nav>x</nav>'
        b'<section class="mt-content-container"><div class="mt-section"><h4 class="editable">Applies to</h4><p>ONTAP 9</p>'
        b'<h4>Procedure</h4><p style="color:red">Run <code>lun map</code> and verify with lun mapping show.</p></div>'
        b'<p>NetApp provides no representations or warranties...</p></section>'
        b'<footer class="elm-content-footer">f</footer></body></html>')
title, page, partial = kb.extract(full, "https://kb.netapp.com/x/How_to_map_a_LUN")
assert title == "How to map a LUN" and not partial and "<h2>Procedure</h2>" in page and "warranties" not in page \
    and 'style="' not in page and "Partial" not in page, page
gated = full.replace(b'<h4>Procedure</h4><p style="color:red">Run <code>lun map</code> and verify with lun mapping show.</p>',
                     b'<h4>Issue</h4><p>LUN is not visible on the host after mapping.</p>'
                     b'<div class="signin"><p>Sign in to view the entire content of this KB article.</p><a>SIGN IN</a></div>')
title, page, partial = kb.extract(gated, "https://kb.netapp.com/x/How_to_map_a_LUN")
assert partial and "Partial article" in page and "SIGN IN" not in page and "ONTAP 9" in page \
    and "<h2>Issue</h2>" in page, page
_, page, _ = kb.extract(b"<html><title>t</title><body>no container</body></html>", "u")
assert page is None
print("stdio server, CLI and NetApp KB extraction OK")

# a second, small index of the person's team knowledge (add-docs --brain): searched with the library, chunk ids offset,
# read_chunk / read_document / related_docs routed to it, list_sources names both
bdocs, bdb = os.path.join(root, "bdocs"), os.path.join(root, "brain.db")
os.makedirs(os.path.join(bdocs, "local", "brain-notes"))
open(os.path.join(bdocs, "local", "brain-notes", "ontap-nas.md"), "w").write(
    "# ONTAP NAS\n- 2026-10-31 the active-active state note of the team: SAN config active-active checked verified ontap\n")
assert docs_index.build(bdocs, bdb, log=lambda *_: None, prefix="brain/")["documents"] == 1
msgs2 = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "active-active state"}}},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "list_sources", "arguments": {}}},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "read_document", "arguments": {"path": "brain/local/brain-notes/ontap-nas.md"}}},
    {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"queries": ["active-active state", "nothing here"], "read_top": 1}}},
]
p = subprocess.run([sys.executable, os.path.join(here, "mcp_stdio.py"), "--db", db, "--brain-db", bdb],
                   input="".join(json.dumps(m) + "\n" for m in msgs2), capture_output=True, text=True, timeout=60)
out = {m["id"]: m for m in (json.loads(l) for l in p.stdout.splitlines() if l.strip())}
hits = json.loads(out[2]["result"]["content"][0]["text"])["results"]
libs = {r.get("library", "main") for r in hits}
assert libs == {"main", "team knowledge"}, hits
team_hit = next(r for r in hits if r.get("library") == "team knowledge")
assert team_hit["chunk_id"] >= 10 ** 10, team_hit
msgs3 = [{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "read_chunk", "arguments": {"chunk_id": team_hit["chunk_id"]}}},
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "related_docs", "arguments": {"chunk_id": team_hit["chunk_id"]}}}]
p3 = subprocess.run([sys.executable, os.path.join(here, "mcp_stdio.py"), "--db", db, "--brain-db", bdb],
                    input="".join(json.dumps(m) + "\n" for m in msgs3), capture_output=True, text=True, timeout=60)
out3 = {m["id"]: m for m in (json.loads(l) for l in p3.stdout.splitlines() if l.strip())}
rc1 = json.loads(out3[1]["result"]["content"][0]["text"])
assert rc1["path"] == "brain/local/brain-notes/ontap-nas.md" and rc1["sections"][0]["chunk_id"] == team_hit["chunk_id"], rc1
assert not out3[2]["result"]["isError"], out3[2]
src = json.loads(out[3]["result"]["content"][0]["text"])["libraries"]
assert [l["library"] for l in src] == ["main", "team knowledge"] and src[1]["documents"] == 1, src
rd = json.loads(out[4]["result"]["content"][0]["text"])
assert rd["sections"][0]["chunk_id"] >= 10 ** 10 and "active-active" in rd["sections"][0]["text"], rd
multi = json.loads(out[5]["result"]["content"][0]["text"])
assert {e["q"] for e in multi["by_query"]} == {"active-active state", "nothing here"} and len(multi["by_query"]) == 2, multi["by_query"]
assert multi["results"][0].get("text"), "read_top fetched across indexes"
print("team-knowledge index ok")

# HTTP mode: token, health, JSON answers, a team's knowledge index built by the server from the team folder
import socket
import threading
import time
import urllib.error
import urllib.request
sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
tdir = os.path.join(root, "teams"); os.makedirs(os.path.join(tdir, "t1", "knowledge", "notes"))
open(os.path.join(tdir, "t1", "team.json"), "w").write(json.dumps({"name": "t1", "title": "Team one"}))
open(os.path.join(tdir, "t1", "knowledge", "notes", "powerscale.md"), "w").write("# PowerScale\n- 2026-10-31 smartconnect zone answers from pool0 verified isi\n")
tok = os.path.join(root, "token"); open(tok, "w").write("s3cret-token\n")
state = os.path.join(root, "state")
srv = subprocess.Popen([sys.executable, os.path.join(here, "mcp_stdio.py"), "--db", db, "--http", f"127.0.0.1:{port}", "--token-file", tok,
                        "--teams-dir", tdir, "--state-dir", state, "--refresh-minutes", "60"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    def req(path, body=None, token="s3cret-token"):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method="POST" if data else "GET",
                                   headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"null")
    for _ in range(100):
        try:
            if req("/health", token="")[0] == 200:
                break
        except Exception:
            time.sleep(0.1)
    for _ in range(100):                      # the refresh thread builds t1's index at start
        if os.path.exists(os.path.join(state, "t1.db.stamp")):
            break
        time.sleep(0.1)
    assert req("/health", token="")[1]["teams"] == ["t1"]
    assert req("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "ping"}, token="")[0] == 401
    assert req("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "ping"}, token="wrong")[0] == 401
    st, init = req("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}})
    assert st == 200 and init["result"]["serverInfo"]["name"] == "docs-search", init
    assert req("/mcp", {"jsonrpc": "2.0", "method": "notifications/initialized"})[0] == 202
    st, lib_only = req("/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "active-active state"}}})
    assert not lib_only["result"]["isError"], lib_only
    hits = json.loads(lib_only["result"]["content"][0]["text"])["results"]
    assert hits and all(r.get("library", "main") == "main" for r in hits), hits        # without ?team= the library alone answers
    st, team = req("/mcp?team=t1", {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "smartconnect zone pool0"}}})
    assert not team["result"]["isError"], team
    hits = json.loads(team["result"]["content"][0]["text"])["results"]
    assert any(r.get("library") == "team knowledge" and "powerscale.md" in r.get("path", "") for r in hits), hits
    st, src = req("/mcp?team=t1", {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "list_sources", "arguments": {}}})
    assert [l["library"] for l in json.loads(src["result"]["content"][0]["text"])["libraries"]] == ["main", "team knowledge"]
    st, bad = req("/mcp", {"jsonrpc": "2.0", "id": 5, "method": "nope"})
    assert st == 200 and bad["error"]["code"] == -32601, bad
    assert req("/mcp", {"jsonrpc": "2.0", "id": 6, "method": "ping"})[1]["result"] == {}
    print("http mode ok")
finally:
    srv.kill()

# on-demand refresh: a new page in the team folder is searchable right after POST /refresh?team=t1 (token required)
srv = subprocess.Popen([sys.executable, os.path.join(here, "mcp_stdio.py"), "--db", db, "--http", f"127.0.0.1:{port}", "--token-file", tok,
                        "--teams-dir", tdir, "--state-dir", state, "--refresh-minutes", "60"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    for _ in range(100):
        try:
            if req("/health", token="")[0] == 200:
                break
        except Exception:
            time.sleep(0.1)
    time.sleep(0.5)
    open(os.path.join(tdir, "t1", "knowledge", "notes", "vast.md"), "w").write("# VAST\n- 2026-10-31 the viewpolicy quorum rule of tenant alpha observed vms\n")
    assert req("/refresh?team=t1", {}, token="")[0] == 401
    assert req("/refresh?team=nope", {})[0] == 404
    st, r = req("/refresh?team=t1", {})
    assert st == 202 and r == {"refreshing": ["t1"]}, (st, r)
    found = False
    for _ in range(100):
        st, team = req("/mcp?team=t1", {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "viewpolicy quorum tenant alpha"}}})
        hits = json.loads(team["result"]["content"][0]["text"]).get("results", []) if not team["result"]["isError"] else []
        if any("vast.md" in r.get("path", "") for r in hits):
            found = True
            break
        time.sleep(0.1)
    assert found, hits
    print("refresh on demand ok")
finally:
    srv.kill()

# --knowledge DIR: the brain folder's notes pages indexed at start (stamp: no rebuild when unchanged); knowledge-only without a library
kb = os.path.join(root, "kbrain"); os.makedirs(os.path.join(kb, "notes")); os.makedirs(os.path.join(kb, "incidents", "2026"))
open(os.path.join(kb, "notes", "fabric.md"), "w").write("# Fabric\n- 2026-10-31 slowdrain on mds9 port fc1/7 verified mds\n")
open(os.path.join(kb, "incidents", "2026", "x.md"), "w").write("# Incident\n- zoning outage on fabric A\n")
kdb = os.path.join(root, "kbrain.db")
ask = [{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "slowdrain mds9 fc1/7"}}},
       {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_sources", "arguments": {}}},
       {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "zoning outage fabric"}}}]
def ask_stdio(args):
    p = subprocess.run([sys.executable, os.path.join(here, "mcp_stdio.py"), *args], input="".join(json.dumps(m) + "\n" for m in ask),
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-500:]
    return {m["id"]: json.loads(m["result"]["content"][0]["text"]) for m in (json.loads(l) for l in p.stdout.splitlines() if l.strip())}
o = ask_stdio(["--db", db, "--knowledge", kb, "--brain-db", kdb])
assert any(r.get("library") == "team knowledge" and "fabric.md" in r.get("path", "") for r in o[1]["results"]), o[1]
assert [l["library"] for l in o[2]["libraries"]] == ["main", "team knowledge"] and o[2]["libraries"][1]["documents"] == 2, o[2]
assert any("incidents" in r.get("path", "") for r in o[3]["results"]), o[3]
m0 = os.path.getmtime(kdb)
time.sleep(1.1)
ask_stdio(["--db", db, "--knowledge", kb, "--brain-db", kdb])
assert os.path.getmtime(kdb) == m0, "unchanged pages: no rebuild"
open(os.path.join(kb, "notes", "fabric.md"), "a").write("- 2026-10-31 another fact verified mds\n")
ask_stdio(["--db", db, "--knowledge", kb, "--brain-db", kdb])
assert os.path.getmtime(kdb) > m0, "changed pages: rebuilt"
# knowledge-only (no --db, no library anywhere near): the knowledge is the whole index
o = ask_stdio(["--knowledge", kb, "--brain-db", kdb])
assert o[1]["results"] and all(r.get("library", "main") == "main" for r in o[1]["results"]), o[1]
assert [l["library"] for l in o[2]["libraries"]] == ["main"] and o[2]["libraries"][0]["documents"] == 2, o[2]
print("knowledge at start ok")

# a shared team index on a multi-user VM: a member's docs-local uses the service's index when its stamp matches the member's
# clone (same pages, by content), and builds its own only when they differ
member = os.path.join(root, "member"); os.makedirs(os.path.join(member, "notes"))
open(os.path.join(member, "team"), "w").write("t1\n")
import shutil
for f in os.listdir(os.path.join(tdir, "t1", "knowledge", "notes")):
    shutil.copy(os.path.join(tdir, "t1", "knowledge", "notes", f), os.path.join(member, "notes", f))
own = os.path.join(root, "member.db")
assert os.path.exists(os.path.join(state, "t1.db.stamp"))
o = ask_stdio(["--db", db, "--knowledge", member, "--brain-db", own, "--shared-knowledge", state])
assert [l["library"] for l in o[2]["libraries"]] == ["main", "team knowledge"] and o[2]["libraries"][1]["documents"] == 2, o[2]
assert not os.path.exists(own), "the shared index served: no index of the member's own was built"
open(os.path.join(member, "notes", "mine.md"), "w").write("# Mine\n- 2026-10-31 a fact only I have observed me\n")
o = ask_stdio(["--db", db, "--knowledge", member, "--brain-db", own, "--shared-knowledge", state])
assert os.path.exists(own) and o[2]["libraries"][1]["documents"] == 3, "pages differ from the service's: own index"
print("shared knowledge ok")
