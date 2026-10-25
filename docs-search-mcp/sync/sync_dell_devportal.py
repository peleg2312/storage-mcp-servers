#!/usr/bin/env python3
"""Dell developer portal (developer.dell.com, public API documentation) -> work/docs/dell/<product>/<version>/.

The portal is a JavaScript app; its two public services give the table of contents and each page's HTML:
  GET  /dev-portal-es-api-svc/apis/v1/<api>/versions/<version>/docs?fileType=toc
  POST /api-docs-svc/api/<api>/version/<version>   body {"slug": "<page uri>"}
Guide pages (Markdown) are taken for every listed version, API operations (HTTP endpoints) only for the
versions given with --endpoints (each operation page already shows its parameters, responses and errors,
so the separate data-schema pages are skipped). Resumable: pages already saved are not fetched again.

    python3 sync/sync_dell_devportal.py --dest work/docs                      # PowerFlex (API 4008)
    python3 sync/sync_dell_devportal.py --api 4008 --product powerflex-api --endpoints 5.1.0,4.5.5-Manager_v4-8-0
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request

BASE = "https://developer.dell.com"
UA = {"User-Agent": "Mozilla/5.0 (storage-mcp-servers docs sync)", "Content-Type": "application/json"}


def get(url, data=None, tries=4):
    """The portal answers 502 / 503 under load: retried with a growing pause."""
    for n in range(tries):
        req = urllib.request.Request(url, data=data, headers=UA, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code < 500 or n == tries - 1:
                raise
            time.sleep(10 * (n + 1))


def pages(toc, with_endpoints):
    """(type, title, uri, section path) for every Markdown page (and HTTP endpoint) in the table of contents."""
    out = []

    def walk(items, path):
        for x in items or []:
            if not isinstance(x, dict):                          # some versions list plain strings: no page
                continue
            t, title = x.get("type"), x.get("title") or ""
            if t == "MARKDOWN" or (t == "HTTP_ENDPOINT" and with_endpoints):
                out.append((t, title, x.get("uri"), " > ".join(path)))
            if t in ("DIVIDER", "FOLDER", "MODULE"):             # data-schema folders: skipped (shown on each operation)
                walk(x.get("children"), path + [title])
    walk(toc, [])
    return [p for p in out if p[2]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="work/docs")
    ap.add_argument("--api", default="4008")
    ap.add_argument("--product", default="powerflex-api")
    ap.add_argument("--endpoints", default="5.1.0,4.5.5-Manager_v4-8-0", help="versions whose API operations are kept")
    ap.add_argument("--versions", default="", help="limit to these versions (default: every listed version)")
    ap.add_argument("--delay", type=float, default=0.3)
    a = ap.parse_args()
    first = json.loads(get(f"{BASE}/dev-portal-es-api-svc/apis/v1/{a.api}/versions/5.1.0/docs?fileType=toc"))
    versions = a.versions.split(",") if a.versions else first["accessibleVersions"]
    endpoint_versions = set(a.endpoints.split(","))
    for v in versions:
        meta = json.loads(get(f"{BASE}/dev-portal-es-api-svc/apis/v1/{a.api}/versions/{v}/docs?fileType=toc"))
        todo = pages(json.loads(meta["toc"]), v in endpoint_versions)
        d = os.path.join(a.dest, "dell", a.product, v)
        os.makedirs(d, exist_ok=True)
        mf = os.path.join(d, "manifest.json")
        man = json.load(open(mf)) if os.path.exists(mf) else {}
        new = 0
        for kind, title, uri, section in todo:
            name = re.sub(r"[^\w\-]+", "-", uri.strip("/"))[:120] + ".html"
            if name in man:
                continue
            try:
                body = json.loads(get(f"{BASE}/api-docs-svc/api/{a.api}/version/{v}", json.dumps({"slug": uri}).encode()))
            except Exception as e:
                print(f"failed {v}{uri}: {e}")
                continue
            if not body.get("success"):
                continue
            label = f"{meta.get('apiName', 'API')} {v}: {title}"
            html = (f"<html><head><title>{label}</title></head><body><p>{section}</p>{body['data']}</body></html>")
            open(os.path.join(d, name), "w", encoding="utf-8").write(html)
            man[name] = {"url": f"{BASE}/apis/{a.api}/versions/{v}{uri}", "title": label}
            new += 1
            if new % 100 == 0:
                json.dump(man, open(mf, "w"), indent=0)
                print(f"... {v}: {new} new pages")
            time.sleep(a.delay)
        json.dump(man, open(mf, "w"), indent=0)
        print(f"{a.product} {v}: {len(todo)} pages listed, {new} new, {len(man)} saved -> {d}")


if __name__ == "__main__":
    main()
