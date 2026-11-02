#!/usr/bin/env python3
"""A team with its own docs library, end to end with a mock team "lab" (library "labdocs") next to the real SAN team:
paas-library builds the library; the docs service answers ?team=lab from it and never from the general library, ?team=san
from the general one; a library that is named but not built gives a clear error, no fallback; the lab plugin's docs-local
opens the team library, and without it never the general one; the docs hooks follow the active team's library; the
marketplace offers one docs-http-<team> item per team. Standard library and git only."""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(R, "docs-search-mcp")
sys.path.insert(0, DOCS)
import docs_index  # noqa: E402

work = tempfile.mkdtemp()
TOKEN = "lab-docs-token-for-tests"
GENERAL_WORD, LAB_WORD = "Zephyrgeneral", "Quokkavault"


def write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


def rpc(port, team, method, params=None):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp" + (f"?team={team}" if team else ""), data=body,
                                 headers={"Authorization": "Bearer " + TOKEN, "content-type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["result"]


def search(port, team, word):
    r = rpc(port, team, "tools/call", {"name": "search_docs", "arguments": {"query": word}})
    return r, ("" if r.get("isError") else r["content"][0]["text"])


def stdio(cmd, env, word):
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": word}}}]
    p = subprocess.run(cmd, input="".join(json.dumps(m) + "\n" for m in msgs), capture_output=True, text=True, env=env, timeout=120)
    lines = [json.loads(x) for x in p.stdout.splitlines() if x.startswith("{")]
    assert len(lines) == 2, (p.stdout[-400:], p.stderr[-400:])
    return lines[1]["result"]["content"][0]["text"]


try:
    # the general library: one document only it has
    write(os.path.join(work, "general", "docs", "acme", "general", "intro.md"), f"# General\n\n## Facts\nThe {GENERAL_WORD} switch is general.\n")
    docs_index.build(os.path.join(work, "general", "docs"), os.path.join(work, "general", "docs.db"), log=lambda *a: None)

    # mock team definitions: lab (own library) beside the real san
    defs = os.path.join(work, "defs")
    write(os.path.join(defs, "lab", "team.json"), json.dumps({
        "name": "lab", "title": "Lab", "description": "Mock team with its own library", "persona": "persona.md",
        "rules": "brain/claude/brain/storage.md", "environment": "brain/claude/brain/environment.md",
        "skills": ["docs-lookup"], "agents": ["Explore"], "mcp": ["docs-local", "docs-search"], "library": "labdocs"}))
    write(os.path.join(defs, "lab", "persona.md"), "\n## Who you work for\nThe lab team.\n")
    os.symlink(os.path.join(R, "brain", "teams", "san"), os.path.join(defs, "san"))
    env = dict(os.environ, PAAS_TEAM_DEFS=defs, PAAS_LIBRARIES=os.path.join(work, "libs"))

    # paas-library: documents in, index built, listed
    write(os.path.join(work, "incoming", "vault.md"), f"# Lab vault\n\n## Restore\nThe {LAB_WORD} restore runs nightly.\n")
    o = subprocess.run([sys.executable, os.path.join(R, "brain", "claude", "tools", "paas-library"), "add", "labdocs",
                        os.path.join(work, "incoming"), "--to", "lab/vault"], env=env, capture_output=True, text=True, timeout=120)
    assert o.returncode == 0 and "indexed 1 documents" in o.stdout, (o.stdout, o.stderr)
    assert "labdocs" in subprocess.run([sys.executable, os.path.join(R, "brain", "claude", "tools", "paas-library"), "list"],
                                       env=env, capture_output=True, text=True).stdout
    print("paas-library ok")

    # publish both teams: the lab plugin and repository carry the library name, san's do not
    teams = os.path.join(work, "teams")
    for t in ("lab", "san"):
        o = subprocess.run([sys.executable, os.path.join(R, "brain", "teams", "publish.py"), t, "--to", os.path.join(teams, t),
                            "--docs-search", "https://vm.example:8001/mcp"], env=env, capture_output=True, text=True, timeout=300)
        assert o.returncode == 0, (o.stdout[-600:], o.stderr[-600:])
    assert json.load(open(os.path.join(teams, "lab", "team.json")))["library"] == "labdocs"
    assert "library" not in json.load(open(os.path.join(teams, "san", "team.json")))
    lab_plug = os.path.join(teams, "lab", "paas-brain-lab")
    assert json.load(open(os.path.join(lab_plug, "team.json")))["library"] == "labdocs"
    assert "libraries/labdocs/docs.db" in open(os.path.join(lab_plug, "bin", "docs-local")).read()
    print("publish ok")

    # the docs service: lab from its own library only, san from the general one
    write(os.path.join(work, "token"), TOKEN)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, os.path.join(DOCS, "mcp_stdio.py"), "--db", os.path.join(work, "general", "docs.db"),
                            "--http", f"127.0.0.1:{port}", "--token-file", os.path.join(work, "token"), "--teams-dir", teams,
                            "--libraries-dir", os.path.join(work, "libs"), "--state-dir", os.path.join(work, "state"),
                            "--refresh-minutes", "60"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
                break
            except OSError:
                time.sleep(0.1)
        _, lab_hit = search(port, "lab", LAB_WORD)
        _, lab_general = search(port, "lab", GENERAL_WORD)
        _, san_general = search(port, "san", GENERAL_WORD)
        _, san_lab = search(port, "san", LAB_WORD)
        assert "vault.md" in lab_hit, lab_hit
        assert "intro.md" not in lab_general and "intro.md" in san_general, (lab_general, san_general)
        assert "vault.md" not in san_lab, san_lab
        src = rpc(port, "lab", "tools/call", {"name": "list_sources", "arguments": {}})["content"][0]["text"]
        assert '"library":"labdocs"' in src, src
        # a team library that is named but not built: a clear error, never the general library
        meta = json.load(open(os.path.join(teams, "lab", "team.json")))
        meta["library"] = "notbuilt"
        write(os.path.join(teams, "lab", "team.json"), json.dumps(meta))
        r, _ = search(port, "lab", GENERAL_WORD)
        assert r["isError"] and "not built yet" in r["content"][0]["text"] and "paas-library build notbuilt" in r["content"][0]["text"], r
        meta["library"] = "labdocs"
        write(os.path.join(teams, "lab", "team.json"), json.dumps(meta))
        assert "vault.md" in search(port, "lab", LAB_WORD)[1]
    finally:
        srv.kill()
    print("docs service per team library ok")

    # the lab plugin's docs-local: the team library where installed; without it, never the general library
    home = os.path.join(work, "home")
    brain = os.path.join(home, ".claude", "brain")
    os.makedirs(os.path.join(brain, "library"))
    os.symlink(os.path.join(work, "general", "docs.db"), os.path.join(brain, "library", "docs.db"))
    henv = dict(os.environ, HOME=home)
    henv.pop("CLAUDE_HOME", None)
    henv.pop("PAAS_DOCS_URL", None)
    exe = [os.path.join(lab_plug, "bin", "docs-local")]
    out = stdio(exe, henv, GENERAL_WORD)
    assert "intro.md" not in out, out                                   # the general library is installed, but not this team's
    os.makedirs(os.path.join(brain, "libraries"))
    os.symlink(os.path.join(work, "libs", "labdocs"), os.path.join(brain, "libraries", "labdocs"))
    assert "vault.md" in stdio(exe, henv, LAB_WORD)
    assert "intro.md" not in stdio(exe, henv, GENERAL_WORD)
    san_exe = [os.path.join(teams, "san", "paas-brain-san", "bin", "docs-local")]
    assert "intro.md" in stdio(san_exe, henv, GENERAL_WORD)            # san keeps the general library
    print("plugin docs-local ok")

    # the docs hooks follow the active team's library
    write(os.path.join(brain, "team"), "lab\n")
    os.makedirs(os.path.join(brain, "teams", "lab"))
    os.symlink(lab_plug, os.path.join(brain, "teams", "lab", "paas-brain-lab"))
    for hook in ("docs-leads.py", "docs-hints.py"):
        code = ("import importlib.util,sys; s=importlib.util.spec_from_file_location('h', sys.argv[1]); m=importlib.util.module_from_spec(s); "
                "s.loader.exec_module(m); print(m.DB)")
        e = dict(henv)
        for k in ("DOCS_LEADS_DB", "DOCS_HINTS_DB"):
            e.pop(k, None)
        db = subprocess.run([sys.executable, "-c", code, os.path.join(R, "brain", "claude", "hooks", hook)], env=e,
                            capture_output=True, text=True).stdout.strip()
        assert db == os.path.join(brain, "libraries", "labdocs", "docs.db"), (hook, db)
    print("docs hooks ok")

    # the marketplace: docs-http-<team> for every team, with ?team=; the old docs-search item goes
    market = os.path.join(work, "market")
    for sub in ("skills", "agents", "mcp"):
        os.makedirs(os.path.join(market, "items", sub))
    write(os.path.join(market, "items", "mcp", "docs-search.json"), json.dumps({"description": "old", "server": {"type": "http", "url": "https://x/mcp"}}))
    menv = dict(os.environ, PAAS_MARKET=market, PAAS_TEAMS=teams, HOME=home)
    mk = os.path.join(R, "brain", "marketplace", "paas_market.py")
    o = subprocess.run([sys.executable, mk, "setup-docs", "https://vm.example:8001/mcp"], input=TOKEN, env=menv, capture_output=True, text=True)
    assert o.returncode == 0 and "docs-http-lab" in o.stdout and "docs-http-san" in o.stdout, (o.stdout, o.stderr)
    items = {i["name"]: i for i in json.load(open(os.path.join(market, "index.json"))) if i["kind"] == "mcp"}
    assert set(items) == {"docs-http-lab", "docs-http-san"}, items
    lab_item = json.load(open(os.path.join(market, "items", "mcp", "docs-http-lab.json")))
    assert lab_item["server"]["url"] == "https://vm.example:8001/mcp?team=lab" and "own library 'labdocs'" in lab_item["description"], lab_item
    assert "general documentation library" in items["docs-http-san"]["description"]
    print("marketplace docs items ok")

    # the read-only guard lets a docs-http tool through even when the query reads like a change
    g = subprocess.run([sys.executable, os.path.join(R, "brain", "claude", "hooks", "block-write-tools.py")], env=henv, text=True,
                       input=json.dumps({"tool_name": "mcp__docs-http-lab__search_docs", "tool_input": {"query": "create volume"}}),
                       capture_output=True)
    assert g.returncode == 0, (g.stdout, g.stderr)
    print("team library ok")
finally:
    shutil.rmtree(work, ignore_errors=True)
