#!/usr/bin/env python3
"""CI gate of a team repository (GitLab CI runs it on every push; run it locally before a manual edit lands):
every JSON file parses, the plugin has its manifest, hooks.json and .mcp.json in their wrapped shapes, every skill and
agent carries a name and a description, the knowledge files carry no private key or password value (mcp.json holds the
servers' tokens by the team's decision and is not scanned), and the memory files stay under their line caps.
Published into every team repository by brain/teams/publish.py as check.py. Standard library, Python 3.9. Exit 1 on a finding."""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
bad = []
SECRET = [(re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
          (re.compile(r"eyJhbGciOi[\w-]{5,}\.[\w-]+"), "JWT"),
          (re.compile(r"""(?i)\b(?:password|passwd|secret)\b["']?\s*[=:]\s*["']?(?!<[^>]*>|REDACTED)(?=[^\s"',;]*[\d_@#$%^&*+/=!?-])[^\s"',;]{6,}"""), "password value")]
CAPS = {"notes.md": 60, "tool-map.md": 80}


def ok(label, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + label + (": " + detail if detail and not cond else ""))
    if not cond:
        bad.append(label)


def front(path):
    parts = open(path, encoding="utf-8", errors="replace").read().split("---")
    return parts[1] if len(parts) > 2 else ""


for f in sorted(glob.glob(os.path.join(ROOT, "**", "*.json"), recursive=True)):
    if os.sep + ".git" + os.sep in f:
        continue
    try:
        json.load(open(f, encoding="utf-8"))
        ok("json " + os.path.relpath(f, ROOT), True)
    except ValueError as e:
        ok("json " + os.path.relpath(f, ROOT), False, str(e))
plugs = [d for d in glob.glob(os.path.join(ROOT, "paas-brain-*")) if os.path.isdir(d)]
ok("one plugin folder", len(plugs) == 1, str(plugs))
for plug in plugs:
    ok("plugin manifest", os.path.isfile(os.path.join(plug, ".claude-plugin", "plugin.json")))
    hooks = os.path.join(plug, "hooks", "hooks.json")
    if os.path.isfile(hooks):
        ok("hooks.json wrapped in hooks", "hooks" in json.load(open(hooks)))
    mcp = os.path.join(plug, ".mcp.json")
    if os.path.isfile(mcp):
        ok(".mcp.json wrapped in mcpServers", "mcpServers" in json.load(open(mcp)))
    for sk in sorted(glob.glob(os.path.join(plug, "skills", "*", "SKILL.md"))):
        fm = front(sk)
        ok("skill " + os.path.basename(os.path.dirname(sk)), "name:" in fm and "description:" in fm, "frontmatter needs name and description")
    for ag in sorted(glob.glob(os.path.join(plug, "agents", "*.md"))):
        ok("agent " + os.path.basename(ag), "description:" in front(ag), "frontmatter needs description")
    t = json.load(open(os.path.join(plug, "team.json")))
    for n in t.get("skills", []):
        ok("team.json skill present: " + n, os.path.isfile(os.path.join(plug, "skills", n, "SKILL.md")))
    for n in t.get("agents", []):
        ok("team.json agent present: " + n, os.path.isfile(os.path.join(plug, "agents", n + ".md")))
for f in sorted(glob.glob(os.path.join(ROOT, "knowledge", "**", "*.md"), recursive=True)):
    text = open(f, encoding="utf-8", errors="replace").read()
    hits = [what for rx, what in SECRET if rx.search(text)]
    ok("no secret in " + os.path.relpath(f, ROOT), not hits, ", ".join(hits))
    cap = CAPS.get(os.path.basename(f))
    if cap and os.path.dirname(f) == os.path.join(ROOT, "knowledge"):
        n = len(text.splitlines())
        ok(f"{os.path.basename(f)} under {cap} lines", n <= cap, f"{n} lines: move facts into notes/<topic>.md")
print(("all checks passed" if not bad else f"{len(bad)} finding(s)"))
sys.exit(1 if bad else 0)
