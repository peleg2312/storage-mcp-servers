"""Self-contained test: build a small corpus (adoc, md, html, pdf, redirect stub), index it,
exercise every tool, then change/remove files and check the incremental update."""
import asyncio
import json
import os
import shutil
import tempfile
import time

root = tempfile.mkdtemp()
docs, db = os.path.join(root, "docs"), os.path.join(root, "index", "docs.db")
os.environ["INDEX_DB"] = db
here = os.path.dirname(os.path.abspath(__file__))


def w(rel, text):
    p = os.path.join(docs, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(text)


w("netapp/ontap/san-admin/map-lun.adoc", """---
permalink: san-admin/map-lun.html
summary: 'Map a LUN to an igroup'
---
= Map a LUN to an igroup
:icons: font

You map a LUN to an igroup so hosts can access it.

== Steps
. Create the mapping:
+
----
lun mapping create -vserver svm1 -path /vol/v1/lun1 -igroup esx_cluster1
----
. Verify with `lun mapping show`.

== Find a LUN by NAA
The NAA ID of an ONTAP LUN is naa.600a0980 followed by the hex of the serial. Use lun show -serial-hex.
""")
w("netapp/ontap/redirect/old-page.adoc", "---\npermalink: old.html\nredirect: ontap/san-admin/map-lun.html\n---\n")
w("netapp/ontap-ems-9171/callhome-hm-events.adoc", "= callhome.hm events\n\n== callhome.hm.alert.critical\n*Severity*:: ALERT\nSystem health monitor alert.\n")
w("runbooks/team/decom.md", "# Datastore decommission\n\n## Order\nUnmount, detach on every host, unmap, rescan, detached remove, unzone.\n")
w("dell/powerflex/kb-eui.html", "<html><head><title>PowerFlex EUI identifier</title><style>x{}</style></head><body>"
  "<nav>menu</nav><h2>Locate the EUI</h2><p>ESXi shows SDC volumes as eui.<b>id</b>; match the Volume ID "
  "from scli --query_all_volumes.</p><script>var a=1;</script></body></html>")
os.makedirs(os.path.join(docs, "dell", "powermax"), exist_ok=True)
shutil.copy(os.path.join(here, "tests", "sample.pdf"), os.path.join(docs, "dell", "powermax", "h8115.pdf"))
json.dump({"h8115.pdf": {"url": "https://example.dell/h8115.pdf", "title": "VAAI with PowerMax"}},
          open(os.path.join(docs, "dell", "powermax", "manifest.json"), "w"))

# identical EMS page in two more ONTAP versions -> folded into one canonical copy (unversioned product wins)
w("netapp/ontap-ems-9161/callhome-hm-events.adoc", "= callhome.hm events\n\n== callhome.hm.alert.critical\n*Severity*:: ALERT\nSystem health monitor alert.\n")
w("netapp/ontap-ems-9181/callhome-hm-events.adoc", "= callhome.hm events\n\n== callhome.hm.alert.critical\n*Severity*:: ALERT\nSystem health monitor alert.\n")

import docs_index  # noqa: E402
r = docs_index.build(docs, db, log=lambda *_: None)
assert r["documents"] == 7 and r["errors"] == 0 and r["deduped"] == 2, r   # redirect stub skipped, 2 copies folded
import sqlite3  # noqa: E402
_c = sqlite3.connect(db)
assert _c.execute("SELECT count(*) FROM docs WHERE dup_of IS NOT NULL").fetchone()[0] == 2
assert _c.execute("SELECT product FROM docs WHERE path LIKE 'netapp/ontap-ems%' AND dup_of IS NULL").fetchone()[0] == "ontap-ems-9181"  # newest version kept
assert _c.execute("SELECT count(*) FROM chunks c JOIN docs d ON d.id=c.doc_id WHERE d.product='ontap-ems-9161'").fetchone()[0] == 0
_c.close()
import server  # noqa: E402


async def main():
    async def call(n, **a):
        return (await server.mcp.call_tool(n, a)).structured_content

    src = await call("list_sources")
    assert src["libraries"][0]["documents"] == 7 and src["libraries"][0]["library"] == "main", src
    s = await call("search_docs", query="lun mapping create igroup")
    top = s["results"][0]
    assert top["url"] == "https://docs.netapp.com/us-en/ontap/san-admin/map-lun.html" and top["vendor"] == "netapp", top
    s = await call("search_docs", query="naa.600a0980 serial")
    assert s["results"] and s["results"][0]["section"] == "Find a LUN by NAA", s
    s = await call("search_docs", query="XCOPY transfer size", vendor="dell")
    assert s["results"][0]["title"] == "VAAI with PowerMax" and s["results"][0]["url"] == "https://example.dell/h8115.pdf"
    s = await call("search_docs", query="query_all_volumes eui", product="powerflex")
    assert s["results"] and "var a" not in s["results"][0]["snippet"] and "menu" not in s["results"][0]["snippet"]
    s = await call("search_docs", query="callhome.hm.alert.critical", product="ontap-ems-9161")  # alias product filter
    assert s["results"] and s["results"][0]["product"] == "ontap-ems-9181" and \
        sorted(s["results"][0]["also_in"]) == ["netapp/ontap-ems-9161", "netapp/ontap-ems-9171"], s["results"][:1]
    assert len([r for r in s["results"] if "callhome" in r["path"]]) == 1, "folded copies must not appear twice"
    rd = await call("read_document", path="netapp/ontap-ems-9161/callhome-hm-events.adoc")  # alias path -> canonical
    assert rd["path"] == "netapp/ontap-ems-9181/callhome-hm-events.adoc" and rd["sections"], rd
    s = await call("search_docs", query="callhome.hm.alarm")  # near miss -> partial match, still found
    assert s["match_mode"].startswith("partial") and s["results"]
    s = await call("search_docs", query="symmetrix XCOPY")          # synonym: VMAX / Symmetrix = PowerMax
    assert s["results"] and s["results"][0]["title"] == "VAAI with PowerMax", s
    s = await call("search_docs", query="detach unzone", vendor="runbooks")
    assert s["results"][0]["product"] == "team"
    rc = await call("read_chunk", chunk_id=top["chunk_id"], context=2)
    assert any(x["is_hit"] for x in rc["sections"]) and len(rc["sections"]) >= 2
    rd = await call("read_document", url="https://example.dell/h8115.pdf", max_sections=1)
    assert rd["total_sections"] == 2 and rd["next_start"] == 1
    for bad in ('"', "   ", "***"):
        try:
            await call("search_docs", query=bad)
            raise SystemExit(f"bad query accepted: {bad!r}")
        except Exception as e:
            assert "empty query" in str(e) or "Error" in str(e)

    # incremental update: change one file, delete one, add one; server picks up the new index
    time.sleep(1.1)
    w("runbooks/team/decom.md", "# Datastore decommission v2\n\nAlways check RDM backings with vmkfstools queryrdm first.\n")
    os.remove(os.path.join(docs, "netapp/ontap-ems-9181/callhome-hm-events.adoc"))   # the canonical copy goes away
    w("runbooks/team/zoning.md", "# Zoning standard\n\nSingle initiator single target, device-alias naming site_host_hbaN.\n")
    r2 = docs_index.build(docs, db, log=lambda *_: None)
    assert (r2["added"], r2["updated"], r2["removed"]) == (1, 1, 1), r2
    s = await call("search_docs", query="vmkfstools queryrdm")
    assert s["results"] and s["results"][0]["title"] == "Datastore decommission v2"
    s = await call("search_docs", query="callhome", limit=5)   # the orphaned aliases were re-parsed: newest left is canonical
    assert len(s["results"]) == 1 and s["results"][0]["product"] == "ontap-ems-9171" \
        and s["results"][0]["also_in"] == ["netapp/ontap-ems-9161"], s
    # second (local) index: the team's own saved KB / runbooks, searched together with the main library
    local_docs, local_db = os.path.join(root, "local"), os.path.join(root, "local.db")
    os.makedirs(os.path.join(local_docs, "saved-kb", "netapp"))
    open(os.path.join(local_docs, "saved-kb", "netapp", "kb-1234.md"), "w").write(
        "# KB 1234: LUN offline after snapshot restore\n\nWorkaround: lun online -vserver svm1 -path /vol/v1/lun1\n")
    docs_index.build(local_docs, local_db, log=lambda *_: None)
    server.DBS.append(local_db)
    s = await call("search_docs", query="lun online snapshot restore")
    hit = s["results"][0]
    assert hit["library"] == "local" and hit["chunk_id"] >= server.ID_BASE, hit
    rc = await call("read_chunk", chunk_id=hit["chunk_id"])
    assert "Workaround" in rc["sections"][0]["text"]
    s = await call("search_docs", query="lun mapping create igroup")
    assert s["results"][0]["library"] == "main"
    libs = (await call("list_sources"))["libraries"]
    assert [x["library"] for x in libs] == ["main", "local"]
    print("ALL TESTS PASSED", r, r2)


asyncio.run(main())

# source code: one section per top-level func, headed by its signature, titled <dir>/<file>
title, chunks = docs_index.parse_code('package scsi\n\nimport "errors"\n\nfunc (s *Scsi) Rescan(dev string) error {\n'
                                      '\treturn errors.New("rescan failed: device busy")\n}\n\ntype Dev struct{}\n',
                                      "/x/gobrick/internal/scsi/scsi.go")
assert title == "scsi/scsi.go", title
assert [h for h, _ in chunks] == ["scsi/scsi.go", "func (s *Scsi) Rescan(dev string) error", "type Dev struct{}"], chunks
assert "rescan failed: device busy" in chunks[1][1]
print("code parser OK")

# page chrome dropped; KB labels drawn as plain text become sections; license headers dropped
kb = ("<html><title>KB 1</title><body><h1>KB 1</h1><div>Print</div><div>Email</div><div>English</div><div>Česky</div>"
      "<div>Dansk</div><div>简体中文</div><div>Affected Products</div><div>Provide Feedback</div>"
      "<div>Symptoms</div><div>LUN offline after upgrade</div><div>Cause</div><div>Bug 123</div>"
      "<div>Resolution</div><div>Upgrade to 10.1</div></body></html>")
_, ch = docs_index.parse_html(kb, "kb")
assert [h for h, _ in ch] == ["Symptoms", "Cause", "Resolution"], ch
assert ch[0][1] == "LUN offline after upgrade" and "Feedback" not in str(ch), ch
_, ch = docs_index.parse_code("# Copyright © 2025 Dell Inc. All Rights Reserved.\n# Licensed under the Apache License\n"
                              "apiVersion: v1\nkind: ConfigMap\n", "/x/powermax-array-config.yaml")
assert "Copyright" not in ch[0][1] and "ConfigMap" in ch[0][1], ch
print("cleanup OK")

# Dell site chrome: cookie banner sections, country menu and feedback lines are dropped
page = ("<html><title>PowerFlex VCF</title><body><h2>Overview</h2><div>PowerFlex supports VCF workload domains.</div>"
        "<div>Thank you for your feedback!</div><div>United States/English</div><div>Canada/English</div>"
        "<h2>Your Cookie Preferences</h2><div>Dell uses different types of cookies</div></body></html>")
_, ch = docs_index.parse_html(page, "x")
assert [h for h, _ in ch] == ["Overview"] and ch[0][1].endswith("PowerFlex supports VCF workload domains."), ch
assert not any(w in ch[0][1] for w in ("feedback", "English", "cookies")), ch
print("site chrome OK")

# markdown license comments and the Info Hub browser banner are dropped
_, ch = docs_index.parse_md("<!-- Copyright (c) 2021 Dell Inc. Licensed under the Apache License -->\n# Guide\n\nUse helm.\n", "g")
assert "Copyright" not in str(ch) and "Use helm." in str(ch), ch
assert "Nytro" not in docs_index._clean("Best practices Your Browser is Out of Date Nytro.ai uses technology that works "
                                         "best in other browsers. For a full experience use one of the browsers below Keep RAID")
print("banner + md license OK")

# Hugo section pages (_index.md: the CSM install guides) and KBs named after a quoted title are indexed
import tempfile as _tf
_d = _tf.mkdtemp()
for _n in ("_index.md", "_PARTNER_DOWN__TAKEOVER_IMPOSSIBLE_1a2b.html", ".hidden.md", "manifest.json"):
    open(os.path.join(_d, _n), "w").write("x")
assert sorted(os.path.basename(p) for p in docs_index.iter_files(_d)) == ["_PARTNER_DOWN__TAKEOVER_IMPOSSIBLE_1a2b.html", "_index.md"]
print("underscore files OK")
