#!/usr/bin/env python3
"""Add "first release with this fix" to the exported pull requests (sync_github_issues.py "prs" lines).

    python3 sync/pr_releases.py --dest work/docs

For each "prs" repository: a blobless bare clone (work/cache/git/<owner>__<repo>.git, history and tags only,
no file contents), the PR number of every commit from its subject ("... (#123)" squash merges, "Merge pull
request #123"), then the release tags in version order: the first tag whose history holds the commit is the
first release with the fix. Each <dest>/<vendor>/<product>/pr-<n>.md gets a line
    - First release: v2.14.0   (or: not in a release tag yet)
Idempotent. Needs git; standard library only.
"""
import argparse
import os
import re
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PR_SUBJECT = re.compile(r"\(#(\d+)\)\s*$|^Merge pull request #(\d+)")
LINE = re.compile(r"^- First release: .*\n", re.M)


def git(d, *args):
    return subprocess.run(["git", "-C", d, *args], check=True, capture_output=True, text=True).stdout


def first_releases(repo, cache):
    d = os.path.join(cache, repo.replace("/", "__") + ".git")
    if os.path.isdir(d):
        git(d, "fetch", "-q", "--tags", "--force", "origin", "+refs/heads/*:refs/heads/*")
    else:
        os.makedirs(cache, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none", f"https://github.com/{repo}.git", d],
                       check=True)
    pr_of = {}
    for line in git(d, "log", "--all", "--format=%H %s").splitlines():
        sha, _, subject = line.partition(" ")
        m = PR_SUBJECT.search(subject)
        if m:
            pr_of.setdefault(sha, int(m.group(1) or m.group(2)))
    first, seen = {}, set()
    for tag in git(d, "tag", "--sort=v:refname").split():
        if not re.match(r"^v?\d+(\.\d+)*$", tag):                 # releases only (no -rc, nightly ...)
            continue
        for sha in git(d, "rev-list", tag).split():
            if sha in seen:
                continue
            seen.add(sha)
            if sha in pr_of:
                first.setdefault(pr_of[sha], tag)
    return first, set(pr_of.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.path.join(HERE, "work", "docs"))
    ap.add_argument("--sources", default=os.path.join(HERE, "sources", "github-issues.txt"))
    ap.add_argument("--cache", default=os.path.join(HERE, "work", "cache", "git"))
    a = ap.parse_args()
    for line in open(a.sources):
        f = line.split("#", 1)[0].split()
        if len(f) < 4 or f[3] != "prs":
            continue
        vendor, product, repo = f[:3]
        d = os.path.join(a.dest, vendor, product)
        if not os.path.isdir(d):
            continue
        try:
            first, merged = first_releases(repo, a.cache)
        except subprocess.CalledProcessError as e:
            print(f"{repo}: git failed: {(e.stderr or '').strip()[:200]}")
            continue
        n = 0
        for name in os.listdir(d):
            m = re.match(r"pr-(\d+)\.md$", name)
            if not m:
                continue
            p = os.path.join(d, name)
            text = LINE.sub("", open(p, encoding="utf-8").read())
            num = int(m.group(1))
            if "- Pull request: merged" not in text:
                continue
            rel = first.get(num) or ("not in a release tag yet" if num in merged else "unknown (merge commit not found)")
            text = re.sub(r"^(- Pull request: merged.*\n)", lambda x: x.group(1) + f"- First release: {rel}\n", text,
                          count=1, flags=re.M)
            open(p, "w", encoding="utf-8").write(text)
            n += num in first
        print(f"{repo}: {len(first)} PRs mapped to a release tag, {n} files annotated -> {d}")


if __name__ == "__main__":
    main()
