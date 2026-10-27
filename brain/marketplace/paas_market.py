#!/usr/bin/env python3
"""Offline marketplace of skills, agents and MCP servers on this VM: root publishes items, each user adds the ones
they want to their own ~/.claude (names stay as they are: /morning-check, not /pack:morning-check).

  paas-market list [--json]              every item, and whether you have it (and an update for it)
  paas-market search <words> [--json]    items whose name / description match
  paas-market add <kind>/<name>...       e.g. skill/morning-check agent/ontap-analyst mcp/harvest
  paas-market remove <kind>/<name>...    only items added from the marketplace
  paas-market update                     re-copy items root changed since you added them
  paas-market enable|disable plugin/<n>  switch an added plugin on / off
  paas-market defaults                   add the items every user starts with (new accounts get them at creation)
  paas-market share <kind>/<name>...     put your own skill / agent into the marketplace for others (again = update)
  paas-market unshare <kind>/<name>...   take it out again (people who added it keep their copy)
  paas-market new <kind> <name>          create a skill / agent / MCP server (JSON on stdin) and share it
  paas-market show <kind>/<name>         print one you shared (skill / agent file; MCP: JSON without the token)
  paas-market edit <kind>/<name>         replace it from stdin (same forms as show; MCP: a blank token keeps it), re-shared
root only:
  paas-market publish <brain/claude dir> [--mcp mcp.json]   (re)build the marketplace from the brain in this repo
  paas-market setup-mcp <name> <url> [<token>]             set where an MCP server is (everyone can then add it)

The marketplace is a folder (PAAS_MARKET, default /opt/paas/marketplace): items/skills/<name>/,
items/agents/<name>.md, items/mcp/<name>.json, index.json (kind, name, description, version) and defaults.json.
What you added is recorded in ~/.claude/paas-market.json; your own skills and agents are never touched.
"""
import getpass
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
# Claude Code plugins (commands, agents, skills, hooks together) from the brain's offline plugin marketplace
PLUGINS = os.environ.get("PAAS_PLUGINS", os.path.join(os.path.dirname(MARKET.rstrip("/")), "plugins"))
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
    """root's items (index.json) plus the skills and agents people shared (contrib/<user>/), marked with their author"""
    try:
        items = json.load(open(os.path.join(MARKET, "index.json")))
    except (OSError, ValueError):
        sys.exit(f"paas-market: no marketplace at {MARKET} (root runs: paas-market publish)")
    items += plugin_items()
    taken = {(i["kind"], i["name"]) for i in items}
    for it in contrib_items():
        if (it["kind"], it["name"]) not in taken:
            taken.add((it["kind"], it["name"]))
            items.append(it)
    return items


def plugin_market():
    try:
        return json.load(open(os.path.join(PLUGINS, ".claude-plugin", "marketplace.json")))
    except (OSError, ValueError):
        return {"name": "", "plugins": []}


def plugin_items():
    m = plugin_market()
    return [{"kind": "plugin", "name": p["name"], "description": p.get("description", ""), "author": None,
             "version": digest(os.path.join(PLUGINS, p["source"])), "path": os.path.join(PLUGINS, p["source"])}
            for p in m["plugins"] if os.path.isdir(os.path.join(PLUGINS, p["source"]))]


def installed_plugins():
    """{plugin name: enabled} for this marketplace, from Claude Code itself"""
    r = claude_cmd("plugin", "list", "--json")
    try:
        rows = json.loads(r.stdout) if r.returncode == 0 else []
    except ValueError:
        rows = []
    suffix = "@" + plugin_market()["name"]
    return {x["id"][:-len(suffix)]: bool(x.get("enabled")) for x in rows if str(x.get("id", "")).endswith(suffix)}


def contrib_items():
    out = []
    base = os.path.join(MARKET, "contrib")
    for user in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        for kind, sub, ext in (("skill", "skills", ""), ("agent", "agents", ".md"), ("mcp", "mcp", ".json")):
            d = os.path.join(base, user, sub)
            for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                p = os.path.join(d, n)
                f = os.path.join(p, "SKILL.md") if kind == "skill" else p
                if not n.endswith(ext) or not os.path.isfile(f):
                    continue
                try:
                    desc = json.load(open(f)).get("description", "") if kind == "mcp" else frontmatter(open(f).read()).get("description", "")
                except ValueError:
                    continue
                out.append({"kind": kind, "name": n[:-len(ext)] if ext else n, "description": desc,
                            "version": digest(p), "author": user, "path": p})
    return out


def own_path(kind, name):
    return os.path.join(CLAUDE, "skills", name) if kind == "skill" else os.path.join(CLAUDE, "agents", name + ".md")


def share(ids):
    """put your own skills / agents into the marketplace (contrib/<you>/), so others can add them; re-share = update"""
    me = getpass.getuser()
    mine = os.path.join(MARKET, "contrib", me)
    if not os.access(mine, os.W_OK):
        sys.exit(f"paas-market: no sharing folder for {me} ({mine}); root runs: paas-user provision {me}")
    others = {(i["kind"], i["name"]): i.get("author") for i in load_index()}
    for kind, name in ids:
        if kind == "mcp":
            cfg = own_mcp(name)
            if not cfg:
                sys.exit(f"paas-market: you have no MCP server '{name}' (claude mcp list)")
        else:
            src = own_path(kind, name)
            if not os.path.exists(src):
                sys.exit(f"paas-market: you have no {kind} '{name}'")
        if (kind, name) in others and others[(kind, name)] != me:
            who = others[(kind, name)] or "root"
            sys.exit(f"paas-market: {kind}/{name} is already in the marketplace (by {who}); rename yours to share it")
        dst = os.path.join(mine, {"skill": "skills", "agent": "agents", "mcp": "mcp"}[kind],
                           name + {"skill": "", "agent": ".md", "mcp": ".json"}[kind])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if kind == "mcp":
            old_desc = json.load(open(dst)).get("description", "") if os.path.exists(dst) else ""
            json.dump({"description": os.environ.get("PAAS_DESCRIPTION", "").strip() or old_desc or f"MCP server {name}",
                       "server": cfg}, open(dst, "w"), indent=2)
        elif kind == "skill":
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".user-skill", "*.bak"))
        else:
            shutil.copy(src, dst)
        print(f"shared {kind}/{name}")


def own_mcp(name):
    """the user-scope MCP server <name> from ~/.claude.json, or None"""
    try:
        return json.load(open(os.path.expanduser("~/.claude.json"))).get("mcpServers", {}).get(name)
    except (OSError, ValueError):
        return None


def new_item(kind, name):
    """create a skill / agent / MCP server of your own from JSON on stdin and share it with everyone:
    skill {description, when, body} - agent {description, tools, model, body} - mcp {description, url, token}"""
    if kind not in KINDS or not re.match(r"^[a-z0-9][a-z0-9-]{1,40}$", name):
        sys.exit("paas-market: name: lower-case letters, digits and dashes, e.g. vm-patching")
    try:
        d = json.load(sys.stdin)
    except ValueError:
        sys.exit("paas-market: the details must be JSON on stdin")
    desc = " ".join(str(d.get("description", "")).split())[:1000]
    if not desc:
        sys.exit("paas-market: a description is needed: it is how Claude (and people) know when to use it")
    if any(i["kind"] == kind and i["name"] == name for i in load_index()):
        sys.exit(f"paas-market: {kind}/{name} is already in the marketplace: pick another name")
    q = json.dumps
    if kind == "skill":
        dst = own_path("skill", name)
        if os.path.exists(dst):
            sys.exit(f"paas-market: you already have a skill '{name}'")
        os.makedirs(dst)
        when = " ".join(str(d.get("when", "")).split())[:600]
        open(os.path.join(dst, "SKILL.md"), "w").write(f"---\nname: {name}\ndescription: {q(desc)}\n"
                                                        + (f"when_to_use: {q(when)}\n" if when else "")
                                                        + f"---\n{str(d.get('body', '')).strip()}\n")
        open(os.path.join(dst, ".user-skill"), "w").write("created in the marketplace\n")
    elif kind == "agent":
        dst = own_path("agent", name)
        if os.path.exists(dst):
            sys.exit(f"paas-market: you already have an agent '{name}'")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tools = " ".join(str(d.get("tools", "")).split())
        model = str(d.get("model", "")).strip()
        open(dst, "w").write(f"---\nname: {name}\ndescription: {q(desc)}\n" + (f"tools: {tools}\n" if tools else "")
                             + (f"model: {model}\n" if re.match(r"^[a-z0-9.-]+$", model) else "")
                             + f"---\n{str(d.get('body', '')).strip()}\n")
        with open(os.path.join(CLAUDE, "agents", ".user-agents"), "a") as f:
            f.write(name + "\n")
    else:
        url = str(d.get("url", "")).strip()
        if not re.match(r"^https?://[\w.-]+(:\d+)?(/\S*)?$", url):
            sys.exit("paas-market: the address must look like http://host:8000/mcp")
        token = str(d.get("token", "")).strip()
        cfg = {"type": "http", "url": url, **({"headers": {"Authorization": f"Bearer {token}"}} if token else {})}
        r = mcp_cmd("add-json", "-s", "user", name, json.dumps(cfg))
        if r.returncode:
            sys.exit(f"paas-market: could not add MCP server {name}: {(r.stderr or r.stdout).strip()}")
    os.environ["PAAS_DESCRIPTION"] = desc
    share([(kind, name)])


def mine_shared(kind, name):
    """(kind, name) must be an item you shared: others' items are edited by their author"""
    if kind not in KINDS or not NAME.match(name):
        sys.exit("paas-market: skill/<name>, agent/<name> or mcp/<name>")
    if not any(i["kind"] == kind and i["name"] == name and i.get("author") == getpass.getuser() for i in load_index()):
        sys.exit(f"paas-market: {kind}/{name} is not one you shared")


def show(kind, name):
    mine_shared(kind, name)
    if kind == "mcp":
        cfg = own_mcp(name) or {}
        dst = os.path.join(MARKET, "contrib", getpass.getuser(), "mcp", name + ".json")
        desc = json.load(open(dst)).get("description", "") if os.path.exists(dst) else ""
        print(json.dumps({"description": desc, "url": cfg.get("url", ""),
                          "has_token": "Authorization" in cfg.get("headers", {})}))
    else:
        print(open(os.path.join(own_path(kind, name), "SKILL.md") if kind == "skill" else own_path(kind, name)).read(), end="")


def edit(kind, name):
    """your copy gets the new text (or MCP address / token), then the marketplace copy is updated from it"""
    mine_shared(kind, name)
    text = sys.stdin.read()
    if kind == "mcp":
        try:
            d = json.loads(text)
        except ValueError:
            sys.exit("paas-market: the details must be JSON on stdin")
        url = str(d.get("url", "")).strip()
        if not re.match(r"^https?://[\w.-]+(:\d+)?(/\S*)?$", url):
            sys.exit("paas-market: the address must look like http://host:8000/mcp")
        old = own_mcp(name) or {}
        token = str(d.get("token", "")).strip()
        headers = {"Authorization": f"Bearer {token}"} if token else old.get("headers", {})
        cfg = {"type": "http", "url": url, **({"headers": headers} if headers else {})}
        mcp_cmd("remove", "-s", "user", name)
        r = mcp_cmd("add-json", "-s", "user", name, json.dumps(cfg))
        if r.returncode:
            sys.exit(f"paas-market: could not update MCP server {name}: {(r.stderr or r.stdout).strip()}")
        os.environ["PAAS_DESCRIPTION"] = " ".join(str(d.get("description", "")).split())[:1000]
    else:
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m or not re.search(r"^description:\s*\S", m.group(1), re.M):
            sys.exit("paas-market: keep the header: --- / name / description: ... / ---, then the instructions")
        if not re.search(rf"^name:\s*{re.escape(name)}\s*$", m.group(1), re.M):
            sys.exit(f"paas-market: keep 'name: {name}' in the header (to rename, create a new one)")
        dst = os.path.join(own_path(kind, name), "SKILL.md") if kind == "skill" else own_path(kind, name)
        open(dst, "w").write(text if text.endswith("\n") else text + "\n")
    share([(kind, name)])


def unshare(ids):
    me = getpass.getuser()
    for kind, name in ids:
        dst = os.path.join(MARKET, "contrib", me, {"skill": "skills", "agent": "agents", "mcp": "mcp"}[kind],
                           name + {"skill": "", "agent": ".md", "mcp": ".json"}[kind])
        if not os.path.exists(dst):
            sys.exit(f"paas-market: you did not share {kind}/{name}")
        shutil.rmtree(dst) if os.path.isdir(dst) else os.remove(dst)
        print(f"unshared {kind}/{name} (people who added it keep their copy)")


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
    plugins = installed_plugins() if os.path.isdir(PLUGINS) else {}
    out = []
    for it in load_index():
        if it["kind"] == "plugin":
            if words and not all(w.lower() in f"{it['name']} {it['description']} plugin".lower() for w in words):
                continue
            out.append({**it, "id": f"plugin/{it['name']}", "added": it["name"] in plugins,
                        "enabled": plugins.get(it["name"], False), "update": False, "ready": True})
            continue
        key = f"{it['kind']}/{it['name']}"
        if words and not all(w.lower() in f"{it['name']} {it['description']} {it['kind']}".lower() for w in words):
            continue
        have = state.get(key)
        out.append({**it, "id": key, "added": bool(have), "update": bool(have and have != it["version"]),
                    "ready": it["kind"] != "mcp" or mcp_ready(json.load(open(it.get("path") or item_path("mcp", it["name"]))))})
    return out


def parse_ids(args):
    ids = []
    for a in args:
        kind, _, name = a.partition("/")
        if kind not in KINDS + ("plugin",) or not NAME.match(name):
            sys.exit(f"paas-market: '{a}' is not <skill|agent|mcp|plugin>/<name>")
        ids.append((kind, name))
    return ids


def mcp_ready(entry):
    """An MCP item can be added once root replaced the HOST / TOKEN placeholders."""
    cfg = entry.get("server", {})
    return "HOST" not in cfg.get("url", "") and "TOKEN" not in json.dumps(cfg.get("headers", {}))


def setup_mcp(name, url, token):
    """root: set the address (and bearer token) of an MCP item, for everyone who adds it from now on."""
    p = item_path("mcp", name)
    if not os.path.exists(p):
        sys.exit(f"paas-market: mcp/{name} is not in the marketplace")
    if not re.match(r"^https?://[\w.-]+(:\d+)?(/\S*)?$", url):
        sys.exit("paas-market: the address must look like http://host:8000/mcp")
    entry = json.load(open(p))
    entry["server"] = {"type": "http", "url": url, **({"headers": {"Authorization": f"Bearer {token}"}} if token else {})}
    json.dump(entry, open(p, "w"), indent=2)
    reindex()
    print(f"mcp/{name} set up: {url}")


def claude_cmd(*args):
    claude = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    try:
        return subprocess.run([claude, *args], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(args, 1, "", str(e))


def mcp_cmd(*args):
    return claude_cmd("mcp", *args)


def plugin_cmd(action, name):
    """install / uninstall / enable / disable a plugin of the brain's offline plugin marketplace for this user"""
    mk = plugin_market()["name"]
    if not mk:
        sys.exit(f"paas-market: no plugin marketplace at {PLUGINS}")
    if action == "install":
        claude_cmd("plugin", "marketplace", "add", PLUGINS)       # once per user; harmless when already there
    r = claude_cmd("plugin", action, f"{name}@{mk}")
    if r.returncode:
        sys.exit(f"paas-market: plugin {action} {name}: {(r.stderr or r.stdout).strip()}")
    print(f"{action} plugin/{name}: done")


def add(ids, quiet=False):
    index = {(i["kind"], i["name"]): i for i in load_index()}
    state = load_state()
    for kind, name in ids:
        it = index.get((kind, name))
        if not it:
            sys.exit(f"paas-market: {kind}/{name} is not in the marketplace")
        if kind == "plugin":
            plugin_cmd("install", name)
            continue
        src = it.get("path") or item_path(kind, name)
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
            if not mcp_ready({"server": cfg}):
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
        if kind == "plugin":
            plugin_cmd("uninstall", name)
            continue
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
    extra = os.path.join(brain, "..", "marketplace", "skills")       # popular skills from anthropics/skills
    for n in sorted(os.listdir(extra)) if os.path.isdir(extra) else []:
        if os.path.isfile(os.path.join(extra, n, "SKILL.md")):
            dst = item_path("skill", n)
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(os.path.join(extra, n), dst)
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
    elif cmd in ("enable", "disable"):
        for kind, name in parse_ids(args):
            if kind != "plugin":
                sys.exit("paas-market: only plugins are switched on / off")
            plugin_cmd(cmd, name)
    elif cmd == "new":
        if len(args) != 2:
            sys.exit("usage: paas-market new <skill|agent|mcp> <name>   (details as JSON on stdin)")
        new_item(args[0], args[1])
    elif cmd in ("show", "edit"):
        ids = parse_ids(args)
        if len(ids) != 1:
            sys.exit(f"usage: paas-market {cmd} <kind>/<name>")
        (show if cmd == "show" else edit)(*ids[0])
    elif cmd == "share":
        share(parse_ids(args))
    elif cmd == "unshare":
        unshare(parse_ids(args))
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
    elif cmd == "setup-mcp":
        if len(args) < 2:
            sys.exit("usage: paas-market setup-mcp <name> <url> [<bearer token>]   (root)")
        setup_mcp(args[0], args[1], args[2] if len(args) > 2 else "")
    elif cmd == "reindex":
        reindex()
    else:
        sys.exit(f"paas-market: unknown command '{cmd}' (paas-market --help)")


if __name__ == "__main__":
    main(sys.argv[1:])
