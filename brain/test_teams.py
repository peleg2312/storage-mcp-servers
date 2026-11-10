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
os.makedirs(os.path.join(home, ".claude", "brain"), exist_ok=True)
# a stand-in claude on the PATH records the plugin commands (marketplace add, install, enable, disable, mcp remove) instead
# of running them; the real plugin mechanics are covered by test_plugin_mode.py
fake_claude = os.path.join(home, "fakebin")
os.makedirs(fake_claude)
open(os.path.join(fake_claude, "claude"), "w").write("#!/bin/sh\necho \"$@\" >> \"$HOME/claude.log\"\n")
os.chmod(os.path.join(fake_claude, "claude"), 0o755)
env["PATH"] = fake_claude + os.pathsep + env["PATH"]
claude_log = lambda: open(os.path.join(home, "claude.log")).read() if os.path.exists(os.path.join(home, "claude.log")) else ""


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
    for f in ("mcp_stdio.py", "search_cli.py", "docs_text.py", "docs_index.py"):
        assert os.path.isfile(os.path.join(plug, "lib", f)), f
san_skills = json.load(open(os.path.join(out, "paas-brain-san", "team.json")))["skills"]
pm_agent = open(os.path.join(out, "paas-brain-san", "agents", "powermax-analyst.md")).read()
assert "mcp__plugin_paas-brain-san_powermax__*" in pm_agent and "mcp__plugin_paas-brain-san_docs-local__*" in pm_agent and "mcp__kuparashit__*" in pm_agent, pm_agent[:400]   # team servers in the plugin's form, a personal one bare
# the plugin's docs-local on a machine without the library: the team knowledge is the index
lh = tempfile.mkdtemp(); os.makedirs(os.path.join(lh, ".claude", "brain", "notes"))
open(os.path.join(lh, ".claude", "brain", "notes", "vast.md"), "w").write("# VAST\n- 2026-10-31 view policy alpha squashes root observed vms\n")
msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "view policy alpha root"}}}]
r = subprocess.run(["sh", os.path.join(out, "paas-brain-nas", "bin", "docs-local")], input="".join(json.dumps(m) + "\n" for m in msgs),
                   capture_output=True, text=True, env=dict(env, HOME=lh), timeout=120)
assert r.returncode == 0, r.stderr[-400:]
ans = {m["id"]: m for m in (json.loads(l) for l in r.stdout.splitlines() if l.strip())}
assert ans[1]["result"]["serverInfo"]["name"] == "docs-search" and "vast.md" in ans[2]["result"]["content"][0]["text"], ans[2]
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
    for p in (".git", ".claude-plugin/marketplace.json", "paas-brain-" + t, "knowledge/notes", "knowledge/runbooks", "knowledge/captures",
              "knowledge/incidents", "knowledge/tool-map.md", f"paas-brain-{t}/team.json", f"paas-brain-{t}/.mcp.json", "README.md", ".gitignore"):
        assert os.path.exists(os.path.join(d, p)), (t, p)
    for p in ("team.json", "mcp.json"):                      # one copy: the plugin's (the only part Claude Code installs)
        assert not os.path.exists(os.path.join(d, p)), (t, p)
    assert "knowledge/notes.md" not in open(os.path.join(d, ".gitignore")).read(), "notes.md and environment.md are team memory"
    for f in ("knowledge/notes.md", "knowledge/environment.md"):
        assert os.path.exists(os.path.join(d, f)), (t, f)
    # servers still on their catalog placeholders wait in team.json; .mcp.json connects only complete ones (docs-local here)
    pending = json.load(open(os.path.join(d, f"paas-brain-{t}", "team.json")))["mcp_pending"]
    assert "docs-local" not in pending and all("HOST" in c.get("url", "") for c in pending.values()), pending
    assert pending["docs-search"]["url"].endswith(f"/mcp?team={t}"), pending["docs-search"]      # the team's own knowledge over HTTP
    assert list(json.load(open(os.path.join(d, f"paas-brain-{t}", ".mcp.json")))["mcpServers"]) == ["docs-local"]
git = lambda d, *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True).stdout
n = git(os.path.join(work, "sources", "san"), "rev-list", "--count", "HEAD").strip()
run([sys.executable, PUBLISH, "san", "--to", os.path.join(work, "sources", "san"), "--remote", "git@gitlab.example:san/brain.git"])
assert git(os.path.join(work, "sources", "san"), "rev-list", "--count", "HEAD").strip() == str(int(n) + 1), "team.json remote recorded = one commit"
assert json.load(open(os.path.join(work, "sources", "san", "paas-brain-san", "team.json")))["remote"] == "git@gitlab.example:san/brain.git"
run([sys.executable, PUBLISH, "san", "--to", os.path.join(work, "sources", "san")])
assert git(os.path.join(work, "sources", "san"), "rev-list", "--count", "HEAD").strip() == str(int(n) + 1), "nothing changed: no commit"
# the recorded remote is unreachable here: paas-team must fall back to the VM's copy (test 3) and keep the remote for later
print("publish ok")

# 2b. a team repository from the earlier layout (mcp.json and team.json at its root): the next publish moves both into the
#     plugin (filled-in servers into .mcp.json, the rest into team.json's mcp_pending, the remote into team.json), removes
#     the root copies, and a team editor commit that only touched those files does not count as a plugin edit
old = os.path.join(work, "oldlayout")
subprocess.run(["git", "clone", "-q", os.path.join(work, "sources", "nas"), old], check=True)
json.dump({"ontap": {"type": "http", "url": "http://ontap.example:8000/mcp", "headers": {"Authorization": "Bearer abcdef0123456789"}},
           "harvest": {"type": "http", "url": "http://HOST:8000/mcp", "headers": {"Authorization": "Bearer TOKEN"}}},
          open(os.path.join(old, "mcp.json"), "w"))
json.dump({"name": "nas", "remote": "git@gitlab.example:nas/brain.git"}, open(os.path.join(old, "team.json"), "w"))
pt = json.load(open(os.path.join(old, "paas-brain-nas", "team.json"))); pt.pop("remote", None); pt.pop("mcp_pending", None)
json.dump(pt, open(os.path.join(old, "paas-brain-nas", "team.json"), "w"))
gitc = ["git", "-C", old, "-c", "user.name=t", "-c", "user.email=t@x"]
subprocess.run(gitc + ["add", "-A"], check=True); subprocess.run(gitc + ["commit", "-qm", "brain tab: team nas edited"], check=True)
rc, o = run([sys.executable, PUBLISH, "nas", "--to", old])
assert not os.path.exists(os.path.join(old, "mcp.json")) and not os.path.exists(os.path.join(old, "team.json")), os.listdir(old)
pm = json.load(open(os.path.join(old, "paas-brain-nas", ".mcp.json")))["mcpServers"]
pt = json.load(open(os.path.join(old, "paas-brain-nas", "team.json")))
assert pm["ontap"]["headers"]["Authorization"] == "Bearer abcdef0123456789" and "harvest" not in pm, pm
assert "harvest" in pt["mcp_pending"] and "ontap" not in pt["mcp_pending"] and pt["remote"] == "git@gitlab.example:nas/brain.git", pt
assert subprocess.run([sys.executable, os.path.join(old, "check.py")], capture_output=True, text=True).returncode == 0
print("one-copy migration ok")

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
allow = json.load(open(os.path.join(home, ".claude", "settings.json")))["permissions"]["allow"]
assert "mcp__plugin_paas-brain-san_powermax" in allow and "mcp__plugin_paas-brain-san_docs-local" in allow and not any("docs-search" in r for r in allow), allow
assert os.readlink(os.path.join(brain, "notes")) == os.path.join(brain, "teams", "san", "knowledge", "notes")
assert open(os.path.join(brain, "notes.md")).read() == "- my core fact\n"
assert os.path.isfile(os.path.join(brain, "teams", "san", "knowledge", "notes", "powermax.md"))
assert git(os.path.join(brain, "teams", "san"), "remote", "get-url", "origin").strip() == "git@gitlab.example:san/brain.git", "remote kept for later syncs"
assert open(os.path.join(brain, "team")).read().strip() == "san"
assert "The SAN team" in open(os.path.join(brain, "persona.md")).read()
skills = lambda: sorted(os.listdir(os.path.join(home, ".claude", "skills")))
assert skills() == ["mine"], skills()                        # the plugin carries the team's skills: nothing is copied into ~/.claude
assert not os.path.exists(os.path.join(home, ".claude", "agents", "powermax-analyst.md"))
log = claude_log()
assert f"plugin marketplace add {os.path.join(brain, 'teams', 'san')}" in log and "plugin install paas-brain-san@paas-brain-san --scope user" in log, log
assert "mcp remove -s user docs-local" in log, log            # one docs-local only: the plugin's
o = team("use", "nas")
assert "team nas" in o, o
assert "NAS" in open(os.path.join(brain, "persona.md")).read() and "NAS" in open(os.path.join(brain, "storage.md")).read().split("\n")[0]
assert skills() == ["mine"]
log = claude_log()
assert "plugin install paas-brain-nas@paas-brain-nas --scope user" in log and "plugin disable paas-brain-san@paas-brain-san" in log, log
assert "my core fact" not in open(os.path.join(brain, "notes.md")).read(), "nas has its own personal notes"
assert not os.path.exists(os.path.join(brain, "notes", "powermax.md"))
team("use", "san")
assert open(os.path.join(brain, "notes.md")).read() == "- my core fact\n" and os.path.exists(os.path.join(brain, "notes", "powermax.md"))
assert "plugin disable paas-brain-nas@paas-brain-nas" in claude_log()
st = team()
assert st.startswith("team: san (") and "other teams: nas" in st, st
print("switch ok")

# 3b. the team's rules live in its repository (rules/) next to knowledge/: linked into ~/.claude/brain, never written by
#     publish.py, paas-team or the notes hook, and Claude cannot change them (the guard)
san_src = os.path.join(work, "sources", "san")
for name in ("main.md", "persona.md", "storage.md", "coding.md"):
    assert os.path.isfile(os.path.join(san_src, "rules", name)), name
    assert os.readlink(os.path.join(brain, name)) == os.path.join(brain, "teams", "san", "rules", name), name
assert open(os.path.join(san_src, "rules", "main.md")).read() == open(os.path.join(san_src, "paas-brain-san", "brain", "CLAUDE.md")).read()
assert "@~/.claude/brain/main.md" in open(os.path.join(home, ".claude", "CLAUDE.md")).read().split()
# the team edits its storage rules; a new publish keeps them (and says so), adds no commit for them
open(os.path.join(san_src, "rules", "storage.md"), "a").write("\nTeam rule: SG names start with SG_.\n")
subprocess.run(["git", "-C", san_src, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qam", "team rule"], check=True)
n = git(san_src, "rev-list", "--count", "HEAD").strip()
rc, o = run([sys.executable, PUBLISH, "san", "--to", san_src])
assert "kept the team's own rules/storage.md" in o, o
assert "Team rule: SG names" in open(os.path.join(san_src, "rules", "storage.md")).read()
assert git(san_src, "rev-list", "--count", "HEAD").strip() == n, "the team's rules are not a publish change"
# a member pulls it: their storage.md is the team's file itself
r = subprocess.run(["git", "-C", os.path.join(brain, "teams", "san"), "pull", "--ff-only", "-q", san_src, "main"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr                           # (origin is the unreachable stand-in GitLab: pull the source directly)
assert "Team rule: SG names" in open(os.path.join(brain, "storage.md")).read()
os.makedirs(os.path.join(home, "chats"), exist_ok=True)       # the web UI's plain chats get the team's rules at session start
subprocess.run([sys.executable, os.path.join(HOOKS, "session-start.py")], input="{}", env=env, capture_output=True, text=True, timeout=60)
assert "Team rule: SG names" in open(os.path.join(home, "chats", "CLAUDE.md")).read()
# the guard: Claude's edits and shell writes to a team rule are blocked, reads and notes pass
guard = lambda payload: subprocess.run([sys.executable, os.path.join(HOOKS, "block-write-tools.py")], input=json.dumps(payload),
                                       capture_output=True, text=True, env=env, timeout=30)
rules_dir = os.path.join(brain, "teams", "san", "rules")
for tool, inp in (("Edit", {"file_path": os.path.join(brain, "storage.md"), "old_string": "a", "new_string": "b"}),
                  ("Write", {"file_path": os.path.join(rules_dir, "new.md"), "content": "x"}),
                  ("MultiEdit", {"file_path": os.path.join(rules_dir, "main.md"), "edits": []}),
                  ("Bash", {"command": "sed -i 's/a/b/' ~/.claude/brain/storage.md"}),
                  ("Bash", {"command": "echo x >> ~/.claude/brain/persona.md"}),
                  ("Bash", {"command": "cp /tmp/x $HOME/.claude/brain/main.md"}),
                  ("Bash", {"command": f"rm {os.path.join(rules_dir, 'coding.md')}"})):
    r = guard({"tool_name": tool, "tool_input": inp})
    assert r.returncode == 2 and "team's rules" in r.stderr, (tool, inp, r.returncode, r.stderr)
for tool, inp in (("Edit", {"file_path": os.path.join(brain, "notes", "powermax.md"), "old_string": "a", "new_string": "b"}),
                  ("Write", {"file_path": os.path.join(home, "project", "storage.md"), "content": "x"}),
                  ("Bash", {"command": "cat ~/.claude/brain/storage.md > /tmp/rules-copy"}),
                  ("Bash", {"command": "cp ~/.claude/brain/storage.md /tmp/rules-copy && grep -i sg ~/.claude/brain/storage.md"})):
    r = guard({"tool_name": tool, "tool_input": inp})
    assert r.returncode == 0, (tool, inp, r.stderr)
# the notes hook never commits rules/: a whole-tree commit leaves a local rules edit alone, a save of a rule file commits nothing
clone = os.path.join(brain, "teams", "san")
open(os.path.join(clone, "rules", "coding.md"), "a").write("\nlocal draft\n")
open(os.path.join(clone, "knowledge", "notes", "fabric.md"), "w").write("# Fabric\n- 2026-11-10 · fact · observed · test\n")
subprocess.run([sys.executable, os.path.join(HOOKS, "notes-check.py"), "--commit", "brain: test"], env=env, check=True, capture_output=True)
assert "knowledge/notes/fabric.md" in git(clone, "show", "--name-only", "--format=", "HEAD")
assert git(clone, "status", "--porcelain").strip() == "M rules/coding.md", git(clone, "status", "--porcelain")
subprocess.run(["git", "-C", clone, "checkout", "-q", "--", "rules/coding.md"], check=True)
# an installed VM whose CLAUDE.md is the brain's full text: kept as a backup, replaced by the import (rules loaded once)
vm = os.path.join(work, "vm")
os.makedirs(os.path.join(vm, ".claude", "brain"))
open(os.path.join(vm, ".claude", "CLAUDE.md"), "w").write(open(os.path.join(R, "brain", "claude", "CLAUDE.md")).read())
run([sys.executable, TOOL, "use", "san"], e=dict(env, HOME=vm))
md = open(os.path.join(vm, ".claude", "CLAUDE.md")).read()
assert "@~/.claude/brain/main.md" in md.split() and "Golden rules" not in md, md
assert any(f.startswith("CLAUDE.md.bak.") for f in os.listdir(os.path.join(vm, ".claude")))
assert os.readlink(os.path.join(vm, ".claude", "brain", "main.md")).endswith(os.path.join("teams", "san", "rules", "main.md"))
print("team rules ok")

# 3c. runbooks: tested change procedures in the team's knowledge/runbooks, linked like notes/, committed by the notes hook,
#     listed in INDEX.md and at session start
assert os.readlink(os.path.join(brain, "runbooks")) == os.path.join(clone, "knowledge", "runbooks")
book = os.path.join(brain, "runbooks", "powermax-add-host.md")
open(book, "w").write("# Add an ESXi host to a PowerMax masking view\n## Pre-checks\n## Procedure\n## Verification\n## Rollback\n"
                      "## History\n- 2025-01-02: created, run on a PowerMax 8000 by dana · verified\n")
subprocess.run([sys.executable, os.path.join(HOOKS, "notes-check.py")], input=json.dumps({"tool_input": {"file_path": book}}),
               env=env, check=True, capture_output=True, text=True)
assert "knowledge/runbooks/powermax-add-host.md" in git(clone, "show", "--name-only", "--format=", "HEAD")
assert "[powermax-add-host.md](runbooks/powermax-add-host.md): Add an ESXi host" in open(os.path.join(clone, "knowledge", "INDEX.md")).read()
r = subprocess.run([sys.executable, os.path.join(HOOKS, "notes-check.py"), "--stale", "180"], env=env, capture_output=True, text=True)
assert "powermax-add-host" not in r.stdout, "a runbook's history dates are not stale facts"
r = subprocess.run([sys.executable, os.path.join(HOOKS, "session-start.py")], input="{}", env=env, capture_output=True, text=True, timeout=60)
assert "runbooks: 1 tested procedures" in r.stdout and "powermax-add-host" in r.stdout, r.stdout
# the same from the team plugin's own hook (laptops, a VM on a team): the person's memory, not the plugin's templates
r = subprocess.run([sys.executable, os.path.join(clone, "paas-brain-san", "hooks", "session-start.py")], input="{}", env=env,
                   capture_output=True, text=True, timeout=60)
assert "notes/powermax.md" in r.stdout and "notes/fabric.md" in r.stdout and "runbooks: 1" in r.stdout, r.stdout
assert "notes.md: 1 core facts" in r.stdout, r.stdout
assert "are links: edit them at ~/.claude/brain/teams/san/knowledge/<file>" in r.stdout, r.stdout   # Claude Code will not write through a file link
# a teammate's commits show up (the rule change "t" committed in 3b), the member's own and publish.py's do not
assert "Team changes in the last 14 days (by teammates): rules/storage.md (t)" in r.stdout, r.stdout
assert "powermax-add-host" not in r.stdout.split("Team changes")[1].split("\n")[0], r.stdout
print("runbooks ok")

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
assert "New line from the team." in open(os.path.join(brain, "teams", "san", "paas-brain-san", "skills", "zoning-audit", "SKILL.md")).read()   # the plugin loads in place
assert "plugin update paas-brain-san@paas-brain-san" in claude_log()
assert run([sys.executable, TOOL, "needs-refresh"], ok=False)[0] == 1
print("hook, sync and refresh ok")

# 5. a marketplace skill of a team-skill name is the person's: a switch or refresh never touches ~/.claude/skills
os.makedirs(os.path.join(home, ".claude", "skills", "docs-lookup"), exist_ok=True)
open(os.path.join(home, ".claude", "skills", "docs-lookup", "SKILL.md"), "w").write("---\nname: docs-lookup\ndescription: market copy\n---\n")
open(os.path.join(home, ".claude", "paas-market.json"), "w").write(json.dumps({"installed": {"skill/docs-lookup": "1", "agent/Explore": "1"}}))
team("refresh")
assert "market copy" in open(os.path.join(home, ".claude", "skills", "docs-lookup", "SKILL.md")).read()
assert skills() == ["docs-lookup", "mine"], skills()
# the team repository carries what a laptop needs on its own: bin/paas-team and the core rules in the plugin (no installer script)
src = os.path.join(work, "sources", "nas")
assert os.path.isfile(os.path.join(src, "bin", "paas-team")) and not os.path.exists(os.path.join(src, "install-team.sh"))
assert os.path.isfile(os.path.join(src, "paas-brain-nas", "brain", "CLAUDE.md"))
# a laptop without GitLab: a copy of the team repository added as the marketplace; the plugin's own session-start hook sets the
# team up from that clone (knowledge clone, links, rules import), no network and no VM copy needed
lap = tempfile.mkdtemp()
subprocess.run(["git", "clone", "-q", src, os.path.join(lap, "brain-nas")], check=True)
lh = os.path.join(lap, "h"); os.makedirs(lh)
rc, o = run([sys.executable, os.path.join(lap, "brain-nas", "paas-brain-nas", "hooks", "session-start.py")], e=dict(env, HOME=lh, PAAS_TEAMS=os.path.join(work, "nowhere")), inp="{}")
assert "set up from the plugin" in o and "First session" in o, o
assert open(os.path.join(lh, ".claude", "brain", "team")).read().strip() == "nas" and "@~/.claude/brain/main.md" in open(os.path.join(lh, ".claude", "CLAUDE.md")).read()
assert git(os.path.join(lh, ".claude", "brain", "teams", "nas"), "remote", "get-url", "origin").strip() == os.path.join(lap, "brain-nas")
# check.py: the gate passes on a fresh repository and catches a broken dot-file and a secret in the knowledge
assert subprocess.run([sys.executable, os.path.join(src, "check.py")], capture_output=True, text=True).returncode == 0
broken = tempfile.mkdtemp(); shutil.copytree(src, os.path.join(broken, "r"), ignore=shutil.ignore_patterns(".git"))
open(os.path.join(broken, "r", "paas-brain-nas", ".mcp.json"), "w").write("{")
open(os.path.join(broken, "r", "knowledge", "notes", "leak.md"), "w").write("- login password=hunter2\n- ok password=abc notes-check: allow\n")
open(os.path.join(broken, "r", "rules", "main.md"), "a").write("x\n" * 200)
open(os.path.join(broken, "r", "knowledge", "runbooks", "good.md"), "w").write("# A\n## Pre-checks\n## Procedure\n## Verification\n## Rollback (from step 2)\n")
open(os.path.join(broken, "r", "knowledge", "runbooks", "bad.md"), "w").write("# B\n## Procedure\n## Verification\n")
r = subprocess.run([sys.executable, os.path.join(broken, "r", "check.py")], capture_output=True, text=True)
assert "note knowledge/notes/leak.md:1: fact line without a date" in r.stdout, r.stdout
assert "FAIL rules/main.md under 120 lines" in r.stdout, r.stdout
assert "ok   runbook knowledge/runbooks/good.md" in r.stdout and "FAIL runbook knowledge/runbooks/bad.md: missing section(s): ## Pre-checks, ## Rollback" in r.stdout, r.stdout
assert r.returncode == 1 and "FAIL json paas-brain-nas/.mcp.json" in r.stdout and "FAIL no secret in knowledge/notes/leak.md: line 1" in r.stdout and "all checks passed" not in r.stdout, r.stdout
# the plugin version is a fingerprint of its content, identical from publish.py and from paas-team bump
v0 = json.load(open(os.path.join(src, "paas-brain-nas", ".claude-plugin", "plugin.json")))["version"]
assert "-" in v0 and team("bump", "nas").strip() == json.load(open(os.path.join(brain, "teams", "nas", "paas-brain-nas", ".claude-plugin", "plugin.json")))["version"]
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
assert "team repository could not be reached" in o and "N1." in o and not os.path.exists(os.path.join(h2, ".claude", "brain", "team")), o
rc, o = run([sys.executable, os.path.join(bare, "plug", "hooks", "session-start.py")], inp="{}")   # a real brain: silent
assert "could not be reached" not in o and "set up from" not in o, o
print("marketplace and bare plugin ok")

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
# the team's servers ride in the plugin's .mcp.json (built from the team's mcp.json; only filled-in ones): nothing per person,
# the person's own marketplace server stays theirs, servers still on placeholders are named in a note
open(os.path.join(home, "claude.log"), "w").close()
o = team("use", "san")
assert "note: MCP powermax: no address or token" in o and "docs-local" not in o.split("note:")[1], o
have = lambda: sorted(k for k in json.load(open(os.path.join(home, ".claude", "paas-market.json")))["installed"] if k.startswith("mcp/"))
assert have() == ["mcp/kuparashit"], have()
assert json.load(open(os.path.join(brain, "teams", ".installed.json")))["mcp"] == {}
plug_mcp = lambda t: json.load(open(os.path.join(brain, "teams", t, "paas-brain-" + t, ".mcp.json")))["mcpServers"]
assert list(plug_mcp("san")) == ["docs-local"] and plug_mcp("san")["docs-local"]["command"] == "${CLAUDE_PLUGIN_ROOT}/bin/docs-local", plug_mcp("san")
lst = json.loads(team("list", "--json"))
assert next(x for x in lst["teams"] if x["name"] == "san")["mcp_added"] == ["docs-local"]
# a person who still has servers from the earlier per-person registration: they are removed once (the stand-in claude logs it)
json.dump({"skills": [], "agents": [], "mcp": {"powermax": "team", "mds": "market"}}, open(os.path.join(brain, "teams", ".installed.json"), "w"))
d0 = json.load(open(os.path.join(home, ".claude", "paas-market.json"))); d0["installed"]["mcp/mds"] = "1"
json.dump(d0, open(os.path.join(home, ".claude", "paas-market.json"), "w"))
env_c = env
subprocess.run([sys.executable, TOOL, "use", "nas"], capture_output=True, text=True, env=env_c, timeout=120, check=True)
assert "mcp remove -s user powermax" in claude_log()
assert have() == ["mcp/kuparashit"], have()
print("team mcp ok")

# 6b. the team editor: show, then edit (title, persona, a SAN skill added to nas, an agent dropped, an MCP server with its
#     token into mcp.json); the change is committed and pushed; the filled-in server lands in the plugin's .mcp.json (the
#     placeholder one does not), so every member's Claude connects it; no `claude mcp` command runs
d = json.loads(team("show", "nas", "--json"))
assert d["skills"] and "share-access-check" in d["skills"] and d["mcp_servers"]["ontap"]["configured"] is False
assert any(c["name"] == "zoning-audit" and c["source"].startswith("team") for c in d["available_skills"]), d["available_skills"][:3]
open(os.path.join(home, "claude.log"), "w").close()
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
servers = json.load(open(os.path.join(nasdir, "paas-brain-nas", ".mcp.json")))["mcpServers"]
assert servers["ontap"]["headers"]["Authorization"] == "Bearer s3cr3t-token-value", servers
pending = json.load(open(os.path.join(nasdir, "paas-brain-nas", "team.json")))["mcp_pending"]
assert "ontap" not in pending and "harvest" not in servers, (pending, servers)      # each server in one place only
assert pending["harvest"]["url"].startswith("http://h.example") and pending["harvest"]["headers"]["Authorization"] == "Bearer TOKEN", pending   # no token given: the placeholder stays
assert not os.path.exists(os.path.join(nasdir, "mcp.json")) and not os.path.exists(os.path.join(nasdir, "team.json"))
assert "NAS person" in open(os.path.join(brain, "persona.md")).read(), "active team re-applied"
assert "NAS person" in open(os.path.join(nasdir, "rules", "persona.md")).read(), "the editor writes the team's rules/"
assert d["main"].startswith("# Brain:") and "Golden rules" in d["main"] and d["coding"], "show returns the team's main.md and coding.md"
r = subprocess.run([sys.executable, TOOL, "edit", "nas"], input=json.dumps({"main": d["main"] + "\n9. Team golden rule.\n",
                   "coding": "# Coding\nTeam coding rule.\n"}), capture_output=True, text=True, env=env_c, timeout=120)
assert r.returncode == 0, r.stderr
assert "9. Team golden rule." in open(os.path.join(nasdir, "rules", "main.md")).read() and "9. Team golden rule." in open(os.path.join(brain, "main.md")).read()
assert open(os.path.join(nasdir, "rules", "coding.md")).read() == "# Coding\nTeam coding rule.\n"
assert "brain tab: team nas edited" in git(nasdir, "log", "-1", "--format=%s")
assert "brain tab: team nas edited" in git(os.path.join(work, "sources", "nas"), "log", "--format=%s")   # pushed to the remote
assert "mcp add-json" not in claude_log(), claude_log()   # the re-apply enables the plugin; no server is registered per person
pm = plug_mcp("nas")
assert sorted(pm) == ["docs-local", "ontap"] and pm["ontap"] == {"type": "http", "url": "http://ontap.example:8000/mcp", "headers": {"Authorization": "Bearer s3cr3t-token-value"}}, pm
assert json.load(open(os.path.join(brain, "teams", ".installed.json")))["mcp"] == {}
assert next(x for x in json.loads(team("list", "--json"))["teams"] if x["name"] == "nas")["mcp_added"] == ["docs-local", "ontap"]
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

# 8. no team: the team's skills and agents leave, the person's own and marketplace ones stay, plain files again (empty: the
# team's memory stays in its clone, so it cannot travel into the next team), the clone stays
team("use", "san")
team("use", "none")
assert not os.path.islink(os.path.join(brain, "notes")) and os.path.isdir(os.path.join(brain, "notes"))
assert not os.path.exists(os.path.join(brain, "notes", "powermax.md"))
assert os.path.isfile(os.path.join(brain, "teams", "san", "knowledge", "notes", "powermax.md"))
assert os.path.isfile(os.path.join(brain, "notes.md")) and not os.path.islink(os.path.join(brain, "notes.md"))
for name in ("main.md", "persona.md", "storage.md", "coding.md"):    # the rules stay usable as plain copies of the team's
    p = os.path.join(brain, name)
    assert os.path.isfile(p) and not os.path.islink(p), name
    assert open(p).read() == open(os.path.join(brain, "teams", "san", "rules", name)).read(), name
assert not os.path.exists(os.path.join(brain, "team")) and os.path.isdir(os.path.join(brain, "teams", "san", ".git"))
assert skills() == ["docs-lookup", "mine"], skills()
assert not os.path.exists(os.path.join(home, ".claude", "agents", "nas-analyst.md"))
assert have() == ["mcp/kuparashit"], have()
assert json.loads(team("list", "--json"))["active"] is None
assert "plugin disable paas-brain-san@paas-brain-san" in claude_log()
print("no team ok")

# 9. the marketplace: every team's skills and agents are items; the active team's items read as added "from your team";
#    the teams are plugin items (added = cloned, enabled = active); adding one switches, adding a team item points to the editor
market = os.path.join(work, "market"); os.makedirs(market)
menv = dict(env, PAAS_MARKET=market)
mk = os.path.join(R, "brain", "marketplace", "paas_market.py")
run([sys.executable, mk, "publish", os.path.join(R, "brain", "claude"), "--mcp", os.path.join(R, "brain", "marketplace", "mcp.json")], e=menv)
team("use", "nas")
rows = {i["id"]: i for i in json.loads(run([sys.executable, mk, "list", "--json"], e=menv)[1])}
assert rows["skill/share-access-check"]["added"] and rows["skill/share-access-check"]["team"] == "nas", rows["skill/share-access-check"]
assert rows["agent/nas-analyst"]["team"] == "nas" and rows["mcp/ontap"]["team"] == "nas"
assert not rows["skill/rdm-inventory"].get("team") and "mcp/powermax" in rows and not rows["mcp/powermax"].get("team")
assert rows["plugin/paas-brain-nas"]["added"] and rows["plugin/paas-brain-nas"]["enabled"] and rows["plugin/paas-brain-nas"]["team"] == "nas"
assert rows["plugin/paas-brain-san"]["added"] and not rows["plugin/paas-brain-san"]["enabled"]
o = run([sys.executable, mk, "add", "skill/share-access-check"], e=menv)[1]
assert "comes with your team plugin (nas)" in o, o
o = run([sys.executable, mk, "add", "plugin/paas-brain-san"], e=menv)[1]
assert open(os.path.join(brain, "team")).read().strip() == "san", o
run([sys.executable, mk, "disable", "plugin/paas-brain-san"], e=menv)
assert not os.path.exists(os.path.join(brain, "team"))
team("use", "san")
print("marketplace teams ok")
shutil.rmtree(work, ignore_errors=True)
