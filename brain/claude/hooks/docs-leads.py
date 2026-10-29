#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook: search the offline library with every request and hand Claude the best
matching documents before it answers - for any request the library can inform (troubleshooting, concepts,
design, best practices, automation against a vendor API, an app modelled on a vendor's design), not only
storage questions. Pasted EMS names / alert codes get their meaning (same logic as docs-hints.py).

Silent unless the match is strong (MIN_WORDS topic words found and MIN_COVER of the request's words in the top
hit), so "yes", "continue" or unrelated requests cost nothing; at most MAX_LEADS documents (~30 tokens each);
the same leads are not repeated in a session. Standard library only; never blocks the prompt (always exit 0).
Library: ~/.claude/brain/library (search.py + docs.db; DOCS_LEADS_LIB / DOCS_LEADS_DB override).
"""
import importlib.util
import json
import os
import re
import sys
import tempfile

LIB = os.environ.get("DOCS_LEADS_LIB") or os.path.expanduser("~/.claude/brain/library")
DB = os.environ.get("DOCS_LEADS_DB") or os.path.join(LIB, "docs.db")
MAX_LEADS, MIN_WORDS, MIN_COVER, MAX_QUERY_WORDS = 4, 2, 0.6, 60
# the library's world: a request gets leads only when it names one of these (plus every product name in the
# library, read from it) or pastes an identifier; "ok continue" or "center a div in css" never does
DOMAIN = set("""netapp ontap dell emc powermax vmax symmetrix powerflex scaleio vxflex powerscale isilon onefs powerstore
unity trident harvest csm csi kubernetes k8s openshift ocp vmware vsphere esxi vcenter vsan vvols vasa datastore datastores
vmfs rdm lun luns naa eui wwpn wwpns wwn wwnn zone zones zoning zoneset fabric fabrics mds nexus brocade ucs fi fcoe fc
iscsi nvme nvmeof multipath multipathing alua hba hbas snapmirror snapvault snapshot snapshots snapvx srdf timefinder
aggregate aggregates svm vserver igroup igroups lif lifs flexvol flexgroup qtree qos fabricpool metrocluster raid ems
autosupport storage san nas nfs smb cifs replication sdc sds mdm pfmp unisphere symcli solutions-enabler pvc pv
storageclass provisioner snapshotter attacher dedupe deduplication compression thin provisioning iops latency throughput
masking initiator initiators target targets array arrays volume volumes disk disks shelf shelves controller controllers
cluster node failover takeover giveback mediator tiebreaker kb contap dsa""".split())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GENERIC = set("""metrics external tools infohub systems switches series operator observability manager issues
changelog utils upgrade unified transition technical system spec setup select retriever restapi reports repo plugin
node monitor metadata health extensions driver docs console classic charts cert automation authorization apps admin
active""".split())     # words in product names that are everyday English: they do not make a request storage-related


def in_domain(words):
    """(request is about the library's world, vendors of the products it names). A named product limits the
    leads to its vendor: "a FastAPI endpoint returning the users list" must not get ONTAP REST pages on users."""
    vocab, vendors_of = set(DOMAIN), {}
    try:
        import sqlite3
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        for v, p in c.execute("SELECT DISTINCT vendor, product FROM docs"):
            vendors_of.setdefault(v.lower(), set()).add(v.lower())
            for w in re.split(r"[-_]", p.lower()):
                if len(w) >= 4 and not w.isdigit() and w not in GENERIC:
                    vocab.add(w)
                    vendors_of.setdefault(w, set()).add(v.lower())
    except Exception:
        pass
    words = [x for x in words if not re.search(r"[/~\\]|^https?:", x)]      # folder paths and urls do not count
    toks = {w.lower() for x in words for w in re.findall(r"[A-Za-z][A-Za-z0-9]+", x)}
    named = set().union(*(vendors_of.get(t, set()) for t in toks)) if toks else set()
    return bool(toks & vocab), named


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = (data.get("prompt") or "").strip()
    if not prompt or prompt.startswith("/") or not os.path.exists(DB) or os.environ.get("DOCS_LEADS") == "0":
        return 0
    lines = []
    # 1. identifiers pasted in the request (EMS names, SYMAPI alerts, SIO codes, CONTAP, DSA): their meaning
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        hints = load("docs_hints", os.path.join(here, "docs-hints.py"))
        hints.DB = DB
        import io
        old = sys.stdin, sys.stdout
        sys.stdin, sys.stdout = io.StringIO(json.dumps({"session_id": data.get("session_id", "x"),
                                                        "tool_name": "mcp__prompt__request", "tool_response": prompt})), io.StringIO()
        try:
            hints.main()
            out = sys.stdout.getvalue()
        finally:
            sys.stdin, sys.stdout = old
        if out:
            lines += json.loads(out)["hookSpecificOutput"]["additionalContext"].splitlines()[1:]
    except Exception:
        pass
    # 2. the best documents for the request itself, when it is about the library's world at all
    words = re.findall(r"\S+", prompt)[:MAX_QUERY_WORDS]
    about, vendors = in_domain(words)
    if not lines and not about:
        return 0
    try:
        mod = os.path.join(LIB, "search.py")
        lib = load("search", mod if os.path.exists(mod) else os.path.join(LIB, "search_cli.py"))
        c = lib.connect(DB)
        q = " ".join(words).replace('"', " ")
        res = lib.search_docs(c, q, vendor=next(iter(vendors)) if len(vendors) == 1 else "", limit=8)["results"]
    except Exception:
        res = []
    leads, seen_docs, seen_titles = [], set(), set()
    for r in res:
        if vendors and r["vendor"].lower() not in vendors:
            continue
        hit, _, n = r.get("matched", "0/1").partition("/")
        if not n or int(hit) < MIN_WORDS or int(hit) / int(n) < MIN_COVER:
            continue
        title = re.sub(r"\s*\|\s*Dell.*$", "", r["title"])[:90]
        if r["path"] in seen_docs or title.lower() in seen_titles:     # one lead per document, not per version
            continue
        seen_docs.add(r["path"]); seen_titles.add(title.lower())
        sec = r.get("section")
        leads.append(f"{title}" + (f" :: {sec[:60]}" if sec else "") + f" [{r['vendor']}/{r['product']}, chunk {r['chunk_id']}]")
        if len(leads) >= MAX_LEADS:
            break
    # once per session: the same leads twice add nothing
    sid = re.sub(r"[^A-Za-z0-9-]", "", str(data.get("session_id", "x")))
    seen_file = os.path.join(tempfile.gettempdir(), f"claude-docs-leads-{sid}")
    try:
        shown = set(open(seen_file).read().splitlines())
    except OSError:
        shown = set()
    leads = [x for x in leads if x not in shown]
    if leads:
        try:
            with open(seen_file, "a") as f:
                f.write("\n".join(leads) + "\n")
        except OSError:
            pass
        lines += ["lead: " + x for x in leads]
    if lines:
        print("Offline docs library, matched to this request (leads, not answers: read_chunk / search_docs before "
              "relying on them; ignore if unrelated):\n" + "\n".join("- " + x.lstrip("- ") for x in lines))
    return 0


if __name__ == "__main__":
    try:   # switched off by this person in the web UI (Brain tab, MCP & hooks)
        if "docs-leads" in open(os.path.expanduser("~/.claude/brain/hooks-off")).read().split():
            sys.exit(0)
    except OSError:
        pass
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
