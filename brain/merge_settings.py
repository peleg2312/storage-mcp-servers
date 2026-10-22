#!/usr/bin/env python3
"""Merge the brain's hook + MCP permissions into ~/.claude/settings.json (keeps everything else).
usage: merge_settings.py <settings.json> [mcp-server-name ...]"""
import json
import os
import shutil
import sys
import time

path, servers = sys.argv[1], sys.argv[2:]
s = {}
if os.path.exists(path):
    shutil.copy(path, f"{path}.bak.{time.strftime('%Y%m%d%H%M%S')}")
    with open(path) as f:
        s = json.load(f)
cmd = "python3 ~/.claude/hooks/block-write-tools.py"
pre = s.setdefault("hooks", {}).setdefault("PreToolUse", [])
if not any(h.get("command") == cmd for e in pre for h in e.get("hooks", [])):
    pre.append({"matcher": "mcp__.*", "hooks": [{"type": "command", "command": cmd}]})
allow = s.setdefault("permissions", {}).setdefault("allow", [])
for srv in servers:
    rule = f"mcp__{srv}"
    if rule not in allow:
        allow.append(rule)
# styled status line inside the Claude Code UI (only if none is configured yet)
if "statusLine" not in s:
    s["statusLine"] = {"type": "command", "command": "python3 ~/.claude/banner/paas-statusline.py", "padding": 0}
with open(path, "w") as f:
    json.dump(s, f, indent=2)
print(f"settings: hook installed, status line set, MCP servers allowed without prompts: {', '.join(servers) or '(none found)'}")
