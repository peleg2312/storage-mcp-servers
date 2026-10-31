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
Layout of a team repository:
  .claude-plugin/marketplace.json   paas-brain-<team>/ (the plugin, replaced on every publish)
  knowledge/{notes,captures,incidents}/ + tool-map.md   (what the team learns; notes.md and environment.md stay personal)
  team.json (name, title, remote)   README.md   .gitignore
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

IGNORE = "knowledge/notes.md\nknowledge/environment.md\n*.bak\n.DS_Store\n._*\n__pycache__/\n"
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
    return (f"# Team brain: {t.get('title', t['name'])}\n\n{t.get('description', '')}\n\n"
            f"- `paas-brain-{t['name']}/`: the brain as a Claude Code plugin ({len(t['skills'])} skills, {len(t['agents'])} agents, "
            f"version {t['version']}); rebuilt by `brain/teams/publish.py` from the storage-mcp-servers repository\n"
            "- `knowledge/`: what the team learns (notes/<topic>.md, captures/, incidents/, tool-map.md), written by every "
            "member's brain and synced through this repository; notes.md and environment.md are personal and never committed\n\n"
            "Use it: on the VM `paas-team use " + t["name"] + "`; on a laptop `sh install-laptop.sh --team " + t["name"]
            + (f" --team-source {remote}" if remote else "") + "`; plugin only: `claude plugin marketplace add "
            + (remote or "<this repository>") + f" && claude plugin install paas-brain-{t['name']}@paas-brain-{t['name']}`.\n")


def publish(team, dest, remote=None, hooks=True, commit=True):
    """build the team into the repository at dest (a directory); returns the plugin's team.json data"""
    os.makedirs(dest, exist_ok=True)
    if not os.path.isdir(os.path.join(dest, ".git")):
        git(dest, "init", "-q", "-b", "main", check=True)
    plug = build.build(dest, team, hooks)
    with open(os.path.join(plug, "team.json")) as f:
        t = json.load(f)
    k = os.path.join(dest, "knowledge")
    for d in ("notes", "captures", "incidents"):
        os.makedirs(os.path.join(k, d), exist_ok=True)
        keep = os.path.join(k, d, ".keep")
        if not os.listdir(os.path.join(k, d)):
            open(keep, "w").close()
    if not os.path.exists(os.path.join(k, "tool-map.md")):
        shutil.copy(os.path.join(plug, "brain", "tool-map.md"), os.path.join(k, "tool-map.md"))
    meta_path = os.path.join(dest, "team.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    meta.update({"name": team, "title": t["title"], "description": t["description"], "version": t["version"],
                 "plugin": "paas-brain-" + team})
    if remote:
        meta["remote"] = remote
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(dest, ".gitignore"), "w") as f:
        f.write(IGNORE)
    with open(os.path.join(dest, "README.md"), "w") as f:
        f.write(readme(t, meta.get("remote")))
    if commit:
        git(dest, "add", "-A")
        git(dest, "commit", "-q", "-m", f"team {team}: plugin {t['version']}")   # nothing new: exits 1, fine
    return t


def publish_url(team, url, hooks, commit):
    tmp = tempfile.mkdtemp(prefix="paas-team-")
    try:
        r = subprocess.run(["git", "clone", "-q", url, tmp], capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        if r.returncode:
            sys.exit(f"publish.py: cannot clone {url}: {r.stderr.strip()[-300:]}")
        if git(tmp, "rev-parse", "--verify", "-q", "HEAD").returncode:      # an empty project
            git(tmp, "checkout", "-q", "-b", "main")
        t = publish(team, tmp, remote=url, hooks=hooks, commit=commit)
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
    everything = hooks = commit = True
    everything = False
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
        elif a.startswith("-") or team:
            sys.exit(__doc__)
        else:
            team = a
    if not dest or not (team or everything) or (team and everything):
        sys.exit(__doc__)
    if everything:
        for name in build.team_names():
            t = publish(name, os.path.join(os.path.abspath(dest), name), remote=remote, hooks=hooks, commit=commit)
            print(f"team {name}: plugin {t['version']} ({len(t['skills'])} skills, {len(t['agents'])} agents) in {os.path.join(dest, name)}")
        return
    if is_url(dest):
        publish_url(team, dest, hooks, commit)
    else:
        t = publish(team, os.path.abspath(dest), remote=remote, hooks=hooks, commit=commit)
        print(f"team {team}: plugin {t['version']} ({len(t['skills'])} skills, {len(t['agents'])} agents) in {dest}")


if __name__ == "__main__":
    main()
