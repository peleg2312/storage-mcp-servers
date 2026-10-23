#!/usr/bin/env python3
"""Collect Dell documentation with a real browser (Playwright + Chrome profile) - for what the plain
scripts cannot get: Dell's bot check refuses cloud addresses and plain clients, its KB listings and
search are JavaScript, and many manuals need a signed-in session.

Runs on a PC with internet. One-time setup (inside the venv):
    pip install playwright && python3 -m playwright install chromium
    python3 sync/dell_browser.py login          # a window opens: sign in to dell.com/support, then press ENTER here

Then (each is incremental; re-running only adds what is new):
    python3 sync/dell_browser.py needed         # extra/dell/NEEDED.md -> extra/dell/<product>/*.pdf (login-only docs)
    python3 sync/dell_browser.py kb             # web searches (DuckDuckGo, Bing, Dell) for every query in
                                                #   sources/dell-kb-queries.txt -> every KB article found -> work/docs/dell/kb
    python3 sync/dell_browser.py infohub        # Info Hub papers on PowerFlex / PowerMax / CSM: PDF or HTML pages
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
import threading
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_web  # noqa: E402
from sync_dell import is_redirect_pdf  # noqa: E402
from sync_dell_kb import FAMILY_RE, ID_RE  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_URL = "https://www.dell.com/support/kbdoc/en-us/{kb}"
DELL_SEARCH = "https://www.dell.com/support/search/en-us#q={q}&sort=relevancy&f:langFacet=[en]"
DDG_SEARCH = "https://html.duckduckgo.com/html/?q={q}"
BING_SEARCH = "https://www.bing.com/search?q={q}&first={first}"
KB_SITE = "site:dell.com/support/kbdoc"
INFOHUB = "https://infohub.delltechnologies.com"
INFOHUB_TOPICS = {"powerflex": "/en-us/t/powerflex-14/", "powermax": "/en-us/t/powermax-9/",
                  "csm": "/en-us/t/container-storage-modules/", "powerscale": "/en-us/t/powerscale/"}
INFOHUB_QUERIES = {"powerflex": ["PowerFlex", "PowerFlex Manager", "VxFlex", "ScaleIO"],
                   "powermax": ["PowerMax", "PowerMaxOS", "Unisphere for PowerMax", "SRDF", "VMAX All Flash"],
                   "csm": ["Container Storage Modules", "CSI PowerMax", "CSI PowerFlex", "CSI PowerScale",
                           "Dell CSM OpenShift", "Dell CSM Kubernetes"],
                   "powerscale": ["PowerScale", "OneFS", "Isilon", "PowerScale SmartConnect", "PowerScale SyncIQ",
                                  "PowerScale NFS", "PowerScale SMB", "PowerScale Kubernetes"]}
NEXT_SELECTORS = ['a[aria-label="Next"]', 'button[aria-label="Next"]', '.coveo-pager-next', 'li.coveo-pager-next a',
                  'a[title="Next"]', 'input[type="submit"][value="Next"]', 'text=Next']
LOAD_MORE = ['text=Load more', 'text=Show more', 'text=View more', 'button:has-text("More")']
PRODUCTS = ("powerflex", "powermax", "powerscale")
# a document (/l/<doc>/<section>/, with or without /en-us) or a blog post (/p/<post>/) -> its root url
DOC_LINK_RE = re.compile(r"https?://infohub\.delltechnologies\.com(?:/en-us)?/([lp])/([a-z0-9][a-z0-9-]*)", re.I)


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
    try:                                                # Dell pages rarely go idle (trackers): don't wait long
        page.wait_for_load_state("networkidle", timeout=6000)
    except Exception:
        pass
    page.wait_for_timeout(ms)


def html_of(page):
    """page.content() that survives 'the page is navigating' (retried)."""
    for _ in range(6):
        try:
            return page.content()
        except Exception:
            page.wait_for_timeout(700)
    return ""


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


def prepare_profile(profile):
    """Chrome preferences for the persistent profile: PDFs are downloaded, not shown in the viewer."""
    d = os.path.join(profile, "Default")
    os.makedirs(d, exist_ok=True)
    pf = os.path.join(d, "Preferences")
    try:
        prefs = json.load(open(pf)) if os.path.exists(pf) else {}
    except Exception:
        prefs = {}
    prefs.setdefault("plugins", {})["always_open_pdf_externally"] = True
    prefs.setdefault("download", {})["prompt_for_download"] = False
    json.dump(prefs, open(pf, "w"))


def unloop(ctx):
    """Outside the US, en-us pages set lwp=c=us and Chrome caches both 301s (en-us -> <country> by IP,
    <country> -> en-us by cookie): the support home then fails with ERR_TOO_MANY_REDIRECTS."""
    ctx.clear_cookies(name="lwp")
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    ctx.new_cdp_session(page).send("Network.clearBrowserCache")


def open_browser(p, profile, headless):
    prepare_profile(profile)
    kw = dict(headless=headless, accept_downloads=True, viewport={"width": 1400, "height": 1000},
              args=["--disable-blink-features=AutomationControlled"])
    exe = os.getenv("DELL_BROWSER_EXECUTABLE")              # a specific Chrome / Chromium binary
    if exe:
        ctx = p.chromium.launch_persistent_context(profile, executable_path=exe, **kw)
    else:
        try:
            ctx = p.chromium.launch_persistent_context(profile, channel="chrome", **kw)   # the installed Chrome
        except Exception:
            ctx = p.chromium.launch_persistent_context(profile, **kw)                    # Playwright's chromium
    unloop(ctx)
    try:
        ctx.add_cookies(json.load(open(session_file(profile))))
    except (OSError, ValueError):
        pass
    return ctx


def session_file(profile):
    """Dell's sign-in cookies (DellCEMSession, the identity provider's) are session cookies: Chrome drops them
    when the window closes, so login keeps a copy here (inside the git-ignored profile, owner-only)."""
    return os.path.join(profile, "session-cookies.json")


def save_session(ctx, profile):
    keep = [c for c in ctx.cookies() if "dell" in c["domain"] and c.get("expires", -1) == -1]
    f = session_file(profile)
    fd = os.open(f + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        json.dump(keep, out)
    os.replace(f + ".tmp", f)


def get_bytes(ctx, url):
    """Fetch with the browser's cookies; returns (bytes, content-type, final url)."""
    r = ctx.request.get(url, timeout=120000, max_redirects=10)
    return r.body(), r.headers.get("content-type", ""), r.url


def is_real_pdf(body):
    return b"%PDF" in body[:1024] and not is_redirect_pdf(body)


def fetch_pdf(ctx, page, url):
    """A PDF that may sit behind Dell's sign-in: plain fetch first; then navigate with the page so the
    identity-provider redirects complete with the stored session (the file arrives as a download, or the
    session cookie for dl.dell.com is set and a second plain fetch succeeds). Returns (bytes|None, note)."""
    body, ctype, final = get_bytes(ctx, url)
    if is_real_pdf(body):
        return body, ""
    m = re.search(rb"Invalid Access Level U:(\d+) =a:(\d+)", body[:500])
    if m:                                               # signed in, but the account lacks the entitlement
        return None, (f"access level {m.group(1).decode()} < {m.group(2).decode()} needed "
                      f"(link the Dell account to an entitled site / product)")
    if re.match(r"^/[a-z]{2}-[a-z]{2}/?$", urllib.parse.urlparse(final).path):   # landed on the Dell home page
        return None, "retired link (redirects to the Dell home page)"
    try:
        with page.expect_download(timeout=45000) as dl:
            try:
                page.goto(url, wait_until="commit")
            except Exception:
                pass                                    # "Download is starting" is the normal outcome
        path = dl.value.path()
        body = open(path, "rb").read()
        if is_real_pdf(body):
            return body, ""
    except Exception:
        pass                                            # no download: a sign-in page, or an inline viewer
    settle(page, 1500)
    if page.url.lower().endswith(".pdf") or "dl.dell.com" in page.url:
        try:
            body, ctype, final = get_bytes(ctx, page.url)
            if is_real_pdf(body):
                return body, ""
        except Exception:
            pass
    body, ctype, final = get_bytes(ctx, url)
    if is_real_pdf(body):
        return body, ""
    return None, f"sign-in page ({final[:70]})"


# ---------------------------------------------------------------- needed (login-only PDFs)
def cmd_needed(ctx, a):
    table = os.path.join(HERE, "extra", "dell", "NEEDED.md")
    if not os.path.isfile(table):
        log("no extra/dell/NEEDED.md"); return
    page = ctx.new_page()
    product = None
    n = bad = 0
    for line in open(table, encoding="utf-8"):
        m = re.match(r"## (\w+)", line)
        if m:
            product = m.group(1).lower() if m.group(1).lower() in PRODUCTS else None
        m = re.match(r"\| `([^`]+)` \| (\S+) \|", line)
        if not m or not product:
            continue
        name, url = m.group(1), m.group(2)
        target = os.path.join(HERE, "extra", "dell", product, name)
        if os.path.exists(target) and is_real_pdf(open(target, "rb").read()):
            continue
        try:
            body, note = fetch_pdf(ctx, page, url)
        except Exception as e:
            log(f"failed {name}: {e}"); bad += 1
            continue
        if body is None:
            log(f"not downloadable: {name}: {note}" + ("" if "retired" in note or "access level" in note
                                                         else " - signed in? run: dell_browser.py login"))
            bad += 1
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, "wb").write(body)
        n += 1
        log(f"ok {product}/{name} ({len(body) // 1024} KB)")
        time.sleep(a.delay)
    log(f"needed: {n} downloaded, {bad} still missing -> extra/dell/  (then: python3 sync/import_extra.py --dest work/docs)")


# ---------------------------------------------------------------- kb (searches -> ids -> articles)
def ids_in_text(text):
    text = urllib.parse.unquote(text)                   # search engines wrap links url-encoded
    return {x or y for x, y in ID_RE.findall(text)}


def search_ddg(page, query, max_pages):
    found = set()
    page.goto(DDG_SEARCH.format(q=urllib.parse.quote_plus(f"{KB_SITE} {query}")), wait_until="domcontentloaded")
    settle(page, 800)
    for n in range(max_pages):
        new = ids_in_text(html_of(page)) - found
        found |= new
        if n and not new:
            break
        if not click_any(page, ['input[type="submit"][value="Next"]', 'a.result--more__btn', 'text=Next']):
            break
        settle(page, 800)
    return found


def search_bing(page, query, max_pages):
    found = set()
    for n in range(max_pages):
        page.goto(BING_SEARCH.format(q=urllib.parse.quote_plus(f"{KB_SITE} {query}"), first=1 + 10 * n),
                  wait_until="domcontentloaded")
        settle(page, 600)
        new = ids_in_text(html_of(page)) - found
        found |= new
        if not new:
            break
    return found


def search_dell(page, query, max_pages, baseline):
    found = set()
    page.goto(DELL_SEARCH.format(q=urllib.parse.quote(query)), wait_until="domcontentloaded")
    settle(page, 2500)
    for n in range(max_pages):
        new = ids_in_text(html_of(page)) - found - baseline
        found |= new
        if n and not new:
            break
        if not click_any(page, NEXT_SELECTORS):
            break
        settle(page, 1500)
    return found


def kb_ok(body, final):
    text = body.decode("utf-8", "replace")
    title = sync_web.title_of(body)
    return ("/support/kbdoc/" in final and title and "Access Denied" not in title and "Sign In" not in title
            and not sync_web.LOGIN_HINTS.search(text[:200000]) and sync_web.text_len(body) >= 500)


def fetch_kb(ctx, page, url):
    """The article through the browser's HTTP client (~1 s, the article is in the served HTML); when Dell
    answers that with Access Denied / sign-in, render it in the page and poll until it is there (a full
    load waits ~25 s for trackers that never go idle). Returns (bytes, final url)."""
    try:
        body, _, final = get_bytes(ctx, url)
        if kb_ok(body, final) or "/di/idp/" in final:     # an article, or sign-in only (the page gets the same)
            return body, final
    except Exception:
        pass
    page.goto(url, wait_until="domcontentloaded")
    body = b""
    for _ in range(60):
        body = html_of(page).encode("utf-8")
        if kb_ok(body, page.url) or "/di/idp/" in page.url:
            break
        page.wait_for_timeout(250)
    return body, page.url


def save_kb(ctx, page, kb, d, man, known, stats, delay, snowball, off):
    url = KB_URL.format(kb=kb)
    try:
        body, final = fetch_kb(ctx, page, url)
    except Exception as e:
        stats["failed"] += 1
        log(f"failed {url}: {e}")
        return
    text = body.decode("utf-8", "replace")
    if "/di/idp/" in final:
        stats["sign_in_only"] += 1                      # retried by the next run (run with --wait-login)
        return
    if not kb_ok(body, final):
        stats["login_or_empty"] += 1
        log(f"empty page: {url}")
        return
    title = sync_web.title_of(body)
    if not FAMILY_RE.search(title) and not FAMILY_RE.search(text[:300000]):
        stats["off_family"] += 1
        off.add(kb)
        return
    name = sync_web.file_name(final, False)
    open(os.path.join(d, name), "wb").write(body)
    man[name] = {"url": url, "title": title}
    known.add(kb)
    stats["saved"] += 1
    if stats["saved"] % 10 == 0:
        log(f"... {stats['saved']} saved, {len(snowball)} queued")
    for linked in (ids_in_text(text) - known):
        snowball.add(linked)
    time.sleep(delay)


def cmd_kb(ctx, a):
    page = ctx.new_page()
    d = os.path.join(a.dest, "dell", "kb")
    man, mf = load_manifest(d)
    known = {re.search(r"(\d{9})", v.get("url", "")).group(1) for v in man.values() if re.search(r"(\d{9})", v.get("url", ""))}
    queries = [q.split("#", 1)[0].strip() for q in open(a.queries, encoding="utf-8")] if os.path.isfile(a.queries) else []
    queries = [q for q in queries if q]
    engines = [e.strip() for e in a.engines.split(",") if e.strip()]
    ids = set()
    baseline = set()
    if "dell" in engines:
        try:
            baseline = search_dell(page, "zzqqxxnothing", 1, set())      # links every search page carries
        except Exception:
            pass
    # search results are kept a week, so a stopped run restarts straight into the article fetches
    cache_f = os.path.join(os.path.dirname(a.profile), "cache", "dell-kb-search.json")
    os.makedirs(os.path.dirname(cache_f), exist_ok=True)
    cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
    for q in queries:
        got = set()
        for eng in engines:
            hit = cache.get(f"{eng}\t{q}")
            if hit and time.time() - hit["t"] < 7 * 86400:
                got |= set(hit["ids"])
                continue
            try:
                if eng == "ddg":
                    found = search_ddg(page, q, a.max_pages)
                elif eng == "bing":
                    found = search_bing(page, q, a.max_pages)
                elif eng == "dell":
                    found = search_dell(page, q, a.max_pages, baseline)
                else:
                    continue
                got |= found
                cache[f"{eng}\t{q}"] = {"t": time.time(), "ids": sorted(found)}
                save_manifest(cache, cache_f)
            except Exception as e:
                log(f"{eng} search failed {q!r}: {e}")
            time.sleep(a.delay)
        log(f"search {q!r}: {len(got)} articles ({len(got - known - ids)} new)")
        ids |= got
    if a.ids_file and os.path.isfile(a.ids_file):
        ids |= set(re.findall(r"\b(\d{9})\b", open(a.ids_file).read()))
    off = set(cache.get("_off_family", []))             # other products: not fetched again
    known |= off
    todo = sorted(ids - known)
    log(f"{len(ids)} article numbers from {len(queries)} queries x {len(engines)} engines, {len(todo)} to fetch")
    stats = {"saved": 0, "off_family": 0, "sign_in_only": 0, "login_or_empty": 0, "failed": 0}
    snowball = set()
    try:
        for kb in todo:
            save_kb(ctx, page, kb, d, man, known, stats, a.delay, snowball, off)
            if stats["saved"] % 10 == 0:
                save_manifest(man, mf)
            if (stats["off_family"] + 1) % 25 == 0:
                cache["_off_family"] = sorted(off)
                save_manifest(cache, cache_f)
            if a.max_articles and stats["saved"] >= a.max_articles:
                break
        # one round of related-article links from the articles just saved
        for kb in sorted(snowball - known - set(todo)):
            if a.max_articles and stats["saved"] >= a.max_articles:
                break
            save_kb(ctx, page, kb, d, man, known, stats, a.delay, set(), off)
            if stats["saved"] % 10 == 0:
                save_manifest(man, mf)
    finally:
        save_manifest(man, mf)
        cache["_off_family"] = sorted(off)
        save_manifest(cache, cache_f)
    log(f"dell kb (browser): {json.dumps(stats)} -> {d}")


# ---------------------------------------------------------------- infohub
def infohub_doc_links(text):
    text = re.sub(r'href="(/[^"]*)"', lambda m: 'href="' + INFOHUB + m.group(1) + '"', urllib.parse.unquote(text))
    # a document's landing page is /t/<doc>/ (its /l/<doc>/ root redirects to the home page); posts are /p/<post>/
    return {f"{INFOHUB}/en-us/{'t' if kind.lower() == 'l' else 'p'}/{slug.lower()}/" for kind, slug in DOC_LINK_RE.findall(text)}


def cmd_infohub(ctx, a):
    page = ctx.new_page()
    engines = [e.strip() for e in a.engines.split(",") if e.strip()]
    for topic, path in INFOHUB_TOPICS.items():
        d = os.path.join(a.dest, "dell", f"infohub-{topic}")
        man, mf = load_manifest(d)
        links = set()
        # 1. the topic page itself (expand as far as it goes)
        try:
            page.goto(INFOHUB + path, wait_until="domcontentloaded")
            settle(page, 2500)
            t = html_of(page)
            if "recaptcha" in t.lower() and "checking your browser" in t.lower():
                log(f"infohub {topic}: bot check page - solve it in the browser window, then re-run")
            for _ in range(60):
                if not click_any(page, LOAD_MORE):
                    break
                settle(page, 1200)
            links |= infohub_doc_links(html_of(page))
        except Exception as e:
            log(f"infohub {topic}: listing failed: {e}")
        # 2. web searches (the listing is JavaScript and may hide most of it)
        for q in INFOHUB_QUERIES.get(topic, []):
            for eng in engines:
                try:
                    if eng == "ddg":
                        page.goto(DDG_SEARCH.format(q=urllib.parse.quote_plus(f"site:infohub.delltechnologies.com {q}")),
                                  wait_until="domcontentloaded")
                        settle(page, 800)
                        for _ in range(a.max_pages):
                            before = len(links)
                            links |= infohub_doc_links(html_of(page))
                            if len(links) == before and _ or not click_any(page, ['input[type="submit"][value="Next"]']):
                                break
                            settle(page, 800)
                    elif eng == "bing":
                        for n in range(a.max_pages):
                            page.goto(BING_SEARCH.format(q=urllib.parse.quote_plus(f"site:infohub.delltechnologies.com {q}"),
                                                         first=1 + 10 * n), wait_until="domcontentloaded")
                            settle(page, 600)
                            before = len(links)
                            links |= infohub_doc_links(html_of(page))
                            if len(links) == before:
                                break
                except Exception as e:
                    log(f"{eng} search failed {q!r}: {e}")
                time.sleep(a.delay)
        links = sorted(links)
        log(f"infohub {topic}: {len(links)} documents found")
        for doc in links:
            key = hashlib.sha1(doc.encode()).hexdigest()[:8]
            if any(v.get("url") == doc for v in man.values()):
                continue
            try:
                page.goto(doc, wait_until="domcontentloaded")
                settle(page, 1000)
                html_ = html_of(page)
                title = sync_web.title_of(html_.encode()) or doc
                pdf = None
                for href in re.findall(r'href="([^"]+)"', html_):
                    full = urllib.parse.urljoin(doc, href)
                    if ".pdf" in full.lower() and "delltechnologies.com" in full:
                        pdf = full
                        break
                stem = re.sub(r"[^\w\-]+", "-", doc.rstrip("/").rsplit("/", 1)[-1])[:90]
                if pdf:
                    body, note = fetch_pdf(ctx, page, pdf)
                    if body:
                        name = f"{stem}_{key}.pdf"
                        open(os.path.join(d, name), "wb").write(body)
                        man[name] = {"url": doc, "title": title}
                        log(f"ok pdf  {title[:70]}")
                        time.sleep(a.delay)
                        continue
                    page.goto(doc, wait_until="domcontentloaded")
                    settle(page, 800)
                    html_ = html_of(page)
                # no PDF: save the landing page and every section of the document (/l/<doc>/<section>/)
                sec = "/l/" + doc.rstrip("/").rsplit("/", 1)[-1] + "/"
                pages = [doc] + sorted({u for u in (urllib.parse.urljoin(doc, h) for h in re.findall(r'href="([^"#?]+)"', html_))
                                        if "/t/" in doc and sec in u and u.startswith(INFOHUB)})
                parts = [html_]
                for sub in pages[1:80]:
                    page.goto(sub, wait_until="domcontentloaded")
                    settle(page, 500)
                    parts.append(html_of(page))
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
        url = re.sub(r"/support/manuals/(?![a-z]{2}-[a-z]{2}/)", "/support/manuals/en-us/", url)   # index links: no locale
        m = re.search(r"(/support/manuals/[a-z]{2}-[a-z]{2}/[^/]+/[^/?]+)", url)
        if not m:
            log(f"not a dell.com manual url: {url}"); continue
        prefix = "https://www.dell.com" + m.group(1)
        guide = m.group(1).rstrip("/").rsplit("/", 1)[-1]
        d = os.path.join(a.dest, "dell", product, f"manual-{guide}")
        man, mf = load_manifest(d)
        page.goto(url, wait_until="domcontentloaded")
        settle(page, 2000)
        first = html_of(page)
        for _ in range(30):                             # the table of contents is drawn by JavaScript, late
            if first.count(guide + "/") > 3:
                break
            page.wait_for_timeout(500)
            first = html_of(page)
        title = sync_web.title_of(first.encode()).strip()
        if "Sign In" in title or title.strip() in ("", "Back Button"):
            log(f"{guide}: needs sign-in (run with --wait-login) - skipped"); continue
        if title.startswith("Sorry"):
            log(f"{guide}: retired link (Dell answers 'Sorry') - find the guide's new url for sources/dell-manuals.txt"); continue
        topics, seen = [url], {url.split("&lang")[0]}
        for href in re.findall(r'href="([^"]+)"', first):
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
                body = html_of(page)
                title = sync_web.title_of(body.encode()).strip()
                if title.startswith("Sorry") or "Sign In" in title or title.strip() in ("", "Back Button"):
                    log(f"skipped (retired or sign-in page): {t}"); continue
                stem = re.sub(r"[^\w\-]+", "-", t.split("?")[0].rstrip("/").rsplit("/", 1)[-1])[:80]
                name = f"{stem}_{key}.html"
                open(os.path.join(d, name), "w", encoding="utf-8").write(body)
                man[name] = {"url": t, "title": title}
            except Exception as e:
                log(f"failed {t}: {e}")
            time.sleep(a.delay)
        save_manifest(man, mf)
        log(f"{guide}: {len(man)} topics -> {d}")


SIGNIN_PROBE = KB_URL.format(kb="000017598")              # an article Dell shows only when signed in


def wait_login(ctx, profile):
    """Sign in inside this run's window and keep going in the same live session (Dell's identity-provider
    session expires, so a session saved by an earlier login no longer opens sign-in-only articles)."""
    page = ctx.new_page()
    page.goto(SIGNIN_PROBE, wait_until="domcontentloaded")
    if "/di/idp/" in page.url:
        log("Sign in to Dell in the browser window; the run continues by itself once you are signed in.")
    for _ in range(1200):                               # up to 10 minutes
        if "/support/kbdoc/" in page.url:
            break
        page.wait_for_timeout(500)
    else:
        log("not signed in after 10 minutes - continuing anonymously")
    save_session(ctx, profile)
    page.close()


def cmd_login(ctx, a):
    page = ctx.new_page()
    page.goto("https://www.dell.com/support/home/en-us")
    done = threading.Event()
    if sys.stdin.isatty():                              # without a terminal only closing the window ends it
        threading.Thread(target=lambda: (sys.stdin.readline(), done.set()), daemon=True).start()
    ctx.on("close", lambda *_: done.set())
    log("\n1. Sign in to Dell Support in the browser window (Sign In / My Account).\n"
        "2. Come back to this terminal and press ENTER (or just close the browser window).\n"
        f"The session is kept in {a.profile} for the other commands.")
    while not done.is_set():
        try:
            if not ctx.pages:
                break
            save_session(ctx, a.profile)                # closing the window is too late to read them
            ctx.pages[0].wait_for_timeout(1000)
        except Exception:
            break
    try:
        save_session(ctx, a.profile)
    except Exception:
        pass
    log("login saved.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["login", "needed", "kb", "infohub", "manuals", "all"])
    ap.add_argument("--dest", default=os.path.join(HERE, "work", "docs"))
    ap.add_argument("--profile", default=os.path.join(HERE, "work", "browser-profile"))
    ap.add_argument("--queries", default=os.path.join(HERE, "sources", "dell-kb-queries.txt"))
    ap.add_argument("--ids-file", default="", help="extra KB numbers, one per line (kb command)")
    ap.add_argument("--engines", default="ddg,dell",
                    help="search engines for kb / infohub discovery (bing: challenges automated browsers, finds nothing)")
    ap.add_argument("--max-pages", type=int, default=8, help="search result pages per query and engine")
    ap.add_argument("--max-articles", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--wait-login", action="store_true",
                    help="open Dell sign-in first and continue in that session once you are signed in")
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
                cmd_login(ctx, a)
                return
            if a.wait_login:
                wait_login(ctx, a.profile)
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
