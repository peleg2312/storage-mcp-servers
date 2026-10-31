#!/usr/bin/env python3
"""Build a Claude Code plugin marketplace (paas-brain) out of brain/claude, for a laptop install.
usage: build.py <out-dir>      -> <out-dir>/.claude-plugin/marketplace.json and <out-dir>/paas-brain/
The plugin carries the skills, agents, hooks (hooks.json is produced by brain/merge_settings.py itself, so the
matchers and timeouts can never drift from the VM install) and the docs-local MCP server. The brain's rules
(CLAUDE.md / main.md) are not a plugin feature: install-laptop.sh handles them. Same output on every run."""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
SRC = os.path.join(BRAIN, "claude")
NAME = "paas-brain"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def hooks_json():
    """the hooks block merge_settings.py would write, with the hook scripts under the plugin root"""
    with tempfile.TemporaryDirectory() as t:
        settings = os.path.join(t, "settings.json")
        subprocess.run([sys.executable, os.path.join(BRAIN, "merge_settings.py"), settings,
                        "--hooks-dir", "${CLAUDE_PLUGIN_ROOT}/hooks"], check=True, stdout=subprocess.DEVNULL)
        with open(settings) as f:
            return {"hooks": json.load(f)["hooks"]}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    plug = os.path.join(out, NAME)
    shutil.rmtree(plug, ignore_errors=True)
    vfile = os.path.join(BRAIN, "..", "library", "VERSION")
    version = open(vfile).read().strip() if os.path.exists(vfile) else datetime.date.today().strftime("%Y.%m.%d")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "._*")
    for d in ("skills", "agents"):
        shutil.copytree(os.path.join(SRC, d), os.path.join(plug, d), ignore=ignore)
    shutil.copytree(os.path.join(SRC, "hooks"), os.path.join(plug, "hooks"), ignore=ignore)
    dump = lambda o: json.dumps(o, indent=2, sort_keys=True) + "\n"
    write(os.path.join(plug, "hooks", "hooks.json"), dump(hooks_json()))
    write(os.path.join(plug, ".claude-plugin", "plugin.json"), dump({
        "name": NAME, "version": version,
        "description": "Read-only SAN / storage assistant: skills, agents, read-only guard and the offline docs library (docs-local)"}))
    write(os.path.join(plug, ".mcp.json"), dump({"docs-local": {"command": "${CLAUDE_PLUGIN_ROOT}/bin/docs-local"}}))
    exe = os.path.join(plug, "bin", "docs-local")
    write(exe, '#!/bin/sh\nexec python3 "$HOME/.claude/brain/library/mcp_stdio.py" --db "$HOME/.claude/brain/library/docs.db"\n')
    os.chmod(exe, 0o755)
    write(os.path.join(out, ".claude-plugin", "marketplace.json"), dump({
        "name": NAME, "owner": {"name": "paas"},
        "plugins": [{"name": NAME, "source": "./" + NAME, "description": "Peleg As A Service storage brain"}]}))
    print(f"built {plug} (version {version})")


if __name__ == "__main__":
    main()
