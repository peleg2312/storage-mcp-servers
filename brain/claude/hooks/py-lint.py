#!/usr/bin/env python3
"""Claude Code PostToolUse hook (Edit / Write / MultiEdit): after Claude changes a .py file, ruff checks it and
the findings go straight back to Claude, which fixes them in the same turn (undefined names, unused imports,
syntax errors...). A project with its own ruff configuration (ruff.toml / .ruff.toml / [tool.ruff] in
pyproject.toml) gets its rules; any other file only the error rules below, never style nags. Nothing is
changed on disk; silent when clean or when ruff is not installed (brain/devtools/install-devtools.sh)."""
import json
import os
import shutil
import subprocess
import sys

MAX_LINES = 15
ERRORS = "E9,F63,F7,F82,F401,F811,F841"   # syntax errors, undefined names, unused imports / variables, redefinitions


def has_config(path):
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.exists(os.path.join(d, "ruff.toml")) or os.path.exists(os.path.join(d, ".ruff.toml")):
            return True
        pp = os.path.join(d, "pyproject.toml")
        if os.path.exists(pp) and "[tool.ruff" in open(pp, encoding="utf-8", errors="replace").read():
            return True
        if os.path.isdir(os.path.join(d, ".git")) or os.path.dirname(d) == d:
            return False
        d = os.path.dirname(d)


def ruff():
    venv = os.path.expanduser("~/.claude/devtools-venv/bin/ruff")
    return shutil.which("ruff") or (venv if os.path.exists(venv) else None)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    path = (data.get("tool_input") or {}).get("file_path", "")
    exe = ruff()
    if not path.endswith((".py", ".pyi")) or not os.path.isfile(path) or not exe:
        return 0
    try:
        cmd = [exe, "check", "--output-format=concise", "--no-cache", "--quiet"]
        if not has_config(path):
            cmd += ["--isolated", "--select", ERRORS]
        r = subprocess.run(cmd + [path],
                           capture_output=True, text=True, timeout=8, cwd=os.path.dirname(os.path.abspath(path)))
    except (OSError, subprocess.TimeoutExpired):
        return 0
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    if r.returncode != 1 or not lines:
        return 0
    more = f"\n... and {len(lines) - MAX_LINES} more" if len(lines) > MAX_LINES else ""
    msg = (f"ruff found {len(lines)} problem(s) in {os.path.basename(path)} after this edit; fix them now "
           f"(`ruff check --fix {path}` handles the auto-fixable ones):\n" + "\n".join(lines[:MAX_LINES]) + more)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    try:   # switched off by this person in the web UI (Brain tab, MCP & hooks)
        if "py-lint" in open(os.path.expanduser("~/.claude/brain/hooks-off")).read().split():
            sys.exit(0)
    except OSError:
        pass
    sys.exit(main())
