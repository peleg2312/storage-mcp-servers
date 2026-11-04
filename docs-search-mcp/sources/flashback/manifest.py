"""MANIFEST.md of a built library: documents and sources per vendor / product.   python3 manifest.py <work dir>"""
import json
import os
import sys
import time

work = sys.argv[1]
docs = os.path.join(work, "docs")
print(f"# Flashback library ({time.strftime('%Y-%m-%d')})\n")
print("Search it with the docs MCP (`docs-local`) or `search.py --db <library>/docs.db`. Vendor / product names below are the")
print("`vendor` and `product` filters.\n")
print("| vendor | product | documents | source |\n|---|---|---|---|")
for v in sorted(os.listdir(docs)):
    for p in sorted(os.listdir(os.path.join(docs, v))):
        d = os.path.join(docs, v, p)
        if not os.path.isdir(d):
            continue
        n = sum(1 for dp, dn, fn in os.walk(d) if "/.git" not in dp
                for f in fn if not f.startswith(".") and f != "manifest.json")
        src = ""
        if os.path.isfile(os.path.join(d, ".source_url")):
            src = open(os.path.join(d, ".source_url")).read().strip()
        elif os.path.isfile(os.path.join(d, "manifest.json")):
            urls = [m.get("url", "") for m in json.load(open(os.path.join(d, "manifest.json"))).values()]
            src = os.path.commonprefix(urls).rsplit("/", 1)[0] + "/" if urls else ""
        print(f"| {v} | {p} | {n} | {src} |")
