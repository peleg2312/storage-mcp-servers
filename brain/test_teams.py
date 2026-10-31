#!/usr/bin/env python3
"""Team profiles: build.py / publish.py build every team, paas-team switches a person between teams in a temporary HOME,
the notes hook commits into the team's repository and syncs it. Standard library; exits 1 on failure."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(R, "brain", "plugin", "build.py")
PUBLISH = os.path.join(R, "brain", "teams", "publish.py")
TOOL = os.path.join(R, "brain", "claude", "tools", "paas-team")
HOOKS = os.path.join(R, "brain", "claude", "hooks")
TEAMS = sorted(d for d in os.listdir(os.path.join(R, "brain", "teams")) if os.path.isfile(os.path.join(R, "brain", "teams", d, "team.json")))
assert "san" in TEAMS and "nas" in TEAMS, TEAMS

work = tempfile.mkdtemp()
home = os.path.join(work, "home")
os.makedirs(home)
env = dict(os.environ, HOME=home, PAAS_TEAMS=os.path.join(work, "sources"))
env.pop("CLAUDE_HOME", None)


def run(cmd, e=env, ok=True, inp=None):
    r = subprocess.run(cmd, capture_output=True, text=True, env=e, timeout=120, input=inp)
    if ok:
        assert r.returncode == 0, (cmd, r.stdout, r.stderr)
    return r.returncode, r.stdout + r.stderr


def team(*a):
    return run([sys.executable, TOOL, *a])[1]


# 1. every team builds; the plugin carries the resolved lists, the rules and templates, hooks.json from merge_settings.py
out = os.path.join(work, "build")
for t in TEAMS:
    run([sys.executable, BUILD, out, "--team", t])
    plug = os.path.join(out, "paas-brain-" + t)
    meta = json.load(open(os.path.join(plug, "team.json")))
    assert meta["name"] == t and meta["skills"] and meta["agents"], meta
    for n in meta["skills"]:
        assert os.path.isfile(os.path.join(plug, "skills", n, "SKILL.md")), (t, n)
    for n in meta["agents"]:
        assert os.path.isfile(os.path.join(plug, "agents", n + ".md")), (t, n)
    for f in ("persona.md", "storage.md", "environment.md", "tool-map.md", "notes.md", "coding.md"):
        assert os.path.getsize(os.path.join(plug, "brain", f)) > 0, (t, f)
    hooks = json.load(open(os.path.join(plug, "hooks", "hooks.json")))["hooks"]
    assert any("block-write-tools.py" in h["command"] for e in hooks["PreToolUse"] for h in e["hooks"])
    mk = json.load(open(os.path.join(out, ".claude-plugin", "marketplace.json")))
    assert mk["plugins"][0]["source"] == "./paas-brain-" + t
    assert json.load(open(os.path.join(plug, ".claude-plugin", "plugin.json")))["name"] == "paas-brain-" + t
    assert os.path.isfile(os.path.join(plug, "skills", "coding-rules", "SKILL.md")) and "coding-rules" in meta["skills"], "coding rules travel as a skill"
    assert "Think before coding" in open(os.path.join(plug, "skills", "coding-rules", "SKILL.md")).read()
san_skills = json.load(open(os.path.join(out, "paas-brain-san", "team.json")))["skills"]
nas_skills = json.load(open(os.path.join(out, "paas-brain-nas", "team.json")))["skills"]
assert "zoning-audit" in san_skills and "zoning-audit" not in nas_skills and "share-access-check" in nas_skills
assert set(json.load(open(os.path.join(out, "paas-brain-nas", "team.json")))["agents"]) >= {"nas-analyst", "docs-researcher"}
run([sys.executable, BUILD, out, "--team", "nas", "--no-hooks"])
assert not os.path.exists(os.path.join(out, "paas-brain-nas", "hooks")), "--no-hooks"
rc, o = run([sys.executable, BUILD, out, "--team", "nope"], ok=False)
assert rc and "no team" in o, o
print("build ok")

# 2. publish: a team repository per team (git, plugin, knowledge skeleton, marketplace); republishing without a change adds no commit
run([sys.executable, PUBLISH, "--all", "--to", os.path.join(work, "sources")])
for t in TEAMS:
    d = os.path.join(work, "sources", t)
    for p in (".git", ".claude-plugin/marketplace.json", "paas-brain-" + t, "knowledge/notes", "knowledge/captures",
              "knowledge/incidents", "knowledge/tool-map.md", "team.json", "README.md", ".gitignore"):
        assert os.path.exists(os.path.join(d, p)), (t, p)
    assert "knowledge/notes.md" not in open(os.path.join(d, ".gitignore")).read(), "notes.md and environment.md are team memory"
    for f in ("knowledge/notes.md", "knowledge/environment.md", "mcp.json"):
        assert os.path.exists(os.path.join(d, f)), (t, f)
    servers = json.load(open(os.path.join(d, "mcp.json")))
    assert "docs-local" not in servers and all("HOST" in c.get("url", "") for c in servers.values()), servers
    assert servers["docs-search"]["url"].endswith(f"/mcp?team={t}"), servers["docs-search"]      # the team's own knowledge over HTTP
git = lambda d, *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True).stdout
n = git(os.path.join(work, "sources", "san"), "rev-list", "--count", "HEAD").strip()
run([sys.executable, PUBLISH, "san", "--to", os.path.join(work, "sources", "san"), "--remote", "git@gitlab.example:san/brain.git"])
assert git(os.path.join(work, "sources", "san"), "rev-list", "--count", "HEAD").strip() == str(int(n) + 1), "team.json remote recorded = one commit"
assert json.load(open(os.path.join(work, "sources", "san", "team.json")))["remote"] == "git@gitlab.example:san/brain.git"
run([sys.executable, PUBLISH, "san", "--to", os.path.join(work, "sources", "san")])
assert git(os.path.join(work, "sources", "san"), "rev-list", "--count", "HEAD").strip() == str(int(n) + 1), "nothing changed: no commit"
# the recorded remote is unreachable here: paas-team must fall back to the VM's copy (test 3) and keep the remote for later
print("publish ok")

# 3. paas-team: a person with notes of their own joins san (notes move in), switches to nas and back; own skill kept
brain = os.path.join(home, ".claude", "brain")
os.makedirs(os.path.join(brain, "notes"))
os.makedirs(os.path.join(home, ".claude", "skills", "mine"))
open(os.path.join(home, ".claude", "skills", "mine", ".user-skill"), "w").close()
open(os.path.join(home, ".claude", "skills", "mine", "SKILL.md"), "w").write("---\nname: mine\ndescription: mine\n---\n")
open(os.path.join(brain, "notes.md"), "w").write("- my core fact\n")
open(os.path.join(brain, "notes", "powermax.md"), "w").write("# PowerMax\n- fact\n")
listing = json.loads(team("list", "--json"))
assert listing["active"] is None and [t["name"] for t in listing["teams"]] == TEAMS and not listing["teams"][0]["local"]
o = team("use", "san")
assert "team san" in o and "your notes moved into it" in o, o
assert os.readlink(os.path.join(brain, "notes")) == os.path.join(brain, "teams", "san", "knowledge", "notes")
assert open(os.path.join(brain, "notes.md")).read() == "- my core fact\n"
assert os.path.isfile(os.path.join(brain, "teams", "san", "knowledge", "notes", "powermax.md"))
assert git(os.path.join(brain, "teams", "san"), "remote", "get-url", "origin").strip() == "git@gitlab.example:san/brain.git", "remote kept for later syncs"
assert open(os.path.join(brain, "team")).read().strip() == "san"
assert "SAN expert" in open(os.path.join(brain, "persona.md")).read()
skills = lambda: sorted(os.listdir(os.path.join(home, ".claude", "skills")))
assert "zoning-audit" in skills() and "mine" in skills() and "share-access-check" not in skills()
assert os.path.isfile(os.path.join(home, ".claude", "agents", "powermax-analyst.md"))
o = team("use", "nas")
assert "team nas" in o, o
assert "NAS" in open(os.path.join(brain, "persona.md")).read() and "NAS" in open(os.path.join(brain, "storage.md")).read().split("\n")[0]
assert "share-access-check" in skills() and "zoning-audit" not in skills() and "mine" in skills()
assert not os.path.exists(os.path.join(home, ".claude", "agents", "powermax-analyst.md"))
assert os.path.isfile(os.path.join(home, ".claude", "agents", "nas-analyst.md"))
assert "my core fact" not in open(os.path.join(brain, "notes.md")).read(), "nas has its own personal notes"
assert not os.path.exists(os.path.join(brain, "notes", "powermax.md"))
team("use", "san")
assert open(os.path.join(brain, "notes.md")).read() == "- my core fact\n" and os.path.exists(os.path.join(brain, "notes", "powermax.md"))
assert "zoning-audit" in skills() and "share-access-check" not in skills()
st = team()
assert st.startswith("team: san (") and "other teams: nas" in st, st
print("switch ok")

# 4. the notes hook commits into the active team's repository; sync against a bare remote; refresh after a plugin change
hooks = os.path.join(home, ".claude", "hooks")
os.makedirs(hooks)
for f in ("notes-check.py", "session-start.py"):
    shutil.copy(os.path.join(HOOKS, f), hooks)
os.makedirs(os.path.join(home, ".claude", "tools"), exist_ok=True)
shutil.copy(TOOL, os.path.join(home, ".claude", "tools", "paas-team"))
nx = os.path.join(brain, "notes", "powermax.md")
open(nx, "w").write("# PowerMax\n- fact 2026-10-31 verified\n")
run([sys.executable, os.path.join(hooks, "notes-check.py")], inp=json.dumps({"tool_input": {"file_path": nx}}))
assert "brain: knowledge/notes/powermax.md" in git(os.path.join(brain, "teams", "san"), "log", "--format=%s")
idx = open(os.path.join(brain, "teams", "san", "knowledge", "INDEX.md")).read()          # regenerated and committed with the note
assert "powermax.md" in idx and "Core facts" in idx and "INDEX.md" in git(os.path.join(brain, "teams", "san"), "ls-files"), idx
# session start: stale facts and due curation are announced
open(os.path.join(brain, "notes", "old.md"), "w").write("# Old\n- 2020-01-01 an old fact observed source\n")
for i in range(5):
    open(os.path.join(brain, "captures", f"c{i}.md"), "w").write("# C\n")
rc, o = run([sys.executable, os.path.join(hooks, "session-start.py")], inp="{}")
assert "stale: 1 fact(s) older than 180 days" in o and "curation is due (5 or more)" in o, o
for i in range(5):
    os.remove(os.path.join(brain, "captures", f"c{i}.md"))
os.remove(os.path.join(brain, "notes", "old.md"))
assert git(brain, "log", "--format=%s") == "", "nothing committed to the old whole-brain folder"
bare = os.path.join(work, "san.git")
subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
team("remote", "san", bare)
rc, o = run([sys.executable, os.path.join(hooks, "notes-check.py"), "--remote", bare])
assert "pushed" in o, o
assert "fact 2026-10-31" in git(bare, "show", "main:knowledge/notes/powermax.md")
o = team("sync")
assert o.strip().endswith("brain: in sync"), o
rc, o = run([sys.executable, os.path.join(hooks, "session-start.py")], inp="{}")
assert o.startswith("Storage brain: Team: san (SAN / block storage, ") and "shared brain: in sync" in o, o
# a teammate pushes a new plugin version (publish into a clone of the bare remote): the next sync re-applies it
clone = os.path.join(work, "teammate")
subprocess.run(["git", "clone", "-q", bare, clone], check=True)
open(os.path.join(clone, "paas-brain-san", "skills", "zoning-audit", "SKILL.md"), "a").write("\nNew line from the team.\n")
subprocess.run(["git", "-C", clone, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qam", "plugin change"], check=True)
subprocess.run(["git", "-C", clone, "push", "-q"], check=True)
o = team("sync")
assert "team san: updated to version" in o, o
assert "New line from the team." in open(os.path.join(home, ".claude", "skills", "zoning-audit", "SKILL.md")).read()
assert run([sys.executable, TOOL, "needs-refresh"], ok=False)[0] == 1
print("hook, sync and refresh ok")

# 5. a marketplace skill of a team-skill name is the person's: never overwritten or removed by a switch
os.makedirs(os.path.join(home, ".claude", "skills", "docs-lookup"), exist_ok=True)
open(os.path.join(home, ".claude", "skills", "docs-lookup", "SKILL.md"), "w").write("---\nname: docs-lookup\ndescription: market copy\n---\n")
open(os.path.join(home, ".claude", "paas-market.json"), "w").write(json.dumps({"installed": {"skill/docs-lookup": "1", "agent/Explore": "1"}}))
team("refresh")
assert "market copy" in open(os.path.join(home, ".claude", "skills", "docs-lookup", "SKILL.md")).read()
assert "docs-lookup" not in json.load(open(os.path.join(brain, "teams", ".installed.json")))["skills"]
# the team repository carries what a laptop needs on its own: install-team.sh, bin/paas-team, the core rules in the plugin
src = os.path.join(work, "sources", "nas")
assert os.access(os.path.join(src, "install-team.sh"), os.X_OK) and os.path.isfile(os.path.join(src, "bin", "paas-team"))
assert os.path.isfile(os.path.join(src, "paas-brain-nas", "brain", "CLAUDE.md"))
assert subprocess.run(["sh", "-n", os.path.join(src, "install-team.sh")]).returncode == 0
# install-team.sh on a laptop: a clone of the team repository, a stand-in claude on PATH (records its calls), empty HOME
lap = tempfile.mkdtemp()
subprocess.run(["git", "clone", "-q", src, os.path.join(lap, "brain-nas")], check=True)
fb = os.path.join(lap, "bin"); os.makedirs(fb)
open(os.path.join(fb, "claude"), "w").write("#!/bin/sh\necho \"$@\" >> \"$HOME/claude.log\"\n"); os.chmod(os.path.join(fb, "claude"), 0o755)
lh = os.path.join(lap, "h"); os.makedirs(lh)
r = subprocess.run(["sh", os.path.join(lap, "brain-nas", "install-team.sh")], capture_output=True, text=True, env=dict(env, HOME=lh, PATH=fb + os.pathsep + env["PATH"]), timeout=120)
assert r.returncode == 0 and "team nas" in r.stdout, (r.stdout, r.stderr)
assert open(os.path.join(lh, ".claude", "brain", "team")).read().strip() == "nas" and "@~/.claude/brain/main.md" in open(os.path.join(lh, ".claude", "CLAUDE.md")).read()
assert "plugin marketplace add" in open(os.path.join(lh, "claude.log")).read() and "plugin install paas-brain-nas@paas-brain-nas" in open(os.path.join(lh, "claude.log")).read()
assert git(os.path.join(lh, ".claude", "brain", "teams", "nas"), "remote", "get-url", "origin").strip() == src
# check.py: the gate passes on a fresh repository and catches a broken dot-file and a secret in the knowledge
assert subprocess.run([sys.executable, os.path.join(src, "check.py")], capture_output=True, text=True).returncode == 0
broken = tempfile.mkdtemp(); shutil.copytree(src, os.path.join(broken, "r"), ignore=shutil.ignore_patterns(".git"))
open(os.path.join(broken, "r", "paas-brain-nas", ".mcp.json"), "w").write("{")
open(os.path.join(broken, "r", "knowledge", "notes", "leak.md"), "w").write("- login password=hunter2\n- ok password=abc notes-check: allow\n")
r = subprocess.run([sys.executable, os.path.join(broken, "r", "check.py")], capture_output=True, text=True)
assert "note knowledge/notes/leak.md:1: fact line without a date" in r.stdout, r.stdout
assert r.returncode == 1 and "FAIL json paas-brain-nas/.mcp.json" in r.stdout and "FAIL no secret in knowledge/notes/leak.md: line 1" in r.stdout and "all checks passed" not in r.stdout, r.stdout
# the plugin version is a fingerprint of its content, identical from publish.py and from paas-team bump
v0 = json.load(open(os.path.join(src, "paas-brain-nas", ".claude-plugin", "plugin.json")))["version"]
assert "-" in v0 and team("bump", "nas").strip() == json.load(open(os.path.join(brain, "teams", "nas", "paas-brain-nas", ".claude-plugin", "plugin.json")))["version"]
o = team("export", "san", work)
assert o.startswith(os.path.join(work, "paas-brain-san-")) and os.path.getsize(o.split("\n")[0]) > 10000, o
import zipfile
names = zipfile.ZipFile(o.split("\n")[0]).namelist()
assert "paas-brain-san/install-team.sh" in names and any(n.endswith("/skills/zoning-audit/SKILL.md") for n in names), names[:5]
# a bare plugin install (claude plugin install from the team repository, nothing else): the session-start hook sets the
# team up from the plugin itself (knowledge clone from the recorded remote, links, rules import) and prints the rules once
bare = tempfile.mkdtemp()
run([sys.executable, PUBLISH, "nas", "--to", os.path.join(work, "sources", "nas"), "--remote", os.path.join(work, "sources", "nas")])
assert json.load(open(os.path.join(src, "paas-brain-nas", "team.json")))["remote"] == os.path.join(work, "sources", "nas")
shutil.copytree(os.path.join(src, "paas-brain-nas"), os.path.join(bare, "plug"))
assert os.access(os.path.join(bare, "plug", "bin", "paas-team"), os.X_OK)
h = os.path.join(bare, "h")
rc, o = run([sys.executable, os.path.join(bare, "plug", "hooks", "session-start.py")], e=dict(env, HOME=h), inp="{}")
assert "set up from the plugin" in o and "First session" in o and "N1." in o and "@~/" not in o.split("First session")[1], o
assert open(os.path.join(h, ".claude", "brain", "team")).read().strip() == "nas"
assert os.path.islink(os.path.join(h, ".claude", "brain", "notes")) and os.path.isdir(os.path.join(h, ".claude", "brain", "teams", "nas", ".git"))
assert "@~/.claude/brain/main.md" in open(os.path.join(h, ".claude", "CLAUDE.md")).read()
assert "NAS" in open(os.path.join(h, ".claude", "brain", "persona.md")).read() and os.path.isfile(os.path.join(h, ".claude", "tools", "paas-team"))
rc, o = run([sys.executable, os.path.join(bare, "plug", "hooks", "session-start.py")], e=dict(env, HOME=h), inp="{}")
assert o.startswith("Storage brain: Team: nas (") and "First session" not in o, o     # second session: the import carries the rules
# the team repository unreachable (and no VM copy to fall back to): the rules are printed, nothing half-made
h2 = os.path.join(bare, "h2")
os.rename(src, src + "-gone")
rc, o = run([sys.executable, os.path.join(bare, "plug", "hooks", "session-start.py")], e=dict(env, HOME=h2, PAAS_TEAMS=os.path.join(work, "nowhere")), inp="{}")
os.rename(src + "-gone", src)
assert "Plugin-only install" in o and "N1." in o and not os.path.exists(os.path.join(h2, ".claude", "brain", "team")), o
rc, o = run([sys.executable, os.path.join(bare, "plug", "hooks", "session-start.py")], inp="{}")   # a real brain: silent
assert "Plugin-only" not in o and "set up from" not in o, o
print("marketplace, export and bare plugin ok")

# 6. the team's MCP servers come from the VM's marketplace (a stand-in paas-market records the calls): san adds its four,
# nas drops them and adds its own; a server the person added themselves is left alone
mk = os.path.join(home, ".local", "bin", "paas-market")
os.makedirs(os.path.dirname(mk), exist_ok=True)
open(mk, "w").write("""import json, os, sys
st = os.path.expanduser("~/.claude/paas-market.json"); d = json.load(open(st)) if os.path.exists(st) else {"installed": {}}
log = open(os.path.expanduser("~/market.log"), "a")
for a in sys.argv[2:]:
    log.write(sys.argv[1] + " " + a + "\\n")
    if sys.argv[1] == "add": d["installed"][a] = "1"
    if sys.argv[1] == "remove": d["installed"].pop(a, None)
json.dump(d, open(st, "w"))
""")
d0 = json.load(open(os.path.join(home, ".claude", "paas-market.json"))); d0["installed"]["mcp/kuparashit"] = "1"
json.dump(d0, open(os.path.join(home, ".claude", "paas-market.json"), "w"))
os.makedirs(os.path.join(brain, "library"), exist_ok=True); open(os.path.join(brain, "library", "docs.db"), "w").close()   # this machine has the library
o = team("use", "san")
assert "MCP powermax, powerflex, ontap, harvest, mds, ucsc" in o and "docs-search" not in o, o          # docs-local covers docs-search here
have = lambda: sorted(k for k in json.load(open(os.path.join(home, ".claude", "paas-market.json")))["installed"] if k.startswith("mcp/"))
assert have() == ["mcp/harvest", "mcp/kuparashit", "mcp/mds", "mcp/ontap", "mcp/powerflex", "mcp/powermax", "mcp/ucsc"], have()
assert "kuparashit" not in json.load(open(os.path.join(brain, "teams", ".installed.json")))["mcp"], "the person's own server is not the team's"
lst = json.loads(team("list", "--json"))
assert next(x for x in lst["teams"] if x["name"] == "san")["mcp_added"] == ["docs-local", "harvest", "mds", "ontap", "powerflex", "powermax", "ucsc"]
team("use", "nas")
assert have() == ["mcp/harvest", "mcp/kuparashit", "mcp/ontap"], have()
print("team mcp ok")

# 6b. the team editor: show, then edit (title, persona, a SAN skill added to nas, an agent dropped, an MCP server with its
#     token into mcp.json); the change is committed and pushed; with the server filled in, a switch applies it through
#     `claude mcp add-json` (a stand-in claude on PATH records the calls) instead of the marketplace
d = json.loads(team("show", "nas", "--json"))
assert d["skills"] and "share-access-check" in d["skills"] and d["mcp_servers"]["ontap"]["configured"] is False
assert any(c["name"] == "zoning-audit" and c["source"].startswith("team") for c in d["available_skills"]), d["available_skills"][:3]
fake_claude = os.path.join(home, "fakebin")
os.makedirs(fake_claude, exist_ok=True)
open(os.path.join(fake_claude, "claude"), "w").write("#!/bin/sh\necho \"$@\" >> \"$HOME/claude.log\"\n")
os.chmod(os.path.join(fake_claude, "claude"), 0o755)
env_c = dict(env, PATH=fake_claude + os.pathsep + env["PATH"])
change = {"title": "NAS team", "persona": "## Who you work for\nA NAS person.\n",
          "skills": d["skills"] + ["zoning-audit"], "agents": [a for a in d["agents"] if a != "ontap-analyst"],
          "mcp_servers": {"ontap": {"url": "http://ontap.example:8000/mcp", "token": "s3cr3t-token-value"}, "harvest": {"url": "http://h.example:8000/mcp"}},
          "remove_mcp": []}
subprocess.run(["git", "-C", os.path.join(work, "sources", "nas"), "config", "receive.denyCurrentBranch", "updateInstead"], check=True)  # GitLab is bare; this stand-in is not
r = subprocess.run([sys.executable, TOOL, "edit", "nas"], input=json.dumps(change), capture_output=True, text=True, env=env_c, timeout=120)
assert r.returncode == 0 and "edited team nas" in r.stdout and "pushed to the team repository" in r.stdout, (r.stdout, r.stderr)
nasdir = os.path.join(brain, "teams", "nas")
assert "zoning-audit" in json.load(open(os.path.join(nasdir, "paas-brain-nas", "team.json")))["skills"]
assert os.path.isfile(os.path.join(nasdir, "paas-brain-nas", "skills", "zoning-audit", "SKILL.md"))
assert not os.path.exists(os.path.join(nasdir, "paas-brain-nas", "agents", "ontap-analyst.md"))
servers = json.load(open(os.path.join(nasdir, "mcp.json")))
assert servers["ontap"]["headers"]["Authorization"] == "Bearer s3cr3t-token-value" and "HOST" in servers["harvest"].get("url", "") or servers["harvest"]["url"].startswith("http://h.example"), servers
assert "NAS person" in open(os.path.join(brain, "persona.md")).read() and "zoning-audit" in skills(), "active team re-applied"
assert "brain tab: team nas edited" in git(os.path.join(work, "sources", "nas"), "log", "--format=%s")   # pushed to the remote
log = open(os.path.join(home, "claude.log")).read()
assert "mcp add-json -s user ontap" in log and "s3cr3t-token-value" in log and "mcp add-json -s user harvest" not in log, log
assert json.load(open(os.path.join(brain, "teams", ".installed.json")))["mcp"] == {"ontap": "team", "harvest": "market"}
sh = json.loads(team("show", "nas", "--json"))
assert sh["title"] == "NAS team" and sh["mcp_servers"]["ontap"]["token_set"] and sh["mcp_servers"]["ontap"]["configured"]
assert sh["version"] != d["version"] and "-" in sh["version"], (sh["version"], d["version"])          # bumped for plugin-mode members
assert "harvest" in sh["mcp"] and "ontap" in sh["mcp"]
print("team editor ok")

# 7. an edit of a team skill made in the team repository (the Brain tab writes it there) is kept from the next publish
#    unless --force; a plain republish still adds nothing
open(os.path.join(src, "paas-brain-nas", "skills", "quota-report", "SKILL.md"), "a").write("\nTeam edit from the Brain tab.\n")
subprocess.run(["git", "-C", src, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qam", "brain tab: team skill quota-report"], check=True)
rc, o = run([sys.executable, PUBLISH, "nas", "--to", src], ok=False)
assert rc and "made outside publish.py" in o and "quota-report" in o, o
assert "Team edit from the Brain tab." in open(os.path.join(src, "paas-brain-nas", "skills", "quota-report", "SKILL.md")).read()
run([sys.executable, PUBLISH, "nas", "--to", src, "--force"])
assert "Team edit" not in open(os.path.join(src, "paas-brain-nas", "skills", "quota-report", "SKILL.md")).read()
print("publish guard ok")

# 8. no team: the team's skills and agents leave, the person's own and marketplace ones stay, plain files again, the clone stays
team("use", "san")
team("use", "none")
assert not os.path.islink(os.path.join(brain, "notes")) and os.path.isfile(os.path.join(brain, "notes", "powermax.md"))
assert not os.path.exists(os.path.join(brain, "team")) and os.path.isdir(os.path.join(brain, "teams", "san", ".git"))
assert skills() == ["docs-lookup", "mine"], skills()
assert sorted(os.listdir(os.path.join(home, ".claude", "agents"))) == ["Explore.md"]
assert have() == ["mcp/kuparashit"], have()
assert json.loads(team("list", "--json"))["active"] is None
print("no team ok")
shutil.rmtree(work, ignore_errors=True)
