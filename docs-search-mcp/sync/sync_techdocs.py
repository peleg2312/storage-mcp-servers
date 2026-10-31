"""
VMware product documentation from techdocs.broadcom.com (vSphere Storage and other guides) into the library,
one topic per HTML file with only the topic's content (the site's navigation, feedback forms and footer removed).

    python3 sync/sync_techdocs.py [--dest work/docs] [--sources sources/techdocs-sections.txt] [--delay 10]

sources/techdocs-sections.txt, one per line:  <product-folder> <url prefix of the guide>
    vsphere-8  https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere/8-0/vsphere-storage/
Every page of the site's sitemap under that prefix is fetched. Files land in <dest>/vmware/<product-folder>/
with manifest.json (title + url). Incremental; the site's robots.txt asks for a 10 s crawl delay (the default).
Standard library only.
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SITE = "https://techdocs.broadcom.com"
UA = os.getenv("DOCS_SYNC_USER_AGENT", "docs-search-mcp/1.1 (internal documentation index)")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xml,*/*"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def sitemap_urls(cache, delay, prefixes):
    """The site's sitemap (800,000 pages) filtered to the chosen guides; cached a week next to the sources."""
    # the cache holds only the pages of the guides it was built for: a new line in the sections file rebuilds it
    key = "# prefixes " + " ".join(sorted(prefixes))
    if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 7 * 86400:
        lines = open(cache, encoding="utf-8").read().split("\n")
        if lines and lines[0] == key:
            return lines[1:]
    urls = [key]
    for index in ("/sitemap.xml", "/techdocs2-sitemap.xml"):
        subs = re.findall(r"<loc>([^<]+)</loc>", get(SITE + index))
        for s in subs:
            urls += [u for u in re.findall(r"<loc>([^<]+)</loc>", get(s)) if u.startswith(prefixes)]
            time.sleep(delay)
    open(cache, "w", encoding="utf-8").write("\n".join(urls))
    return urls[1:]


def topic_html(page):
    """The topic's own content: from the main content block to the previous/next navigation."""
    start = page.find('<div class="main-content"')
    if start < 0:
        return None
    end = min([i for i in (page.find('<div class="cmp-previous-next-navigation"', start),
                           page.find('<div class="cmp-feedback"', start), page.find("<footer", start)) if i > 0] or [len(page)])
    body = page[start:end]
    body = re.sub(r"(?is)<(script|style|form|button)[^>]*>.*?</\1>", " ", body)
    body = re.sub(r"(?is)<div class=\"linklist relatedlinks\".*", "", body)
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.getenv("DOCS_DIR", "/data/docs"))
    ap.add_argument("--sources", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources", "techdocs-sections.txt"))
    ap.add_argument("--delay", type=float, default=10.0, help="seconds between requests (robots.txt: 10)")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    sections = []
    for line in open(a.sources, encoding="utf-8"):
        line = line.split(" #", 1)[0].strip()
        if line and not line.startswith("#"):
            folder, prefix = line.split()[:2]
            sections.append((folder, prefix))
    os.makedirs(os.path.join(a.dest, "vmware"), exist_ok=True)
    urls = sitemap_urls(a.sources + ".sitemap-cache", min(a.delay, 2), tuple(p for _, p in sections))
    todo = [(folder, u) for folder, prefix in sections for u in urls if u.startswith(prefix)]
    print(f"sitemap: {len(todo)} pages in the chosen guides", flush=True)
    manifests = {}
    saved = skipped = failed = 0
    for folder, url in todo:
        if a.limit and saved >= a.limit:
            break
        d = os.path.join(a.dest, "vmware", folder)
        os.makedirs(d, exist_ok=True)
        if folder not in manifests:
            mp = os.path.join(d, "manifest.json")
            manifests[folder] = json.load(open(mp)) if os.path.exists(mp) else {}
        stem = re.sub(r"[^\w.\-]+", "_", url.rsplit("/", 1)[1].replace(".html", ""))[:90]
        name = f"{stem}_{hashlib.sha1(url.encode()).hexdigest()[:8]}.html"
        path = os.path.join(d, name)
        if os.path.exists(path):
            skipped += 1
            continue
        try:
            page = get(url)
        except (urllib.error.URLError, OSError) as e:
            failed += 1
            print(f"  fail {url}: {e}", flush=True)
            time.sleep(a.delay)
            continue
        body = topic_html(page)
        m = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
        title = re.sub(r"\s+", " ", html.unescape(m.group(1))).strip() if m else stem
        if not body:
            failed += 1
            print(f"  no content {url}", flush=True)
            time.sleep(a.delay)
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"<html><head><title>{html.escape(title)}</title></head><body>{body}</body></html>")
        manifests[folder][name] = {"title": title, "url": url}
        saved += 1
        if saved % 50 == 0:
            json.dump(manifests[folder], open(os.path.join(d, "manifest.json"), "w"), indent=0)
            print(f"  saved={saved} skipped={skipped} failed={failed} ({folder})", flush=True)
        time.sleep(a.delay)
    for folder, mf in manifests.items():
        json.dump(mf, open(os.path.join(a.dest, "vmware", folder, "manifest.json"), "w"), indent=0)
    print(f"done: saved={saved} skipped={skipped} failed={failed}")
    return 1 if failed and not saved else 0


if __name__ == "__main__":
    sys.exit(main())
