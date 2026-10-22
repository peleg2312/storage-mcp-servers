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

import docs_index  # noqa: E402
r = docs_index.build(docs, db, log=lambda *_: None)
assert r["documents"] == 5 and r["errors"] == 0, r   # redirect stub skipped
import server  # noqa: E402


async def main():
    async def call(n, **a):
        return (await server.mcp.call_tool(n, a)).structured_content

    src = await call("list_sources")
    assert src["totals"]["documents"] == 5, src
    s = await call("search_docs", query="lun mapping create igroup")
    top = s["results"][0]
    assert top["url"] == "https://docs.netapp.com/us-en/ontap/san-admin/map-lun.html" and top["vendor"] == "netapp", top
    s = await call("search_docs", query="naa.600a0980 serial")
    assert s["results"] and s["results"][0]["section"] == "Find a LUN by NAA", s
    s = await call("search_docs", query="XCOPY transfer size", vendor="dell")
    assert s["results"][0]["title"] == "VAAI with PowerMax" and s["results"][0]["url"] == "https://example.dell/h8115.pdf"
    s = await call("search_docs", query="query_all_volumes eui", product="powerflex")
    assert s["results"] and "var a" not in s["results"][0]["snippet"] and "menu" not in s["results"][0]["snippet"]
    s = await call("search_docs", query="callhome.hm.alarm")  # near miss -> any-word fallback
    assert s["match_mode"].startswith("any word") and s["results"]
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
    os.remove(os.path.join(docs, "netapp/ontap-ems-9171/callhome-hm-events.adoc"))
    w("runbooks/team/zoning.md", "# Zoning standard\n\nSingle initiator single target, device-alias naming site_host_hbaN.\n")
    r2 = docs_index.build(docs, db, log=lambda *_: None)
    assert (r2["added"], r2["updated"], r2["removed"]) == (1, 1, 1), r2
    s = await call("search_docs", query="vmkfstools queryrdm")
    assert s["results"] and s["results"][0]["title"] == "Datastore decommission v2"
    s = await call("search_docs", query="callhome", limit=5)
    assert not s["results"], s
    print("ALL TESTS PASSED", r, r2)


asyncio.run(main())
