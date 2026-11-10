#!/usr/bin/env python3
"""External brains that opt in to learning: what Claude learns is kept in the brain's own git, in its own folders and by
its own guide, instead of the person's private notes - as a team built here shares its notes, but the brain's way.

Switched on by "learn" in the brain's brain.json, in root's /opt/paas/teams/<name>.brain.json or in the clone's
.git/paas-brain.json (paas-team learn <brain> merge-request|push|off writes it). paas-team works out the folders (its
notes / runbooks / incidents / captures, or the ones "learn" names) and its guide (LEARNING.md, or "learn": {"guide"}),
and keeps them in the clone's .git/paas-external.json. Three hooks use this module and keep running for such a brain on
the VM, while its other hooks step aside for the brain's own:
  session-start.py  refreshes the copy Claude writes in, says where to save and by which guide, lists its runbooks and
                    note topics
  notes-check.py    a page saved in those folders: scanned for secrets, committed as the person, then pushed to the
                    brain's branch ("save": "push") or sent to its GitLab as a merge request from the person's branch
                    learn/<user> ("save": "merge-request", the default: its team reviews what Claude learned)
  capture-nudge.py  after a long session that saved nothing there, asks once for a capture in its captures folder
The brain's own hooks still run too (they may ask for more; a page they commit themselves is simply not committed again).
Standard library; every error is swallowed: a hook never breaks a session."""
import getpass
import json
import os
import re
import socket
import subprocess
import sys

KINDS = ("notes", "runbooks", "incidents", "captures")
NAME = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


def home():
    return os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")


def jload(p):
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def git(repo, *args, timeout=20, env=None):
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0", **(env or {})))
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:                                   # no git, a timeout
        return 124, str(e)


def origin(repo):
    """origin url from .git/config itself (root's copies on the VM belong to another account, where git refuses)"""
    m = re.search(r'^\s*\[remote\s+"origin"\]\s*$(.*?)(?=^\s*\[|\Z)', read(os.path.join(repo, ".git", "config")), re.M | re.S)
    u = re.search(r"^\s*url\s*=\s*(\S.*?)\s*$", m.group(1), re.M) if m else None
    return u.group(1) if u else ""


def same_remote(a, b):
    norm = lambda u: re.sub(r"(\.git)?/*$", "", re.sub(r"://[^/@]+@", "://", (u or "").strip())).lower()
    return bool(a and b) and norm(a) == norm(b)


def raw_learn(clone):
    """the "learn" setting where paas-team reads it (the brain's brain.json, root's <name>.brain.json, the clone's
    .git/paas-brain.json; the later wins), or None when none sets it"""
    srcs = [os.path.join(clone, "brain.json")]
    teams = os.environ.get("PAAS_TEAMS") or "/opt/paas/teams"
    mine = origin(clone)
    try:
        for f in sorted(os.listdir(teams)) if mine and os.path.isdir(teams) else []:
            if f.endswith(".brain.json") and same_remote(origin(os.path.join(teams, f[:-len(".brain.json")])), mine):
                srcs.append(os.path.join(teams, f))
                break
    except OSError:
        pass
    srcs.append(os.path.join(clone, ".git", "paas-brain.json"))
    val = None
    for f in srcs:
        d = jload(f)
        if "learn" in d:
            val = d["learn"]
    return val


def is_on(raw):
    return raw not in (None, False, "", "off", "no")


def tool():
    return next((p for p in (os.environ.get("PAAS_TEAM_TOOL", ""), os.path.join(home(), "tools", "paas-team"), "/opt/paas/bin/paas-team",
                             os.path.expanduser("~/.local/bin/paas-team")) if p and os.path.isfile(p)), "")


def config(refresh=False):
    """the active external brain's learning, or None. refresh (session start): when root or the brain changed "learn" since
    the last switch, paas-team works the folders out again first"""
    b = os.path.join(home(), "brain")
    team = read(os.path.join(b, "team")).strip()
    if not NAME.match(team):
        return None
    clone = os.path.join(b, "teams", team)
    recp = os.path.join(clone, ".git", "paas-external.json")
    rec = jload(recp)
    if not rec.get("plugin"):
        return None
    raw = raw_learn(clone)
    lay = rec.get("learn") if isinstance(rec.get("learn"), dict) else None
    if refresh and (is_on(raw) != bool(lay) or (lay and lay.get("raw") != raw)) and tool():
        try:
            subprocess.run([sys.executable, tool(), "relayout", team], capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        except Exception:
            pass
        rec = jload(recp)
        lay = rec.get("learn") if isinstance(rec.get("learn"), dict) else None
    if not is_on(raw) or not lay or lay.get("save") not in ("push", "merge-request"):
        return None
    try:
        login = getpass.getuser()
    except Exception:
        login = os.environ.get("USER") or "user"
    user = re.sub(r"[^a-z0-9._-]+", "-", login.lower()).strip("-.") or "user"
    root = clone if lay["save"] == "push" else os.path.join(b, "teams", ".learn-" + team)
    rel = {k: str(lay.get(k) or k) for k in KINDS}
    return {"team": team, "title": str(rec.get("title") or team), "clone": clone, "root": root, "save": lay["save"],
            "branch": str(lay.get("branch") or "main"), "user": user, "login": login, "learn_branch": "learn/" + user,
            "rel": rel, "paths": {k: os.path.join(root, v) for k, v in rel.items()},
            "guide": os.path.join(root, lay["guide"]) if lay.get("guide") else ""}


def identity(repo):
    """the person's own git identity when configured, else <login>@<host>: the brain's history says who learned what"""
    rc, out = git(repo, "config", "--get-regexp", r"^user\.(name|email)$", timeout=5)
    have = {l.split()[0] for l in out.splitlines() if l.strip()} if rc == 0 else set()
    try:
        name = getpass.getuser()
    except Exception:
        name = os.environ.get("USER") or "brain"
    env = {}
    if "user.name" not in have:
        env.update(GIT_AUTHOR_NAME=name, GIT_COMMITTER_NAME=name)
    if "user.email" not in have:
        env.update(GIT_AUTHOR_EMAIL=f"{name}@{socket.gethostname()}", GIT_COMMITTER_EMAIL=f"{name}@{socket.gethostname()}")
    return env


def ensure_root(c):
    """merge-request mode: the person's worktree on branch learn/<user> (beside the clone, so the clone's own branch stays
    exactly the brain's): created from the remote branch when it exists (work from another machine), else from the
    brain's branch. True when it is there."""
    wt = c["root"]
    if c["save"] == "push" or os.path.exists(os.path.join(wt, ".git")):
        return True
    clone, lb = c["clone"], c["learn_branch"]
    git(clone, "fetch", "-q", "origin", timeout=60)
    base = next((r for r in ("origin/" + lb, "origin/" + c["branch"], "HEAD") if git(clone, "rev-parse", "-q", "--verify", r + "^{commit}")[0] == 0), "HEAD")
    git(clone, "worktree", "prune")
    rc, _ = git(clone, "worktree", "add", "-q", "-B", lb, wt, base, timeout=60)
    if rc == 0:
        git(wt, "branch", "-q", "--unset-upstream")
    return rc == 0


def refresh(c):
    """session start: the copy Claude writes in brought up to the brain's branch, and anything not sent yet sent"""
    root, target = c["root"], "origin/" + c["branch"]
    if not ensure_root(c):
        return "the learning copy could not be made (git worktree)"
    git(root, "fetch", "-q", "origin", timeout=60)
    dirty = bool(git(root, "status", "--porcelain", timeout=10)[1])
    if git(root, "rev-parse", "-q", "--verify", target)[0] != 0:
        return ""                                        # no remote branch (offline, or a brain with no remote)
    n = git(root, "rev-list", "--count", f"{target}..HEAD")[1].strip()
    ahead = int(n) if n.isdigit() else 0
    if c["save"] == "push":
        if not dirty:
            git(root, "pull", "-q", "--rebase", "origin", c["branch"], timeout=60)
        return send(c) if ahead else ""
    if dirty:
        return send(c) if ahead else ""
    learned = [c["rel"][k] for k in KINDS]
    if ahead == 0 or git(root, "diff", "--quiet", target, "HEAD", "--", *learned)[0] == 0:
        git(root, "reset", "-q", "--hard", target)       # nothing pending, or all of it merged: start from the brain's branch
        return ""
    if git(root, "rebase", "-q", target, timeout=60)[0] != 0:
        git(root, "rebase", "--abort")                   # a clash with what the team changed: the merge request shows it
    return send(c)


def send(c):
    """push what was committed: to the brain's branch, or to learn/<user> with a merge request (GitLab push options).
    Returns one line for Claude when something needs the person; "" when it went through."""
    root, marker = c["root"], os.path.join(c["clone"], ".git", "paas-learn-failed")
    if c["save"] == "push":
        rc, out = git(root, "push", "-q", "origin", "HEAD:refs/heads/" + c["branch"], timeout=30)
        if rc not in (0, 124) and ("rejected" in out or "non-fast-forward" in out or "fetch first" in out):
            if git(root, "pull", "-q", "--rebase", "origin", c["branch"], timeout=60)[0] == 0:
                rc, out = git(root, "push", "-q", "origin", "HEAD:refs/heads/" + c["branch"], timeout=30)
            else:
                git(root, "rebase", "--abort")
        msg = "" if rc == 0 else f"saved here, not pushed to {c['title']}'s git yet ({reason(out)}); it is sent again at the next save or session start"
    else:
        opts = ["-o", "merge_request.create", "-o", "merge_request.target=" + c["branch"],
                "-o", f"merge_request.title=Learned in chats ({c['login']})", "-o", "merge_request.remove_source_branch"]
        dest = "HEAD:refs/heads/" + c["learn_branch"]
        rc, out = git(root, "push", "-q", "--force-with-lease", "origin", dest, *opts, timeout=30)
        if rc != 0 and "push option" in out.lower():     # not GitLab: the branch alone, the person opens the merge request
            rc, out = git(root, "push", "-q", "--force-with-lease", "origin", dest, timeout=30)
            if rc == 0:
                msg = f"sent to {c['title']}'s git as branch {c['learn_branch']}: its server makes no merge request by itself, open one there"
                write_marker(marker, "")
                return msg
        msg = "" if rc == 0 else f"saved here, not sent to {c['title']}'s git yet ({reason(out)}); it is sent again at the next save or session start"
    write_marker(marker, "" if rc == 0 else msg)
    return msg


def write_marker(p, text):
    try:
        if text:
            with open(p, "w", encoding="utf-8") as f:
                f.write(text + "\n")
        elif os.path.exists(p):
            os.remove(p)
    except OSError:
        pass


def reason(out):
    low = out.lower()
    if any(k in low for k in ("authentication", "could not read username", "permission denied", "403", "401", "terminal prompts")):
        return "no GitLab credential: root runs paas-user git-token <host> once, or set your own"
    if "protected branch" in low or "pre-receive hook declined" in low:
        return "its branch is protected: ask root to switch it to merge requests (paas-team learn <brain> merge-request)"
    return re.sub(r"://[^/@]+@", "://", (out.strip().splitlines() or ["no answer"])[-1])[:160]


def handles(c, path):
    """a page in one of the brain's learning folders, inside the copy Claude writes in"""
    p = os.path.realpath(path) if path else ""
    return any(p.startswith(os.path.realpath(d) + os.sep) for d in c["paths"].values()) and os.path.isfile(p)


def saved(c, path, findings):
    """notes-check.py: a page saved in a learning folder. A page with a secret is not committed (the redacted save is)."""
    p = os.path.realpath(path)
    f = findings(p)
    if f:
        print(f"{os.path.basename(p)} holds {len(f)} secret(s) or real location(s); replace each value with <REDACTED> or a "
              "placeholder now:\n" + "\n".join(f[:15]))
        return 0
    root = os.path.realpath(c["root"])
    rel = os.path.relpath(p, root)
    git(root, "add", "--", rel, timeout=10)
    if git(root, "diff", "--cached", "--quiet", "--", rel)[0] != 0:   # changed (the brain's own hook may have committed it already)
        git(root, "commit", "-q", "-m", f"learn: {rel}", "--", rel, timeout=10, env=identity(root))
    msg = send(c)
    say(msg or (f"saved in {c['title']}'s git" if c["save"] == "push"
                else f"sent to {c['title']}'s git for review (merge request from {c['learn_branch']})"))
    return 0


def say(text):
    """a line Claude reads after the tool call"""
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}))


def listing(d, limit=25):
    try:
        names = sorted(n[:-3] for n in os.listdir(d) if n.endswith(".md") and not n.lower().startswith(("readme", "_template")))
    except OSError:
        return ""
    return ", ".join(names[:limit]) + (f", ... {len(names) - limit} more" if len(names) > limit else "") if names else ""


def session_text(c, problem=""):
    p, how = c["paths"], ("pushed to its git at once" if c["save"] == "push" else
                          f"sent to its git as a merge request for its team to review (your branch {c['learn_branch']}; "
                          "your pages wait there until merged and you keep seeing them here)")
    lines = [f"Learning for the {c['title']} brain is ON: what you learn is kept in its own git, {how}. Its folders replace "
             "~/.claude/brain for that (golden rule 6), and a saved page is committed for you:",
             f"- facts, quirks, owners, thresholds: {p['notes']}/<topic>.md (one dated line: date - fact - confidence - source)",
             f"- a fix or root cause not yet sure: {p['captures']}/<YYYY-MM-DD>-<slug>.md (symptom, cause, fix, scope, how we know, confidence)",
             f"- a change procedure the user ran and confirmed: {p['runbooks']}/<topic>-<task>.md (## Pre-checks, ## Procedure, "
             "## Verification, ## Rollback, ## Scope, ## History; every command for the user to run)",
             f"- an incident: {p['incidents']}/<YYYY>/<YYYY-MM-DD>-<slug>.md",
             "Never passwords, tokens or real credentials: a page holding one is not committed."]
    if c["guide"] and os.path.isfile(c["guide"]):
        lines.append(f"{c['title']}'s own rules for what to keep and how: read {c['guide']} before the first save and follow it "
                     "over the formats above (its folders and names win).")
    books = listing(p["runbooks"])
    if books:
        lines.append(f"runbooks ({p['runbooks']}): {books}: before giving change steps, read a matching one and follow it")
    topics = listing(p["notes"])
    if topics:
        lines.append(f"note topics ({p['notes']}): {topics}: read the one a question touches first")
    if problem:
        lines.append("note: " + problem)
    return "\n".join(lines)


def session_start(c):
    """session-start.py: refresh, then the lines above as the session's context"""
    problem = ""
    try:
        problem = refresh(c)
    except Exception as e:
        problem = f"learning copy not refreshed ({e})"
    print(session_text(c, problem))
    return 0


def nudge_reason(c):
    return (f"This was a substantial session and nothing was saved in {c['title']}'s learning folders. Check whether it produced "
            "durable, non-obvious knowledge: a root cause, a workaround, a quirk of this environment, a procedure that worked, "
            f"a wrong assumption corrected. If yes, write it as a capture in {c['paths']['captures']}/<YYYY-MM-DD>-<slug>.md "
            "(or a note / runbook where the session start said)"
            + (f", following {c['guide']}" if c["guide"] and os.path.isfile(c["guide"]) else "")
            + ", and tell the user in two lines. If not, reply with one short line saying nothing needed saving and stop. "
            "Do not repeat your previous answer.")


def saved_this_session(c, transcript):
    """a page written into a learning folder this session (a mention of the path in prose does not count)"""
    for d in c["paths"].values():
        if re.search(r'"file_path"\s*:\s*"' + re.escape(d.replace("\\", "/")) + "/", transcript.replace("\\\\", "/")):
            return True
    return False
