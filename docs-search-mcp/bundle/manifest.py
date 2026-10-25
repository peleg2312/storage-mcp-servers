#!/usr/bin/env python3
"""Write MANIFEST.md for a library: what is inside (per vendor/product: documents, sections, source).
    python3 bundle/manifest.py --db work/index/docs.db --docs work/docs --label 2026.10.22 > MANIFEST.md
"""
import argparse
import json
import os
import sqlite3

NOTES = {
    "netapp": "docs.netapp.com is generated from these NetAppDocs repositories: the git sync IS the NetApp documentation site.",
    "dell": "csm = dell.github.io/csm-docs (all versions under content/); powermax / powerflex = PDFs from dell.com hubs; the rest = Dell GitHub repos.",
    "kb": "curated KB pointers (sources/kb/kb-pointers.md).",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--docs", required=True)
    ap.add_argument("--label", required=True)
    a = ap.parse_args()
    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    rows = c.execute("SELECT vendor, product, count(*), sum(chunks), sum(size) FROM docs "
                     "GROUP BY vendor, product ORDER BY vendor, product").fetchall()
    meta = dict(c.execute("SELECT key, value FROM meta").fetchall())
    tot_d = sum(r[2] for r in rows)
    tot_s = sum(r[3] or 0 for r in rows)
    folded = c.execute("SELECT count(*) FROM docs WHERE dup_of IS NOT NULL").fetchone()[0]
    print(f"# Documentation library {a.label}\n")
    print(f"Indexed {meta.get('indexed_at')}: **{tot_d - folded} unique documents, {tot_s} sections** "
          f"({tot_d} files: {folded} are identical copies, e.g. the same page in several ONTAP versions, "
          "kept as aliases of one indexed copy and shown as `also_in`). "
          "Search it with `python3 search.py search \"...\"` (no dependencies) or the docs-search MCP server.\n")
    print("Document counts below are files per product; an identical copy counts in every product it appears in.\n")
    print("| Vendor | Product | Documents | Sections | Source |")
    print("|---|---|---:|---:|---|")
    for vendor, product, nd, ns, _ in rows:
        src = ""
        f = os.path.join(a.docs, vendor, product, ".source_url")
        if os.path.isfile(f):
            src = open(f).read().strip()
        else:
            mf = os.path.join(a.docs, vendor, product, "manifest.json")
            if os.path.isfile(mf):
                try:
                    hubs = {v.get("hub") for v in json.load(open(mf)).values() if v.get("hub")}
                    src = ", ".join(sorted(hubs)) or "individual URLs (manifest.json)"
                except Exception:
                    src = "manifest.json"
        print(f"| {vendor} | {product} | {nd} | {ns or 0} | {src} |")
    print()
    for v, n in NOTES.items():
        if any(r[0] == v for r in rows):
            print(f"- **{v}**: {n}")


if __name__ == "__main__":
    main()
