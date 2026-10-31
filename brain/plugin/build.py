#!/usr/bin/env python3
"""Build a team's brain as a Claude Code plugin marketplace out of brain/claude and brain/teams/<team>.
usage: build.py <out-dir> [--team NAME] [--no-hooks]
   -> <out-dir>/.claude-plugin/marketplace.json and <out-dir>/paas-brain-<team>/   (team: san by default)
The plugin carries the team's skills and agents (brain/teams/<team>/{skills,agents} first, then brain/claude), the
hooks (hooks.json is produced by brain/merge_settings.py itself, so matchers and timeouts never drift from the VM
install; --no-hooks for a VM whose hooks are managed), the docs-local MCP server, and under brain/ the files a
plugin cannot activate itself: persona.md, storage.md (the team's rules), the environment / tool-map / notes
templates, coding.md and the core CLAUDE.md. paas-team puts those in place. team.json inside the plugin lists what was resolved.
Same output on every run. Standard library, Python 3.9."""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
ROOT = os.path.dirname(BRAIN)
SRC = os.path.join(BRAIN, "claude")
TEAMS = os.path.join(BRAIN, "teams")
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "._*", ".user-skill")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def dump(o):
    return json.dumps(o, indent=2, sort_keys=True) + "\n"


def team_names():
    return sorted(d for d in os.listdir(TEAMS) if os.path.isfile(os.path.join(TEAMS, d, "team.json")))


def load_team(name):
    path = os.path.join(TEAMS, name, "team.json")
    if not os.path.isfile(path):
        sys.exit(f"build.py: no team {name!r} (brain/teams/{name}/team.json); teams: {', '.join(team_names())}")
    with open(path) as f:
        t = json.load(f)
    t["name"] = name
    return t


def team_file(team, key, default=None):
    """a file named in team.json: relative to brain/teams/<team>, or to the repository when it starts with brain/"""
    rel = team.get(key, default)
    if not rel:
        return None
    path = os.path.join(ROOT, rel) if rel.startswith("brain/") else os.path.join(TEAMS, team["name"], rel)
    if not os.path.isfile(path):
        sys.exit(f"build.py: team {team['name']}: {key} = {rel} not found")
    return path


def resolve(team, kind):
    """[(name, source path)] of the team's skills (folders) or agents (.md files)"""
    own = os.path.join(TEAMS, team["name"], kind)
    shared = os.path.join(SRC, kind)
    wanted = team.get(kind, "all")

    def path_of(folder, name):
        p = os.path.join(folder, name if kind == "skills" else name + ".md")
        return p if (os.path.isdir(p) if kind == "skills" else os.path.isfile(p)) else None

    if wanted == "all":
        names = sorted({n[:-3] if kind == "agents" and n.endswith(".md") else n
                        for folder in (shared, own) if os.path.isdir(folder) for n in os.listdir(folder)
                        if not n.startswith(".") and (kind == "skills" or n.endswith(".md"))})
    else:
        names = list(dict.fromkeys(wanted))
    out = []
    for n in names:
        p = path_of(own, n) or path_of(shared, n)
        if not p:
            sys.exit(f"build.py: team {team['name']}: {kind[:-1]} {n!r} not found in brain/teams/{team['name']}/{kind} or brain/claude/{kind}")
        out.append((n, p))
    return out


def hooks_json():
    """the hooks block merge_settings.py would write, with the hook scripts under the plugin root"""
    with tempfile.TemporaryDirectory() as t:
        settings = os.path.join(t, "settings.json")
        subprocess.run([sys.executable, os.path.join(BRAIN, "merge_settings.py"), settings,
                        "--hooks-dir", "${CLAUDE_PLUGIN_ROOT}/hooks"], check=True, stdout=subprocess.DEVNULL)
        with open(settings) as f:
            return {"hooks": json.load(f)["hooks"]}


def version():
    vfile = os.path.join(ROOT, "library", "VERSION")
    return open(vfile).read().strip() if os.path.exists(vfile) else datetime.date.today().strftime("%Y.%m.%d")


def build(out, team_name="san", hooks=True):
    """build the team's plugin into <out>/paas-brain-<team> + <out>/.claude-plugin/marketplace.json; returns the plugin dir"""
    team = load_team(team_name)
    name = "paas-brain-" + team_name
    plug = os.path.join(out, name)
    shutil.rmtree(plug, ignore_errors=True)
    skills, agents = resolve(team, "skills"), resolve(team, "agents")
    for n, p in skills:
        shutil.copytree(p, os.path.join(plug, "skills", n), ignore=IGNORE)
    os.makedirs(os.path.join(plug, "agents"), exist_ok=True)
    for n, p in agents:
        shutil.copy(p, os.path.join(plug, "agents", n + ".md"))
    if hooks:
        shutil.copytree(os.path.join(SRC, "hooks"), os.path.join(plug, "hooks"), ignore=IGNORE)
        write(os.path.join(plug, "hooks", "hooks.json"), dump(hooks_json()))
    # what a plugin cannot activate: the rules and the templates, put in place by paas-team
    b = os.path.join(plug, "brain")
    os.makedirs(b)
    shutil.copy(team_file(team, "persona", "persona.md"), os.path.join(b, "persona.md"))
    shutil.copy(team_file(team, "rules", "brain/claude/brain/storage.md"), os.path.join(b, "storage.md"))
    shutil.copy(team_file(team, "environment", "brain/claude/brain/environment.md"), os.path.join(b, "environment.md"))
    for f in ("tool-map.md", "notes.md", "coding.md"):
        shutil.copy(os.path.join(SRC, "brain", f), os.path.join(b, f))
    shutil.copy(os.path.join(SRC, "CLAUDE.md"), os.path.join(b, "CLAUDE.md"))      # the core rules (main.md on a laptop)
    write(os.path.join(plug, "team.json"), dump({
        "name": team_name, "title": team.get("title", team_name), "description": team.get("description", ""),
        "version": version(), "skills": [n for n, _ in skills], "agents": [n for n, _ in agents],
        "mcp": team.get("mcp", ["docs-local"]), "hooks": hooks}))
    write(os.path.join(plug, ".claude-plugin", "plugin.json"), dump({
        "name": name, "version": version(), "description": team.get("description", "")}))
    write(os.path.join(plug, ".mcp.json"), dump({"docs-local": {"command": "${CLAUDE_PLUGIN_ROOT}/bin/docs-local"}}))
    exe = os.path.join(plug, "bin", "docs-local")
    write(exe, '#!/bin/sh\nexec python3 "$HOME/.claude/brain/library/mcp_stdio.py" --db "$HOME/.claude/brain/library/docs.db"\n')
    os.chmod(exe, 0o755)
    write(os.path.join(out, ".claude-plugin", "marketplace.json"), dump({
        "name": name, "owner": {"name": "paas"},
        "plugins": [{"name": name, "source": "./" + name, "description": team.get("title", team_name) + " brain"}]}))
    return plug


def main():
    args = sys.argv[1:]
    team, hooks, out = "san", True, None
    while args:
        a = args.pop(0)
        if a == "--team" and args:
            team = args.pop(0)
        elif a == "--no-hooks":
            hooks = False
        elif a.startswith("-") or out:
            sys.exit(__doc__)
        else:
            out = os.path.abspath(a)
    if not out:
        sys.exit(__doc__)
    plug = build(out, team, hooks)
    with open(os.path.join(plug, "team.json")) as f:
        t = json.load(f)
    print(f"built {plug} (team {team}, version {t['version']}, {len(t['skills'])} skills, {len(t['agents'])} agents"
          f"{'' if hooks else ', no hooks'})")


if __name__ == "__main__":
    main()
