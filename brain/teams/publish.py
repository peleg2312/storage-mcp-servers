#!/usr/bin/env python3
"""Publish a team's brain as a team repository: the plugin (built by brain/plugin/build.py) plus the team's shared
knowledge folder, in one git repository people clone (paas-team add) and Claude Code installs from
(claude plugin marketplace add <url>).
  publish.py <team> --to <dir>        build into <dir> (git init on first use), commit the new plugin
  publish.py <team> --to <git-url>    clone the team repository (an empty GitLab project is fine), rebuild the
                                      plugin, commit, push; the url is recorded as the team's knowledge remote
  publish.py --all --to <parent-dir>  every team of brain/teams into <parent>/<team> (install-shared.sh)
  options: --remote <url>  record another url as the remote members clone and push to
           --no-hooks      the plugin without hooks (a VM whose hooks are managed settings)
           --no-commit     leave the files uncommitted
           --force         replace a plugin that members changed from the Brain tab (their edits are dropped)
Layout of a team repository:
  .claude-plugin/marketplace.json   paas-brain-<team>/ (the plugin, replaced on every publish)
  knowledge/{notes,captures,incidents}/ + notes.md, environment.md, tool-map.md   (the team's memory, shared by every member)
  mcp.json   the team's live MCP servers with address and token (the owner's decision: readable by everyone in the
             project; use read-only tokens and rotate them when someone leaves); HOST / TOKEN placeholders until filled
  team.json (name, title, remote)   README.md   .gitignore
  install-team.sh + bin/paas-team   a laptop installs the team from the clone alone (no storage-mcp-servers checkout):
                                    git clone <url> && sh <clone>/install-team.sh
  check.py + .gitlab-ci.yml         the repository's own gate (JSON, plugin shape, skills, no secrets in knowledge, caps)
Standard library, Python 3.9."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BRAIN, "plugin"))
import build  # noqa: E402  (brain/plugin/build.py)

IGNORE = "*.bak\n.DS_Store\n._*\n__pycache__/\n"
CATALOG = os.path.join(BRAIN, "marketplace", "mcp.json")        # the servers' shapes (HOST / TOKEN placeholders)
IDENT = ["-c", "user.name=brain", "-c", "user.email=brain@localhost"]


def git(repo, *args, check=False, timeout=120):
    r = subprocess.run(["git", "-C", repo] + IDENT + list(args), capture_output=True, text=True, timeout=timeout,
                       env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    if check and r.returncode:
        sys.exit(f"publish.py: git {' '.join(args)} failed: {(r.stderr or r.stdout).strip()[-300:]}")
    return r


def is_url(s):
    return "://" in s or (":" in s and not os.path.exists(s) and not s.startswith((".", "/")))


def readme(team, remote):
    t = team
    url = remote or "<this repository>"
    return (f"# Team brain: {t.get('title', t['name'])}\n\n{t.get('description', '')}\n\n"
            f"- `paas-brain-{t['name']}/`: the brain as a Claude Code plugin ({len(t['skills'])} skills, {len(t['agents'])} agents, "
            f"version {t['version']}); rebuilt by `brain/teams/publish.py` from the storage-mcp-servers repository\n"
            "- `knowledge/`: what the team learns (notes/<topic>.md, captures/, incidents/, tool-map.md), written by every "
            "member's brain and synced through this repository; notes.md and environment.md are personal and never committed\n\n"
            "## Install on a laptop (Claude Code installed; macOS or Linux)\n\n"
            f"```sh\ngit clone {url} brain-{t['name']} && sh brain-{t['name']}/install-team.sh\n```\n"
            "Rules, skills, agents, hooks and the team's knowledge, synced with this repository; `paas-team` shows the state, "
            "`paas-team use <other>` switches team. Without the docs library (`install-laptop.sh` of storage-mcp-servers adds it) "
            "the docs-local MCP server stays disconnected and the brain says so.\n"
            f"Plugin only (no rules, no knowledge): `claude plugin marketplace add {url} && claude plugin install "
            f"paas-brain-{t['name']}@paas-brain-{t['name']}`.\n\n"
            f"On the VM: `paas-team use {t['name']}` (or the Brain tab).\n")


INSTALL_TEAM = r"""#!/bin/sh
# Install this team's brain on a laptop from this clone alone: the plugin paas-brain-<team> (skills, agents, hooks,
# docs-local), the rules (persona + storage rules + core CLAUDE.md as ~/.claude/brain/main.md, one import line in your own
# ~/.claude/CLAUDE.md) and the team's knowledge folder, kept in sync with this repository. Needs: claude, python3, git.
#   git clone <url> brain-<team> && sh brain-<team>/install-team.sh        update: git -C brain-<team> pull && sh .../install-team.sh
# No docs library here (install-laptop.sh of storage-mcp-servers adds it); docs-local stays disconnected until then.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
TEAM=$(sed -n 's/^ *"name": *"\([a-z0-9_-]*\)".*//p' "$HERE/team.json" | head -n1)
[ -n "$TEAM" ] || { echo "install-team.sh: no team name in $HERE/team.json"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }
command -v claude >/dev/null 2>&1 || { echo "claude (Claude Code) is required: install it first, then run this again"; exit 1; }
DST=${CLAUDE_HOME:-$HOME/.claude}; B=$DST/brain
mkdir -p "$DST/tools" "$B" "$HOME/storage-reports"
cp "$HERE/bin/paas-team" "$DST/tools/paas-team"; chmod 755 "$DST/tools/paas-team"
mkdir -p "$HOME/.local/bin" && ln -sf "$DST/tools/paas-team" "$HOME/.local/bin/paas-team"
cp "$HERE/paas-brain-$TEAM/brain/CLAUDE.md" "$B/main.md"
cp "$HERE/paas-brain-$TEAM/brain/coding.md" "$B/coding.md"
touch "$DST/CLAUDE.md"
grep -qxF '@~/.claude/brain/main.md' "$DST/CLAUDE.md" || printf '
@~/.claude/brain/main.md
' >> "$DST/CLAUDE.md"
echo plugin > "$B/team-mode"
if [ -d "$B/teams/$TEAM/.git" ]; then git -C "$B/teams/$TEAM" pull -q --rebase --autostash || echo "note: pull of the team clone failed (offline?)"
else python3 "$DST/tools/paas-team" add "$TEAM" "$HERE"; fi
ORIGIN=$(git -C "$HERE" remote get-url origin 2>/dev/null || true)
[ -z "$ORIGIN" ] || python3 "$DST/tools/paas-team" remote "$TEAM" "$ORIGIN" >/dev/null
python3 "$DST/tools/paas-team" use "$TEAM"
echo "Rules: @~/.claude/brain/main.md in $DST/CLAUDE.md. Check: claude plugin list (paas-brain-$TEAM enabled); in claude: /brain-setup"
"""



def publish(team, dest, remote=None, hooks=True, commit=True, force=False):
    """build the team into the repository at dest (a directory); returns the plugin's team.json data"""
    os.makedirs(dest, exist_ok=True)
    if not os.path.isdir(os.path.join(dest, ".git")):
        git(dest, "init", "-q", "-b", "main", check=True)
    plugdir = os.path.join(dest, "paas-brain-" + team)
    if os.path.isdir(os.path.join(dest, ".git")) and os.path.isdir(plugdir) and not force:
        # commits touching the plugin that publish.py did not make: someone changed a team skill from the Brain tab (the
        # change is live for the whole team). Port it into brain/teams/<team> or brain/claude first, or pass --force.
        r = git(dest, "log", "--format=%h %s", "--", "paas-brain-" + team)
        edits = [l for l in r.stdout.splitlines() if not l.split(" ", 1)[1].startswith(f"team {team}: plugin")] if r.returncode == 0 else []
        if edits:
            sys.exit(f"publish.py: the team repository holds {len(edits)} change(s) to the plugin made outside publish.py "
                     f"(Brain tab edits):\n  " + "\n  ".join(edits[:10]) + "\nPort them into brain/teams/" + team
                     + " (git -C <repo> show <sha>) or re-run with --force to drop them.")
    plug = build.build(dest, team, hooks)
    # Claude Code gives a user a new copy of a plugin from a git-hosted marketplace only when plugin.json's version changes:
    # the version is the library version plus a fingerprint of the plugin's content, so every publish with a change is one
    import hashlib
    h = hashlib.sha1()
    for root, dirs, files in os.walk(plug):
        dirs.sort()
        for f in sorted(files):
            if f == "plugin.json" or f == "team.json":
                continue
            h.update(os.path.relpath(os.path.join(root, f), plug).encode())
            with open(os.path.join(root, f), "rb") as fh:
                h.update(fh.read())
    for name in ("team.json", os.path.join(".claude-plugin", "plugin.json")):
        pj = os.path.join(plug, name)
        with open(pj) as f:
            d = json.load(f)
        d["version"] = d["version"].split("-")[0] + "-" + h.hexdigest()[:8]
        with open(pj, "w") as f:
            json.dump(d, f, indent=2, sort_keys=True)
            f.write("\n")
    with open(os.path.join(plug, "team.json")) as f:
        t = json.load(f)
    k = os.path.join(dest, "knowledge")
    for d in ("notes", "captures", "incidents"):
        os.makedirs(os.path.join(k, d), exist_ok=True)
        keep = os.path.join(k, d, ".keep")
        if not os.listdir(os.path.join(k, d)):
            open(keep, "w").close()
    for f in ("tool-map.md", "notes.md", "environment.md"):           # the team's memory starts from the templates, once
        if not os.path.exists(os.path.join(k, f)):
            shutil.copy(os.path.join(plug, "brain", f), os.path.join(k, f))
    mcp_path = os.path.join(dest, "mcp.json")                          # made once from the catalog; members fill and edit it
    if not os.path.exists(mcp_path):
        cat = json.load(open(CATALOG)) if os.path.exists(CATALOG) else {}
        servers = {n: cat[n]["server"] for n in t.get("mcp", []) if n in cat and n != "docs-local"}
        with open(mcp_path, "w") as f:
            json.dump(servers, f, indent=2, sort_keys=True)
            f.write("\n")
    meta_path = os.path.join(dest, "team.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    meta.update({"name": team, "title": t["title"], "description": t["description"], "version": t["version"],
                 "plugin": "paas-brain-" + team})
    if remote:
        meta["remote"] = remote
    if meta.get("remote"):                                   # into the plugin too: its session-start hook clones from it
        pj = os.path.join(plug, "team.json")
        with open(pj) as f:
            pt = json.load(f)
        pt["remote"] = meta["remote"]
        with open(pj, "w") as f:
            json.dump(pt, f, indent=2, sort_keys=True)
            f.write("\n")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(dest, ".gitignore"), "w") as f:
        f.write(IGNORE)
    with open(os.path.join(dest, "README.md"), "w") as f:
        f.write(readme(t, meta.get("remote")))
    with open(os.path.join(dest, "install-team.sh"), "w") as f:
        f.write(INSTALL_TEAM)
    shutil.copy(os.path.join(HERE, "team-check.py"), os.path.join(dest, "check.py"))      # the repository's own CI gate
    os.chmod(os.path.join(dest, "check.py"), 0o755)
    if not os.path.exists(os.path.join(dest, ".gitlab-ci.yml")):
        shutil.copy(os.path.join(HERE, "team-gitlab-ci.yml"), os.path.join(dest, ".gitlab-ci.yml"))
    os.chmod(os.path.join(dest, "install-team.sh"), 0o755)
    os.makedirs(os.path.join(dest, "bin"), exist_ok=True)
    shutil.copy(os.path.join(BRAIN, "claude", "tools", "paas-team"), os.path.join(dest, "bin", "paas-team"))
    os.chmod(os.path.join(dest, "bin", "paas-team"), 0o755)
    if commit:
        git(dest, "add", "-A")
        git(dest, "commit", "-q", "-m", f"team {team}: plugin {t['version']}")   # nothing new: exits 1, fine
    return t


def publish_url(team, url, hooks, commit, force=False):
    tmp = tempfile.mkdtemp(prefix="paas-team-")
    try:
        r = subprocess.run(["git", "clone", "-q", url, tmp], capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        if r.returncode:
            sys.exit(f"publish.py: cannot clone {url}: {r.stderr.strip()[-300:]}")
        if git(tmp, "rev-parse", "--verify", "-q", "HEAD").returncode:      # an empty project
            git(tmp, "checkout", "-q", "-b", "main")
        t = publish(team, tmp, remote=url, hooks=hooks, commit=commit, force=force)
        if commit:
            r = git(tmp, "push", "-u", "origin", "HEAD:main", timeout=300)
            if r.returncode:
                sys.exit(f"publish.py: push failed: {(r.stderr or r.stdout).strip()[-300:]}")
        print(f"team {team}: plugin {t['version']} ({len(t['skills'])} skills, {len(t['agents'])} agents) pushed to {url}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = sys.argv[1:]
    team = dest = remote = None
    hooks = commit = True
    everything = force = False
    while args:
        a = args.pop(0)
        if a == "--to" and args:
            dest = args.pop(0)
        elif a == "--remote" and args:
            remote = args.pop(0)
        elif a == "--all":
            everything = True
        elif a == "--no-hooks":
            hooks = False
        elif a == "--no-commit":
            commit = False
        elif a == "--force":
            force = True
        elif a.startswith("-") or team:
            sys.exit(__doc__)
        else:
            team = a
    if not dest or not (team or everything) or (team and everything):
        sys.exit(__doc__)
    if everything:
        for name in build.team_names():
            t = publish(name, os.path.join(os.path.abspath(dest), name), remote=remote, hooks=hooks, commit=commit, force=force)
            print(f"team {name}: plugin {t['version']} ({len(t['skills'])} skills, {len(t['agents'])} agents) in {os.path.join(dest, name)}")
        return
    if is_url(dest):
        publish_url(team, dest, hooks, commit, force)
    else:
        t = publish(team, os.path.abspath(dest), remote=remote, hooks=hooks, commit=commit, force=force)
        print(f"team {team}: plugin {t['version']} ({len(t['skills'])} skills, {len(t['agents'])} agents) in {dest}")


if __name__ == "__main__":
    main()
