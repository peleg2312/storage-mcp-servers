#!/usr/bin/env python3
"""Claude Code SessionStart hook: prints 3-5 lines of brain status into the session context.
Standard library only; never fails the session (always exit 0, errors are swallowed)."""
import glob
import json
import os
import re
import sys

# the .claude directory this hook was installed into: ~/.claude (user install) or <project>/.claude
# (install-vm.sh --project <dir>); the documentation library is always shared in ~/.claude/brain/library
HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_HOME = os.path.expanduser("~/.claude")


def read(path, limit=None):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(limit) if limit else f.read()
    except OSError:
        return ""


def library_line():
    lib = os.path.join(USER_HOME, "brain", "library")
    version = read(os.path.join(lib, "VERSION")).strip()
    head = read(os.path.join(lib, "MANIFEST.md"), 2000)
    m = re.search(r"(\d[\d,]*)\s+(?:unique\s+)?documents,\s+(\d[\d,]*)\s+sections", head)
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
    if filled == 0:
        state = "still the template (run /brain-setup or fill it in)"
    else:
        state = f"filled ({filled} table rows{', ' + str(blanks) + ' threshold blanks left' if blanks else ''})"
    return f"environment.md: {state}."


NOTES_CAP = 60
TOPIC_CAP = 150          # a topic file is read whole when its topic comes up


def memory_line():
    """The memory catalog: notes.md is always loaded; the topic files are listed here and read on demand."""
    # multi-user VM: hooks live in /opt/paas (no notes there), each person's notes in their own ~/.claude
    mem = HOME if os.path.exists(os.path.join(HOME, "brain", "notes.md")) else USER_HOME
    notes = read(os.path.join(mem, "brain", "notes.md"))
    n = len(notes.splitlines())
    line = f"notes.md: {sum(1 for l in notes.splitlines() if l.startswith('- '))} core facts, {n} lines"
    if n > NOTES_CAP:
        line += (f" - OVER the {NOTES_CAP}-line cap: move facts most sessions do not need into notes/<topic>.md "
                 "(it is loaded every session)")
    topics = []
    for path in sorted(glob.glob(os.path.join(mem, "brain", "notes", "*.md"))):
        text = read(path)
        title = text.split("\n", 1)[0].lstrip("# ").strip()[:70]
        facts = sum(1 for l in text.splitlines() if l.startswith("- "))
        big = len(text.splitlines()) > TOPIC_CAP
        topics.append(f"  notes/{os.path.basename(path)} ({facts}): {title}"
                      + (f" - OVER {TOPIC_CAP} lines: merge duplicates, drop stale facts" if big else ""))
    if n > NOTES_CAP or any("OVER" in t for t in topics):
        line += ". Tidy the memory files marked OVER after answering his first question, then tell him in one line"
    if topics:
        return line + ".\nMemory topics (read the one a question touches; grep notes/ for an unknown name):\n" + "\n".join(topics)
    return line + "; no topic files yet (notes/<topic>.md)."


def hook_line():
    cmds = ""
    for f in (os.path.join(HOME, "settings.json"), "/etc/claude-code/managed-settings.json"):   # user / VM-wide
        try:
            hooks = json.loads(read(f) or "{}").get("hooks", {})
        except ValueError:
            hooks = {}
        cmds += " ".join(h.get("command", "") for e in hooks.get("PreToolUse", []) for h in e.get("hooks", []))
    if "block-write-tools.py" in cmds and os.path.exists(os.path.join(HOME, "hooks", "block-write-tools.py")):
        return "Read-only guard: active (PreToolUse hook blocks write-looking MCP calls)."
    return f"Read-only guard: NOT configured in {HOME}/settings.json (re-run sh brain/install.sh)."


def main():
    try:
        sys.stdin.read()  # the hook input (session id, source) is not needed
    except Exception:
        pass
    lines = []
    for fn in (library_line, environment_line, memory_line, hook_line):
        try:
            lines.append(fn())
        except Exception:
            pass
    lines.append("Mode: read-only toward infrastructure (arrays, fabrics, UCS, vCenter, host storage): give the user "
                 "the exact commands to run; the user's own code and app deployments are normal work. "
                 "New facts: core ones in notes.md, the rest in notes/<topic>.md.")
    print("Storage brain: " + "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
