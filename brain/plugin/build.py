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
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
ROOT = os.path.dirname(BRAIN)
SRC = os.path.join(BRAIN, "claude")
TEAMS = os.environ.get("PAAS_TEAM_DEFS") or os.path.join(BRAIN, "teams")   # another folder of team definitions: the tests' mock teams
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
    if t.get("library") and not re.match(r"^[a-z0-9][a-z0-9_-]{0,31}$", str(t["library"])):
        sys.exit(f"build.py: team {name}: library {t['library']!r}: lower-case letters, digits, - and _")
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
        return p if (os.path.isfile(os.path.join(p, "SKILL.md")) if kind == "skills" else os.path.isfile(p)) else None   # an empty folder an update left: no skill

    if wanted == "all":
        names = sorted({n[:-3] if kind == "agents" and n.endswith(".md") else n
                        for folder in (shared, own) if os.path.isdir(folder) for n in os.listdir(folder)
                        if not n.startswith(".") and (path_of(folder, n) if kind == "skills" else n.endswith(".md"))})
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
                        "--hooks-dir", '"${CLAUDE_PLUGIN_ROOT}"/hooks'], check=True, stdout=subprocess.DEVNULL)   # quoted: a path with spaces stays one word
        with open(settings) as f:
            h = {"hooks": json.load(f)["hooks"]}
    # in the plugin every hook starts through hooks/pyrun: python3, python or py -3, whichever this machine has (Windows has
    # no python3), and without any Python the read-only guard blocks instead of letting calls through unchecked
    for groups in h["hooks"].values():
        for g in groups:
            for x in g.get("hooks", []):
                c = x.get("command", "")
                if c.startswith('python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/'):
                    x["command"] = 'sh "${CLAUDE_PLUGIN_ROOT}"/hooks/pyrun ' + c[len("python3 "):]
    return h


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
    # Claude Code names a plugin's MCP tools mcp__plugin_<plugin>_<server>__<tool>: an agent's `tools:` list written for the
    # bare server names would not let it call the team's servers, so the team's servers are renamed here (a server the
    # person adds themselves, kuparashit or aria outside the team, keeps the bare form and still matches)
    plugin_servers = {m for m in team.get("mcp", []) if m != "docs-search"} | {"docs-local"}
    for n, p in agents:
        text = open(p, encoding="utf-8").read()
        text = re.sub(r"\bmcp__([A-Za-z0-9_.-]+)__\*", lambda m: (f"mcp__plugin_{name}_{m.group(1)}__*" if m.group(1) in plugin_servers
                      else f"mcp__plugin_{name}_docs-http__*" if m.group(1) == "docs-search" else m.group(0)), text, count=0)
        write(os.path.join(plug, "agents", n + ".md"), text)
    # the coding rules as a skill too (one source: brain/claude/brain/coding.md), so a plugin-only install has them and
    # Claude loads them by itself before code work; the file copy under brain/ stays for the installed brains
    coding = open(os.path.join(SRC, "brain", "coding.md"), encoding="utf-8").read()
    write(os.path.join(plug, "skills", "coding-rules", "SKILL.md"),
          "---\nname: coding-rules\ndescription: The brain's coding rules, read once before the first code change of a session "
          "(think first, simplicity, surgical changes, checkable goals). Triggers - writing or changing code, scripts, services, apps\n---\n"
          + coding.split("\n", 1)[1].lstrip("\n"))
    skills = skills + [("coding-rules", os.path.join(plug, "skills", "coding-rules"))]
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
        "mcp": team.get("mcp", ["docs-local"]), "hooks": hooks, **({"library": team["library"]} if team.get("library") else {})}))
    write(os.path.join(plug, ".claude-plugin", "plugin.json"), dump({
        "name": name, "version": version(), "description": team.get("description", ""),
        "author": {"name": "storage team"}, "license": "Apache-2.0"}))
    write(os.path.join(plug, ".mcp.json"), dump({"mcpServers": {"docs-local": {"command": "${CLAUDE_PLUGIN_ROOT}/bin/docs-local"}}}))
    os.makedirs(os.path.join(plug, "bin"), exist_ok=True)
    shutil.copy(os.path.join(SRC, "tools", "paas-team"), os.path.join(plug, "bin", "paas-team"))   # the hook's bootstrap runs it
    os.chmod(os.path.join(plug, "bin", "paas-team"), 0o755)
    # the docs server and its indexer travel with the plugin (standard library, ~110 KB): docs-local serves the library plus the
    # person's team knowledge where the library is installed, the team knowledge alone on a laptop (the VM's docs-search adds
    # the library there); the knowledge index is refreshed at every server start when the pages changed
    os.makedirs(os.path.join(plug, "lib"), exist_ok=True)
    for f in ("mcp_stdio.py", "search_cli.py", "docs_text.py", "docs_index.py"):
        shutil.copy(os.path.join(ROOT, "docs-search-mcp", f), os.path.join(plug, "lib", f))
    exe = os.path.join(plug, "bin", "docs-local")
    # a team with its own library ("library" in team.json) opens ~/.claude/brain/libraries/<name>/docs.db and never the general
    # one; where it is not installed the bridge to the VM's docs-search serves it (?team=<team> picks it there)
    db = f'$B/libraries/{team["library"]}/docs.db' if team.get("library") else "$B/library/docs.db"
    nolib = " --no-library" if team.get("library") else ""            # knowledge alone, never the general library by default
    write(exe, '#!/bin/sh\n# docs-local of the team plugin: the library (when installed) and the team knowledge of ~/.claude/brain.\n'
               '# No library but the team\'s docs-search address in the environment (.mcp.json, from the team\'s mcp.json): a stdio bridge to\n'
               '# that server (the VM\'s library and the team\'s knowledge index, over its certificate). Neither: the knowledge folder alone.\n'
               'B="${CLAUDE_HOME:-$HOME/.claude}/brain"; L=$(cd "$(dirname "$0")/.." && pwd)/lib\n'
               'S=""; [ -d /var/lib/paas-docs/index ] && S="--shared-knowledge /var/lib/paas-docs/index"   # multi-user VM: one index per team, built by the docs service\n'
               f'DB="{db}"\n'
               'if [ -f "$DB" ]; then exec python3 "$L/mcp_stdio.py" --db "$DB" --knowledge "$B" $S\n'
               'elif [ -n "${PAAS_DOCS_URL:-}" ]; then CA=""; [ -f "$L/paas-ui.crt" ] && CA="--ca $L/paas-ui.crt"; exec python3 "$L/mcp_stdio.py" --proxy "$PAAS_DOCS_URL" $CA\n'
               f'else exec python3 "$L/mcp_stdio.py" --knowledge "$B" $S{nolib}; fi\n')
    os.chmod(exe, 0o755)
    write(os.path.join(out, ".claude-plugin", "marketplace.json"), dump({
        "name": name, "owner": {"name": "paas"}, "description": team.get("title", team_name) + " brain: " + team.get("description", ""),
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
