#!/usr/bin/env python3
"""
Export the public NetApp Knowledge Base (kb.netapp.com) for offline search.

    python3 sync/sync_netapp_kb.py [--dest /data/docs] [--include on-prem/ontap ...] [--delay 5]
                                   [--max 0] [--list] [--since 2020]

- Article list: the site's own sitemap (https://kb.netapp.com/sitemap.xml, ~49,000 public articles).
- Only the chosen categories (--include, sitemap path prefixes), newest articles first, so a run that
  is stopped early still holds the most recent KBs. Default order: ONTAP SAN, host utilities, performance,
  data protection, hardware, MetroCluster, Trident, ONTAP tools for VMware, switches, then the rest of
  ONTAP (OS, data management, NAS...), ASA r2, FlexPod, SnapCenter, AIQUM.
- Polite and legal: kb.netapp.com/robots.txt asks for one request per 5 s (Crawl-delay 5,
  Request-rate 1/5); that is the default --delay. One article per request, no API, no login.
  429 / 503 answers back off for a minute.
- Articles whose Cause / Solution is behind the NetApp Support login keep their public part
  (Applies to, Issue / Description) and are marked "Partial article" (manifest: partial=true).
  With NETAPP_KB_COOKIE set to your own logged-in kb.netapp.com browser session (the Cookie header
  value, copied from the browser's developer tools), the full articles your account can read are
  saved instead, and previously partial articles are re-fetched (--refresh-partial).
- Saves only the article body (the "mt-content-container" section: Applies to, Issue, Cause,
  Solution / Procedure, Additional information), as a small clean HTML file:
      <dest>/netapp/kb-<area>/<article>_<hash>.html   + manifest.json (title, url, lastmod)
  so the indexer links every hit back to the kb.netapp.com URL.
- Incremental and resumable: already-saved articles are skipped unless the sitemap's lastmod changed;
  the manifest is written every 10 articles, so the run can be killed and restarted at any time.
Standard library only.
"""

import argparse
import hashlib
import html
import json
import os
import re
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = os.getenv("DOCS_SYNC_USER_AGENT", "docs-search-mcp/1.1 (internal documentation index)")
SITEMAP = "https://kb.netapp.com/sitemap.xml"
# sitemap path prefix -> product folder (order = priority)
DEFAULT_AREAS = [
    ("on-prem/ontap/da/SAN/", "kb-ontap"),            # SAN: FC / iSCSI / NVMe, LUNs, igroups, multipath
    ("on-prem/ontap/da/Host-Utilities/", "kb-ontap"),
    ("on-prem/ontap/Perf/", "kb-ontap"),
    ("on-prem/ontap/DP/", "kb-ontap"),                # SnapMirror, snapshots, NDMP
    ("on-prem/ontap/OHW/", "kb-ontap"),               # hardware, disks, shelves, adapters, ports
    ("on-prem/ontap/mc/", "kb-ontap"),                # MetroCluster
    ("Cloud/Astra/NetApp_Trident/", "kb-trident"),
    ("data-mgmt/OTV/", "kb-ontap-tools-vmware"),
    ("on-prem/Switches/", "kb-switches"),             # Cisco / Brocade / NetApp cluster switches
    ("on-prem/ontap/Ontap_OS/", "kb-ontap"),          # OS, filesystem, RAID, networking issues
    ("on-prem/ontap/DM/", "kb-ontap"),                # volumes, aggregates, efficiency
    ("on-prem/ontap/Upgrade/", "kb-ontap"),
    ("on-prem/ontap/Mediator/", "kb-ontap"),
    ("on-prem/ASAr2/", "kb-asar2"),
    ("on-prem/ontap/da/", "kb-ontap"),                # NAS, S3, XCP
    ("on-prem/ontap/", "kb-ontap"),                   # anything else under ONTAP
    ("hybrid/FlexPod/", "kb-flexpod"),
    ("data-mgmt/SnapCenter/", "kb-snapcenter"),
    ("data-mgmt/AIQUM/", "kb-aiqum"),
    ("Legacy/ONTAP/", "kb-ontap"),
    ("Cloud/Astra/", "kb-astra"),
]


COOKIE = os.getenv("NETAPP_KB_COOKIE", "")   # optional: your kb.netapp.com browser session (see README)


def fetch(url, timeout=90):
    hdrs = {"User-Agent": UA, "Accept": "text/html,application/xml,*/*"}
    if COOKIE and "kb.netapp.com" in url:
        hdrs["Cookie"] = COOKIE
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers


def load_sitemap(cache):
    if cache and os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 86400:
        data = open(cache, "rb").read()
    else:
        data, _ = fetch(SITEMAP, 300)
        if cache:
            open(cache, "wb").write(data)
    text = data.decode("utf-8", "replace")
    out = []
    for m in re.finditer(r"<url>(.*?)</url>", text, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", m.group(1))
        mod = re.search(r"<lastmod>(.*?)</lastmod>", m.group(1))
        if loc:
            out.append((html.unescape(loc.group(1).strip()), mod.group(1).strip() if mod else ""))
    return out


def area_of(url, areas):
    path = urllib.parse.urlparse(url).path.lstrip("/")
    for i, (prefix, folder) in enumerate(areas):
        if path.startswith(prefix):
            return i, folder
    return None, None


def clean_body(section):
    s = re.sub(r"(?is)<(script|style|noscript|iframe|svg)[^>]*>.*?</\1>", " ", section)
    s = re.sub(r'(?i)\s(style|class|id|data-[\w-]+|mt-[\w-]+|rel|target|aria-[\w-]+|role|title)="[^"]*"', "", s)
    s = re.sub(r"(?i)<img[^>]*>", "", s)
    s = re.sub(r"(?i)<(/?)h4\b", r"<\1h2", s)             # Applies to / Issue / Cause / Solution -> sections
    s = re.sub(r"(?i)<(/?)h5\b", r"<\1h3", s)
    s = re.sub(r"(?i)<span>\s*</span>", "", s)
    s = re.sub(r"\n[ \t]+\n", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def extract(body, url):
    text = body.decode("utf-8", "replace")
    t = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    title = re.sub(r"\s+", " ", html.unescape(t.group(1))).strip() if t else ""
    title = re.sub(r"\s*-\s*NetApp Knowledge Base\s*$", "", title)
    start = text.find('<section class="mt-content-container">')
    if start < 0:
        return title, None, False
    end = text.find('<footer class="elm-content-footer">', start)
    if end < 0:
        end = text.find("</section>", start)
    section = text[start:end]
    # Many articles show "Applies to" + "Issue" publicly and gate Cause / Solution behind a NetApp
    # Support login: keep the public part, cut the sign-in box, and mark the article as partial.
    k = section.find("Sign in to view")
    partial = k >= 0
    if partial:
        cut = section.rfind("<div", 0, k)
        section = section[:cut if cut > 0 else k]
    d = section.find("NetApp provides no representations")          # legal boilerplate on every page
    if d >= 0:
        cut = section.rfind("<p", 0, d)
        section = section[:cut if cut > 0 else d]
    content = clean_body(section)
    if len(re.sub(r"<[^>]+>", "", content).strip()) < 25:
        return title, None, partial
    note = ('<p><strong>Partial article: the Cause / Solution section requires a NetApp Support login '
            '(open the source URL with your account).</strong></p>\n') if partial else ""
    page = (f'<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f'<link rel="canonical" href="{html.escape(url)}"></head>\n<body>\n<h1>{html.escape(title)}</h1>\n'
            f'<p>Source: <a href="{html.escape(url)}">{html.escape(url)}</a></p>\n{note}{content}\n</body></html>\n')
    return title, page, partial


def file_name(url):
    p = urllib.parse.urlparse(url).path
    stem = re.sub(r"[^\w.\-]+", "_", urllib.parse.unquote(os.path.basename(p.rstrip("/"))))[:120] or "page"
    return f"{stem}_{hashlib.sha1(url.encode()).hexdigest()[:8]}.html"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", default=os.getenv("DOCS_DIR", "/data/docs"))
    ap.add_argument("--include", nargs="*", help="sitemap path prefixes to export (default: ONTAP, Trident, OTV, ...)")
    ap.add_argument("--delay", type=float, default=float(os.getenv("DOCS_SYNC_DELAY", "5")))
    ap.add_argument("--max", type=int, default=0, help="stop after N new/updated articles (0 = all)")
    ap.add_argument("--since", default="", help="only articles with sitemap lastmod >= YYYY[-MM]")
    ap.add_argument("--list", action="store_true", help="only print what would be fetched")
    ap.add_argument("--refresh-partial", action="store_true",
                    help="re-fetch articles saved as partial (use with NETAPP_KB_COOKIE)")
    a = ap.parse_args()
    def folder_for(prefix):
        """--include prefixes use the same product folders as DEFAULT_AREAS (longest matching prefix)."""
        best = max((d for d in DEFAULT_AREAS if prefix.startswith(d[0]) or d[0].startswith(prefix)),
                   key=lambda d: len(d[0]), default=None)
        return best[1] if best else "kb-" + re.sub(r"[^\w]+", "-", prefix.rstrip("/").split("/")[-1]).lower()
    areas = [(p if p.endswith("/") else p + "/", folder_for(p if p.endswith("/") else p + "/"))
             for p in a.include] if a.include else DEFAULT_AREAS

    os.makedirs(a.dest, exist_ok=True)
    cache = os.path.join(a.dest, ".netapp-kb-sitemap.xml")
    try:
        entries = load_sitemap(cache)
    except Exception as e:
        sys.exit(f"cannot read the sitemap {SITEMAP}: {e}")
    todo = []
    for url, mod in entries:
        pri, folder = area_of(url, areas)
        if folder is None or (a.since and mod < a.since):
            continue
        if url.rstrip("/").endswith("KBs"):          # category pages (SAN-KBs, Perf-KBs): lists of titles
            continue
        todo.append((pri, mod, url, folder))
    todo.sort(key=lambda t: (t[0], t[1]), reverse=False)
    # priority ascending, but newest first inside each area
    todo.sort(key=lambda t: (t[0], "" if not t[1] else "".join(chr(255 - ord(c)) for c in t[1])))
    print(f"sitemap: {len(entries)} public articles, {len(todo)} in the chosen areas", flush=True)
    if COOKIE:
        try:
            body, _ = fetch("https://kb.netapp.com/")
            who = re.search(rb'"(?:username|name)"\s*:\s*"([^"]+)"', body)
            logged = b"Special:UserLogin" not in body and b"mt-user-login" not in body
            print(f"NETAPP_KB_COOKIE set: session {'accepted' if logged else 'NOT accepted (still anonymous: copy a fresh cookie)'}"
                  + (f" ({who.group(1).decode()})" if who and logged else ""), flush=True)
            time.sleep(a.delay)
        except Exception as e:
            print(f"NETAPP_KB_COOKIE set but the probe failed: {e}", flush=True)

    manifests, dirty = {}, {}

    def manifest(folder):
        d = os.path.join(a.dest, "netapp", folder)
        if d not in manifests:
            os.makedirs(d, exist_ok=True)
            mf = os.path.join(d, "manifest.json")
            manifests[d] = json.load(open(mf)) if os.path.exists(mf) else {}
        return d, manifests[d]

    def flush():
        for d, m in manifests.items():
            if dirty.get(d):
                tmp = os.path.join(d, "manifest.json.tmp")
                json.dump(m, open(tmp, "w"), indent=1)
                os.replace(tmp, os.path.join(d, "manifest.json"))
                dirty[d] = False

    stats = {"saved": 0, "updated": 0, "partial": 0, "skipped": 0, "empty": 0, "failed": 0}
    t0 = time.time()
    for sig in (signal.SIGTERM, signal.SIGHUP):          # a kill still writes the manifest (resumable)
        signal.signal(sig, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        for n, (pri, mod, url, folder) in enumerate(todo, 1):
            d, man = manifest(folder)
            name = file_name(url)
            old = man.get(name)
            if old and old.get("lastmod") == mod and os.path.exists(os.path.join(d, name)) \
                    and not (a.refresh_partial and old.get("partial")):
                stats["skipped"] += 1
                continue
            if a.list:
                print(f"{folder}  {mod}  {url}")
                continue
            try:
                body, hdrs = fetch(url)
            except urllib.error.HTTPError as e:
                if e.code in (429, 503):
                    wait = int(e.headers.get("Retry-After", "60") or 60)
                    print(f"{e.code} from server, waiting {wait}s", flush=True)
                    time.sleep(wait)
                    stats["failed"] += 1
                    continue
                stats["failed"] += 1
                print(f"failed {e.code}: {url}", flush=True)
                time.sleep(a.delay)
                continue
            except (urllib.error.URLError, OSError) as e:
                stats["failed"] += 1
                print(f"failed: {url}: {e}", flush=True)
                time.sleep(a.delay)
                continue
            title, page, partial = extract(body, url)
            if page is None:
                stats["empty"] += 1
                print(f"no public content: {url}", flush=True)
            else:
                with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                    f.write(page)
                man[name] = {"url": url, "title": title or name, "lastmod": mod, "partial": partial}
                dirty[d] = True
                stats["updated" if old else "saved"] += 1
                stats["partial"] += partial
            done = stats["saved"] + stats["updated"]
            if done and done % 10 == 0:
                flush()
                rate = done / max(1, time.time() - t0) * 3600
                print(f"... {done} articles saved ({n}/{len(todo)} checked, {rate:.0f}/h) {folder}", flush=True)
            if a.max and done >= a.max:
                break
            time.sleep(a.delay)
    except KeyboardInterrupt:
        print("stopped; progress is saved, re-run to continue", flush=True)
    finally:
        flush()
    print("netapp kb:", json.dumps(stats), f"in {time.time() - t0:.0f}s -> {a.dest}/netapp/kb-*", flush=True)
    return 1 if stats["failed"] and not (stats["saved"] or stats["updated"] or stats["skipped"]) else 0


if __name__ == "__main__":
    sys.exit(main())
