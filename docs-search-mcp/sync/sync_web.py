"""
Download individual web pages / PDFs you choose (NetApp KB articles, Dell KB articles, any vendor page)
into the library, for offline search.

    python sync/sync_web.py [--dest /data/docs] [--sources sources/web-pages.txt] [--delay 3]

sources/web-pages.txt, one per line:   <vendor> <product> <url>
    netapp  kb  https://kb.netapp.com/on-prem/ontap/...
    dell    kb  https://www.dell.com/support/kbdoc/en-us/000204833/...
Also accepts a plain list of URLs (vendor/product guessed from the host) with --urls file.

- One page per URL: no crawling. Respects robots.txt. One request at a time with a delay.
- Saves HTML (or the PDF) to <dest>/<vendor>/<product>/ plus manifest.json (title + url) for the indexer.
- Incremental: already-saved URLs are skipped (--refresh to re-download).
- Pages that need a login, or come back as an empty JavaScript shell, are reported, not saved: save
  those from your browser instead (Ctrl+S / Print to PDF) into extra/<vendor>/<product>/.
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
import urllib.parse
import urllib.request
import urllib.robotparser

UA = os.getenv("DOCS_SYNC_USER_AGENT", "docs-search-mcp/1.1 (internal documentation index)")
LOGIN_HINTS = re.compile(r"(sign in to view|please log ?in|login required|you must be logged in|"
                         r"access denied|<title>[^<]*(sign in|log ?in)[^<]*</title>)", re.I)
GUESS = [("netapp.com", "netapp", "kb"), ("dell.com", "dell", "kb"), ("delltechnologies.com", "dell", "kb"),
         ("broadcom.com", "vmware", "kb"), ("vmware.com", "vmware", "kb"), ("cisco.com", "cisco", "kb"),
         ("redhat.com", "redhat", "kb")]
_robots = {}


def robots_ok(url):
    p = urllib.parse.urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except Exception:
            rp = None                      # no robots.txt reachable: allowed
        _robots[base] = rp
    rp = _robots[base]
    return rp is None or rp.can_fetch(UA, url)


DELL_COOKIE = os.getenv("DELL_KB_COOKIE", "")    # optional: your logged-in dell.com/support browser session


def fetch(url):
    hdrs = {"User-Agent": UA, "Accept": "text/html,application/pdf,*/*"}
    if DELL_COOKIE and urllib.parse.urlparse(url).netloc.endswith("dell.com"):
        hdrs["Cookie"] = DELL_COOKIE
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(), r.headers.get("Content-Type", ""), r.geturl()


def file_name(url, is_pdf):
    p = urllib.parse.urlparse(url)
    m = re.search(r"\b(\d{6,9})\b", p.path)          # KB number if any
    stem = re.sub(r"[^\w.\-]+", "_", urllib.parse.unquote(os.path.basename(p.path.rstrip("/"))))[:100] or "page"
    stem = os.path.splitext(stem)[0]
    if m and m.group(1) not in stem:
        stem = f"{m.group(1)}_{stem}"
    h = hashlib.sha1(url.encode()).hexdigest()[:8]
    return f"{stem}_{h}.{'pdf' if is_pdf else 'html'}"


def title_of(body):
    m = re.search(rb"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    t = html.unescape(m.group(1).decode("utf-8", "replace")) if m else ""
    return re.sub(r"\s+", " ", t).strip()


def text_len(body):
    b = re.sub(rb"(?is)<(script|style|noscript)[^>]*>.*?</\1>", b" ", body)
    return len(re.sub(rb"\s+", b" ", re.sub(rb"<[^>]+>", b" ", b)).strip())


def load(args):
    rows = []
    if args.urls:
        for line in open(args.urls, encoding="utf-8"):
            u = line.strip()
            if u.startswith("http"):
                host = urllib.parse.urlparse(u).netloc.lower()
                v, p = next(((v, p) for h, v, p in GUESS if host.endswith(h)), ("web", "pages"))
                rows.append((v, p, u))
    if os.path.exists(args.sources):
        for line in open(args.sources, encoding="utf-8"):
            line = line.split(" #", 1)[0].strip()
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 3:
                    rows.append((parts[0].lower(), parts[1], parts[2]))
    return rows


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.getenv("DOCS_DIR", "/data/docs"))
    ap.add_argument("--sources", default=os.path.join(here, "sources", "web-pages.txt"))
    ap.add_argument("--urls", help="file with one URL per line (vendor/product guessed from the host)")
    ap.add_argument("--delay", type=float, default=float(os.getenv("DOCS_SYNC_DELAY", "3")))
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    rows = load(a)
    stats = {"saved": 0, "skipped": 0, "login_or_empty": 0, "robots": 0, "failed": 0}
    manifests = {}
    for vendor, product, url in rows:
        d = os.path.join(a.dest, vendor, product)
        os.makedirs(d, exist_ok=True)
        mf = os.path.join(d, "manifest.json")
        man = manifests.setdefault(mf, json.load(open(mf)) if os.path.exists(mf) else {})
        if not a.refresh and any(v.get("url") == url for v in man.values()):
            stats["skipped"] += 1
            continue
        if not robots_ok(url):
            stats["robots"] += 1
            print(f"robots.txt disallows, not fetched: {url}")
            continue
        try:
            body, ctype, final = fetch(url)
        except (urllib.error.URLError, OSError) as e:
            stats["failed"] += 1
            print(f"failed: {url}: {e}")
            continue
        finally:
            time.sleep(a.delay)
        is_pdf = body[:5] == b"%PDF-" or "pdf" in ctype.lower()
        if not is_pdf and (LOGIN_HINTS.search(body[:200000].decode("utf-8", "replace")) or text_len(body) < 500):
            stats["login_or_empty"] += 1
            print(f"needs login or is a JavaScript-only page, save it from the browser instead: {url}")
            continue
        name = file_name(url, is_pdf)
        with open(os.path.join(d, name), "wb") as f:
            f.write(body)
        man[name] = {"url": url, "title": title_of(body) if not is_pdf else name}
        stats["saved"] += 1
        print(f"saved {vendor}/{product}/{name}")
    for mf, man in manifests.items():
        json.dump(man, open(mf, "w"), indent=1)
    print("web pages:", json.dumps(stats))
    return 1 if stats["failed"] and not stats["saved"] else 0


if __name__ == "__main__":
    sys.exit(main())
