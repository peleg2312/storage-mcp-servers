#!/usr/bin/env python3
"""Merge the brain's hooks (PreToolUse read-only guard for MCP tools and shell commands, PostToolUse docs hints, UserPromptSubmit docs leads, SessionStart status, PostToolUse ruff on edited .py files), MCP permissions and the status line
into a Claude Code settings.json (keeps everything else).
usage: merge_settings.py <settings.json> [--hooks-dir DIR] [--banner-dir DIR] [--mcpjson NAME] [mcp-server-name ...]
  --hooks-dir / --banner-dir  where the hook and banner scripts live (default ~/.claude/hooks, ~/.claude/banner;
                              a project install passes <dir>/.claude/hooks etc. as absolute paths)
  --mcpjson NAME              pre-approve the .mcp.json server NAME (enabledMcpjsonServers; project install)"""
import copy
import json
import os
import shutil
import sys

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
    with open(path) as f:
        s = json.load(f)
old = copy.deepcopy(s)
pre = s.setdefault("hooks", {}).setdefault("PreToolUse", [])
post = s["hooks"].setdefault("PostToolUse", [])
ups = s["hooks"].setdefault("UserPromptSubmit", [])
start = s["hooks"].setdefault("SessionStart", [])


def hook(groups, script, timeout, matcher=None):
    """add the hook, or bring an existing entry (same command) up to the current matcher and timeout"""
    cmd = f"python3 {hooks_dir}/{script}"
    for e in groups:
        for h in e.get("hooks", []):
            if h.get("command") == cmd:
                h["timeout"] = timeout
                if matcher:
                    e["matcher"] = matcher
                return
    e = {"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]}
    groups.append({"matcher": matcher, **e} if matcher else e)


hook(pre, "block-write-tools.py", 10, "mcp__.*|Bash")   # a timed-out hook lets the call through: keep slack
hook(post, "docs-hints.py", 5, "mcp__.*")                # meaning of EMS / alerts / codes seen in live results
hook(post, "py-lint.py", 5, "Edit|Write|MultiEdit")      # ruff findings on every .py file Claude edits
hook(ups, "docs-leads.py", 5)                            # library leads for each request (silent when unrelated)
hook(start, "session-start.py", 10)
# security-guidance plugin: pattern warnings only (its LLM reviews would send every diff to Opus and pip-install
# an SDK the air-gapped VM cannot fetch); set it to 1 in settings.json "env" to turn the reviews on.
# No internet on the VM: no auto-update, telemetry or other background traffic.
env = s.setdefault("env", {})
env.setdefault("ENABLE_CODE_SECURITY_REVIEW", "0")
for k in ("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "DISABLE_AUTOUPDATER"):
    env.setdefault(k, "1")
allow = s.setdefault("permissions", {}).setdefault("allow", [])
# air-gapped: the web tools can never answer and NotebookEdit has no notebooks here; denied tools leave the tool list,
# so every session starts ~2-3k tokens lighter
deny = s["permissions"].setdefault("deny", [])
for tool in ("WebFetch", "WebSearch", "NotebookEdit"):
    if tool not in deny:
        deny.append(tool)
# Chrome DevTools plugin: drives the person's own Chrome (empty profile); its connector refuses infrastructure pages
if "mcp__plugin_chrome-devtools_chrome-devtools" not in allow:
    allow.append("mcp__plugin_chrome-devtools_chrome-devtools")
for srv in servers:
    rule = f"mcp__{srv}"
    if rule not in allow:
        allow.append(rule)
for name in mcpjson:
    lst = s.setdefault("enabledMcpjsonServers", [])
    if name not in lst:
        lst.append(name)
# auto mode: tell its classifier this is his own dev VM, so routine work there (files, scripts, builds, his own
# services) is not denied; the built-in rules stay ("$defaults").
if not mcpjson:
    amenv = s.setdefault("autoMode", {}).setdefault("environment", ["$defaults"])
    for line in (
        "Host containment: Claude Code runs on the user's own air-gapped RHEL 9 development VM (no internet). Editing "
        "files in his home and projects, installing packages from the VM's local repositories, running scripts and "
        "tests, and building and running his own apps, containers and local services on this VM is the intended work",
        "Primary use: storage operations (read-only toward infrastructure) and developing his own FastAPI services",
        "Source control: the offline GitLab server configured as the git remote(s) on this VM, and all repos on it",
        "Sensitive remote targets: storage arrays (PowerMax, PowerFlex, PowerScale, NetApp ONTAP), SAN switches "
        "(Cisco MDS / Nexus), UCS, vCenter / ESXi and OpenShift clusters: changes to them are made by the user"):
        if line not in amenv:
            amenv.append(line)
# no "suggested next message" model call after every reply (tokens, no effect on answers); a person may turn it on
s.setdefault("promptSuggestionEnabled", False)
# look and feel (UI only, no tokens): always the brain's, replacing earlier values (one backup, settings.json.bak, when the file changes)
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
if os.path.exists(path) and s != old:
    shutil.copy(path, f"{path}.bak")
with open(path, "w") as f:
    json.dump(s, f, indent=2)
print(f"settings ({path}): read-only, auto-mode environment, docs-hints, docs-leads and session-start hooks installed, status line set, MCP servers allowed without prompts: "
      f"{', '.join(servers) or '(none found)'}{'; .mcp.json servers pre-approved: ' + ', '.join(mcpjson) if mcpjson else ''}; "
      f"theme {s['theme']}, notifications {s['preferredNotifChannel']}")
