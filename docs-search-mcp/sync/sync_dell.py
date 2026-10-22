"""
Download Dell PowerMax / PowerFlex public documentation listed in sources/dell-sources.txt.

    python sync/sync_dell.py [--dest /data/docs/dell] [--sources sources/dell-sources.txt]
                             [--delay 2] [--max-per-hub 400] [--dry-run]

- 'hub' pages are fetched once and every linked PDF (dl.dell.com/content/docu*|manual*,
  dell.com/.../collaterals/unauth/*.pdf, dell.com/content/dam/*.pdf, delltechnologies.com/asset/*.pdf)
  is downloaded. Only one level deep - no crawling beyond the hub.
- Already-downloaded files are skipped (re-run = incremental).
- Polite: one request at a time, a delay between requests, an honest User-Agent.
- Writes manifest.json (file -> title, source url, hub) used by the indexer for titles and links.
Run it from a network that can reach dell.com (your cluster / workstation). Standard library only.
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

UA = os.getenv("DOCS_SYNC_USER_AGENT", "docs-search-mcp/1.0 (internal documentation index)")
PDF_LINK = re.compile(
    r'href="([^"]+?\.pdf(?:\?[^"]*)?)"[^>]*>(.*?)</a>', re.I | re.S)
ALLOWED = re.compile(r"^https://(dl\.dell\.com/content/|www\.dell\.com/[^\s]*?(collaterals/unauth|content/dam)/|"
                     r"(www\.)?delltechnologies\.com/asset/)", re.I)


DELL_COOKIE = os.getenv("DELL_KB_COOKIE", "")    # optional: your logged-in www.dell.com/support browser session
DL_COOKIE = os.getenv("DELL_DL_COOKIE", DELL_COOKIE)   # optional: the session for dl.dell.com downloads (login-only manuals)


def fetch(url, timeout=120):
    hdrs = {"User-Agent": UA, "Accept": "*/*"}
    host = urllib.parse.urlparse(url).netloc
    if host == "dl.dell.com" and DL_COOKIE:
        hdrs["Cookie"] = DL_COOKIE
    elif DELL_COOKIE and host.endswith("dell.com"):
        hdrs["Cookie"] = DELL_COOKIE
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def safe_name(url, title=None):
    path = urllib.parse.urlparse(url).path
    base = os.path.basename(path) or "index"
    base = re.sub(r"[^\w.\-]+", "_", urllib.parse.unquote(base))[:150]
    if not os.path.splitext(base)[1]:
        base += ".html"
    if base in ("index.html", "default.html") or len(base) < 6:
        base = hashlib.sha1(url.encode()).hexdigest()[:12] + "_" + base
    return base


def page_title(body):
    m = re.search(rb"<title[^>]*>(.*?)</title>", body[:200000], re.I | re.S)
    return clean_title(m.group(1).decode("utf-8", "replace"))[:80] if m else ""


def pdf_link_in_html(body, base):
    """A PDF link inside an HTML answer: meta refresh, location=..., or the first allowed *.pdf href."""
    text = body[:400000].decode("utf-8", "replace")
    for pat in (r'http-equiv="refresh"[^>]*url=([^"\'>\s]+)', r'location(?:\.href)?\s*=\s*["\']([^"\']+\.pdf[^"\']*)',
                r'href="([^"]+\.pdf(?:\?[^"]*)?)"', r'(https://dl\.dell\.com/content/[^"\'\s<>]+)'):
        for m in re.finditer(pat, text, re.I):
            full = urllib.parse.urljoin(base, html.unescape(m.group(1)))
            if full != base and ALLOWED.match(full):
                return full
    return None


def clean_title(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def load_sources(path):
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip() if not line.lstrip().startswith("#") else ""
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3 or parts[0] not in ("hub", "pdf", "page"):
            print(f"ignoring malformed line: {line}", file=sys.stderr)
            continue
        out.append(tuple(parts))
    return out


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.path.join(os.getenv("DOCS_DIR", "/data/docs"), "dell"))
    ap.add_argument("--sources", default=os.path.join(here, "sources", "dell-sources.txt"))
    ap.add_argument("--delay", type=float, default=float(os.getenv("DOCS_SYNC_DELAY", "2")))
    ap.add_argument("--max-per-hub", type=int, default=400)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    jobs = []  # (product, url, title, hub)
    for kind, product, url in load_sources(a.sources):
        if kind == "hub":
            try:
                body, _ = fetch(url)
                time.sleep(a.delay)
            except Exception as e:
                print(f"hub failed {url}: {e}", file=sys.stderr)
                continue
            text = body.decode("utf-8", "replace")
            found = 0
            for href, label in PDF_LINK.findall(text):
                href = html.unescape(href)
                full = urllib.parse.urljoin(url, href)
                if not ALLOWED.match(full):
                    continue
                jobs.append((product, full, clean_title(label), url))
                found += 1
                if found >= a.max_per_hub:
                    break
            print(f"hub {url}: {found} documents")
        else:
            jobs.append((product, url, None, None))

    seen, done, skipped, failed = set(), 0, 0, 0
    manifests = {}
    for product, url, title, hub in jobs:
        key = urllib.parse.urlsplit(url)._replace(query="").geturl()
        if key in seen:
            continue
        seen.add(key)
        d = os.path.join(a.dest, product)
        os.makedirs(d, exist_ok=True)
        if d not in manifests:
            mpath = os.path.join(d, "manifest.json")
            manifests[d] = json.load(open(mpath)) if os.path.exists(mpath) else {}
        name = safe_name(url)
        target = os.path.join(d, name)
        if os.path.exists(target) and os.path.getsize(target) > 0:
            skipped += 1
            manifests[d].setdefault(name, {"url": url, "title": title, "hub": hub})
            continue
        if a.dry_run:
            print(f"would download {url} -> {target}")
            continue
        try:
            body, ctype = fetch(url)
        except (urllib.error.URLError, OSError) as e:
            failed += 1
            print(f"failed {url}: {e}", file=sys.stderr)
            time.sleep(a.delay)
            continue
        if name.endswith(".pdf") and not body.startswith(b"%PDF"):
            # dell.com often answers a .pdf link with an HTML page that carries the real file link
            # (meta refresh / JavaScript redirect / download button): follow it once.
            inner = pdf_link_in_html(body, url)
            if inner:
                try:
                    time.sleep(a.delay)
                    body, ctype = fetch(inner)
                except (urllib.error.URLError, OSError) as e:
                    body = b""
                    print(f"follow-up failed {inner}: {e}", file=sys.stderr)
            if not body.startswith(b"%PDF"):
                failed += 1
                print(f"not a PDF ({page_title(body) or 'no title'}): {url}", file=sys.stderr)
                time.sleep(a.delay)
                continue
        if name.endswith(".pdf") and b"modern slavery" in body[:400000].lower():
            failed += 1
            print(f"not the document (download redirected to Dell's legal statement): {url}", file=sys.stderr)
            time.sleep(a.delay)
            continue
        with open(target + ".part", "wb") as f:
            f.write(body)
        os.replace(target + ".part", target)
        manifests[d][name] = {"url": url, "title": title or None, "hub": hub}
        done += 1
        print(f"ok {product}/{name} ({len(body) // 1024} KB)")
        time.sleep(a.delay)
    for d, m in manifests.items():
        json.dump(m, open(os.path.join(d, "manifest.json"), "w"), indent=1)
    print(f"Dell: {done} downloaded, {skipped} already present, {failed} failed -> {a.dest}")


if __name__ == "__main__":
    main()
