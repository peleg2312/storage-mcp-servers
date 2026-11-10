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
USER_HOME = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")   # as the installers, paas-team and notes-check.py
# where the person's memory is: the .claude this hook was installed into (~/.claude, or <project>/.claude), else (the hook runs
# from a team plugin, whose brain/ holds only templates, or from /opt/paas on the multi-user VM) the person's ~/.claude
MEM = HOME if os.path.basename(HOME) == ".claude" and os.path.exists(os.path.join(HOME, "brain", "notes.md")) else USER_HOME
BOOTSTRAPPED = False                       # set when this very session set the team up from the plugin: sync and refresh then wait


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


def team_repo():
    """the git history to sync: the active team's clone (same rule as notes-check.py), else the brain folder"""
    brain = os.path.join(USER_HOME, "brain")
    team = read(os.path.join(brain, "team")).strip()
    if team and re.match(r"^[a-z][a-z0-9_-]{0,31}$", team) and os.path.isdir(os.path.join(brain, "teams", team, ".git")):
        if os.path.isfile(os.path.join(brain, "teams", team, ".git", "paas-external.json")):
            return brain                              # an external brain: its own hooks pull it, nothing is pushed from here
        return os.path.join(brain, "teams", team)
    return brain


def shared_line():
    """Shared brain: the --sync of notes-check.py, 6 s at most (on timeout it is left to finish or fail on its own)."""
    if BOOTSTRAPPED:
        return ""                                    # the clone is seconds old: nothing to sync, and the hook's budget is spent
    brain = team_repo()                               # team mode: the team's clone holds the history
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
        local = os.path.dirname(os.path.dirname(here))            # the plugin runs in place from a clone of the team repository?
        if os.path.isdir(os.path.join(local, ".git")) and os.path.isdir(os.path.join(local, "knowledge")):
            src = local                                           # offline-safe; paas-team keeps GitLab as origin for the syncs
        else:
            src = meta.get("remote") or (market if os.path.isdir(os.path.join(market, ".git")) else "")
        if meta.get("name") and src:               # persona.md missing is the whole condition: a clone that exists is re-applied
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(here), "bin", "paas-team"), "bootstrap", meta["name"], src],
                               stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=25)
            if r.returncode == 0:
                done = r.stdout.strip() + "\n"
                global BOOTSTRAPPED
                BOOTSTRAPPED = True
    except Exception:
        pass
    mine = os.path.join(USER_HOME, "brain")                   # set up: the team's own rules (links into its rules/)
    src = lambda f, tpl: (read(os.path.join(mine, f)) if done else "") or read(os.path.join(b, tpl))
    text = src("main.md", "CLAUDE.md")
    text = re.sub(r"^@~/\.claude/brain/persona\.md\s*$", src("persona.md", "persona.md").strip(), text, flags=re.M)
    text = re.sub(r"^@\S+\s*$\n?", "", text, flags=re.M)      # notes.md and the like do not exist yet
    rules = re.sub(r"^@\S+\s*$\n?", "", src("storage.md", "storage.md"), flags=re.M)
    if done:
        return (done + "First session: these are the brain's rules (from the next session they come from ~/.claude/CLAUDE.md).\n"
                + text.strip() + "\n\n" + rules.strip() + "\n(No docs library yet: install-laptop.sh of storage-mcp-servers adds it.)")
    return ("The team repository could not be reached, so the team's memory is not set up yet (retried at the next session start); "
            "these are the brain's rules for this session.\n"
            + text.strip() + "\n\n" + rules.strip() + "\n(No GitLab from here? Copy a clone of the team repository over and run "
            "`claude plugin marketplace add <that folder>`: the plugin sets the team up from it.)")


def team_line():
    """Team mode (paas-team): which team's brain this is, and a re-apply when its repository brought a new plugin."""
    name = read(os.path.join(USER_HOME, "brain", "team")).strip()
    if not name or not re.match(r"^[a-z][a-z0-9_-]{0,31}$", name):
        shared = os.environ.get("PAAS_TEAMS") or "/opt/paas/teams"           # a VM that offers teams: say how to pick one, once per session
        offered = sorted(d for d in (os.listdir(shared) if os.path.isdir(shared) else []) if re.match(r"^[a-z][a-z0-9_-]{0,31}$", d))
        return f"Team: none (your own rules; {', '.join(offered)} available: Brain tab, Team, one click)." if offered else ""
    tdir = os.path.join(USER_HOME, "brain", "teams", name)
    try:
        ext = json.loads(read(os.path.join(tdir, ".git", "paas-external.json")) or "{}")
    except ValueError:
        ext = {}
    if ext.get("plugin"):                                    # an external brain: kept as it is, its own hooks brief Claude
        return (f"Brain: {name} (external, plugin {ext['plugin']}: its skills are /{ext['plugin']}:<skill>; follow its own "
                f"instructions for its knowledge).")
    try:
        meta = json.loads(next((read(f) for f in sorted(glob.glob(os.path.join(tdir, "paas-brain-*", "team.json")))
                                + [os.path.join(tdir, "team.json")] if read(f)), "") or "{}")   # the plugin's (an older repository: its root copy)
    except ValueError:
        meta = {}
    line = f"Team: {name} ({meta.get('title', name)}, {meta.get('version', '?')})"
    if BOOTSTRAPPED:
        return line + "."
    here = os.path.dirname(os.path.abspath(__file__))        # run from the plugin: its own bin/paas-team is the current one
    own = os.path.join(os.path.dirname(here), "bin", "paas-team") if os.path.exists(os.path.join(here, "hooks.json")) else ""
    tool = next((p for p in (own, os.path.join(USER_HOME, "tools", "paas-team"), "/opt/paas/bin/paas-team",
                             os.path.expanduser("~/.local/bin/paas-team")) if p and os.path.exists(p)), "")
    if tool:
        try:
            if subprocess.run([sys.executable, tool, "needs-refresh"], stdin=subprocess.DEVNULL, capture_output=True,
                              timeout=3).returncode == 0:
                # files and links now; the plugin update (a marketplace fetch on a laptop) runs on in the background
                subprocess.run([sys.executable, tool, "relink", "--background"], stdin=subprocess.DEVNULL, capture_output=True, timeout=12)
                line += " - updated from the team repository: the new version applies to the next session"
        except subprocess.TimeoutExpired:
            pass
    return line + "."


def env_path():
    # multi-user VM: everyone has their own environment.md (started from root's default in /opt/paas/brain, used until then)
    own = os.path.join(MEM, "brain", "environment.md")
    return own if os.path.exists(own) else os.path.join(HOME, "brain", "environment.md")


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


STALE_DAYS = 180


def stale_count(mem):
    """'- ' lines of notes.md and notes/*.md whose first date is older than STALE_DAYS (cheap: a regex per line)"""
    cut = time.time() - STALE_DAYS * 86400
    n = 0
    for f in [os.path.join(mem, "brain", "notes.md")] + glob.glob(os.path.join(mem, "brain", "notes", "*.md")):
        for line in read(f).splitlines():
            m = line.startswith("- ") and re.search(r"(\d{4})-(\d{2})-(\d{2})", line)
            if m:
                try:
                    import calendar
                    if calendar.timegm((int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, 0, 0)) < cut:
                        n += 1
                except (ValueError, OverflowError):
                    pass
    return n


def memory_line():
    """The memory catalog: notes.md is always loaded; the topic files are listed here and read on demand."""
    mem = MEM
    notes = read(os.path.join(mem, "brain", "notes.md"))
    n = len(notes.splitlines())
    line = f"notes.md: {sum(1 for l in notes.splitlines() if l.startswith('- '))} core facts, {n} lines"
    link = os.path.join(mem, "brain", "notes.md")
    if os.path.islink(link):              # team mode: Claude Code does not Write / Edit through a file link, so name the real place
        line += (f" (notes.md, environment.md and tool-map.md are links: edit them at "
                 f"{os.path.dirname(os.path.realpath(link)).replace(os.path.expanduser('~'), '~', 1)}/<file>)")
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
    cap_files = glob.glob(os.path.join(USER_HOME, "brain", "captures", "*.md"))
    caps = len(cap_files)
    if caps:
        oldest = min((time.time() - os.path.getmtime(c)) / 86400 for c in cap_files)
        due = caps >= 5 or oldest > 14
        line += f".\ncaptures: {caps} waiting for curation (brain-learn skill)" + \
            (f" - curation is due ({'5 or more' if caps >= 5 else f'the oldest is {int(oldest)} days old'}): offer it once after his first question" if due else "")
    stale = stale_count(mem)
    if stale:
        line += f".\nstale: {stale} fact(s) older than 180 days; re-verify the ones a question touches (brain-learn marks them verified / observed again)"
    inc = glob.glob(os.path.join(USER_HOME, "brain", "incidents", "**", "*.md"), recursive=True)
    if inc:
        line += f".\nincidents: {len(inc)} under ~/.claude/brain/incidents/ (grep them; brain-learn writes them)"
    books = sorted(glob.glob(os.path.join(mem, "brain", "runbooks", "*.md")))
    if books:
        names = [os.path.basename(b)[:-3] for b in books]
        line += (f".\nrunbooks: {len(books)} tested procedures in ~/.claude/brain/runbooks/ ({', '.join(names[:15])}"
                 + (f", ... {len(names) - 15} more" if len(names) > 15 else "")
                 + "): before giving change steps, read a matching one and follow it")
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
    if MEM != USER_HOME:
        return                                   # a project install never owns ~/chats (a team plugin's hooks do)
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
    d = os.path.join(tempfile.gettempdir(), f"claude-brain-{os.getuid() if hasattr(os, 'getuid') else 'w'}")
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
    # the shared brain is pulled first, so the team line sees a plugin that this very pull brought (printed in the usual order)
    order = (bare_plugin_rules, shared_line, team_line, library_line, environment_line, memory_line, hook_line)
    shown = (bare_plugin_rules, team_line, library_line, environment_line, memory_line, shared_line, hook_line)
    got = {}
    for fn in order:
        try:
            got[fn] = fn()
        except Exception:
            got[fn] = ""
    try:
        chats_rules()                      # after the pull: a rule the team just changed reaches the web UI's plain chats now
    except Exception:
        pass
    lines = [got[fn] for fn in shown]
    print("Storage brain: " + "\n".join(l for l in lines if l))
    return 0



def team_hooks_active():
    """VM: the active team's own hooks, those of its plugin from its git repository, run instead of the VM's copies under
    /opt/paas/hooks, so whatever the team keeps in git is what runs, guard included (removed there: not run). True when
    this is the VM's copy and the active team's plugin (a paas team or an external brain) is enabled for this person."""
    if not os.path.realpath(__file__).startswith("/opt/paas/hooks/"):
        return False                                   # the plugin's own copy (or a single-user install) always runs
    try:
        import json as _j
        import pwd as _pwd                             # the account's own home, not an environment variable a setting could change
        c = os.path.join(_pwd.getpwuid(os.getuid()).pw_dir, ".claude")
        t = open(os.path.join(c, "brain", "team"), encoding="utf-8").read().strip()
        d = os.path.join(c, "brain", "teams", t)
        if not t or not os.path.isdir(d):
            return False
        ext = os.path.join(d, ".git", "paas-external.json")
        if os.path.isfile(ext):
            r = _j.load(open(ext, encoding="utf-8"))
            pid = f"{r['plugin']}@{r['marketplace']}"
        elif os.path.isdir(os.path.join(d, "paas-brain-" + t)):
            pid = f"paas-brain-{t}@paas-brain-{t}"
        else:
            return False
        return _j.load(open(os.path.join(c, "settings.json"), encoding="utf-8")).get("enabledPlugins", {}).get(pid) is True
    except Exception:
        return False

if __name__ == "__main__":
    # VM: the VM's copy steps aside while the active team's plugin brings its own hooks from git (team_hooks_active)
    if len(sys.argv) == 1 and team_hooks_active():
        sys.exit(0)
    try:   # switched off by this person in the web UI (Brain tab, MCP & hooks)
        if "session-start" in open(os.path.expanduser("~/.claude/brain/hooks-off")).read().split():
            sys.exit(0)
    except OSError:
        pass
    sys.exit(main())
