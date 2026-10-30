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
p = subprocess.run([sys.executable, os.path.join(here, "mcp_stdio.py"), "--db", db],
                   input="".join(json.dumps(m) + "\n" for m in msgs), capture_output=True, text=True, timeout=60)
out = {m["id"]: m for m in (json.loads(l) for l in p.stdout.splitlines() if l.strip())}
assert out[1]["result"]["serverInfo"]["name"] == "docs-search" and out[1]["result"]["instructions"]
assert [t["name"] for t in out[2]["result"]["tools"]] == ["search_docs", "explain_code", "read_chunk", "read_document", "list_sources"]
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
