#!/usr/bin/env python3
"""Offline marketplace of skills, agents and MCP servers on this VM: root publishes items, each user adds the ones
they want to their own ~/.claude (names stay as they are: /morning-check, not /pack:morning-check).

  paas-market list [--json]              every item, and whether you have it (and an update for it)
  paas-market search <words> [--json]    items whose name / description match
  paas-market add <kind>/<name>...       e.g. skill/morning-check agent/ontap-analyst mcp/harvest
  paas-market remove <kind>/<name>...    only items added from the marketplace
  paas-market update                     re-copy items root changed since you added them
  paas-market defaults                   add the items every user starts with (new accounts get them at creation)
root only:
  paas-market publish <brain/claude dir> [--mcp mcp.json]   (re)build the marketplace from the brain in this repo

The marketplace is a folder (PAAS_MARKET, default /opt/paas/marketplace): items/skills/<name>/,
items/agents/<name>.md, items/mcp/<name>.json, index.json (kind, name, description, version) and defaults.json.
What you added is recorded in ~/.claude/paas-market.json; your own skills and agents are never touched.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

MARKET = os.environ.get("PAAS_MARKET", "/opt/paas/marketplace")
CLAUDE = os.path.expanduser("~/.claude")
STATE = os.path.join(CLAUDE, "paas-market.json")
KINDS = ("skill", "agent", "mcp")
NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,60}$")


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text or "", re.S)
    out = {}
    for line in (m.group(1) if m else "").splitlines():
        kv = re.match(r"^([\w-]+):\s*(.*)$", line)
        if kv:
            v = kv.group(2).strip()
            if v.startswith('"') and v.endswith('"'):
                try:
                    v = json.loads(v)
                except ValueError:
                    v = v[1:-1]
            out[kv.group(1)] = v.strip("'")
    return out


def digest(path):
    h = hashlib.sha256()
    if os.path.isdir(path):
        for root, dirs, files in sorted(os.walk(path)):
            dirs.sort()
            for f in sorted(files):
                p = os.path.join(root, f)
                h.update(os.path.relpath(p, path).encode())
                h.update(open(p, "rb").read())
    else:
        h.update(open(path, "rb").read())
    return h.hexdigest()[:12]


def item_path(kind, name, market=MARKET):
    return os.path.join(market, "items", {"skill": "skills", "agent": "agents", "mcp": "mcp"}[kind],
                        name + {"skill": "", "agent": ".md", "mcp": ".json"}[kind])


def load_index():
    try:
        return json.load(open(os.path.join(MARKET, "index.json")))
    except (OSError, ValueError):
        sys.exit(f"paas-market: no marketplace at {MARKET} (root runs: paas-market publish)")


def load_state():
    try:
        return json.load(open(STATE))
    except (OSError, ValueError):
        return {"installed": {}}


def save_state(state):
    os.makedirs(CLAUDE, exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(state, open(tmp, "w"), indent=2)
    os.replace(tmp, STATE)


def listing(words=None):
    state = load_state()["installed"]
    out = []
    for it in load_index():
        key = f"{it['kind']}/{it['name']}"
        if words and not all(w.lower() in f"{it['name']} {it['description']} {it['kind']}".lower() for w in words):
            continue
        have = state.get(key)
        out.append({**it, "id": key, "added": bool(have), "update": bool(have and have != it["version"])})
    return out


def parse_ids(args):
    ids = []
    for a in args:
        kind, _, name = a.partition("/")
        if kind not in KINDS or not NAME.match(name):
            sys.exit(f"paas-market: '{a}' is not <skill|agent|mcp>/<name>")
        ids.append((kind, name))
    return ids


def mcp_cmd(*args):
    claude = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    return subprocess.run([claude, "mcp", *args], capture_output=True, text=True, timeout=60)


def add(ids, quiet=False):
    index = {(i["kind"], i["name"]): i for i in load_index()}
    state = load_state()
    for kind, name in ids:
        it = index.get((kind, name))
        if not it:
            sys.exit(f"paas-market: {kind}/{name} is not in the marketplace")
        src = item_path(kind, name)
        if kind == "skill":
            dst = os.path.join(CLAUDE, "skills", name)
            if os.path.exists(dst) and f"skill/{name}" not in state["installed"]:
                sys.exit(f"paas-market: you already have your own skill '{name}'; rename it first")
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
        elif kind == "agent":
            dst = os.path.join(CLAUDE, "agents", name + ".md")
            if os.path.exists(dst) and f"agent/{name}" not in state["installed"]:
                sys.exit(f"paas-market: you already have your own agent '{name}'; rename it first")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
        else:
            cfg = json.load(open(src))["server"]
            if "HOST" in cfg.get("url", "") or "TOKEN" in json.dumps(cfg.get("headers", {})):
                sys.exit(f"paas-market: mcp/{name} is not set up yet: root sets its address in the marketplace")
            mcp_cmd("remove", "-s", "user", name)
            r = mcp_cmd("add-json", "-s", "user", name, json.dumps(cfg))
            if r.returncode:
                sys.exit(f"paas-market: could not add MCP server {name}: {(r.stderr or r.stdout).strip()}")
        state["installed"][f"{kind}/{name}"] = it["version"]
        save_state(state)
        if not quiet:
            print(f"added {kind}/{name}")


def remove(ids):
    state = load_state()
    for kind, name in ids:
        if f"{kind}/{name}" not in state["installed"]:
            sys.exit(f"paas-market: {kind}/{name} was not added from the marketplace")
        if kind == "skill":
            shutil.rmtree(os.path.join(CLAUDE, "skills", name), ignore_errors=True)
        elif kind == "agent":
            try:
                os.remove(os.path.join(CLAUDE, "agents", name + ".md"))
            except FileNotFoundError:
                pass
        else:
            mcp_cmd("remove", "-s", "user", name)
        del state["installed"][f"{kind}/{name}"]
        save_state(state)
        print(f"removed {kind}/{name}")


def update():
    todo = [tuple(i["id"].split("/", 1)) for i in listing() if i["update"]]
    add(todo)
    if not todo:
        print("everything is up to date")


def defaults():
    try:
        ids = json.load(open(os.path.join(MARKET, "defaults.json")))
    except (OSError, ValueError):
        ids = []
    have = load_state()["installed"]
    add(parse_ids([i for i in ids if i not in have]))


def publish(brain, mcp_file=None):
    """Rebuild the marketplace from <brain>/skills and <brain>/agents (+ an MCP catalog); keeps items root added by
    hand in items/ (only the brain's own items are overwritten). defaults.json is created once, then root's."""
    for sub in ("skills", "agents", "mcp"):
        os.makedirs(os.path.join(MARKET, "items", sub), exist_ok=True)
    for n in sorted(os.listdir(os.path.join(brain, "skills"))):
        if os.path.isfile(os.path.join(brain, "skills", n, "SKILL.md")):
            dst = item_path("skill", n)
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(os.path.join(brain, "skills", n), dst)
    for n in sorted(os.listdir(os.path.join(brain, "agents"))):
        if n.endswith(".md"):
            shutil.copy(os.path.join(brain, "agents", n), item_path("agent", n[:-3]))
    for name, entry in (json.load(open(mcp_file)) if mcp_file else {}).items():
        dst = item_path("mcp", name)
        if not os.path.exists(dst):                     # root's edited address / headers win over the template
            json.dump(entry, open(dst, "w"), indent=2)
    reindex()
    dfile = os.path.join(MARKET, "defaults.json")
    if not os.path.exists(dfile):
        json.dump(["skill/docs-lookup", "skill/explain-error", "skill/report-export", "skill/brain-health",
                   "agent/docs-researcher", "mcp/docs-local"], open(dfile, "w"), indent=2)
    print(f"published {len(load_index())} items to {MARKET}")


def reindex():
    items = []
    for kind in KINDS:
        d = os.path.join(MARKET, "items", {"skill": "skills", "agent": "agents", "mcp": "mcp"}[kind])
        for n in sorted(os.listdir(d)):
            name = n[:-3] if kind == "agent" else n[:-5] if kind == "mcp" else n
            p = os.path.join(d, n)
            if kind == "mcp":
                desc = json.load(open(p)).get("description", "")
            else:
                desc = frontmatter(open(os.path.join(p, "SKILL.md") if kind == "skill" else p).read()).get("description", "")
            items.append({"kind": kind, "name": name, "description": desc, "version": digest(p)})
    tmp = os.path.join(MARKET, "index.json.tmp")
    json.dump(items, open(tmp, "w"), indent=1)
    os.replace(tmp, os.path.join(MARKET, "index.json"))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    if cmd in ("list", "search"):
        rows = listing(args if cmd == "search" else None)
        if as_json:
            print(json.dumps(rows))
        else:
            for r in rows:
                mark = "update" if r["update"] else "added" if r["added"] else ""
                print(f"{r['id']:<38} {mark:<7} {r['description'][:90]}")
    elif cmd == "add":
        add(parse_ids(args))
    elif cmd == "remove":
        remove(parse_ids(args))
    elif cmd == "update":
        update()
    elif cmd == "defaults":
        defaults()
    elif cmd == "publish":
        if not args:
            sys.exit("usage: paas-market publish <brain/claude dir> [--mcp mcp.json]")
        mcp = args[args.index("--mcp") + 1] if "--mcp" in args else None
        publish(args[0], mcp)
    elif cmd == "reindex":
        reindex()
    else:
        sys.exit(f"paas-market: unknown command '{cmd}' (paas-market --help)")


if __name__ == "__main__":
    main(sys.argv[1:])
