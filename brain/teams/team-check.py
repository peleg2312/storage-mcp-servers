#!/usr/bin/env python3
"""CI gate of a team repository (GitLab CI runs it on every push; run it locally before a manual edit lands):
every JSON file parses (dot-folders included: .claude-plugin, .mcp.json), the plugin has its manifest, hooks.json and
.mcp.json in their wrapped shapes, every skill and agent carries a name and a description, team.json's lists resolve to
files, the knowledge files carry no secret (the same patterns as the brain's notes-check hook, the same 'notes-check: allow'
marker; mcp.json holds the servers' tokens by the team's decision and is not scanned), and notes.md / tool-map.md stay under
their line caps. Published into every team repository by brain/teams/publish.py as check.py. Standard library, Python 3.9.
Exit 1 on a finding; a broken file is a finding, never a traceback."""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
bad = []
# the brain's notes-check.py patterns (brain/claude/hooks/notes-check.py), kept identical
SECRET = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"eyJhbGciOi[\w-]{5,}\.[\w-]+"), "JWT"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"), "bearer token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bsha256~[\w-]{20,}"), "OpenShift token"),
    (re.compile(r"(?i)\b(?:symcfg|symaccess|symcli|sshpass)\b.*\s-(?:password|p)\s+(?!<)\S+"), "password argument"),
    (re.compile(r"""(?i)\b(?:password|passwd|secret|token)\b["']?\s*[=:]\s*["']?(?!<[^>]*>|REDACTED)(?=[^\s"',;]*[\d_@#$%^&*+/=!?-])[^\s"',;]{6,}"""), "credential value"),
]
CAPS = {"notes.md": 60, "tool-map.md": 80}


def ok(label, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + label + (": " + detail if detail and not cond else ""))
    if not cond:
        bad.append(label)


def files(suffix, under=ROOT):
    out = []
    for root, dirs, names in os.walk(under):
        dirs[:] = sorted(d for d in dirs if d != ".git" and d != "__pycache__")
        out += [os.path.join(root, n) for n in sorted(names) if n.endswith(suffix)]
    return out


def jload(path):
    """parsed JSON, or None after a FAIL line"""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        ok("json " + os.path.relpath(path, ROOT), True)
        return d
    except (OSError, ValueError) as e:
        ok("json " + os.path.relpath(path, ROOT), False, str(e))
        return None


def front(path):
    try:
        parts = open(path, encoding="utf-8", errors="replace").read().split("---")
    except OSError:
        return ""
    return parts[1] if len(parts) > 2 else ""


parsed = {f: jload(f) for f in files(".json")}
plugs = [os.path.join(ROOT, d) for d in sorted(os.listdir(ROOT)) if d.startswith("paas-brain-") and os.path.isdir(os.path.join(ROOT, d))]
ok("one plugin folder", len(plugs) == 1, str([os.path.basename(p) for p in plugs]))
ok("marketplace file", isinstance(parsed.get(os.path.join(ROOT, ".claude-plugin", "marketplace.json")), dict))
for plug in plugs:
    ok("plugin manifest", isinstance(parsed.get(os.path.join(plug, ".claude-plugin", "plugin.json")), dict))
    hooks = parsed.get(os.path.join(plug, "hooks", "hooks.json"))
    if os.path.isfile(os.path.join(plug, "hooks", "hooks.json")):
        ok("hooks.json wrapped in hooks", isinstance(hooks, dict) and "hooks" in hooks)
    mcp = parsed.get(os.path.join(plug, ".mcp.json"))
    if os.path.isfile(os.path.join(plug, ".mcp.json")):
        ok(".mcp.json wrapped in mcpServers", isinstance(mcp, dict) and "mcpServers" in mcp)
    for sk in files("SKILL.md", os.path.join(plug, "skills")):
        fm = front(sk)
        ok("skill " + os.path.basename(os.path.dirname(sk)), "name:" in fm and "description:" in fm, "frontmatter needs name and description")
    for ag in files(".md", os.path.join(plug, "agents")):
        ok("agent " + os.path.basename(ag), "description:" in front(ag), "frontmatter needs description")
    t = parsed.get(os.path.join(plug, "team.json"))
    if isinstance(t, dict):
        for n in t.get("skills", []):
            ok("team.json skill present: " + str(n), os.path.isfile(os.path.join(plug, "skills", str(n), "SKILL.md")))
        for n in t.get("agents", []):
            ok("team.json agent present: " + str(n), os.path.isfile(os.path.join(plug, "agents", str(n) + ".md")))
    else:
        ok("plugin team.json", False, "missing or not an object")
for f in files(".md", os.path.join(ROOT, "knowledge")):
    try:
        lines = open(f, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        continue
    hits = []
    for n, line in enumerate(lines, 1):
        if line.rstrip().endswith("notes-check: allow"):
            continue
        for rx, what in SECRET:
            if rx.search(line):
                hits.append(f"line {n}: {what}")
                break
    ok("no secret in " + os.path.relpath(f, ROOT), not hits, "; ".join(hits[:5]))
    cap = CAPS.get(os.path.basename(f))
    if cap and os.path.dirname(f) == os.path.join(ROOT, "knowledge"):
        ok(f"{os.path.basename(f)} under {cap} lines", len(lines) <= cap, f"{len(lines)} lines: move facts into notes/<topic>.md")
print("all checks passed" if not bad else f"{len(bad)} finding(s)")
sys.exit(1 if bad else 0)
