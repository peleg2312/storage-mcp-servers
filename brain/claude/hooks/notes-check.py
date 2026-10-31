#!/usr/bin/env python3
"""Claude Code PostToolUse hook (Edit / Write / MultiEdit) and command-line checker for the brain's notes.
Hook: a file under ~/.claude/brain/ or ~/storage-reports/ is scanned for secrets (private keys, JWTs, tokens,
password = value, AWS keys, -password/-p arguments) and private IPv4 addresses; findings go back to Claude to
replace with <REDACTED>. Silent when clean. A line ending in 'notes-check: allow' (or holding '# allow-ip' for
IPs) is skipped; environment.md and tool-map.md may hold management IPs.
  notes-check.py --scan        scan all notes and captures, exit 1 on findings
  notes-check.py --stale N     list '- ' note lines whose first YYYY-MM-DD is older than N days (informational)"""
import datetime
import glob
import json
import os
import re
import sys

BRAIN = os.path.expanduser("~/.claude/brain")
MAX_LINES = 15
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
        sorted(glob.glob(os.path.join(BRAIN, "captures", "*.md")))


def stale(days):
    cut = datetime.date.today() - datetime.timedelta(days=days)
    n = 0
    for f in note_files():
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


def hook():
    try:
        path = (json.load(sys.stdin).get("tool_input") or {}).get("file_path", "")
    except Exception:
        return 0
    path = os.path.realpath(os.path.expanduser(path)) if path else ""
    roots = [os.path.realpath(p) + os.sep for p in (BRAIN, os.path.expanduser("~/storage-reports"))]
    if not path.startswith(tuple(roots)) or not os.path.isfile(path):
        return 0
    f = findings(path)
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
    return hook()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
