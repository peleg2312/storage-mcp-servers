"""
Export public GitHub issue trackers (bug reports, fixes, workarounds) for offline search.

    GITHUB_TOKEN=... python sync/sync_github_issues.py [--dest /data/docs] [--sources sources/github-issues.txt]

Each issue (open and closed, pull requests excluded) becomes <dest>/<vendor>/<product>/issue-<n>.md with
title, state, labels, dates, body and all comments, plus manifest.json (title + URL) for the indexer.
Incremental: re-runs fetch only issues updated since the last run (.issues-state.json).
A GITHUB_TOKEN (any read-only token) is strongly recommended: without it GitHub allows 60 requests/hour.
Standard library only.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"


def gh(url, token):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "docs-search-mcp-issue-export",
                                               **({"Authorization": f"Bearer {token}"} if token else {})})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                remaining = int(r.headers.get("X-RateLimit-Remaining", "1"))
                reset = int(r.headers.get("X-RateLimit-Reset", "0"))
                data = json.loads(r.read() or b"null")
                link = r.headers.get("Link", "")
            if remaining == 0 and reset:
                wait = max(0, reset - time.time()) + 2
                print(f"rate limit reached, sleeping {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
            nxt = None
            for part in link.split(","):
                if 'rel="next"' in part:
                    nxt = part[part.index("<") + 1:part.index(">")]
            return data, nxt
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < 4:
                time.sleep(60 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"giving up on {url}")


def render(issue, comments):
    labels = ", ".join(lb["name"] for lb in issue.get("labels", [])) or "-"
    out = [f"# #{issue['number']} {issue['title']}", "",
           f"- State: {issue['state']}{' (' + issue['state_reason'] + ')' if issue.get('state_reason') else ''}",
           f"- Labels: {labels}",
           f"- Opened: {issue['created_at'][:10]} by {issue['user']['login']}",
           f"- Updated: {issue['updated_at'][:10]}" + (f" | Closed: {issue['closed_at'][:10]}" if issue.get("closed_at") else ""),
           f"- URL: {issue['html_url']}", "", "## Description", "", (issue.get("body") or "(no description)").strip()]
    if comments:
        out += ["", "## Comments"]
        for c in comments:
            out += ["", f"### {c['user']['login']} - {c['created_at'][:10]}", "", (c.get("body") or "").strip()]
    return "\n".join(out) + "\n"


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.getenv("DOCS_DIR", "/data/docs"))
    ap.add_argument("--sources", default=os.path.join(here, "sources", "github-issues.txt"))
    ap.add_argument("--max-issues", type=int, default=0, help="limit per repo (testing)")
    a = ap.parse_args()
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        print("warning: no GITHUB_TOKEN - only 60 requests/hour; large trackers will take many hours", file=sys.stderr)
    for line in open(a.sources):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        vendor, product, repo = line.split()[:3]
        d = os.path.join(a.dest, vendor, product)
        os.makedirs(d, exist_ok=True)
        state_f, man_f = os.path.join(d, ".issues-state.json"), os.path.join(d, "manifest.json")
        state = json.load(open(state_f)) if os.path.exists(state_f) else {}
        manifest = json.load(open(man_f)) if os.path.exists(man_f) else {}
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        url = f"{API}/repos/{repo}/issues?state=all&per_page=100&sort=updated&direction=asc"
        if state.get("since"):
            url += f"&since={state['since']}"
        n = 0
        while url:
            items, url = gh(url, token)
            for it in items or []:
                if "pull_request" in it:
                    continue
                comments = []
                if it.get("comments"):
                    curl = it["comments_url"] + "?per_page=100"
                    while curl:
                        page, curl = gh(curl, token)
                        comments += page or []
                name = f"issue-{it['number']}.md"
                with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                    f.write(render(it, comments))
                manifest[name] = {"url": it["html_url"], "title": f"{repo}#{it['number']}: {it['title']}"}
                n += 1
                if a.max_issues and n >= a.max_issues:
                    url = None
                    break
        json.dump(manifest, open(man_f, "w"), indent=1)
        if not a.max_issues:
            json.dump({"since": started}, open(state_f, "w"))
        print(f"{repo}: {n} issues written/updated -> {d}")


if __name__ == "__main__":
    main()
