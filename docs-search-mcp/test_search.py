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
os.environ["DOCS_ENV_FILE"] = os.path.join(root, "environment.md")
open(os.environ["DOCS_ENV_FILE"], "w").write("# My environment\n\n## Versions\n- ONTAP 9.16.1 → `ontap-ems-9161`\n\n## Fabrics\n`trident-2510`\n")
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
w("runbooks/team/decom.md", "# Datastore decommission\n\n## Order\nUnmount, detach on every host, unmap, rescan, detached remove, unzone.\n\nSee [mapping](https://DOCS.netapp.com/us-en/ontap/san-admin/map-lun.html/).\n")
w("dell/powerflex/kb-eui.html", "<html><head><title>PowerFlex EUI identifier</title><style>x{}</style></head><body>"
  "<nav>menu</nav><h2>Locate the EUI</h2><p>ESXi shows SDC volumes as eui.<b>id</b>; match the Volume ID "
  "from scli --query_all_volumes.</p><a href='https://docs.netapp.com/us-en/ontap/san-admin/map-lun.html?utm_source=x#steps'>LUN mapping</a>"
  "<a href='https://example.com/outside'>outside</a><a href='mailto:a@b.c'>m</a>"
  "<script>var a=1;</script></body></html>")
os.makedirs(os.path.join(docs, "dell", "powermax"), exist_ok=True)
shutil.copy(os.path.join(here, "tests", "sample.pdf"), os.path.join(docs, "dell", "powermax", "h8115.pdf"))
os.utime(os.path.join(docs, "dell", "powermax", "h8115.pdf"), (time.time() - 600 * 86400,) * 2)   # fetched 20 months ago: stale
json.dump({"h8115.pdf": {"url": "https://example.dell/h8115.pdf", "title": "VAAI with PowerMax"}},
          open(os.path.join(docs, "dell", "powermax", "manifest.json"), "w"))

# identical EMS page in two more ONTAP versions -> folded into one canonical copy (unversioned product wins)
w("netapp/ontap-ems-9161/callhome-hm-events.adoc", "= callhome.hm events\n\n== callhome.hm.alert.critical\n*Severity*:: ALERT\nSystem health monitor alert.\n")
w("netapp/ontap-ems-9181/callhome-hm-events.adoc", "= callhome.hm events\n\n== callhome.hm.alert.critical\n*Severity*:: ALERT\nSystem health monitor alert.\n")

w("netapp/ontap-ems/quokka.md", "# Quokka events\n\nThe quokkaword event fires on a shelf fault.\n")

import docs_index  # noqa: E402
r = docs_index.build(docs, db, log=lambda *_: None)
assert r["documents"] == 8 and r["errors"] == 0 and r["deduped"] == 2, r   # redirect stub skipped, 2 copies folded
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
    assert src["libraries"][0]["documents"] == 8 and src["libraries"][0]["library"] == "main", src
    # related_docs: the html page and the markdown runbook both cite the NetApp page (utm / fragment / case / slash normalized)
    rel_p = await call("related_docs", path="dell/powerflex/kb-eui.html")
    assert [d["path"] for d in rel_p["links_to"]] == ["netapp/ontap/san-admin/map-lun.adoc"] and rel_p["unresolved"] == 1, rel_p
    rel_u = await call("related_docs", url="https://docs.netapp.com/us-en/ontap/san-admin/map-lun.html")
    assert {d["path"] for d in rel_u["linked_from"]} == {"dell/powerflex/kb-eui.html", "runbooks/team/decom.md"}, rel_u
    assert rel_u["doc"]["path"] == "netapp/ontap/san-admin/map-lun.adoc" and not rel_u["links_to"], rel_u
    hit = (await call("search_docs", query="LUN igroup mapping"))["results"][0]["chunk_id"]
    assert await call("related_docs", chunk_id=hit) == rel_u
    assert src["libraries"][0]["by_vendor"]["netapp"].endswith("ontap 1") and len(json.dumps(src)) < 4000, src
    assert (await call("list_sources", vendor="runbooks"))["libraries"][0]["by_vendor"] == {"runbooks": "team 1"}
    s = await call("search_docs", query="lun mapping create igroup")
    top = s["results"][0]
    assert top["url"] == "https://docs.netapp.com/us-en/ontap/san-admin/map-lun.html" and top["vendor"] == "netapp", top
    assert "matched" not in top and "library" not in top and s.get("partial") is None, s   # lean reply: only partial hits say matched
    assert top["fetched"] == time.strftime("%Y-%m", time.gmtime()) and "stale" not in top and "note" not in top, top
    s = await call("search_docs", query="naa.600a0980 serial")
    assert s["results"] and s["results"][0]["section"] == "Find a LUN by NAA", s
    s = await call("search_docs", query="XCOPY transfer size", vendor="dell")
    assert s["results"][0]["title"] == "VAAI with PowerMax" and s["results"][0]["url"] == "https://example.dell/h8115.pdf"
    assert s["results"][0]["stale"] is True and s["results"][0]["fetched"] < time.strftime("%Y-%m", time.gmtime()), s["results"][0]
    s = await call("search_docs", query="query_all_volumes eui", product="powerflex")
    assert s["results"] and "var a" not in s["results"][0]["snippet"] and "menu" not in s["results"][0]["snippet"]
    s = await call("search_docs", query="callhome.hm.alert.critical", product="ontap-ems-9161")  # alias product filter
    assert s["results"] and s["results"][0]["product"] == "ontap-ems-9181" and \
        sorted(s["results"][0]["also_in"]) == ["netapp/ontap-ems-9161", "netapp/ontap-ems-9171"], s["results"][:1]
    assert s["results"][0]["note"] == "for ontap-ems-9181; yours: ontap-ems-9161", s["results"][0]   # environment.md version differs
    assert len([r for r in s["results"] if "callhome" in (r.get("path") or r.get("url") or "")]) == 1, "folded copies must not appear twice"
    s = await call("search_docs", query="quokkaword should")   # filler words are not required for "all words"
    assert s["results"] and "partial" not in s and "unmatched" not in s, s
    assert s["results"][0]["note"].startswith("unversioned copy") and "ontap-ems-9161" in s["results"][0]["note"], s["results"][0]
    rd = await call("read_document", path="netapp/ontap-ems-9161/callhome-hm-events.adoc")  # alias path -> canonical
    assert rd["path"] == "netapp/ontap-ems-9181/callhome-hm-events.adoc" and rd["sections"], rd
    s = await call("search_docs", query="callhome.hm.alarm")  # near miss -> partial match, still found
    assert s["partial"] is True and s["results"] and "query" not in s and "matched" in s["results"][0], s
    s = await call("search_docs", query="symmetrix XCOPY")          # synonym: VMAX / Symmetrix = PowerMax
    assert s["results"] and s["results"][0]["title"] == "VAAI with PowerMax", s
    s = await call("search_docs", query="detach unzone", vendor="runbooks")
    assert s["results"][0]["product"] == "team"
    s = await call("search_docs", query="lun mapping create igroup", read_top=1)      # read_top: text inline
    assert "lun mapping create" in s["results"][0]["text"] and "text" not in s["results"][1], s
    s = await call("search_docs", queries=["detach unzone", "vmkfstools"], vendor="runbooks")   # queries: merged
    assert s["results"][0]["product"] == "team" and [q["q"] for q in s["by_query"]] == ["detach unzone", "vmkfstools"], s
    e = await call("explain_code", code="callhome.hm.alert.critical")
    assert e["kind"] == "ontap-ems" and e["severity"] == "ALERT" and e["chunk_id"], e
    assert await call("explain_code", code="foo.bar.baz") == {"code": "foo.bar.baz", "documented": False}
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
    for bad in (-1, 10 ** 10 * 5):
        try:
            await call("read_chunk", chunk_id=bad)
            raise SystemExit("bad chunk id accepted")
        except Exception as e:
            assert "not found" in str(e), e
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
t, secs = docs_index.parse_md("# Features { #features }\n\nThe features text is long enough to stay alone.\n\n## Sub part { #sub-part }\n\nThe sub part text is long enough to stay alone as well.\n", "f")
assert t == "Features" and [h for h, _ in secs] == ["Features", "Sub part"], (t, secs)                  # mkdocs anchors dropped
print("mkdocs anchors OK")
for h in ("Affected Products", "Article Properties", "Table of Contents", "Contents"):      # boilerplate sections
    assert docs_index._NOISE_HEAD.match(h), h
assert not docs_index._NOISE_HEAD.match("Additional Information") and not docs_index._NOISE_HEAD.match("Resolution")
import search_cli
assert search_cli._norm_title("PowerFlex API 5.1.0: Map a volume") == search_cli._norm_title("PowerFlex API 4.5.5-Manager_v4-8-0: Map a volume")
print("boilerplate + version folding OK")
o = search_cli.for_agent({"results": [{"title": "Trident PVC stuck", "snippet": "«Trident» «PVC» stuck\n\nCheck the backend",
                                       "url": "https://x/y", "path": "netapp/kb/y.html", "score": 3.2}]})["results"][0]
assert "score" not in o and "path" not in o and o["snippet"] == "Check the backend", o       # lean answer for agents
assert "path" in search_cli.for_agent({"results": [{"title": "t", "snippet": "s", "url": None, "path": "p"}]})["results"][0]
t, ch = docs_index.parse_md("# T\n\nUse <dfn title='x'><strong>DI</strong></dfn>.\n\n```html\n<div>k</div>\n```\n", "f")
assert "Use DI." in ch[0][1] and "<div>k</div>" in ch[0][1], ch                               # inline HTML out, code kept
print("agent answer + inline html OK")
t, ch = docs_index.parse_md("# KB\n\nCookie Settings\n\nsearch\n\ncancel\n\n## Symptom\n\nThe host loses all paths to the datastore after a reboot.\n", "f")
assert all("Cookie Settings" not in b and b.strip() != "search" for _, b in ch) and len(ch) == 1, ch   # banner lines are noise
t, ch = docs_index.parse_md("# Model\n\nThe long description of the model goes on here for a while.\n\n## additionalInformation_text\n\nstring\n", "f")
assert len(ch) == 1 and "additionalInformation_text: string" in ch[0][1], ch                  # one-word field merged, not a chunk
print("junk chunks OK")
# --add (brain add-docs): the user's inbox goes INTO the library db; library documents are never removed or re-ranked
_lib, _inbox, _adb = (os.path.join(root, n) for n in ("addlib", "inbox", "add.db"))
for base, rel, text in ((_lib, "netapp/ontap/vol.md", "# Volumes\n\nvolume create makes a flexvol.\n"),
                        (_inbox, "netapp/ontap/vol.md", "# Volumes\n\nvolume create makes a flexvol.\n"),
                        (_inbox, "notes.md", "# Our naming\n\nZone names use host_array_fabric.\n")):
    os.makedirs(os.path.dirname(os.path.join(base, rel)), exist_ok=True)
    open(os.path.join(base, rel), "w").write(text)
docs_index.build(_lib, _adb, log=lambda *_: None)
r = docs_index.build(_inbox, _adb, log=lambda *_: None, prefix="inbox/")
rows = dict(((p, (v, pr, d)) for p, v, pr, d in sqlite3.connect(_adb).execute("SELECT path, vendor, product, dup_of FROM docs")))
assert r["added"] == 2 and rows["netapp/ontap/vol.md"][2] is None and rows["inbox/netapp/ontap/vol.md"][2] is not None, rows
assert rows["inbox/notes.md"][:2] == ("local", "inbox"), rows                    # loose file -> local/inbox
os.remove(os.path.join(_inbox, "notes.md"))
r = docs_index.build(_inbox, _adb, log=lambda *_: None, prefix="inbox/")
assert r["removed"] == 1 and r["documents"] == 2, r                             # only the inbox file left
print("add-docs (--add) OK")
