"""Check of the docs-hints hook on a tiny library: python3 brain/test_docs_hints.py"""
import json, os, sqlite3, subprocess, sys, tempfile

d = tempfile.mkdtemp()
db = os.path.join(d, "docs.db")
c = sqlite3.connect(db)
c.executescript("""CREATE TABLE docs(id INTEGER PRIMARY KEY, path TEXT, vendor TEXT, product TEXT, title TEXT, dup_of INTEGER);
CREATE TABLE chunks(id INTEGER PRIMARY KEY, doc_id INTEGER, seq INTEGER);
CREATE VIRTUAL TABLE chunks_fts USING fts5(title, heading, text, tokenize='porter unicode61 remove_diacritics 2');""")
rows = [(1, "netapp/ontap-ems/wafl-vol-events.adoc", "netapp", "ontap-ems", "wafl.vol events", "wafl.vol.full",
         "*Severity*:: ALERT *Description*:: This message occurs when the volume is full. *Corrective Action*:: Grow it."),
        (2, "dell/kb/000185226_sio.html", "dell", "kb", "PowerFlex: Dial home alert SIO02.04.0000005 - CAPACITY | Dell US",
         "Symptoms", "Spare capacity is below the threshold.")]
for i, path, v, p, title, head, text in rows:
    c.execute("INSERT INTO docs VALUES (?,?,?,?,?,NULL)", (i, path, v, p, title))
    c.execute("INSERT INTO chunks VALUES (?,?,0)", (i * 10, i))
    c.execute("INSERT INTO chunks_fts(rowid, title, heading, text) VALUES (?,?,?,?)", (i * 10, title, head, text))
c.commit()

hook = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude", "hooks", "docs-hints.py")


def run(tool, text, sid):
    inp = json.dumps({"session_id": sid, "tool_name": tool, "tool_response": [{"type": "text", "text": text}]})
    out = subprocess.run([sys.executable, hook], input=inp, capture_output=True, text=True,
                         env={**os.environ, "DOCS_HINTS_DB": db}).stdout
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""


sid = f"t{os.getpid()}"
ctx = run("mcp__ontap__ems", "node1: wafl.vol.full on vol1.prod; host esx01.corp.local; SIO02.04.0000005", sid)
assert "wafl.vol.full [ontap-ems, chunk 10]: ALERT. This message occurs when the volume is full." in ctx, ctx
assert "Corrective action: Grow it." in ctx and "SIO02.04.0000005 [dell/kb, chunk 20]" in ctx, ctx
assert "vol1.prod" not in ctx and "esx01" not in ctx, ctx                       # only documented names
assert run("mcp__ontap__ems", "wafl.vol.full again", sid) == ""                # once per session
assert run("mcp__docs-local__search_docs", "wafl.vol.full", sid + "b") == ""   # not on the docs MCP itself
assert run("mcp__ontap__ems", "all good, nothing to report", sid + "c") == ""
for f in os.listdir(tempfile.gettempdir()):
    if f.startswith("claude-docs-hints-t"):
        os.remove(os.path.join(tempfile.gettempdir(), f))
print("docs hints ok")
