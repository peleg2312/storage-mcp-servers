"""
VAST Data knowledge base (kb.vastdata.com: product documentation, knowledge base, API reference) into the library.
The site publishes an index of every article (llms.txt) and each article as Markdown (<url>.md), so no HTML
scraping: one small text file per article.

    python3 sync/sync_vast.py [--dest work/docs] [--delay 1] [--refresh]

Files land in <dest>/vast/<product>/<slug>.md with manifest.json (title + url) for the indexer:
    vast/docs     Product Documentation (VAST Cluster / AI OS: protocols, views, replication, hardware, CLI, release notes)
    vast/kb       Knowledge Base (support procedures, troubleshooting, health checks, hardware datasheets)
    vast/api-5-5  VAST 5.5 REST API reference
Incremental (already-saved articles are skipped), one request at a time, robots.txt allows everything.
Standard library only.
"""
import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

INDEX = "https://kb.vastdata.com/llms.txt"
UA = os.getenv("DOCS_SYNC_USER_AGENT", "docs-search-mcp/1.1 (internal documentation index)")
LINK = re.compile(r"^- \[([^\]]*)\]\((https://kb\.vastdata\.com/[^)\s]+\.md)\)", re.M)


def product_of(url):
    path = url.split("kb.vastdata.com/", 1)[1]
    if path.startswith("documentation/"):
        return "docs"
    if path.startswith("docs/"):
        return "kb"
    m = re.match(r"(api-[\w-]+)/", path)
    return m.group(1) if m else path.split("/")[0]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/markdown,text/plain,*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.getenv("DOCS_DIR", "/data/docs"))
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--refresh", action="store_true", help="re-download saved articles")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4, help="parallel fetches (the site answers in ~3 s each)")
    a = ap.parse_args()
    index = get(INDEX)
    items = [(t, u) for t, u in LINK.findall(index)]
    print(f"index: {len(items)} articles", flush=True)
    manifests = {}
    saved = skipped = failed = 0
    todo = []
    for title, url in items:
        product = product_of(url)
        d = os.path.join(a.dest, "vast", product)
        os.makedirs(d, exist_ok=True)
        if product not in manifests:
            mp = os.path.join(d, "manifest.json")
            manifests[product] = json.load(open(mp)) if os.path.exists(mp) else {}
        name = re.sub(r"[^\w.\-]+", "_", url.rsplit("/", 1)[1])
        path = os.path.join(d, name)
        if os.path.exists(path) and not a.refresh:
            if name not in manifests[product]:          # saved by a run that ended before writing its manifest
                m = re.search(r'^title:\s*"?(.*?)"?\s*$', open(path, encoding="utf-8").read(2000), re.M)
                manifests[product][name] = {"title": (m.group(1) if m else title).strip(), "url": url[:-3]}
            skipped += 1
            continue
        todo.append((title, url, product, name, path))
    if a.limit:
        todo = todo[:a.limit]

    def fetch(job):
        title, url, product, name, path = job
        try:
            body = get(url)
        except (urllib.error.URLError, OSError) as e:
            return job, None, str(e)
        finally:
            time.sleep(a.delay)
        # the site prepends a "fetch llms.txt" note to every article: keep the article only
        return job, re.sub(r"\n> ## Documentation Index\n(>.*\n)+", "\n", body, count=1), None

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        for job, body, err in pool.map(fetch, todo):
            title, url, product, name, path = job
            if body is None:
                failed += 1
                print(f"  fail {url}: {err}", flush=True)
                continue
            if re.search(r'^type: "index"', body[:600], re.M):     # a table of contents: its articles are fetched on their own
                skipped += 1
                continue
            m = re.search(r'^title:\s*"?(.*?)"?\s*$', body, re.M)
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            manifests[product][name] = {"title": (m.group(1) if m else title).strip(), "url": url[:-3]}
            saved += 1
            if saved % 100 == 0:
                for p, mf in manifests.items():
                    json.dump(mf, open(os.path.join(a.dest, "vast", p, "manifest.json"), "w"), indent=0)
                print(f"  saved={saved}/{len(todo)} skipped={skipped} failed={failed}", flush=True)
    for p, mf in manifests.items():
        json.dump(mf, open(os.path.join(a.dest, "vast", p, "manifest.json"), "w"), indent=0)
    print(f"done: saved={saved} skipped={skipped} failed={failed}")
    return 1 if failed and not saved else 0


if __name__ == "__main__":
    sys.exit(main())
