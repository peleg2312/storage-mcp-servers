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
