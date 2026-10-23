#!/usr/bin/env python3
"""Collect Dell documentation with a real browser (Playwright + Chrome profile) - for what the plain
scripts cannot get: Dell's bot check refuses cloud addresses and plain clients, its KB listings and
search are JavaScript, and many manuals need a signed-in session.

Runs on a PC with internet. One-time setup (inside the venv):
    pip install playwright && python3 -m playwright install chromium
    python3 sync/dell_browser.py login          # a window opens: sign in to dell.com/support, then close it

Then (each is incremental; re-running only adds what is new):
    python3 sync/dell_browser.py needed         # extra/dell/NEEDED.md -> extra/dell/<product>/*.pdf (login-only docs)
    python3 sync/dell_browser.py kb             # Dell support search for every query in sources/dell-kb-queries.txt
                                                #   -> every KB article found (login-only ones too) -> work/docs/dell/kb
    python3 sync/dell_browser.py infohub        # Info Hub topics (PowerFlex, PowerMax, CSM): every paper as PDF or HTML
    python3 sync/dell_browser.py manuals        # HTML manuals listed in sources/dell-manuals.txt, topic by topic
    python3 sync/dell_browser.py all            # needed + kb + infohub + manuals

The browser profile lives in work/browser-profile (your Dell login cookies; never commit it). Headed by
default because Dell's bot check dislikes headless browsers; add --headless to try without a window.
Afterwards: python3 sync/import_extra.py --dest work/docs ; python3 docs_index.py ... ; sh bundle/pack-library.sh
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_web  # noqa: E402
from sync_dell import is_redirect_pdf  # noqa: E402
from sync_dell_kb import FAMILY_RE, ID_RE  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH = "https://www.dell.com/support/search/en-us#q={q}&sort=relevancy&f:langFacet=[en]"
KB_URL = "https://www.dell.com/support/kbdoc/en-us/{kb}"
INFOHUB = "https://infohub.delltechnologies.com"
INFOHUB_TOPICS = {"powerflex": "/en-us/t/powerflex-14/", "powermax": "/en-us/t/powermax-9/",
                  "csm": "/en-us/t/container-storage-modules/"}
NEXT_SELECTORS = ['a[aria-label="Next"]', 'button[aria-label="Next"]', '.coveo-pager-next', 'li.coveo-pager-next a',
                  'a[title="Next"]', 'text=Next']
LOAD_MORE = ['text=Load more', 'text=Show more', 'text=View more', 'button:has-text("More")']


def log(*a):
    print(*a, flush=True)


def load_manifest(d):
    os.makedirs(d, exist_ok=True)
    mf = os.path.join(d, "manifest.json")
    return (json.load(open(mf)) if os.path.exists(mf) else {}), mf


def save_manifest(man, mf):
    tmp = mf + ".tmp"
    json.dump(man, open(tmp, "w"), indent=1)
    os.replace(tmp, mf)


def settle(page, ms=1500):
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(ms)


def click_any(page, selectors):
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.count() and el.is_visible() and el.is_enabled():
                el.click(timeout=3000)
                return True
        except Exception:
            continue
    return False


def open_browser(p, profile, headless):
    kw = dict(headless=headless, accept_downloads=True, viewport={"width": 1400, "height": 1000},
              args=["--disable-blink-features=AutomationControlled"])
    exe = os.getenv("DELL_BROWSER_EXECUTABLE")              # a specific Chrome / Chromium binary
    if exe:
        return p.chromium.launch_persistent_context(profile, executable_path=exe, **kw)
    try:
        return p.chromium.launch_persistent_context(profile, channel="chrome", **kw)   # the installed Chrome
    except Exception:
        return p.chromium.launch_persistent_context(profile, **kw)                    # Playwright's chromium


def get_bytes(ctx, url):
    """Fetch with the browser's cookies; returns (bytes, content-type, final url)."""
    r = ctx.request.get(url, timeout=120000, max_redirects=10)
    return r.body(), r.headers.get("content-type", ""), r.url


# ---------------------------------------------------------------- needed (login-only PDFs)
def cmd_needed(ctx, a):
    table = os.path.join(HERE, "extra", "dell", "NEEDED.md")
    if not os.path.isfile(table):
        log("no extra/dell/NEEDED.md"); return
    product = None
    n = bad = 0
    for line in open(table, encoding="utf-8"):
        m = re.match(r"## (\w+)", line)
        if m:
            product = m.group(1)
        m = re.match(r"\| `([^`]+)` \| (\S+) \|", line)
        if not m or not product:
            continue
        name, url = m.group(1), m.group(2)
        target = os.path.join(HERE, "extra", "dell", product, name)
        if os.path.exists(target) and not is_redirect_pdf(open(target, "rb").read()):
            continue
        try:
            body, ctype, final = get_bytes(ctx, url)
        except Exception as e:
            log(f"failed {name}: {e}"); bad += 1
            continue
        if b"%PDF" not in body[:1024] or is_redirect_pdf(body):
            log(f"still the sign-in / redirect page: {name}  ({final[:80]}) - are you signed in? run: dell_browser.py login")
            bad += 1
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, "wb").write(body)
        n += 1
        log(f"ok {product}/{name} ({len(body) // 1024} KB)")
        time.sleep(a.delay)
    log(f"needed: {n} downloaded, {bad} still missing -> extra/dell/  (then: python3 sync/import_extra.py --dest work/docs)")


# ---------------------------------------------------------------- kb (search -> ids -> articles)
def ids_on(page):
    return {x or y for x, y in ID_RE.findall(page.content())}


def search_ids(page, query, max_pages):
    found = set()
    page.goto(SEARCH.format(q=urllib.parse.quote(query)), wait_until="domcontentloaded")
    settle(page, 2500)
    for n in range(max_pages):
        new = ids_on(page) - found
        found |= new
        if n and not new:
            break
        if not click_any(page, NEXT_SELECTORS):
            break
        settle(page, 1500)
    return found


def save_kb(page, kb, d, man, known, stats, delay, snowball):
    url = KB_URL.format(kb=kb)
    try:
        page.goto(url, wait_until="domcontentloaded")
        settle(page, 800)
        body = page.content().encode("utf-8")
        final = page.url
    except Exception as e:
        stats["failed"] += 1
        log(f"failed {url}: {e}")
        return
    text = body.decode("utf-8", "replace")
    if "/support/kbdoc/" not in final or sync_web.LOGIN_HINTS.search(text[:200000]) or sync_web.text_len(body) < 500:
        stats["login_or_empty"] += 1
        log(f"empty / sign-in page: {url}")
        return
    title = sync_web.title_of(body)
    if not FAMILY_RE.search(title) and not FAMILY_RE.search(text[:300000]):
        stats["off_family"] += 1
        return
    name = sync_web.file_name(final, False)
    open(os.path.join(d, name), "wb").write(body)
    man[name] = {"url": url, "title": title}
    known.add(kb)
    stats["saved"] += 1
    if stats["saved"] % 10 == 0:
        log(f"... {stats['saved']} saved, {len(snowball)} queued")
    for linked in ({x or y for x, y in ID_RE.findall(text)} - known):
        snowball.add(linked)
    time.sleep(delay)


def cmd_kb(ctx, a):
    page = ctx.new_page()
    d = os.path.join(a.dest, "dell", "kb")
    man, mf = load_manifest(d)
    known = {re.search(r"(\d{9})", v.get("url", "")).group(1) for v in man.values() if re.search(r"(\d{9})", v.get("url", ""))}
    queries = [q.split("#", 1)[0].strip() for q in open(a.queries, encoding="utf-8")] if os.path.isfile(a.queries) else []
    queries = [q for q in queries if q]
    ids = set()
    for q in queries:
        try:
            got = search_ids(page, q, a.max_pages)
        except Exception as e:
            log(f"search failed {q!r}: {e}")
            continue
        log(f"search {q!r}: {len(got)} articles ({len(got - known)} new)")
        ids |= got
        time.sleep(a.delay)
    if a.ids_file and os.path.isfile(a.ids_file):
        ids |= set(re.findall(r"\b(\d{9})\b", open(a.ids_file).read()))
    todo = sorted(ids - known)
    log(f"{len(ids)} article numbers from {len(queries)} searches, {len(todo)} to fetch")
    stats = {"saved": 0, "off_family": 0, "login_or_empty": 0, "failed": 0}
    snowball = set()
    try:
        for kb in todo:
            save_kb(page, kb, d, man, known, stats, a.delay, snowball)
            if stats["saved"] % 10 == 0:
                save_manifest(man, mf)
            if a.max_articles and stats["saved"] >= a.max_articles:
                break
        # one round of related-article links from the articles just saved
        for kb in sorted(snowball - known - set(todo)):
            if a.max_articles and stats["saved"] >= a.max_articles:
                break
            save_kb(page, kb, d, man, known, stats, a.delay, set())
            if stats["saved"] % 10 == 0:
                save_manifest(man, mf)
    finally:
        save_manifest(man, mf)
    log(f"dell kb (browser): {json.dumps(stats)} -> {d}")


# ---------------------------------------------------------------- infohub
def cmd_infohub(ctx, a):
    page = ctx.new_page()
    for topic, path in INFOHUB_TOPICS.items():
        d = os.path.join(a.dest, "dell", f"infohub-{topic}")
        man, mf = load_manifest(d)
        page.goto(INFOHUB + path, wait_until="domcontentloaded")
        settle(page, 2500)
        if "recaptcha" in page.content().lower() and "checking your browser" in page.content().lower():
            log(f"infohub {topic}: bot check page - solve it in the browser window, then re-run"); continue
        for _ in range(60):                       # expand the listing as far as it goes
            if not click_any(page, LOAD_MORE):
                break
            settle(page, 1200)
        links = sorted({urllib.parse.urljoin(INFOHUB, h) for h in re.findall(r'href="(/en-us/l/[^"#?]+/)"', page.content())})
        log(f"infohub {topic}: {len(links)} documents listed")
        for doc in links:
            key = hashlib.sha1(doc.encode()).hexdigest()[:8]
            if any(v.get("url") == doc for v in man.values()):
                continue
            try:
                page.goto(doc, wait_until="domcontentloaded")
                settle(page, 1000)
                html_ = page.content()
                title = sync_web.title_of(html_.encode()) or doc
                pdf = None
                for href in re.findall(r'href="([^"]+)"', html_):
                    full = urllib.parse.urljoin(doc, href)
                    if ".pdf" in full.lower() and "delltechnologies.com" in full:
                        pdf = full
                        break
                stem = re.sub(r"[^\w\-]+", "-", doc.rstrip("/").rsplit("/", 1)[-1])[:90]
                if pdf:
                    body, ctype, final = get_bytes(ctx, pdf)
                    if b"%PDF" in body[:1024] and not is_redirect_pdf(body):
                        name = f"{stem}_{key}.pdf"
                        open(os.path.join(d, name), "wb").write(body)
                        man[name] = {"url": doc, "title": title}
                        log(f"ok pdf  {title[:70]}")
                        time.sleep(a.delay)
                        continue
                # no PDF: save every HTML page of the document
                pages = [doc] + sorted({urllib.parse.urljoin(doc, h) for h in re.findall(r'href="([^"#?]+)"', html_)
                                        if urllib.parse.urljoin(doc, h).startswith(doc) and urllib.parse.urljoin(doc, h) != doc})
                parts = [html_]
                for sub in pages[1:60]:
                    page.goto(sub, wait_until="domcontentloaded")
                    settle(page, 500)
                    parts.append(page.content())
                name = f"{stem}_{key}.html"
                open(os.path.join(d, name), "w", encoding="utf-8").write("\n<!-- page break -->\n".join(parts))
                man[name] = {"url": doc, "title": title}
                log(f"ok html {title[:70]} ({len(pages)} pages)")
                time.sleep(a.delay)
            except Exception as e:
                log(f"failed {doc}: {e}")
            if len(man) % 10 == 0:
                save_manifest(man, mf)
        save_manifest(man, mf)
        log(f"infohub {topic}: {len(man)} documents -> {d}")


# ---------------------------------------------------------------- manuals (HTML, topic by topic)
def cmd_manuals(ctx, a):
    src = os.path.join(HERE, "sources", "dell-manuals.txt")
    if not os.path.isfile(src):
        log("no sources/dell-manuals.txt"); return
    page = ctx.new_page()
    for line in open(src, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        product, url = line.split(None, 1)
        m = re.search(r"(/support/manuals/[a-z]{2}-[a-z]{2}/[^/]+/[^/?]+)", url)
        if not m:
            log(f"not a dell.com manual url: {url}"); continue
        prefix = "https://www.dell.com" + m.group(1)
        guide = m.group(1).rstrip("/").rsplit("/", 1)[-1]
        d = os.path.join(a.dest, "dell", product, f"manual-{guide}")
        man, mf = load_manifest(d)
        page.goto(url, wait_until="domcontentloaded")
        settle(page, 2000)
        if "Sign In" in sync_web.title_of(page.content().encode()):
            log(f"{guide}: needs sign-in (run: dell_browser.py login) - skipped"); continue
        topics, seen = [url], {url.split("&lang")[0]}
        for href in re.findall(r'href="([^"]+)"', page.content()):
            full = urllib.parse.urljoin(url, href.replace("&amp;", "&"))
            if full.startswith(prefix) and full.split("&lang")[0] not in seen:
                seen.add(full.split("&lang")[0]); topics.append(full)
        log(f"{guide}: {len(topics)} topics")
        for t in topics:
            key = hashlib.sha1(t.split("&lang")[0].encode()).hexdigest()[:8]
            if any(k.endswith(f"_{key}.html") for k in man):
                continue
            try:
                page.goto(t, wait_until="domcontentloaded")
                settle(page, 600)
                body = page.content()
                title = sync_web.title_of(body.encode())
                stem = re.sub(r"[^\w\-]+", "-", t.split("?")[0].rstrip("/").rsplit("/", 1)[-1])[:80]
                name = f"{stem}_{key}.html"
                open(os.path.join(d, name), "w", encoding="utf-8").write(body)
                man[name] = {"url": t, "title": title}
            except Exception as e:
                log(f"failed {t}: {e}")
            time.sleep(a.delay)
        save_manifest(man, mf)
        log(f"{guide}: {len(man)} topics -> {d}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["login", "needed", "kb", "infohub", "manuals", "all"])
    ap.add_argument("--dest", default=os.path.join(HERE, "work", "docs"))
    ap.add_argument("--profile", default=os.path.join(HERE, "work", "browser-profile"))
    ap.add_argument("--queries", default=os.path.join(HERE, "sources", "dell-kb-queries.txt"))
    ap.add_argument("--ids-file", default="", help="extra KB numbers, one per line (kb command)")
    ap.add_argument("--max-pages", type=int, default=15, help="search result pages per query")
    ap.add_argument("--max-articles", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--headless", action="store_true")
    a = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("pip install playwright && python3 -m playwright install chromium")
    os.makedirs(a.profile, exist_ok=True)
    with sync_playwright() as p:
        ctx = open_browser(p, a.profile, a.headless and a.command != "login")
        try:
            if a.command == "login":
                page = ctx.new_page()
                page.goto("https://www.dell.com/support/home/en-us")
                log("Sign in to Dell Support in the window (My Account), open one login-only manual to confirm, "
                    "then close the window. The session is kept in", a.profile)
                try:
                    page.wait_for_event("close", timeout=0)
                except Exception:
                    pass
                return
            if a.command in ("needed", "all"):
                cmd_needed(ctx, a)
            if a.command in ("kb", "all"):
                cmd_kb(ctx, a)
            if a.command in ("infohub", "all"):
                cmd_infohub(ctx, a)
            if a.command in ("manuals", "all"):
                cmd_manuals(ctx, a)
        finally:
            try:
                ctx.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
