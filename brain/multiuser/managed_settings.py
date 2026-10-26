#!/usr/bin/env python3
"""VM-wide Claude Code settings for the multi-user VM (managed settings: every user, cannot be overridden).

usage: managed_settings.py <managed-settings.json> <paas dir>

The same hooks, permissions, auto-mode description and look as the single-user brain (merge_settings.py), with the
scripts in <paas dir>/hooks and <paas dir>/banner, plus the API key helper. Root's own ~/.claude/settings.json loses
the brain's hook entries, so they do not run twice for root (everything else in it is kept).
"""
import json
import os
import subprocess
import sys

path, paas = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
catalog = json.load(open(os.path.join(here, "..", "marketplace", "mcp.json")))
subprocess.run([sys.executable, os.path.join(here, "..", "merge_settings.py"), path,
                "--hooks-dir", f"{paas}/hooks", "--banner-dir", f"{paas}/banner", *catalog], check=True,
               stdout=subprocess.DEVNULL)
s = json.load(open(path))
s["apiKeyHelper"] = f"{paas}/bin/paas-api-key"
json.dump(s, open(path, "w"), indent=2)
for bak in [f for f in os.listdir(os.path.dirname(path)) if f.startswith(os.path.basename(path) + ".bak.")]:
    os.remove(os.path.join(os.path.dirname(path), bak))      # merge_settings' backups do not belong in /etc

root = "/root/.claude/settings.json"
BRAIN_HOOKS = ("block-write-tools.py", "docs-hints.py", "docs-leads.py", "session-start.py", "py-lint.py")
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
