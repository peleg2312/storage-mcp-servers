#!/usr/bin/env python3
"""Copy hand-downloaded documents from extra/<vendor>/<product>/ into the synced tree (work/docs) with
manifest entries, so the indexer and the library pack pick them up.

    python3 sync/import_extra.py --dest work/docs

extra/dell/NEEDED.md lists the Dell documents that only a signed-in browser can download, with the file
name to save them under; the source link in that table becomes the document's URL in search results.
Files not in the table are imported too (title from the file name, no URL). Redirect-page PDFs (Dell's
"Statement against modern slavery") are skipped."""
import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_dell import is_redirect_pdf  # noqa: E402

here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def links(table_md):
    out = {}
    if os.path.isfile(table_md):
        for m in re.finditer(r"^\| `([^`]+)` \| (\S+) \|", open(table_md, encoding="utf-8").read(), re.M):
            out[m.group(1)] = m.group(2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.getenv("DOCS_DIR", os.path.join(here, "work", "docs")))
    ap.add_argument("--extra", default=os.path.join(here, "extra"))
    a = ap.parse_args()
    n = skipped = 0
    for vendor in sorted(os.listdir(a.extra)) if os.path.isdir(a.extra) else []:
        vdir = os.path.join(a.extra, vendor)
        if not os.path.isdir(vdir):
            continue
        urls = links(os.path.join(vdir, "NEEDED.md"))
        for product in sorted(os.listdir(vdir)):
            pdir = os.path.join(vdir, product)
            if not os.path.isdir(pdir):
                continue
            dest = os.path.join(a.dest, vendor, product)
            os.makedirs(dest, exist_ok=True)
            man_f = os.path.join(dest, "manifest.json")
            man = json.load(open(man_f)) if os.path.exists(man_f) else {}
            for f in sorted(os.listdir(pdir)):
                src = os.path.join(pdir, f)
                if not os.path.isfile(src) or f.startswith("."):
                    continue
                body = open(src, "rb").read()
                if f.lower().endswith(".pdf") and is_redirect_pdf(body):
                    print(f"skipped (Dell redirect page, sign in and download again): {vendor}/{product}/{f}")
                    skipped += 1
                    continue
                target = os.path.join(dest, f)
                if os.path.exists(target) and open(target, "rb").read() == body:
                    continue
                shutil.copy(src, target)
                title = re.sub(r"^(manual|docu)\d+-?", "", os.path.splitext(f)[0]).replace("-", " ").replace("_", " ").strip()
                man.setdefault(f, {})
                man[f].update({"url": urls.get(f) or man[f].get("url"), "title": man[f].get("title") or title or None,
                               "hub": "extra"})
                n += 1
            json.dump(man, open(man_f, "w"), indent=1)
    print(f"extra: {n} documents imported into {a.dest}, {skipped} skipped")


if __name__ == "__main__":
    main()
