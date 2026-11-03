#!/usr/bin/env python3
"""A server renamed in the brain (ucsc -> ucs-central) keeps what people set up: the team repository's filled-in entry and
root's Market item move to the new name with their address and token, the team's notes and tool map stay byte for byte,
the agents accept both names, the read-only guard treats both as the in-house server. Standard library and git."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
work = tempfile.mkdtemp()
digest = lambda *ps: hashlib.sha1(b"".join(open(p, "rb").read() for p in ps)).hexdigest()
try:
    team = os.path.join(work, "san")
    publish = [sys.executable, os.path.join(R, "brain", "teams", "publish.py"), "san", "--to", team]
    subprocess.run(publish, check=True, capture_output=True)
    m = json.load(open(os.path.join(team, "mcp.json")))
    m.pop("ucs-central", None)                         # as published before the rename, with the address filled in
    m["ucsc"] = {"type": "http", "url": "http://ucs.example:8000/mcp", "headers": {"Authorization": "Bearer ucs-token-123456"}}
    json.dump(m, open(os.path.join(team, "mcp.json"), "w"), indent=2)
    k = os.path.join(team, "knowledge")
    open(os.path.join(k, "notes.md"), "a").write("- 2026-11-03 · UCS domain dc1 has 2 FIs · verified · ucs\n")
    open(os.path.join(k, "tool-map.md"), "a").write("\n<!-- a line the team wrote -->\n")
    subprocess.run(["git", "-C", team, "add", "-A"], check=True)
    subprocess.run(["git", "-C", team, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "filled"], check=True)
    before = digest(os.path.join(k, "notes.md"), os.path.join(k, "tool-map.md"))
    subprocess.run(publish, check=True, capture_output=True)
    m = json.load(open(os.path.join(team, "mcp.json")))
    assert "ucsc" not in m and m["ucs-central"]["url"] == "http://ucs.example:8000/mcp", m
    assert m["ucs-central"]["headers"]["Authorization"] == "Bearer ucs-token-123456"
    plug = json.load(open(os.path.join(team, "paas-brain-san", ".mcp.json")))["mcpServers"]
    assert "ucs-central" in plug and "ucsc" not in plug, plug
    assert digest(os.path.join(k, "notes.md"), os.path.join(k, "tool-map.md")) == before, "team knowledge must not change"
    agent = open(os.path.join(team, "paas-brain-san", "agents", "fabric-investigator.md")).read()
    assert "mcp__plugin_paas-brain-san_ucs-central__*" in agent and "mcp__ucsc__*" in agent, agent[:300]
    print("team repository rename ok")

    market = os.path.join(work, "market")
    os.makedirs(os.path.join(market, "items", "mcp"))
    json.dump({"description": "UCS", "token": "shared", "server": {"type": "http", "url": "http://ucs.example:8000/mcp"}},
              open(os.path.join(market, "items", "mcp", "ucsc.json"), "w"))
    subprocess.run([sys.executable, os.path.join(R, "brain", "marketplace", "paas_market.py"), "publish", os.path.join(R, "brain", "claude"),
                    "--mcp", os.path.join(R, "brain", "marketplace", "mcp.json")], env=dict(os.environ, PAAS_MARKET=market),
                   check=True, capture_output=True)
    items = os.listdir(os.path.join(market, "items", "mcp"))
    assert "ucsc.json" not in items and "ucs-central.json" in items, items
    assert json.load(open(os.path.join(market, "items", "mcp", "ucs-central.json")))["server"]["url"] == "http://ucs.example:8000/mcp"
    print("market rename ok")

    g = [sys.executable, os.path.join(R, "brain", "claude", "hooks", "block-write-tools.py")]
    for name in ("mcp__ucs-central__list_centrals", "mcp__ucsc__list_centrals", "mcp__ucs-central__query_class"):
        r = subprocess.run(g, input=json.dumps({"tool_name": name, "tool_input": {}}), capture_output=True, text=True)
        assert r.returncode == 0 and not r.stdout.strip(), (name, r.stdout, r.stderr)
    print("renames ok")
finally:
    shutil.rmtree(work, ignore_errors=True)
