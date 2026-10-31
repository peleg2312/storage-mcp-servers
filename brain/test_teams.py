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
    assert "knowledge/notes.md" in open(os.path.join(d, ".gitignore")).read()
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

# 5. off: plain files again, the clone stays
team("off")
assert not os.path.islink(os.path.join(brain, "notes")) and os.path.isfile(os.path.join(brain, "notes", "powermax.md"))
assert not os.path.exists(os.path.join(brain, "team")) and os.path.isdir(os.path.join(brain, "teams", "san", ".git"))
print("off ok")
shutil.rmtree(work, ignore_errors=True)
