"""Offline test of sync_github_issues.py with a fake GitHub API."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync"))
import sync_github_issues as gi  # noqa: E402

API = "https://api.github.com"
U = {"login": "user1"}
ISSUES = [
    {"number": 101, "title": "trident-node: failed to stage volume, iscsiadm timeout", "state": "closed", "state_reason": "completed",
     "labels": [{"name": "bug"}, {"name": "tracked"}], "user": U, "created_at": "2025-01-02T00:00:00Z",
     "updated_at": "2025-02-01T00:00:00Z", "closed_at": "2025-02-01T00:00:00Z", "html_url": "https://github.com/NetApp/trident/issues/101",
     "body": "Pods stuck ContainerCreating. Error: failed to stage volume", "comments": 2,
     "comments_url": f"{API}/repos/NetApp/trident/issues/101/comments"},
    {"number": 102, "title": "PR: fix", "pull_request": {}, "state": "open"},
    {"number": 103, "title": "Question about ontap-san-economy", "state": "open", "labels": [], "user": U,
     "created_at": "2025-03-01T00:00:00Z", "updated_at": "2025-03-02T00:00:00Z", "closed_at": None,
     "html_url": "https://github.com/NetApp/trident/issues/103", "body": None, "comments": 0, "comments_url": "x"},
]
CALLS = []


def fake_gh(url, token):
    CALLS.append(url)
    if url.endswith("/comments?per_page=100"):
        return [{"user": U, "created_at": "2025-01-10T00:00:00Z", "body": "Fixed in 25.02 - workaround: restart iscsid"}], f"{url}&page=2"
    if "comments?per_page=100&page=2" in url:
        return [{"user": {"login": "netapp-dev"}, "created_at": "2025-01-11T00:00:00Z", "body": "Confirmed fixed."}], None
    if "page=2" in url:
        return [ISSUES[2]], None
    return ISSUES[:2], url + "&page=2"


gi.gh = fake_gh
d = tempfile.mkdtemp()
src = os.path.join(d, "s.txt")
open(src, "w").write("netapp trident-issues NetApp/trident\n")
sys.argv = ["x", "--dest", d, "--sources", src]
gi.main()
out = os.path.join(d, "netapp", "trident-issues")
files = sorted(f for f in os.listdir(out) if f.startswith("issue-"))
assert files == ["issue-101.md", "issue-103.md"], files
t = open(os.path.join(out, "issue-101.md")).read()
assert "- State: closed (completed)" in t and "Labels: bug, tracked" in t and "restart iscsid" in t and "Confirmed fixed." in t
m = json.load(open(os.path.join(out, "manifest.json")))
assert m["issue-101.md"]["url"] == "https://github.com/NetApp/trident/issues/101"
assert m["issue-101.md"]["title"].startswith("NetApp/trident#101:")
st = json.load(open(os.path.join(out, ".issues-state.json")))
CALLS.clear()
gi.main()
assert f"&since={st['since']}" in CALLS[0], CALLS[0]
print(open(os.path.join(out, "issue-101.md")).read()[:400])
print("ALL TESTS PASSED")
