#!/usr/bin/env python3
"""
Export Dell Knowledge Base articles (errors, bugs, how-tos) for PowerMax, PowerFlex, CSM / CSI and
related products into the library, for offline search.

    python3 sync/sync_dell_kb.py [--dest /data/docs] [--products powermax scaleio ...] [--delay 3]
                                 [--ids-file extra-ids.txt] [--list]

Dell has no sitemap or export for its KB. This script finds the articles two ways and fetches each one:
 1. the per-product listings on the support site,
      https://www.dell.com/support/product-details/en-us/product/<product>/resources/articles
    (every page of the listing; article numbers are taken from the HTML and from any JSON inside it),
 2. article numbers you add yourself (--ids-file, one 9-digit number or kbdoc URL per line) and the
    seed list below (collected from web searches).
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
    ap.add_argument("--no-listings", action="store_true", help="skip the product listings (seed + ids-file only)")
    a = ap.parse_args()
    work = os.path.join(here, "work")
    os.makedirs(work, exist_ok=True)

    ids = set(SEED_IDS)
    if a.ids_file:
        for line in open(a.ids_file, encoding="utf-8"):
            m = re.search(r"(\d{9})", line)
            if m:
                ids.add(m.group(1))
    if not a.no_listings:
        for product in a.products:
            ids |= harvest(product, a.delay, work)
            time.sleep(a.delay)
    urls = [f"https://www.dell.com/support/kbdoc/en-us/{i}" for i in sorted(ids)]
    list_path = os.path.join(work, "dell-kb-urls.txt")
    open(list_path, "w").write("\n".join(urls) + "\n")
    print(f"{len(urls)} Dell KB articles to fetch (list saved to {list_path})")
    if a.list:
        return 0

    # fetch through sync_web's machinery (manifest, login/empty detection, incremental)
    sys.argv = ["sync_web.py", "--dest", a.dest, "--urls", list_path, "--sources", os.devnull, "--delay", str(a.delay)]
    return sync_web.main()


if __name__ == "__main__":
    sys.exit(main())
