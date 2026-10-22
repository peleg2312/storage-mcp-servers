#!/usr/bin/env python3
"""Claude Code SessionStart hook: prints 3-5 lines of brain status into the session context.
Standard library only; never fails the session (always exit 0, errors are swallowed)."""
import json
import os
import re
import sys

HOME = os.path.expanduser("~/.claude")


def read(path, limit=None):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(limit) if limit else f.read()
    except OSError:
        return ""


def library_line():
    lib = os.path.join(HOME, "brain", "library")
    version = read(os.path.join(lib, "VERSION")).strip()
    head = read(os.path.join(lib, "MANIFEST.md"), 2000)
    m = re.search(r"(\d[\d,]*)\s+documents,\s+(\d[\d,]*)\s+sections", head)
    if not version and not head:
        return "Library: not installed on this VM (use the docs-search MCP; sh brain/install.sh installs docs-local)."
    counts = f", {m.group(1)} documents / {m.group(2)} sections" if m else ""
    return f"Library: {version or 'version unknown'}{counts} in ~/.claude/brain/library (MCP docs-local / docs-search, or search.py)."


def environment_line():
    text = read(os.path.join(HOME, "brain", "environment.md"))
    if not text:
        return "environment.md: MISSING (run /brain-setup)."
    filled = 0
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or set(cells[0]) <= {"-", ""} or cells[0] in ("Name", "Fabric", "vCenter", "Domain"):
            continue
        if cells[0] and any(cells[1:]):  # a label alone (template rows "| A | | | |") is not filled
            filled += 1
    blanks = len(re.findall(r"\b__\b", text))
    notes = read(os.path.join(HOME, "brain", "notes.md"))
    facts = sum(1 for l in notes.splitlines() if l.startswith("- "))
    if filled == 0:
        state = "still the template (run /brain-setup or fill it in)"
    else:
        state = f"filled ({filled} table rows{', ' + str(blanks) + ' threshold blanks left' if blanks else ''})"
    return f"environment.md: {state}; notes.md: {facts} learned facts."


def hook_line():
    s = read(os.path.join(HOME, "settings.json"))
    try:
        hooks = json.loads(s).get("hooks", {}) if s else {}
    except ValueError:
        hooks = {}
    cmds = " ".join(h.get("command", "") for e in hooks.get("PreToolUse", []) for h in e.get("hooks", []))
    if "block-write-tools.py" in cmds and os.path.exists(os.path.join(HOME, "hooks", "block-write-tools.py")):
        return "Read-only guard: active (PreToolUse hook blocks write-looking MCP calls)."
    return "Read-only guard: NOT configured in ~/.claude/settings.json (re-run sh brain/install.sh)."


def main():
    try:
        sys.stdin.read()  # the hook input (session id, source) is not needed
    except Exception:
        pass
    lines = []
    for fn in (library_line, environment_line, hook_line):
        try:
            lines.append(fn())
        except Exception:
            pass
    lines.append("Mode: READ-ONLY. Never change anything; give the user the exact commands to run himself. "
                 "Append newly learned environment facts to ~/.claude/brain/notes.md.")
    print("Storage brain: " + "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
