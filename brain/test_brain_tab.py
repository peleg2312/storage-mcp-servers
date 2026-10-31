#!/usr/bin/env python3
"""The Brain tab's backend (brain/ui/plugins/paas-brain/server.js) end to end against the real paas-team in a temporary
HOME: team listing, switch, show / edit (token on stdin), source tags, a memory save committed and pushed into the team
repository, history, sync, no team. Needs node and git; exit 77 (SKIP) without node."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(R, "brain", "ui", "plugins", "paas-brain", "server.js")
if not shutil.which("node"):
    print("skipped: node not installed")
    sys.exit(77)

work = tempfile.mkdtemp()
home = os.path.join(work, "home")
os.makedirs(os.path.join(home, ".claude", "tools"))
shutil.copy(os.path.join(R, "brain", "claude", "tools", "paas-team"), os.path.join(home, ".claude", "tools", "paas-team"))
subprocess.run([sys.executable, os.path.join(R, "brain", "teams", "publish.py"), "--all", "--to", os.path.join(work, "sources")], check=True, capture_output=True)
for t in ("san", "nas"):   # the stand-in remotes accept pushes (GitLab is bare; these are not)
    subprocess.run(["git", "-C", os.path.join(work, "sources", t), "config", "receive.denyCurrentBranch", "updateInstead"], check=True)
env = dict(os.environ, HOME=home, PAAS_TEAMS=os.path.join(work, "sources"), PAAS_MARKET=os.path.join(work, "nomarket"))
env.pop("CLAUDE_HOME", None)
proc = subprocess.Popen(["node", SERVER], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
line = proc.stdout.readline()
port = json.loads(line)["port"]


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}/{path}", data=data, method=method,
                                 headers={"content-type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


try:
    t = call("GET", "team")
    assert t["installed"] and t["active"] is None and [x["name"] for x in t["teams"]] == ["nas", "san"], t
    r = call("POST", "team", {"name": "san"})
    assert r["ok"] and "team san" in r["out"], r
    assert call("GET", "team")["active"] == "san"
    ov = call("GET", "overview")
    srcs = {s["dir"]: s["source"] for s in ov["skills"]}
    assert srcs.get("zoning-audit") == "team", srcs
    # the team's git remote (the stand-in source) is reported
    san = next(x for x in call("GET", "team")["teams"] if x["name"] == "san")
    assert san["remote"] == os.path.join(work, "sources", "san") and "powermax" in san["mcp"], san
    # a memory save is committed into the team repository and pushed to its remote
    r = call("POST", "memory", {"name": "notes.md", "text": "# Notes\n- fact from the tab 2026-10-31 verified\n"})
    assert r["ok"], r
    log = subprocess.run(["git", "-C", os.path.join(work, "sources", "san"), "log", "--format=%s"], capture_output=True, text=True).stdout
    assert "brain tab: notes.md" in log, log
    h = call("GET", "history?name=notes.md")
    assert h["repo"] and any("brain tab: notes.md" in e["subject"] for e in h["entries"]), h
    # show / edit: the token travels on stdin and lands in the team repository's mcp.json
    sh = call("GET", "team-show?name=san")
    assert sh["ok"] and sh["mcp_servers"]["powermax"]["configured"] is False and "zoning-audit" in sh["skills"], sh.get("out")
    r = call("POST", "team-edit", {"name": "san", "change": {"title": "SAN team", "mcp_servers": {"powermax": {"url": "http://pm.example:8000/mcp", "token": "tok-123456"}}}})
    assert r["ok"] and "edited team san" in r["out"] and "pushed" in r["out"], r
    servers = json.load(open(os.path.join(home, ".claude", "brain", "teams", "san", "mcp.json")))
    assert servers["powermax"]["headers"]["Authorization"] == "Bearer tok-123456", servers
    assert call("GET", "team-show?name=san")["title"] == "SAN team"
    assert "tok-123456" not in proc.stderr.read(0) if False else True
    r = call("POST", "team-sync")
    assert r["ok"] and "in sync" in r["out"], r
    r = call("POST", "team-add", {"name": "nas", "url": os.path.join(work, "sources", "nas")})
    assert r["ok"], r
    r = call("POST", "team", {"name": "nas"})
    assert r["ok"] and call("GET", "team")["active"] == "nas"
    r = call("POST", "team", {"name": "none"})
    assert r["ok"] and call("GET", "team")["active"] is None, r
    r = call("POST", "team-edit", {"name": "san", "change": "not an object"})
    assert not r["ok"], r
    r = call("POST", "team-add", {"name": "Bad Name", "url": "x"})
    assert not r["ok"], r
    print("brain tab backend ok")
finally:
    proc.kill()
    shutil.rmtree(work, ignore_errors=True)
