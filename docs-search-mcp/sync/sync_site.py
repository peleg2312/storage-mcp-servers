"""
Crawl a documentation site from its sitemap (or a URL list) into the library: one topic per file, the page's own
breadcrumb kept as the first line so the search knows where a topic sits ("Databases > SQL Server > Always On").

    python sync/sync_site.py commvault --version 11.40 --dest work/flashback/docs [--include RE] [--exclude RE]
    python sync/sync_site.py veeam --guide vbr/userguide --dest work/flashback/docs [--exclude RE]
    python sync/sync_site.py redhat --guide openshift_container_platform/4.20/backup_and_restore --product oadp-1.5
    python sync/sync_site.py --list sources/flashback/sites.txt --dest work/flashback/docs   # every line of a list

Sites (profiles below): commvault (documentation.commvault.com/<version>/software, product commvault/<version>),
veeam (helpcenter.veeam.com/docs/<guide>, product veeam/<guide with / as ->), redhat (a docs.redhat.com html-single guide,
split into one file per section with its chapter as breadcrumb). --include / --exclude are regular
expressions over "breadcrumb > title" (and the url): only matching topics are kept, so a version's 9,000 pages become the
few thousand a team needs. Topics are fetched with --workers parallel requests (default 4), robots.txt respected,
incremental (saved topics are skipped unless --refresh; a topic dropped by the filter is never fetched again: its
breadcrumb is remembered in .crawl.json). Writes <dest>/<vendor>/<product>/<slug>.html (title, breadcrumb, article only)
and manifest.json (url, title) for docs_index.py. Standard library only.
"""

import argparse
import concurrent.futures as cf
import gzip
import html
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

UA = os.getenv("DOCS_SYNC_USER_AGENT", "docs-search-mcp/1.1 (internal documentation index)")


def _between(s, start_re, end_re):
    m = re.search(start_re, s, re.S)
    if not m:
        return ""
    e = re.search(end_re, s[m.end():], re.S)
    return s[m.end(): m.end() + e.start()] if e else s[m.end():]


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def commvault_parse(page):
    crumbs = [_text(c) for c in re.findall(r'class="breadcrumb breadcrumb-link"[^>]*>(.*?)</a>', page, re.S)]
    title = _text(_between(page, r'<h1 class="heading">', r"</h1>")) or _text(_between(page, r"<title>", r"</title>"))
    art = _between(page, r'<article class="article">', r"</article>")
    return title, crumbs, art


def veeam_parse(page):
    nav = _between(page, r'<ol class="breadcrumb js-breadcrumb">', r"</ol>")
    crumbs = [_text(c) for c in re.findall(r'itemprop="name"[^>]*>(.*?)</span>', nav, re.S)]
    crumbs = [c for c in crumbs if c and c != "Home"][:-1]          # the last one is the page itself
    art = _between(page, r'<article class="js-page-article[^"]*">', r"</article>")
    title = _text(_between(art, r"<h1[^>]*>", r"</h1>")) or _text(_between(page, r"<title>", r"</title>"))
    art = re.sub(r"<aside class=\"mini-toc.*?</aside>", "", art, flags=re.S)
    art = re.sub(r"<h1[^>]*>.*?</h1>", "", art, count=1, flags=re.S)
    return title, crumbs, art


def redhat_split(page, url):
    """a docs.redhat.com html-single guide -> [(anchor, title, crumbs, html)]: one part per section, the chapter as breadcrumb"""
    start = page.find('class="rhdocs"')
    end = page.find("</article>", start)
    body = page[start:end if end > 0 else len(page)]
    body = re.sub(r"<rh-tooltip\b.*?</rh-tooltip>", "", body, flags=re.S)
    guide = _text(_between(page, r"<title>", r"</title>")).split("|")[0].strip()
    marks = [(m.start(), m.group(1), m.group(2)) for m in
             re.finditer(r'<section class="(chapter|section|appendix)" id="([^"]+)"', body)]
    parts, chapter = [], ""
    for i, (pos, kind, anchor) in enumerate(marks):
        chunk = body[pos: marks[i + 1][0] if i + 1 < len(marks) else len(body)]
        title = _text(_between(chunk, r"<h[1-6][^>]*>", r"</h[1-6]>"))
        title = re.sub(r"^(Chapter|Appendix)\s+[\w.]+\.\s*", "", title)
        if kind != "section":
            chapter = title
        chunk = re.sub(r"<h[1-6][^>]*>.*?</h[1-6]>", "", chunk, count=1, flags=re.S)
        if len(_text(chunk)) < 40:
            continue
        parts.append((anchor, title, [guide] + ([chapter] if chapter and chapter != title else []), chunk))
    return parts


SITES = {
    "commvault": {"vendor": "commvault", "parse": commvault_parse,
                  "sitemap": "https://documentation.commvault.com/{version}/{part}/sitemap.xml",
                  "product": lambda a: a.version + ("" if a.part == "software" else "-" + a.part)},
    "veeam": {"vendor": "veeam", "parse": veeam_parse, "sitemap": "https://helpcenter.veeam.com/sitemap.xml",
              "prefix": "https://helpcenter.veeam.com/docs/{guide}/", "product": lambda a: a.guide.replace("/", "-")},
}


def fetch(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
            time.sleep(2 ** i)
        except Exception:
            time.sleep(2 ** i)
    return None


def clean_article(art):
    art = re.sub(r"<(script|style|noscript|button|svg|form)\b.*?</\1>", "", art, flags=re.S | re.I)
    art = re.sub(r"<img\b[^>]*>", "", art, flags=re.I)
    art = re.sub(r"\s(class|style|id|data-[\w-]+|onclick|target|rel|aria-[\w-]+|itemprop|itemscope|itemtype)=\"[^\"]*\"", "", art)
    return re.sub(r"\n\s*\n+", "\n", art).strip()


def crawl_redhat(args):
    """--guide openshift_container_platform/4.20/backup_and_restore [--product oadp-1.5]"""
    prod_path, _, guide = args.guide.rpartition("/")
    product = args.product or args.guide.replace("/", "-")
    out = os.path.join(args.dest, "redhat", product)
    os.makedirs(out, exist_ok=True)
    url = f"https://docs.redhat.com/en/documentation/{prod_path}/html-single/{guide}/index"
    page = open(args.file, encoding="utf-8", errors="replace").read() if args.file else fetch(url)
    if not page:
        sys.exit(f"cannot fetch {url}: download it (curl -L --compressed -o guide.html {url}) and give it with --file")
    manifest = {}
    for old in os.listdir(out):
        if old.endswith(".html"):
            os.remove(os.path.join(out, old))
    for anchor, title, crumbs, chunk in redhat_split(page, url):
        name = re.sub(r"[^\w.-]+", "_", anchor)[:120] + ".html"
        u = f"{url}#{anchor}"
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(f"<html><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title></head><body>\n"
                    f"<p>{html.escape(' > '.join(crumbs))}</p>\n<h1>{html.escape(title)}</h1>\n{clean_article(chunk)}\n"
                    f"<p>Source: {html.escape(u)}</p></body></html>\n")
        manifest[name] = {"url": u, "title": title}
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=0)
    print(f"redhat {product}: {len(manifest)} sections from {url}", flush=True)


def crawl(site, args):
    if site == "redhat":
        return crawl_redhat(args)
    prof = SITES[site]
    product = prof["product"](args)
    out = os.path.join(args.dest, prof["vendor"], product)
    os.makedirs(out, exist_ok=True)
    smap = prof["sitemap"].format(version=getattr(args, "version", ""), guide=getattr(args, "guide", ""),
                                  part=getattr(args, "part", "software") or "software")
    xml = fetch(smap) or ""
    urls = [html.unescape(u) for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)]
    if prof.get("prefix"):
        pre = prof["prefix"].format(guide=args.guide)
        urls = [u for u in urls if u.startswith(pre)]
    urls = [u.split("#")[0] for u in urls if u.endswith(".html")]
    rp = urllib.robotparser.RobotFileParser()
    pr = urllib.parse.urlparse(smap)
    rp.parse((fetch(f"{pr.scheme}://{pr.netloc}/robots.txt") or "").splitlines())
    urls = [u for u in dict.fromkeys(urls) if rp.can_fetch(UA, u)]
    mpath, spath = os.path.join(out, "manifest.json"), os.path.join(out, ".crawl.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    state = json.load(open(spath)) if os.path.exists(spath) else {}      # url -> "breadcrumb > title" of every topic seen
    inc = re.compile(args.include, re.I) if args.include else None
    exc = re.compile(args.exclude, re.I) if args.exclude else None

    like = {}                                          # --like: another version's .crawl.json, by file name
    if args.like:
        for lu, lw in json.load(open(os.path.join(args.like, ".crawl.json"))).items():
            like[lu.rsplit("/", 1)[-1]] = lw
    def wanted(where, url):
        hay = where + " " + url
        return (not inc or inc.search(hay)) and not (exc and exc.search(hay))

    def keep(where, url):                              # a topic --like kept is kept here too, wherever this version moved it
        base = url.rsplit("/", 1)[-1]
        return wanted(where, url) or (base in like and wanted(like[base], url) and not (exc and exc.search(where)))

    todo = []
    for u in urls:
        name = re.sub(r"[^\w.-]+", "_", urllib.parse.urlparse(u).path.rsplit("/", 1)[-1])
        if name in manifest and not args.refresh:
            continue
        base = u.rsplit("/", 1)[-1]
        if u in state and not args.refresh and not keep(state[u], u):
            continue
        if base in like and u not in state and not wanted(like[base], u):   # the same topic in the other version was dropped
            continue
        todo.append((u, name))
    print(f"{site} {product}: {len(urls)} topics in the sitemap, {len(manifest)} saved, {len(todo)} to check", flush=True)
    lock, kept, skipped, failed = threading.Lock(), [0], [0], [0]

    def one(item):
        u, name = item
        page = fetch(u)
        if not page:
            with lock:
                failed[0] += 1
            return
        title, crumbs, art = prof["parse"](page)
        where = " > ".join(crumbs + [title])
        with lock:
            state[u] = where
        if not keep(where, u) or not art.strip():
            with lock:
                skipped[0] += 1
                progress()
            return
        body = clean_article(art)
        doc = (f"<html><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title></head><body>\n"
               f"<p>{html.escape(' > '.join(crumbs))}</p>\n<h1>{html.escape(title)}</h1>\n{body}\n"
               f"<p>Source: {html.escape(u)}</p></body></html>\n")
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(doc)
        with lock:
            manifest[name] = {"url": u, "title": title}
            kept[0] += 1
            progress()

    def progress():                                    # under the lock
        n = kept[0] + skipped[0]
        if n % 250 == 0:
            print(f"  {n}/{len(todo)}  kept {kept[0]}", flush=True)
            json.dump(manifest, open(mpath, "w"), indent=0)
            json.dump(state, open(spath, "w"), indent=0)

    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(one, todo))
    if args.prune:                                     # topics the filter no longer wants
        for name in [n for n, m in manifest.items() if m["url"] in state and not keep(state[m["url"]], m["url"])]:
            try:
                os.remove(os.path.join(out, name))
            except OSError:
                pass
            manifest.pop(name)
    json.dump(manifest, open(mpath, "w"), indent=0)
    json.dump(state, open(spath, "w"), indent=0)
    print(f"{site} {product}: kept {kept[0]} new, filtered out {skipped[0]}, failed {failed[0]}; {len(manifest)} topics in {out}",
          flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site", nargs="?", choices=sorted(SITES) + ["redhat"])
    ap.add_argument("--product", default="", help="the library product name (redhat: oadp-1.5 ...)")
    ap.add_argument("--version", default="", help="commvault: 11.40, 2024e (= 11.36), 11.42 ...")
    ap.add_argument("--guide", default="", help="veeam: vbr/userguide, one/userguide, agentforlinux/userguide ...")
    ap.add_argument("--file", default="", help="redhat: the guide's html-single page, already downloaded")
    ap.add_argument("--part", default="software", help="commvault: software (Command Center docs) or commcell-console")
    ap.add_argument("--like", default="", help="a folder of another version already crawled: topics its filter dropped are "
                    "not fetched again (same file name)")
    ap.add_argument("--include", default="")
    ap.add_argument("--exclude", default="")
    ap.add_argument("--dest", default="work/docs")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--prune", action="store_true", help="delete saved topics the filter no longer keeps")
    ap.add_argument("--list", help="a file of lines: <site> <version or guide> [include=RE] [exclude=RE]")
    a = ap.parse_args()
    if a.list:
        for line in open(a.list, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            sub = argparse.Namespace(**vars(a))
            sub.site, sub.include, sub.exclude, sub.product, sub.like = parts[0], a.include, a.exclude, "", ""
            sub.version = sub.guide = parts[1]
            for p in parts[2:]:
                k, _, v = p.partition("=")
                if k in ("include", "exclude", "product", "part", "like"):
                    setattr(sub, k, os.path.expandvars(v))
            crawl(sub.site, sub)
        return
    if not a.site:
        sys.exit("a site (commvault, veeam) or --list")
    crawl(a.site, a)


if __name__ == "__main__":
    main()
