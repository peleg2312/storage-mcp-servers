#!/usr/bin/env python3
"""Tests for the notes-check and capture-nudge hooks, in a temporary HOME (stdlib only; exits 1 on failure).
The hooks read HOME at run time, so each case runs them as a subprocess like Claude Code does."""
import datetime
import json
import os
import subprocess
import sys
import tempfile

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude", "hooks")
home = tempfile.mkdtemp()
env = dict(os.environ, HOME=home)
env.pop("BRAIN_NUDGE_DISABLE", None)
env.pop("BRAIN_NUDGE_MIN_TOOLS", None)
brain = os.path.join(home, ".claude", "brain")
os.makedirs(brain)
notes = os.path.join(brain, "notes.md")
today = datetime.date.today().isoformat()
open(notes, "w").write(f"- login password=hunter2\n- array at 10.1.2.3\n- old fact 2025-01-01 is fine\n- new fact {today} is fine\n")
outside = os.path.join(home, "other.md")
open(outside, "w").write("password=hunter2\n")


def run(script, payload=None, args=(), e=env):
    r = subprocess.run([sys.executable, os.path.join(HOOKS, script), *args], input=json.dumps(payload or {}),
                       capture_output=True, text=True, env=e, timeout=20)
    return r.returncode, r.stdout


rc, out = run("notes-check.py", {"tool_input": {"file_path": notes}})
assert rc == 0 and "notes.md:1: credential value" in out and "notes.md:2: private IP" in out, out
assert "hunter2" not in out and ":3:" not in out and ":4:" not in out, out
assert run("notes-check.py", {"tool_input": {"file_path": outside}}) == (0, "")
print("notes-check hook ok")

rc, out = run("notes-check.py", args=["--scan"])
assert rc == 1 and "notes.md:1" in out, (rc, out)
rc, out = run("notes-check.py", args=["--stale", "180"])
assert rc == 0 and out.count("notes.md:3:") == 1 and out.strip().endswith("1 stale lines"), out
open(notes, "w").write("- ok <REDACTED>\n- token: <your token>\n- password=\"\"\n- x 10.0.0.1 # allow-ip\n- password=abc notes-check: allow\n")
assert run("notes-check.py", args=["--scan"]) == (0, "\n"), "placeholders and markers must pass"
print("notes-check cli ok")

tr = os.path.join(home, "t.jsonl")
sess = lambda sid, **k: {"session_id": sid, "transcript_path": tr, **k}
open(tr, "w").write('{"type":"tool_use"}\n' * 19)
assert run("capture-nudge.py", sess("a")) == (0, "")
open(tr, "w").write('{"type": "tool_use"}\n' * 25)
rc, out = run("capture-nudge.py", sess("a"))
assert rc == 0 and json.loads(out)["decision"] == "block", out
assert run("capture-nudge.py", sess("a")) == (0, ""), "second time must be silent"
assert run("capture-nudge.py", sess("b", stop_hook_active=True)) == (0, "")
open(tr, "w").write('{"type":"tool_use"}\n' * 25 + '{"type":"tool_use","name":"Write","input":{"file_path":"/home/u/.claude/brain/captures/x.md"}}\n')
assert run("capture-nudge.py", sess("c")) == (0, "")
print("capture-nudge ok")

# brain as a git repository: the hook commits what it scans, --commit works, incidents are scanned
git = lambda *a: subprocess.run(["git", "-C", brain, *a], capture_output=True, text=True).stdout
os.makedirs(os.path.join(brain, "notes"))
nx = os.path.join(brain, "notes", "x.md")
open(nx, "w").write("# X\n- fine\n")
assert run("notes-check.py", {"tool_input": {"file_path": nx}}) == (0, ""), "no repository: silent"
subprocess.run(["git", "-C", brain, "init", "-q"], check=True)
open(nx, "w").write("# X\n- fine, again\n")
assert run("notes-check.py", {"tool_input": {"file_path": nx}}) == (0, ""), "commit must print nothing"
assert "brain: notes/x.md" in git("log", "--format=%s"), git("log")
open(nx, "w").write("# X\n- third\n")
assert run("notes-check.py", args=["--commit", "brain: manual"]) == (0, "")
assert git("log", "-1", "--format=%s").strip() == "brain: manual"
assert run("notes-check.py", args=["--commit", "nothing changed"]) == (0, "")
os.makedirs(os.path.join(brain, "incidents", "2026"))
open(os.path.join(brain, "incidents", "2026", "x.md"), "w").write("- password=hunter2\n")
rc, out = run("notes-check.py", args=["--scan"])
assert rc == 1 and "incidents/2026/x.md:1" in out, (rc, out)
print("brain git history ok")

# shared brain: a bare remote, a second person joins, hook commits push, --sync, conflict leaves a usable tree
gi = lambda d, *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True).stdout
bare = os.path.join(home, "shared.git")
subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
assert run("notes-check.py", args=["--sync"]) == (0, "brain: no shared remote\n")
subprocess.run(["git", "-C", brain, "checkout", "-q", "-B", "main"], check=True)
open(os.path.join(brain, ".gitignore"), "w").write("notes.md\nenvironment.md\n")
rc, out = run("notes-check.py", args=["--remote", bare])
assert rc == 0 and "pushed" in out, (rc, out)
assert run("notes-check.py", args=["--remote", bare])[0] == 0, "idempotent"
home2 = tempfile.mkdtemp()
env2 = dict(os.environ, HOME=home2)
brain2 = os.path.join(home2, ".claude", "brain")
os.makedirs(brain2)
subprocess.run(["git", "-C", brain2, "init", "-q", "-b", "main"], check=True)
open(os.path.join(brain2, "mine.md"), "w").write("mine\n")
rc, out = run("notes-check.py", args=["--remote", bare], e=env2)
assert rc == 0 and os.path.exists(os.path.join(brain2, "notes", "x.md")), (rc, out)
assert run("notes-check.py", args=["--sync"]) == (0, "brain: in sync\n")   # takes the second one's join commit
open(nx, "w").write("# X\n- line one\n- shared line\n")
assert run("notes-check.py", {"tool_input": {"file_path": nx}}) == (0, "")
assert "line one" in gi(bare, "show", "main:notes/x.md"), (gi(brain, "log", "--oneline"), gi(brain, "status"), gi(bare, "log", "main", "--oneline"))
rc, out = run("notes-check.py", args=["--sync"], e=env2)
assert rc == 0 and out.strip() == "brain: in sync" and "line one" in open(os.path.join(brain2, "notes", "x.md")).read(), (rc, out, gi(brain2, "log", "--oneline", "--all"), gi(brain2, "status"), open(os.path.join(brain2, "notes", "x.md")).read())
# conflict: the same line changed on both sides (the second to sync loses nothing, the tree stays usable)
nx2 = os.path.join(brain2, "notes", "x.md")
open(nx2, "w").write("# X\n- line one\n- from two\n")
run("notes-check.py", args=["--commit", "two"], e=env2)
open(nx, "w").write("# X\n- line one\n- from one\n")
run("notes-check.py", args=["--commit", "one"])
rc, out = run("notes-check.py", args=["--sync"])        # two pushed first, so one clashes
assert rc == 1 and out.startswith("brain: conflict with the shared brain in: notes/x.md;"), (rc, out)
assert gi(brain, "status", "--porcelain").strip() == "", gi(brain, "status")
assert "<<<<" not in open(nx).read() and "from one" in open(nx).read()
# a file holding a secret is reported, not committed (the redacted save is); a rebase left behind by a killed sync is aborted
leak = os.path.join(brain, "notes", "leak.md")
open(leak, "w").write("# L\n- login password=hunter2!\n")
rc, out = run("notes-check.py", {"tool_input": {"file_path": leak}})
assert rc == 0 and "credential value" in out and "notes/leak.md" not in gi(brain, "log", "--format=%s", "--", "notes/leak.md"), out
open(leak, "w").write("# L\n- login password=<REDACTED>\n")
assert run("notes-check.py", {"tool_input": {"file_path": leak}}) == (0, "")
assert "brain: notes/leak.md" in gi(brain, "log", "--format=%s", "--", "notes/leak.md")
os.makedirs(os.path.join(brain, ".git", "rebase-merge"))          # what a killed pull --rebase leaves behind
open(os.path.join(brain, ".git", "rebase-merge", "head-name"), "w").write("refs/heads/main\n")
rc, out = run("notes-check.py", args=["--sync"])
assert rc == 0 and not os.path.isdir(os.path.join(brain, ".git", "rebase-merge")), (rc, out)
print("secrets and stuck rebase ok")
print("shared brain ok")

# add-docs --brain: pages land as local/brain-notes and local/brain-incidents; a removed page leaves the index
import shutil, sqlite3
repo = os.path.dirname(HOOKS.rsplit("claude", 1)[0].rstrip(os.sep))
tools = os.path.join(home, "tools")
os.makedirs(tools)
shutil.copy(os.path.join(HOOKS, "..", "tools", "add-docs"), tools)
for m in ("docs_index.py", "docs_text.py"):
    shutil.copy(os.path.join(repo, "docs-search-mcp", m), tools)
db = os.path.join(home, "docs.db")
os.makedirs(os.path.join(home, "empty"))
subprocess.run([sys.executable, os.path.join(tools, "docs_index.py"), "--docs", os.path.join(home, "empty"), "--db", db],
               capture_output=True, env=env)
os.makedirs(os.path.join(brain, "incidents", "2026"), exist_ok=True)
open(os.path.join(brain, "incidents", "2026", "x.md"), "w").write("# Incident\n- zoning outage\n")
os.makedirs(os.path.join(brain, "captures"))
open(os.path.join(brain, "captures", "c.md"), "w").write("# Capture\n")
e2 = dict(env, DOCS_DB=db)
paths = lambda: sorted(r[0] for r in sqlite3.connect(db).execute("SELECT path FROM docs"))
r = subprocess.run(["sh", os.path.join(tools, "add-docs"), "--brain"], capture_output=True, text=True, env=e2)
assert r.returncode == 0 and paths() == ["brain/local/brain-incidents/2026-x.md", "brain/local/brain-notes/x.md"], (r.stderr, paths())
os.remove(nx)
subprocess.run(["sh", os.path.join(tools, "add-docs"), "--brain"], capture_output=True, env=e2)
assert paths() == ["brain/local/brain-incidents/2026-x.md"], paths()
print("add-docs --brain ok")
