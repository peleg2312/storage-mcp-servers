#!/usr/bin/env python3
"""VM-wide Claude Code settings for the multi-user VM (managed settings: every user, cannot be overridden).

usage: managed_settings.py <managed-settings.json> <paas dir>

The same hooks, permissions, auto-mode description and look as the single-user brain (merge_settings.py), with the
scripts in <paas dir>/hooks and <paas dir>/banner, plus the API key helper. Root's own ~/.claude/settings.json loses
the brain's hook entries, so they do not run twice for root (everything else in it is kept).
"""
import json
import os
import shutil
import subprocess
import sys

path, paas = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
catalog = json.load(open(os.path.join(here, "..", "marketplace", "mcp.json")))
tmp = path + ".new"                                          # built beside the target, then swapped in whole
for f in (tmp, tmp + ".bak"):
    if os.path.exists(f):
        os.remove(f)
if os.path.exists(path):
    shutil.copy(path, tmp)
# the read-only guard is the one hook every account must run and cannot switch off; docs hints and leads, the notes
# scan, lint, the capture nudge and session start come with the team plugin (the same for the VM and every laptop)
subprocess.run([sys.executable, os.path.join(here, "..", "merge_settings.py"), tmp, "--guard-only",
                "--hooks-dir", f"{paas}/hooks", "--banner-dir", f"{paas}/banner", *catalog], check=True,
               stdout=subprocess.DEVNULL)
s = json.load(open(tmp))
s["apiKeyHelper"] = f"{paas}/bin/paas-api-key"
deny = s.setdefault("permissions", {}).setdefault("deny", [])
if "Read(/etc/paas/**)" not in deny:                         # the shared API key lives there
    deny.append("Read(/etc/paas/**)")
with open(tmp, "w") as f:
    json.dump(s, f, indent=2)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, path)
if os.path.exists(tmp + ".bak"):
    os.remove(tmp + ".bak")                                  # merge_settings' backup does not belong in /etc

root = "/root/.claude/settings.json"
BRAIN_HOOKS = ("block-write-tools.py", "docs-hints.py", "docs-leads.py", "session-start.py", "py-lint.py", "notes-check.py", "capture-nudge.py")
if os.path.exists(root):
    r = json.load(open(root))
    for event, groups in list(r.get("hooks", {}).items()):
        for g in groups:
            g["hooks"] = [h for h in g.get("hooks", []) if not str(h.get("command", "")).endswith(BRAIN_HOOKS)]
        r["hooks"][event] = [g for g in groups if g["hooks"]]
        if not r["hooks"][event]:
            del r["hooks"][event]
    r.pop("autoMode", None)
    json.dump(r, open(root, "w"), indent=2)
print(f"managed settings: {path} (hooks in {paas}/hooks, API key helper, {len(catalog)} MCP servers pre-approved)")
