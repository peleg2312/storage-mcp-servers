#!/usr/bin/env python3
"""Claude Code PostToolUse hook (Edit / Write / MultiEdit) and command-line checker for the brain's notes.
Hook: a file under ~/.claude/brain/ or ~/storage-reports/ is scanned for secrets (private keys, JWTs, tokens,
password = value, AWS keys, -password/-p arguments) and private IPv4 addresses; findings go back to Claude to
replace with <REDACTED>. Silent when clean. A line ending in 'notes-check: allow' (or holding '# allow-ip' for
IPs) is skipped; environment.md and tool-map.md may hold management IPs. A file saved under the
brain is also committed to the brain's git history ('brain: <path>') when ~/.claude/brain/.git exists; silent.
  notes-check.py --scan        scan all notes, captures and incidents, exit 1 on findings
  notes-check.py --commit MSG  commit everything changed in the brain (silent, exit 0)
  notes-check.py --remote URL  set up the shared brain: origin = URL, pull what the team has, push ours (idempotent)
  notes-check.py --sync        pull --rebase and push the shared brain; 'brain: in sync' / 'N ahead, M behind'
  notes-check.py --stale N     list '- ' note lines whose first YYYY-MM-DD is older than N days (informational)"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys

BRAIN = os.path.join(os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude"), "brain")   # as the installers and paas-team
MAX_LINES = 15


def team_repo():
    """Team mode (paas-team): the knowledge files are links into ~/.claude/brain/teams/<team>, a clone of the team's
    repository; that is the history to commit to and sync. Otherwise the brain folder itself."""
    try:
        t = open(os.path.join(BRAIN, "team"), encoding="utf-8").read().strip()
    except OSError:
        return BRAIN
    d = os.path.join(BRAIN, "teams", t)
    return d if t and os.path.isdir(os.path.join(d, ".git")) else BRAIN


REPO = team_repo()
SECRET = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"eyJhbGciOi[\w-]{5,}\.[\w-]+"), "JWT"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"), "bearer token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bsha256~[\w-]{20,}"), "OpenShift token"),
    (re.compile(r"(?i)\b(?:symcfg|symaccess|symcli|sshpass)\b.*\s-(?:password|p)\s+(?!<)\S+"), "password argument"),  # ssh -p is a port
    # a value with a digit or a symbol: "password=hunter2" yes, "token: in the vault" no
    (re.compile(r"""(?i)\b(?:password|passwd|secret|token)\b["']?\s*[=:]\s*["']?(?!<[^>]*>|REDACTED)(?=[^\s"',;]*[\d_@#$%^&*+/=!?-])[^\s"',;]{6,}"""), "credential value"),
]
IP = re.compile(r"\b(?:10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|192\.168(?:\.\d{1,3}){2})\b")


def findings(path):
    out = []
    ips = os.path.basename(path) not in ("environment.md", "tool-map.md")
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return out
    for n, line in enumerate(lines, 1):
        if line.rstrip().endswith("notes-check: allow"):
            continue
        for rx, what in SECRET:
            if rx.search(line):
                out.append(f"{path}:{n}: {what}")
                break
        else:
            if ips and "# allow-ip" not in line and IP.search(line):
                out.append(f"{path}:{n}: private IP address")
    return out


def note_files():
    return [os.path.join(BRAIN, "notes.md")] + sorted(glob.glob(os.path.join(BRAIN, "notes", "*.md"))) + \
        sorted(glob.glob(os.path.join(BRAIN, "captures", "*.md"))) + \
        sorted(glob.glob(os.path.join(BRAIN, "incidents", "**", "*.md"), recursive=True))


def stale(days):
    cut = datetime.date.today() - datetime.timedelta(days=days)
    n = 0
    for f in note_files():
        if os.sep + "incidents" + os.sep in f:
            continue                       # --stale: notes and captures only
        try:
            lines = open(f, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            m = line.startswith("- ") and re.search(r"\d{4}-\d{2}-\d{2}", line)
            try:
                if m and datetime.date.fromisoformat(m.group()) < cut:
                    print(f"{f}:{i}: {m.group()} {line[2:].strip()}")
                    n += 1
            except ValueError:
                pass
    print(f"{n} stale lines")
    return 0


def commit(message, rel=None):
    """Brain history: git add + commit, 4 s each, every error swallowed. Not a repository: nothing happens."""
    if not os.path.isdir(os.path.join(REPO, ".git")):
        return
    ident = ["-c", "user.name=brain", "-c", "user.email=brain@localhost"]
    try:
        for cmd in (["add", "-A"] + (["--", rel] if rel else []), ident + ["commit", "-q", "-m", message]):
            subprocess.run(["git", "-C", REPO] + cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=4)
        if upstream():       # a failed push is retried by the next --sync or session start; never a credential prompt
            subprocess.run(["git", "-C", REPO, "push", "-q"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=4, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    except Exception:
        pass


def git(args, timeout=15):
    """(exit code, stdout+stderr) of a git command in the brain's repository; 124 on timeout."""
    try:
        r = subprocess.run(["git", "-C", REPO, "-c", "user.name=brain", "-c", "user.email=brain@localhost"] + args,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 124, str(e)


def upstream():
    return os.path.isdir(os.path.join(REPO, ".git")) and git(["rev-parse", "--abbrev-ref", "@{upstream}"], 3)[0] == 0


def conflict():
    """Abort the rebase and say which files clashed."""
    files = git(["diff", "--name-only", "--diff-filter=U"], 5)[1].split()
    git(["rebase", "--abort"], 10)
    where = REPO.replace(os.path.expanduser("~"), "~", 1)
    print("brain: conflict with the shared brain in: " + (", ".join(files) or "?") + f"; resolve it in {where} "
          "with git, then run notes-check.py --sync")
    return 1


def counts():
    rc, out = git(["rev-list", "--left-right", "--count", "HEAD...@{upstream}"], 5)
    a, b = (out.split() + ["0", "0"])[:2] if rc == 0 else ("0", "0")
    return "brain: in sync" if (a, b) == ("0", "0") else f"brain: {a} ahead, {b} behind"


def remote(url):
    if not os.path.isdir(os.path.join(REPO, ".git")):
        print("brain: ~/.claude/brain is not a git repository (run install.sh)")
        return 1
    git(["remote", "set-url", "origin", url] if git(["remote", "get-url", "origin"], 3)[0] == 0
        else ["remote", "add", "origin", url], 5)
    commit("brain: before joining the shared brain")
    rc, out = git(["fetch", "origin"], 20)
    if rc:
        print("brain: cannot reach the shared remote: " + out.splitlines()[-1][:200] if out else "brain: fetch failed")
        return 1
    if git(["rev-parse", "--verify", "-q", "origin/main"], 5)[0] == 0:
        rc, out = git(["pull", "--rebase", "--allow-unrelated-histories", "origin", "main"], 60)
        if rc:
            return conflict()
    rc, out = git(["push", "-u", "origin", "HEAD:main"], 20)
    print("brain: shared remote set; " + ("pushed" if rc == 0 else "push failed: " + out.splitlines()[-1][:200]))
    return 0 if rc == 0 else 1


def unstick():
    """a rebase left behind by a killed or crashed earlier run (rebase-merge / rebase-apply folder) is aborted first"""
    gitdir = git(["rev-parse", "--git-dir"], 3)[1]
    gitdir = gitdir if os.path.isabs(gitdir) else os.path.join(REPO, gitdir)
    for d in ("rebase-merge", "rebase-apply"):
        if os.path.isdir(os.path.join(gitdir, d)):
            git(["rebase", "--abort"], 10)
            if os.path.isdir(os.path.join(gitdir, d)):           # too broken for git to abort: git's own advice is to remove it
                import shutil
                shutil.rmtree(os.path.join(gitdir, d), ignore_errors=True)


def sync():
    if not upstream():
        print("brain: no shared remote")
        return 0
    unstick()
    commit("brain: update")                          # whatever is uncommitted goes in first
    rc, out = git(["pull", "--rebase", "--autostash", "-q"], 15)
    if rc == 124:                                    # killed mid-rebase: leave a usable tree, try again next time
        git(["rebase", "--abort"], 10)
        print("brain: sync timed out (remote slow or unreachable); nothing changed, the next sync retries")
        return 0
    if rc and git(["diff", "--name-only", "--diff-filter=U"], 5)[1]:
        return conflict()
    git(["push", "-q"], 15)                          # offline is not an error
    print(counts())
    return 0


def hook():
    try:
        path = (json.load(sys.stdin).get("tool_input") or {}).get("file_path", "")
    except Exception:
        return 0
    path = os.path.realpath(os.path.expanduser(path)) if path else ""
    roots = [os.path.realpath(p) + os.sep for p in (BRAIN, os.path.expanduser("~/storage-reports"))]
    if not path.startswith(tuple(roots)) or not os.path.isfile(path) or os.path.basename(path) == "mcp.json":
        return 0                                   # a team's mcp.json carries its servers' tokens by the owner's decision
    f = findings(path)
    repo = os.path.realpath(REPO) + os.sep         # team mode: the real file lives in the team clone
    if path.startswith(repo) and not f:            # a file holding a secret is not committed: the redacted save is
        commit("brain: " + path[len(repo):], path[len(repo):])
    if f:
        more = f"\n... and {len(f) - MAX_LINES} more" if len(f) > MAX_LINES else ""
        print(f"{os.path.basename(path)} holds {len(f)} secret(s) or real location(s); replace each value with "
              "<REDACTED> or a placeholder now:\n" + "\n".join(f[:MAX_LINES]) + more)
    return 0


def main():
    a = sys.argv[1:]
    if a[:1] == ["--scan"]:
        f = [x for p in note_files() for x in findings(p)]
        print("\n".join(f))
        return 1 if f else 0
    if a[:1] == ["--stale"]:
        return stale(int(a[1]) if len(a) > 1 and a[1].isdigit() else 180)
    if a[:1] == ["--remote"] and len(a) > 1:
        return remote(a[1])
    if a[:1] == ["--sync"]:
        return sync()
    if a[:1] == ["--commit"]:
        commit(a[1] if len(a) > 1 else "brain: update")
        return 0
    return hook()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
