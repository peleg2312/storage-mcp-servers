#!/usr/bin/env python3
"""Merge the brain's hooks (PreToolUse read-only guard, SessionStart status), MCP permissions and the status line
into a Claude Code settings.json (keeps everything else).
usage: merge_settings.py <settings.json> [--hooks-dir DIR] [--banner-dir DIR] [--mcpjson NAME] [mcp-server-name ...]
  --hooks-dir / --banner-dir  where the hook and banner scripts live (default ~/.claude/hooks, ~/.claude/banner;
                              a project install passes <dir>/.claude/hooks etc. as absolute paths)
  --mcpjson NAME              pre-approve the .mcp.json server NAME (enabledMcpjsonServers; project install)"""
import json
import os
import shutil
import sys
import time

args = sys.argv[1:]
path = args.pop(0)
hooks_dir, banner_dir, mcpjson, servers = "~/.claude/hooks", "~/.claude/banner", [], []
while args:
    a = args.pop(0)
    if a == "--hooks-dir":
        hooks_dir = args.pop(0)
    elif a == "--banner-dir":
        banner_dir = args.pop(0)
    elif a == "--mcpjson":
        mcpjson.append(args.pop(0))
    else:
        servers.append(a)
s = {}
if os.path.exists(path):
    shutil.copy(path, f"{path}.bak.{time.strftime('%Y%m%d%H%M%S')}")
    with open(path) as f:
        s = json.load(f)
cmd = f"python3 {hooks_dir}/block-write-tools.py"
pre = s.setdefault("hooks", {}).setdefault("PreToolUse", [])
if not any(h.get("command") == cmd for e in pre for h in e.get("hooks", [])):
    pre.append({"matcher": "mcp__.*", "hooks": [{"type": "command", "command": cmd}]})
start_cmd = f"python3 {hooks_dir}/session-start.py"
start = s["hooks"].setdefault("SessionStart", [])
if not any(h.get("command") == start_cmd for e in start for h in e.get("hooks", [])):
    start.append({"hooks": [{"type": "command", "command": start_cmd}]})
allow = s.setdefault("permissions", {}).setdefault("allow", [])
for srv in servers:
    rule = f"mcp__{srv}"
    if rule not in allow:
        allow.append(rule)
for name in mcpjson:
    lst = s.setdefault("enabledMcpjsonServers", [])
    if name not in lst:
        lst.append(name)
# look and feel (UI only, no tokens): always the brain's, replacing earlier values (settings.json is backed up above)
s["statusLine"] = {"type": "command", "command": f"python3 {banner_dir}/paas-statusline.py", "padding": 0}
s["theme"] = "custom:paas"                                   # ~/.claude/themes/paas.json, banner colours; /theme to change
s["preferredNotifChannel"] = "terminal_bell"                 # bell when Claude finishes while you look away
s["spinnerVerbs"] = {"mode": "append", "verbs": [
    "Zoning", "Decoding NAAs", "Counting paths", "Checking both fabrics", "Reading the masking view",
    "Following the WWPN", "Rescanning HBAs", "Asking the array", "Consulting the KB", "Measuring latency"]}
s["spinnerTipsOverride"] = {"label": "Brain tip", "tips": [
    "Paste any error, alert or EMS name: the brain explains it from the offline docs",
    "/zoning-audit fabric A checks zoning against logins and masking",
    "/brain-health checks the MCP servers, the library and the read-only guard",
    "Ask \"is naa.xxx safe to remove\" before any unmap: decommission-check proves it",
    "Quote an error message in your question: quoted text is matched exactly in the library",
    "Teach it a fact once (\"our SGs start with SG_\"): it is kept in notes.md for every session"]}
os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
with open(path, "w") as f:
    json.dump(s, f, indent=2)
print(f"settings ({path}): read-only + session-start hooks installed, status line set, MCP servers allowed without prompts: "
      f"{', '.join(servers) or '(none found)'}{'; .mcp.json servers pre-approved: ' + ', '.join(mcpjson) if mcpjson else ''}; "
      f"theme {s['theme']}, notifications {s['preferredNotifChannel']}")
