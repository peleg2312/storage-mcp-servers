#!/usr/bin/env python3
"""Plugin mode with the real Claude Code CLI (the way every VM and laptop installs a team): paas-team installs the team's
plugin from the person's clone, switching enables one team and disables the other, a user-scope docs-local gives way to the
plugin's, no team disables it; brain/install.sh --team writes no brain hooks into settings.json (the plugin runs them);
the guard run from a plugin steps aside when the VM's managed settings run it. Needs the claude command: exit 77 without."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not shutil.which("claude"):
    print("skipped: claude not installed")
    sys.exit(77)
TOOL = os.path.join(R, "brain", "claude", "tools", "paas-team")
work = tempfile.mkdtemp()
home = os.path.join(work, "home")
os.makedirs(os.path.join(home, ".claude", "tools"))
shutil.copy(TOOL, os.path.join(home, ".claude", "tools", "paas-team"))
subprocess.run([sys.executable, os.path.join(R, "brain", "teams", "publish.py"), "--all", "--to", os.path.join(work, "sources")], check=True, capture_output=True)
env = dict(os.environ, HOME=home, PAAS_TEAMS=os.path.join(work, "sources"))
env.pop("CLAUDE_HOME", None)


def run(cmd, ok=True, e=env, inp=None):
    r = subprocess.run(cmd, capture_output=True, text=True, env=e, timeout=300, input=inp)
    assert not ok or r.returncode == 0, (cmd, r.stdout[-800:], r.stderr[-800:])
    return r.stdout + r.stderr


def plugins():
    out = run(["claude", "plugin", "list"])
    state = {}
    for block in out.split("\n  > ")[1:]:
        name = block.split("\n", 1)[0].strip()
        state[name] = "enabled" if "enabled" in block and "disabled" not in block else "disabled"
    return state


# 1. a user-scope docs-local of the old kind, then the first team: the plugin provides docs-local, the old entry leaves
run(["claude", "mcp", "add", "docs-local", "-s", "user", "--", "python3", "/nonexistent/mcp_stdio.py"])
assert "docs-local" in run(["claude", "mcp", "list"], ok=False)
o = run([sys.executable, TOOL, "use", "nas"])
assert "plugin mode" in o, o
st = plugins()
assert st.get("paas-brain-nas@paas-brain-nas") == "enabled", st
mcps = run(["claude", "mcp", "list"], ok=False)
assert "plugin:paas-brain-nas:docs-local" in mcps and not any(l.startswith("docs-local:") for l in mcps.splitlines()), mcps
plug = os.path.join(home, ".claude", "brain", "teams", "nas", "paas-brain-nas")
msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_sources", "arguments": {}}}]
r = subprocess.run(["sh", os.path.join(plug, "bin", "docs-local")], input="".join(json.dumps(m) + "\n" for m in msgs), capture_output=True, text=True, env=env, timeout=120)
assert r.returncode == 0 and '"docs-search"' in r.stdout, (r.stdout[-300:], r.stderr[-300:])   # knowledge-only: the plugin's own server answers
assert not os.path.exists(os.path.join(home, ".claude", "skills", "share-access-check")), "no copies in plugin mode"
print("plugin install ok")

# 2. switching: one enabled, the other installed but disabled; refresh runs no plugin command (fast path)
run([sys.executable, TOOL, "use", "san"])
st = plugins()
assert st.get("paas-brain-san@paas-brain-san") == "enabled" and st.get("paas-brain-nas@paas-brain-nas") == "disabled", st
assert "SAN expert" in open(os.path.join(home, ".claude", "brain", "persona.md")).read()
run([sys.executable, TOOL, "refresh"])
run([sys.executable, TOOL, "use", "none"])
st = plugins()
assert st.get("paas-brain-san@paas-brain-san") == "disabled", st
print("switch ok")

# 3. brain/install.sh --team in plugin mode: settings.json carries no brain hook entries, the plugin runs them
home2 = os.path.join(work, "home2")
os.makedirs(home2)
env2 = dict(env, HOME=home2)
r = subprocess.run(["sh", os.path.join(R, "brain", "install.sh"), "--no-library", "--team", "nas"], capture_output=True, text=True, env=env2, timeout=900)
assert r.returncode == 0, (r.stdout[-1500:], r.stderr[-800:])
settings = json.load(open(os.path.join(home2, ".claude", "settings.json")))
assert not settings.get("hooks"), settings.get("hooks")
assert open(os.path.join(home2, ".claude", "brain", "team-mode")).read().strip() == "plugin"
assert "paas-brain-nas@paas-brain-nas" in run(["claude", "plugin", "list"], e=env2)
print("install.sh plugin mode ok")

# 4. the guard from a plugin on a VM whose managed settings run it: steps aside; without that twin it judges as always
hook = os.path.join(R, "brain", "claude", "hooks", "block-write-tools.py")
managed = os.path.join(work, "managed.json")
open(managed, "w").write(json.dumps({"hooks": {"PreToolUse": [{"matcher": "mcp__.*|Bash", "hooks": [{"type": "command", "command": "python3 /opt/paas/hooks/block-write-tools.py"}]}]}}))
call = json.dumps({"tool_name": "mcp__powermax__delete_volume", "tool_input": {"id": "x"}, "session_id": "t"})
twin = dict(env, CLAUDE_PLUGIN_ROOT="/x", PAAS_MANAGED_SETTINGS=managed)
r = subprocess.run([sys.executable, hook], input=call, capture_output=True, text=True, env=twin, timeout=30)
assert r.returncode == 0 and not r.stdout.strip(), (r.returncode, r.stdout, r.stderr)
alone = dict(env, CLAUDE_PLUGIN_ROOT="/x", PAAS_MANAGED_SETTINGS=os.path.join(work, "none.json"))
r = subprocess.run([sys.executable, hook], input=call, capture_output=True, text=True, env=alone, timeout=30)
assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
print("guard twin ok")
shutil.rmtree(work, ignore_errors=True)
