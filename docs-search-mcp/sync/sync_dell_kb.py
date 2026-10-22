#!/usr/bin/env python3
"""
Export Dell Knowledge Base articles (errors, bugs, how-tos) for PowerMax, PowerFlex, CSM / CSI and
related products into the library, for offline search.

    python3 sync/sync_dell_kb.py [--dest /data/docs] [--products powermax scaleio ...] [--delay 3]
                                 [--ids-file extra-ids.txt] [--list]

Dell has no sitemap or export for its KB. This script starts from known article numbers (the seed list
below, collected from web searches, plus --ids-file: one 9-digit number or kbdoc URL per line) and
SNOWBALLS: every Dell KB article links to related articles; each linked article that concerns the
PowerMax / PowerFlex / Solutions Enabler / Unisphere / SRDF / PowerPath / CSM-CSI family is fetched too,
and its links followed, until nothing new is found. (--listings additionally tries the support site's
per-product article listings, but those pages are JavaScript shells for most products.)
Each article is saved as <dest>/dell/kb/<id>_<slug>.html with manifest.json (title + URL) via the same
code as sync_web.py, so the indexer links hits to the kbdoc URL. Incremental: known articles are skipped.
Polite: one request at a time, --delay seconds apart. Dell's site refuses cloud / datacenter IPs
(Akamai "Access Denied"): run this from an office or home PC.
Standard library only.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_web  # noqa: E402

UA = sync_web.UA
LISTING = "https://www.dell.com/support/product-details/en-us/product/{product}/resources/articles"
# product slugs of the support site (the part after /product/ in the product's support URL)
DEFAULT_PRODUCTS = [
    "powermax", "powermax-os-10", "powermax-2500", "powermax-8500", "powermax-2000", "powermax-8000",
    "unisphere-for-powermax", "solutions-enabler", "srdfasynchronous", "srdf-metro", "powerpath",
    "scaleio",                                   # PowerFlex software (the site still uses the old slug)
    "powerflex-appliance", "powerflex-rack", "powerflex-custom-node", "powerflex-manager",
    "dell-container-storage-modules", "csi-drivers-for-powermax", "csi-drivers-for-powerflex",
    "vmax-250f", "vmax-950f", "vmax-all-flash",
]
# KB numbers already known to matter (from web searches, Oct 2026); the listings add the rest
SEED_IDS = """
000189115 000207989 000124257 000191486 000211967 000297022 000021788 000175073 000193693 000200466
000217800 000491367 000168740 000281255 000170807 000203026 000187271 000191962 000195144 000123384
000183520 000326420 000207080 000192878 000223383 000014042 000228795 000258197 000203060 000049294
000082203 000058331 000486788 000325262 000251292 000446482 000205794 000220860 000184617 000210360
000217820 000220627 000204833 000228219 000204697 000264404 000437810
000024577 000186018 000359526 000205512 000225181 000008488 000222114 000199917 000370801 000184704
000373677 000070786 000209777 000021638 000211832 000216718 000032739 000197487 000199106 000219120
000065593 000213161 000226160 000256801 000227818 000035374 000444629 000210943 000261389 000185734
000417124 000421825 000227849 000266253 000308670 000273261 000415896 000229064 000255840 000291125
000466913 000059388 000056877 000062991 000170270 000066341 000222640 000223773 000132371 000184098
000122457 000234329 000030226
000373328 000387366 000025301 000249601 000215508 000195947 000052840 000194607 000225511 000196837
000435259 000233376 000321628 000321705 000348141 000446474 000340894 000350685 000194824 000213270
000462918 000221806 000365831 000365825 000171816 000027185 000207227 000193832 000051959 000211289
000013914 000007990 000222294 000208281 000106211 000374126 000203646 000181515 000296065 000188229
000222165 000467149 000200975 000402262 000184565 000180923 000189606 000153804 000181200 000194640
000153790 000199943 000222640 000223773 000132371
000249350 000213016 000381561 000498657 000362228 000372260 000181277 000315113 000315070 000242214
000455911 000052096 000047656 000308007 000226398 000275691 000194030 000224263 000204042 000204041
000228793 000221576 000205090 000022528 000434761 000302961 000201919 000021638 000210943 000261389
""".split()
ID_RE = re.compile(r"kbdoc/(?:[a-z]{2}-[a-z]{2}/)?(\d{9})|\"(?:articleId|ArticleId|kbId|id)\"\s*:\s*\"?(\d{9})", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json,*/*"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read(), r.geturl()


def ids_in(body):
    return {a or b for a, b in ID_RE.findall(body.decode("utf-8", "replace"))}


def harvest(product, delay, dump_dir):
    """All article ids of one product listing (follows ?page=N while new ids keep appearing)."""
    found, page, misses = set(), 1, 0
    while page <= 200:
        url = LISTING.format(product=product) + (f"?page={page}" if page > 1 else "")
        try:
            body, final = fetch(url)
        except urllib.error.HTTPError as e:
            print(f"{product}: listing page {page}: HTTP {e.code}" + (" (access denied: not from a cloud IP?)" if e.code == 403 else ""))
            break
        except (urllib.error.URLError, OSError) as e:
            print(f"{product}: listing page {page}: {e}")
            break
        if dump_dir and page == 1:
            open(os.path.join(dump_dir, f"dell-kb-listing-{product}.html"), "wb").write(body)
        new = ids_in(body) - found
        if page == 1 and not new:
            title = sync_web.title_of(body)
            print(f"{product}: no article numbers on {final} (title: {title[:70]!r}); "
                  f"listing saved to {dump_dir or 'nowhere'} - send it to the maintainer to adapt the parser")
            break
        found |= new
        print(f"{product}: page {page}: {len(new)} new, {len(found)} total")
        if not new:
            misses += 1
            if misses >= 1:
                break
        page += 1
        time.sleep(delay)
    return found


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", default=os.getenv("DOCS_DIR", "/data/docs"))
    ap.add_argument("--products", nargs="*", default=DEFAULT_PRODUCTS, help="support-site product slugs")
    ap.add_argument("--ids-file", help="extra article numbers / kbdoc URLs, one per line")
    ap.add_argument("--delay", type=float, default=float(os.getenv("DOCS_SYNC_DELAY", "3")))
    ap.add_argument("--list", action="store_true", help="only harvest and print the article URLs")
    ap.add_argument("--listings", action="store_true",
                    help="also try the support-site product listings (usually JavaScript shells; off by default)")
    ap.add_argument("--max-articles", type=int, default=0, help="stop after N saved articles (0 = all)")
    a = ap.parse_args()
    work = os.path.join(here, "work")
    os.makedirs(work, exist_ok=True)

    ids = set(SEED_IDS)
    if a.ids_file:
        for line in open(a.ids_file, encoding="utf-8"):
            m = re.search(r"(\d{9})", line)
            if m:
                ids.add(m.group(1))
    if a.listings:
        for product in a.products:
            ids |= harvest(product, a.delay, work)
            time.sleep(a.delay)
    list_path = os.path.join(work, "dell-kb-urls.txt")
    print(f"{len(ids)} Dell KB articles to start from; related articles found inside them are followed "
          f"(snowball) while they concern {', '.join(FAMILY[:6])}...")
    if a.list:
        open(list_path, "w").write("\n".join(f"https://www.dell.com/support/kbdoc/en-us/{i}" for i in sorted(ids)) + "\n")
        print(f"list saved to {list_path}")
        return 0
    return crawl(ids, a.dest, a.delay, a.max_articles)


FAMILY = ["PowerMax", "VMAX", "PowerFlex", "VxFlex", "ScaleIO", "Solutions Enabler", "Unisphere", "SRDF",
          "SnapVX", "TimeFinder", "PowerPath", "Container Storage Modules", "CSI", "CSM", "PowerMaxOS", "SYMCLI"]
FAMILY_RE = re.compile("|".join(re.escape(f) for f in FAMILY), re.I)


def crawl(seed_ids, dest, delay, max_articles):
    """Fetch every article; queue the kbdoc numbers linked inside an article that belongs to the family."""
    d = os.path.join(dest, "dell", "kb")
    os.makedirs(d, exist_ok=True)
    mf = os.path.join(d, "manifest.json")
    man = json.load(open(mf)) if os.path.exists(mf) else {}
    known_ids = {re.search(r"(\d{9})", v.get("url", "")).group(1) for v in man.values() if re.search(r"(\d{9})", v.get("url", ""))}
    queue, seen = list(sorted(seed_ids)), set(seed_ids)
    stats = {"saved": 0, "skipped": 0, "off_family": 0, "login_or_empty": 0, "failed": 0, "queued_from_links": 0}
    t0 = time.time()

    def flush():
        tmp = mf + ".tmp"
        json.dump(man, open(tmp, "w"), indent=1)
        os.replace(tmp, mf)

    try:
        while queue:
            kb = queue.pop(0)
            url = f"https://www.dell.com/support/kbdoc/en-us/{kb}"
            if kb in known_ids:
                stats["skipped"] += 1
                continue
            try:
                body, ctype, final = sync_web.fetch(url)
            except urllib.error.HTTPError as e:
                stats["failed"] += 1
                print(f"failed {e.code}: {url}" + (" (Dell refuses this client; try DOCS_SYNC_USER_AGENT=<your browser's UA>)" if e.code == 403 else ""))
                if e.code in (429, 503):
                    time.sleep(60)
                time.sleep(delay)
                continue
            except (urllib.error.URLError, OSError) as e:
                stats["failed"] += 1
                print(f"failed: {url}: {e}")
                time.sleep(delay)
                continue
            text = body.decode("utf-8", "replace")
            if sync_web.LOGIN_HINTS.search(text[:200000]) or sync_web.text_len(body) < 500:
                stats["login_or_empty"] += 1
                print(f"empty / login page: {url}")
                time.sleep(delay)
                continue
            title = sync_web.title_of(body)
            head = text[:300000]
            in_family = bool(FAMILY_RE.search(title)) or bool(FAMILY_RE.search(head))
            if not in_family and kb not in seed_ids:
                stats["off_family"] += 1
                time.sleep(delay)
                continue
            name = sync_web.file_name(final, False)
            with open(os.path.join(d, name), "wb") as f:
                f.write(body)
            man[name] = {"url": url, "title": title}
            known_ids.add(kb)
            stats["saved"] += 1
            # related / linked articles -> queue (only from family articles)
            linked = {i for i in ids_in(body) if i not in seen}
            for i in sorted(linked):
                seen.add(i)
                queue.append(i)
            stats["queued_from_links"] += len(linked)
            if stats["saved"] % 10 == 0:
                flush()
                print(f"... {stats['saved']} saved, {len(queue)} queued ({stats['saved'] / max(1, time.time() - t0) * 3600:.0f}/h)", flush=True)
            if max_articles and stats["saved"] >= max_articles:
                break
            time.sleep(delay)
    except KeyboardInterrupt:
        print("stopped; progress is saved, re-run to continue")
    finally:
        flush()
    print("dell kb:", json.dumps(stats), f"-> {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
