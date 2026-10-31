#!/usr/bin/env python3
"""Claude Code SessionStart hook: prints 3-5 lines of brain status into the session context.
Standard library only; never fails the session (always exit 0, errors are swallowed)."""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time

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


def shared_line():
    """Shared brain: the --sync of notes-check.py, 6 s at most (on timeout it is left to finish or fail on its own)."""
    brain = os.path.join(USER_HOME, "brain")
    team = read(os.path.join(brain, "team")).strip()
    if team and os.path.isdir(os.path.join(brain, "teams", team, ".git")):
        brain = os.path.join(brain, "teams", team)          # team mode: the team's clone holds the history
    nc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes-check.py")
    if not os.path.isdir(os.path.join(brain, ".git")) or not os.path.exists(nc):
        return ""
    if subprocess.run(["git", "-C", brain, "rev-parse", "--abbrev-ref", "@{upstream}"], stdin=subprocess.DEVNULL,
                      capture_output=True, timeout=3).returncode:
        return ""
    try:
        out = subprocess.run([sys.executable, nc, "--sync"], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                             timeout=6).stdout.strip()
    except subprocess.TimeoutExpired:
        return "shared brain: sync still running (offline?)"
    return "shared brain: " + out.replace("brain: ", "", 1) if out else ""


def bare_plugin_rules():
    """The hooks run from a team plugin (hooks.json beside this file) and nothing put the rules in place (no
    ~/.claude/brain/persona.md: a plain `claude plugin install`). First the plugin sets the team up itself (bin/paas-team
    bootstrap: a clone of the team repository as the knowledge folder, links, rules, one import line in CLAUDE.md), so the
    standard plugin install is the whole install and notes flow back to the team; unreachable repository: the plugin's own
    persona and rules are printed as context. Installed brains (persona.md present) pay nothing here."""
    here = os.path.dirname(os.path.abspath(__file__))
    b = os.path.join(os.path.dirname(here), "brain")
    if os.path.exists(os.path.join(USER_HOME, "brain", "persona.md")) or not os.path.exists(os.path.join(here, "hooks.json")) \
            or not os.path.isdir(b):
        return ""
    done = ""
    try:                                   # set the team up from the plugin: knowledge clone (the team repository, from the
        meta = json.loads(read(os.path.join(os.path.dirname(here), "team.json")) or "{}")   # remote recorded by publish.py,
        market = os.path.join(USER_HOME, "plugins", "marketplaces", "paas-brain-" + meta.get("name", ""))  # else the local clone)
        src = meta.get("remote") or (market if os.path.isdir(os.path.join(market, ".git")) else "")
        if meta.get("name") and src and not os.path.exists(os.path.join(USER_HOME, "brain", "team")):
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(here), "bin", "paas-team"), "bootstrap", meta["name"], src],
                               stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=25)
            if r.returncode == 0:
                done = r.stdout.strip() + "\n"
    except Exception:
        pass
    text = read(os.path.join(b, "CLAUDE.md"))
    text = re.sub(r"^@~/\.claude/brain/persona\.md\s*$", read(os.path.join(b, "persona.md")).strip(), text, flags=re.M)
    text = re.sub(r"^@\S+\s*$\n?", "", text, flags=re.M)      # notes.md and the like do not exist yet
    rules = re.sub(r"^@\S+\s*$\n?", "", read(os.path.join(b, "storage.md")), flags=re.M)
    if done:
        return (done + "First session: these are the brain's rules (from the next session they come from ~/.claude/CLAUDE.md).\n"
                + text.strip() + "\n\n" + rules.strip() + "\n(No docs library yet: install-laptop.sh of storage-mcp-servers adds it.)")
    return ("Plugin-only install (no ~/.claude/brain, team repository not reachable): these are the brain's rules for this session.\n"
            + text.strip() + "\n\n" + rules.strip() + "\n(For notes, environment and the docs library run install-team.sh from the team "
            "repository, or install-laptop.sh.)")


def team_line():
    """Team mode (paas-team): which team's brain this is, and a re-apply when its repository brought a new plugin."""
    name = read(os.path.join(USER_HOME, "brain", "team")).strip()
    if not name or not re.match(r"^[a-z][a-z0-9_-]{0,31}$", name):
        return ""
    tdir = os.path.join(USER_HOME, "brain", "teams", name)
    try:
        meta = json.loads(read(os.path.join(tdir, "team.json")) or "{}")
    except ValueError:
        meta = {}
    line = f"Team: {name} ({meta.get('title', name)}, {meta.get('version', '?')})"
    tool = next((p for p in (os.path.join(USER_HOME, "tools", "paas-team"), "/opt/paas/bin/paas-team",
                             os.path.expanduser("~/.local/bin/paas-team")) if os.path.exists(p)), "")
    if tool:
        try:
            if subprocess.run([sys.executable, tool, "needs-refresh"], stdin=subprocess.DEVNULL, capture_output=True,
                              timeout=3).returncode == 0:
                subprocess.run([sys.executable, tool, "refresh"], stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
                line += " - updated from the team repository: new skills apply to the next session"
        except subprocess.TimeoutExpired:
            pass
    return line + "."


def env_path():
    # multi-user VM: everyone has their own environment.md (started from root's default in /opt/paas/brain)
    own = os.path.join(USER_HOME, "brain", "environment.md")
    if not os.path.exists(os.path.join(HOME, "brain", "notes.md")) and os.path.exists(own):
        return own
    return os.path.join(HOME, "brain", "environment.md")


def env_filled(text):
    filled = 0
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or set(cells[0]) <= {"-", ""} or cells[0] in ("Name", "Fabric", "vCenter", "Domain"):
            continue
        if cells[0] and any(cells[1:]):  # a label alone (template rows "| A | | | |") is not filled
            filled += 1
    return filled


def environment_line():
    text = read(env_path())
    if not text:
        return "environment.md: MISSING (run /brain-setup)."
    filled = env_filled(text)
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
    if len(topics) > 25:
        topics = topics[:25] + [f"  ... and {len(topics) - 25} more (grep notes/)"]
    caps = len(glob.glob(os.path.join(USER_HOME, "brain", "captures", "*.md")))
    if caps:
        line += f".\ncaptures: {caps} waiting for curation (brain-learn skill)"
    inc = glob.glob(os.path.join(USER_HOME, "brain", "incidents", "**", "*.md"), recursive=True)
    if inc:
        line += f".\nincidents: {len(inc)} under ~/.claude/brain/incidents/ (grep them; brain-learn writes them)"
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
    # the script the settings run (~/.claude/hooks for one user, /opt/paas/hooks on the shared server) must exist
    # a project install writes "$CLAUDE_PROJECT_DIR"/.claude/hooks/...: expand it to the project dir
    scripts = [os.path.expanduser(re.sub(r'"?\$\{?CLAUDE_PROJECT_DIR\}?"?', lambda m: os.path.dirname(HOME), p))
               for p in re.findall(r"(\S*block-write-tools\.py)", cmds)]
    if any(os.path.exists(p) for p in scripts):
        return ""                                # healthy: say nothing
    # laptop install: the hooks run from the paas-brain plugin, registered by its own hooks.json next to this file
    here = os.path.dirname(os.path.abspath(__file__))
    if "block-write-tools.py" in read(os.path.join(here, "hooks.json")) and \
            os.path.exists(os.path.join(here, "block-write-tools.py")):
        return ""
    return f"Read-only guard: NOT configured in {HOME}/settings.json (re-run sh brain/install.sh)."


CHATS_MARK = "<!-- generated by the brain (session-start hook)"


def chats_rules():
    """~/chats (plain chats of the web UI) gets the storage rules, environment and tool map as one generated
    CLAUDE.md, refreshed when a source changes; code projects load only the core ~/.claude/CLAUDE.md. A copy, not an
    @import: an import from outside the folder waits for an approval dialog the web UI never shows."""
    chats = os.path.expanduser("~/chats")
    dst = os.path.join(chats, "CLAUDE.md")
    storage = next((p for p in (os.path.join(USER_HOME, "brain", "storage.md"), os.path.join(HOME, "brain", "storage.md"))
                    if os.path.exists(p)), None)
    if HOME != USER_HOME and os.path.exists(os.path.join(HOME, "brain", "notes.md")):
        return                                   # a project install never owns ~/chats
    if not storage or not os.path.isdir(chats) or (os.path.exists(dst) and not read(dst, 200).startswith(CHATS_MARK)):
        return                                   # no brain storage rules, no Chats folder, or a CLAUDE.md of his own
    srcs = [storage, env_path(), os.path.join(USER_HOME, "brain", "tool-map.md")]
    if os.path.exists(dst) and all(os.path.getmtime(p) <= os.path.getmtime(dst) for p in srcs if os.path.exists(p)):
        return
    text = re.sub(r"^@\S+\s*$\n?", "", read(storage), flags=re.M)
    parts = [f"{CHATS_MARK} from ~/.claude/brain/storage.md, environment.md and tool-map.md: edit those) -->", text]
    # the blank environment.md template is not worth its bytes; the hook line already says to fill it in
    parts += [read(p) for p in srcs[1:] if os.path.exists(p) and (p != srcs[1] or env_filled(read(p)))]
    tmp = dst + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n\n".join(x.strip() for x in parts if x.strip()) + "\n")
    os.replace(tmp, dst)


def prune_tmp():
    """Delete files older than 7 days in the private dir docs-leads / docs-hints use for seen files and caches."""
    d = os.path.join(tempfile.gettempdir(), f"claude-brain-{os.getuid()}")
    for name in os.listdir(d):
        p = os.path.join(d, name)
        if os.path.isfile(p) and time.time() - os.lstat(p).st_mtime > 7 * 86400:
            os.remove(p)


def main():
    try:
        sys.stdin.read()  # the hook input (session id, source) is not needed
    except Exception:
        pass
    try:
        prune_tmp()
    except Exception:
        pass
    try:
        chats_rules()
    except Exception:
        pass
    lines = []
    for fn in (bare_plugin_rules, team_line, library_line, environment_line, memory_line, shared_line, hook_line):
        try:
            lines.append(fn())
        except Exception:
            pass
    print("Storage brain: " + "\n".join(l for l in lines if l))
    return 0


if __name__ == "__main__":
    try:   # switched off by this person in the web UI (Brain tab, MCP & hooks)
        if "session-start" in open(os.path.expanduser("~/.claude/brain/hooks-off")).read().split():
            sys.exit(0)
    except OSError:
        pass
    sys.exit(main())
