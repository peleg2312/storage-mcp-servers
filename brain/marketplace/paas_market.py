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
  paas-market view <kind>/<name>         read any item before adding it (MCP: without its token)
  paas-market show <kind>/<name>         print one you shared (skill / agent file; MCP: JSON without the token)
  paas-market edit <kind>/<name>         replace it from stdin (same forms as show; MCP: a blank token keeps it), re-shared
  paas-market connect <https://vm:3443> [<token>] [--fingerprint SHA256:..]   use another VM's marketplace (read-only; refreshed every 10 min)
  paas-market pull | disconnect          refresh it now / back to this VM's own marketplace
root only:
  paas-market publish <brain/claude dir> [--mcp mcp.json]   (re)build the marketplace from the brain in this repo
  paas-market setup-mcp <name> <url> [shared|personal|none]  set where an MCP server is; the token: shared = one
                                                           for everyone (on stdin), personal = each person adds
                                                           their own when they add it, none = no token
  paas-market import-mcp [<item>=<your server>...]        set up the marketplace's MCP items from your own Claude's
                                                           servers of the same name (or the names you map)
  paas-market source add <git-url|folder> [<name>]        another marketplace (e.g. a copy of anthropics/skills or
                                                           anthropics/claude-plugins-official): its skills, agents and
                                                           plugins show as their own section, ids <kind>/<name>@<source>
  paas-market source list | sync [<name>] | remove <name>  list them / fetch them again / take one away

The marketplace is a folder (PAAS_MARKET, default /opt/paas/marketplace): items/skills/<name>/,
items/agents/<name>.md, items/mcp/<name>.json, index.json (kind, name, description, version) and defaults.json.
Other marketplaces (paas-market source add) are copied into PAAS_SOURCES (default /opt/paas/plugin-sources/<name>/).
What you added is recorded in ~/.claude/paas-market.json; your own skills and agents are never touched.
"""
import getpass
import hashlib
import io
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request

MARKET = os.environ.get("PAAS_MARKET", "/opt/paas/marketplace")
CLAUDE = os.path.expanduser("~/.claude")
STATE = os.path.join(CLAUDE, "paas-market.json")
KINDS = ("skill", "agent", "mcp")
# Claude Code plugins (commands, agents, skills, hooks together) from the brain's offline plugin marketplace
PLUGINS = os.environ.get("PAAS_PLUGINS", os.path.join(os.path.dirname(MARKET.rstrip("/")), "plugins"))
NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,60}$")
SNAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,60}(@[a-z0-9][a-z0-9_.-]{0,40})?$")    # name or name@source
# another VM's marketplace (paas-market connect): a local copy of it, which list / add / update read
REMOTE_CFG = os.path.join(CLAUDE, "paas-market-remote.json")
REMOTE_CRT = os.path.join(CLAUDE, "paas-market-remote.crt")     # its certificate, pinned at connect
MIRROR = os.path.join(CLAUDE, "paas-market-mirror")
REMOTE = None
if "PAAS_MARKET" not in os.environ and os.path.exists(REMOTE_CFG):
    REMOTE = json.load(open(REMOTE_CFG))
    MARKET, PLUGINS = os.path.join(MIRROR, "marketplace"), os.path.join(MIRROR, "plugins")
# other marketplaces root added (paas-market source add); with another VM's marketplace, that VM's sources
SOURCES = os.environ.get("PAAS_SOURCES") or (os.path.join(MIRROR, "plugin-sources") if REMOTE
                                             else os.path.join(os.path.dirname(MARKET.rstrip("/")), "plugin-sources"))


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
    """{plugin id: enabled}: '<name>' for this VM's plugin marketplace, '<name>@<source>' for a source's, from Claude Code"""
    r = claude_cmd("plugin", "list", "--json")
    try:
        rows = json.loads(r.stdout) if r.returncode == 0 else []
    except ValueError:
        rows = []
    to_id = {plugin_market()["name"]: ""} if plugin_market()["name"] else {}
    for src in source_names():
        mk = source_market(src)["name"]
        if mk:
            to_id.setdefault(mk, "@" + src)
    out = {}
    for x in rows:
        name, _, mk = str(x.get("id", "")).rpartition("@")
        if mk in to_id:
            out[name + to_id[mk]] = bool(x.get("enabled"))
    return out


# ---------------------------------------------------------------------------
# Other marketplaces (sources): a git repository or folder copied to SOURCES/<name>/; read-only for users
# ---------------------------------------------------------------------------

def source_names():
    return sorted(n for n in os.listdir(SOURCES) if NAME.match(n) and os.path.isdir(os.path.join(SOURCES, n))) \
        if os.path.isdir(SOURCES) else []


def source_info():
    try:
        return json.load(open(os.path.join(SOURCES, "sources.json")))
    except (OSError, ValueError):
        return {}


def source_market(src):
    try:
        return json.load(open(os.path.join(SOURCES, src, ".claude-plugin", "marketplace.json")))
    except (OSError, ValueError):
        return {"name": "", "plugins": []}


def source_items():
    """every source's plugins (from .claude-plugin/marketplace.json) and every SKILL.md / agents/*.md in it"""
    out = []
    info = source_info()
    for src in source_names():
        base = os.path.join(SOURCES, src)
        mk = source_market(src)
        title = info.get(src, {}).get("title") or mk.get("name") or src
        common = {"author": None, "source": src, "source_title": title}
        for p in mk.get("plugins", []):
            if not NAME.match(str(p.get("name", ""))):
                continue
            local = isinstance(p.get("source"), str)          # {"source": "github", ...} needs the internet
            path = os.path.normpath(os.path.join(base, p["source"])) if local else ""
            ok = local and (path == base or path.startswith(base + os.sep)) and os.path.isdir(path)
            out.append({**common, "kind": "plugin", "name": f"{p['name']}@{src}", "description": p.get("description", ""),
                        "version": digest(path) if ok else "", "path": path, "offline": ok})
        seen = set()
        for root, dirs, files in sorted(os.walk(base)):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "node_modules")
            if "SKILL.md" in files:
                fm = frontmatter(open(os.path.join(root, "SKILL.md"), errors="replace").read())
                n = str(fm.get("name") or os.path.basename(root)).lower()
                if NAME.match(n) and ("skill", n) not in seen:
                    seen.add(("skill", n))
                    out.append({**common, "kind": "skill", "name": f"{n}@{src}", "description": fm.get("description", ""),
                                "version": digest(root), "path": root})
            if os.path.basename(root) == "agents":
                for f in sorted(files):
                    fm = frontmatter(open(os.path.join(root, f), errors="replace").read()) if f.endswith(".md") else {}
                    n = str(fm.get("name") or "").lower()
                    if fm.get("description") and NAME.match(n) and ("agent", n) not in seen:
                        seen.add(("agent", n))
                        out.append({**common, "kind": "agent", "name": f"{n}@{src}", "description": fm["description"],
                                    "version": digest(os.path.join(root, f)), "path": os.path.join(root, f)})
    return out


def _fetch(origin, dst):
    """git clone (depth 1) or copy a folder into dst; nothing is run from it"""
    if os.path.isdir(origin):
        shutil.copytree(origin, dst, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    elif re.match(r"^(https?|ssh|git)://\S+$|^[\w.-]+@[\w.-]+:\S+$", origin):
        r = subprocess.run(["git", "clone", "-q", "--depth", "1", "--", origin, dst], capture_output=True, text=True, timeout=600)
        if r.returncode:
            sys.exit(f"paas-market: git clone {origin}: {(r.stderr or r.stdout).strip()}")
        shutil.rmtree(os.path.join(dst, ".git"), ignore_errors=True)
    else:
        sys.exit(f"paas-market: {origin} is not a folder or a git URL (https://, ssh://, git@host:repo)")
    for root, dirs, files in os.walk(dst):                 # readable by everyone, writable by root only
        for n in dirs + files:
            p = os.path.join(root, n)
            if os.path.islink(p):
                os.remove(p)                                # no links out of the copy
            else:
                os.chmod(p, 0o755 if os.path.isdir(p) else 0o644)
    os.chmod(dst, 0o755)


def source_cmd(args):
    sub, rest = (args[0], args[1:]) if args else ("list", [])
    if sub == "list":
        info = source_info()
        items = source_items()
        for src in source_names():
            n = sum(1 for i in items if i["source"] == src)
            print(f"{src:<24} {n:>4} items  {info.get(src, {}).get('origin', '')}")
        return None if source_names() else print("no other marketplaces (root: paas-market source add <git-url|folder>)")
    if os.geteuid() != 0:
        sys.exit("paas-market: only root adds, syncs and removes other marketplaces")
    info = source_info()
    if sub == "add":
        if not rest:
            sys.exit("usage: paas-market source add <git-url|folder> [<name>]")
        origin = rest[0].rstrip("/")
        name = (rest[1] if len(rest) > 1 else re.sub(r"\.git$", "", re.split(r"[/:]", origin)[-1])).lower()
        name = re.sub(r"[^a-z0-9_.-]", "-", name).strip("-.")
        if not NAME.match(name) or name in info or os.path.exists(os.path.join(SOURCES, name)):
            sys.exit(f"paas-market: source name '{name}' is taken or not valid; give one: paas-market source add {origin} <name>")
        todo = {name: os.path.abspath(origin) if os.path.isdir(origin) else origin}
    elif sub == "sync":
        todo = {n: info[n]["origin"] for n in (rest or sorted(info)) if n in info}
        if rest and set(rest) - set(todo):
            sys.exit(f"paas-market: no source {', '.join(sorted(set(rest) - set(todo)))}")
    elif sub == "remove":
        if not rest or rest[0] not in info:
            sys.exit("usage: paas-market source remove <name>   (paas-market source list)")
        shutil.rmtree(os.path.join(SOURCES, rest[0]), ignore_errors=True)
        info.pop(rest[0])
        json.dump(info, open(os.path.join(SOURCES, "sources.json"), "w"), indent=2)
        return print(f"removed source {rest[0]} (people who added its items keep their copy)")
    else:
        sys.exit("usage: paas-market source add <git-url|folder> [<name>] | list | sync [<name>] | remove <name>")
    os.makedirs(SOURCES, mode=0o755, exist_ok=True)
    for name, origin in todo.items():
        new = os.path.join(SOURCES, f".{name}.new")
        shutil.rmtree(new, ignore_errors=True)
        _fetch(origin, new)
        old = os.path.join(SOURCES, f".{name}.old")
        shutil.rmtree(old, ignore_errors=True)
        if os.path.exists(os.path.join(SOURCES, name)):
            os.rename(os.path.join(SOURCES, name), old)
        os.rename(new, os.path.join(SOURCES, name))
        shutil.rmtree(old, ignore_errors=True)
        info[name] = {**info.get(name, {}), "origin": origin, "synced": time.strftime("%Y-%m-%d %H:%M")}
        json.dump(info, open(os.path.join(SOURCES, "sources.json"), "w"), indent=2)
        os.chmod(os.path.join(SOURCES, "sources.json"), 0o644)
        n = sum(1 for i in source_items() if i["source"] == name)
        print(f"source {name}: {n} items from {origin}")


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
            old = json.load(open(dst)) if os.path.exists(dst) else {}
            mode = os.environ.get("PAAS_TOKEN_MODE") or old.get("token") or ("shared" if cfg.get("headers") else "none")
            if mode != "shared":                     # personal / none: your token stays in your own Claude only
                cfg = {k: v for k, v in cfg.items() if k != "headers"}
            json.dump({"description": os.environ.get("PAAS_DESCRIPTION", "").strip() or old.get("description") or f"MCP server {name}",
                       "token": mode, "server": cfg}, open(dst, "w"), indent=2)
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


def mcp_folders(name):
    """folders where <name> was added for that folder only (`claude mcp add` without -s user)"""
    try:
        projects = json.load(open(os.path.expanduser("~/.claude.json"))).get("projects", {})
    except (OSError, ValueError):
        return []
    return [p for p, v in projects.items() if name in (v.get("mcpServers") or {})]


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
        mode = d.get("token_mode") or ("shared" if token else "none")
        if mode not in TOKEN_MODES or (mode == "shared" and not token):
            sys.exit("paas-market: token: shared (give the token everyone uses), personal or none")
        os.environ["PAAS_TOKEN_MODE"] = mode
        cfg = {"type": "http", "url": url, **({"headers": {"Authorization": f"Bearer {token}"}} if token and mode != "none" else {})}
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
        shared = json.load(open(dst)) if os.path.exists(dst) else {}
        print(json.dumps({"description": shared.get("description", ""), "url": cfg.get("url", ""), "token_mode": token_mode(shared),
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
        cur = os.path.join(MARKET, "contrib", getpass.getuser(), "mcp", name + ".json")
        mode = d.get("token_mode") or token_mode(json.load(open(cur)) if os.path.exists(cur) else {})
        if mode not in TOKEN_MODES:
            sys.exit("paas-market: token: shared, personal or none")
        os.environ["PAAS_TOKEN_MODE"] = mode
        headers = {} if mode == "none" else {"Authorization": f"Bearer {token}"} if token else old.get("headers", {})
        if mode == "shared" and not headers:
            sys.exit("paas-market: a shared token is needed (or: personal, none)")
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


def already_have(kind, name):
    """you have it from before (an earlier install, by hand) under the marketplace's name, and did not create it here:
    the marketplace counts it as added, so Remove / Add work on it. Skills and agents you created are never touched."""
    if kind == "skill":
        d = os.path.join(CLAUDE, "skills", name)
        return os.path.isdir(d) and not os.path.exists(os.path.join(d, ".user-skill"))
    if kind == "agent":
        try:
            mine = open(os.path.join(CLAUDE, "agents", ".user-agents")).read().split()
        except OSError:
            mine = []
        return os.path.isfile(own_path("agent", name)) and name not in mine
    return kind == "mcp" and (own_mcp(name) is not None or bool(mcp_folders(name)))


def risky(it):
    """someone else's skill / agent that grants tools (allowed-tools, tools: Bash/Write/Edit), runs hooks, ships scripts or has a huge description"""
    if not it.get("author") or it["author"] == getpass.getuser() or it["kind"] not in ("skill", "agent"):
        return ""
    p = it["path"]
    fm = frontmatter(open(os.path.join(p, "SKILL.md") if it["kind"] == "skill" else p).read())
    why = [k for k in ("allowed-tools", "hooks") if k in fm]
    if it["kind"] == "agent" and re.search(r"\b(Bash|Write|Edit)\b", str(fm.get("tools", ""))):
        why.append("tools")
    if len(str(fm.get("description", ""))) > 600:
        why.append("long description")
    if it["kind"] == "skill" and any(not f.endswith(".md") for _, _, fs in os.walk(p) for f in fs):
        why.append("scripts")
    return ", ".join(why)


def view(kind, name):
    """print any item, read-only (MCP: without its token)"""
    it = next((i for i in load_index() + source_items() if i["kind"] == kind and i["name"] == name), None)
    if not it or kind == "plugin":
        sys.exit(f"paas-market: {kind}/{name} is not in the marketplace")
    p = it.get("path") or item_path(kind, name)
    if kind == "mcp":
        e = json.load(open(p))
        e["server"] = {k: v for k, v in e.get("server", {}).items() if k != "headers"}
        return print(json.dumps(e, indent=2))
    print(open(os.path.join(p, "SKILL.md") if kind == "skill" else p).read(), end="")
    if kind == "skill":
        extra = sorted(os.path.relpath(os.path.join(r, f), p) for r, _, fs in os.walk(p) for f in fs if f != "SKILL.md")
        if extra:
            print("\n--- other files in this skill: " + ", ".join(extra))


def listing(words=None):
    state = load_state()["installed"]
    plugins = installed_plugins() if os.path.isdir(PLUGINS) or source_names() else {}
    out = []
    for it in load_index() + source_items():
        it.setdefault("source", "")
        if it["kind"] == "plugin":
            if words and not all(w.lower() in f"{it['name']} {it['description']} plugin".lower() for w in words):
                continue
            out.append({**it, "id": f"plugin/{it['name']}", "added": it["name"] in plugins,
                        "enabled": plugins.get(it["name"], False), "update": False, "ready": it.get("offline", True)})
            continue
        key = f"{it['kind']}/{it['name']}"
        if words and not all(w.lower() in f"{it['name']} {it['description']} {it['kind']}".lower() for w in words):
            continue
        have = state.get(key)
        mcp_entry = json.load(open(it.get("path") or item_path("mcp", it["name"]))) if it["kind"] == "mcp" else {}
        mcp = mcp_entry.get("server", {})
        out.append({**it, "id": key, "added": bool(have) or ("@" not in it["name"] and already_have(it["kind"], it["name"])),
                    "update": bool(have and have != it["version"]),
                    "ready": it["kind"] != "mcp" or mcp_ready(mcp_entry), "risky": risky(it),
                    "local": it["kind"] == "mcp" and mcp.get("type", "stdio") == "stdio",   # runs on this VM: no address
                    **({"token_mode": token_mode(mcp_entry), "url": "" if "HOST" in mcp.get("url", "") else mcp.get("url", "")}
                       if it["kind"] == "mcp" else {})})
    return out


def parse_ids(args):
    ids = []
    for a in args:
        kind, _, name = a.partition("/")
        if kind not in KINDS + ("plugin",) or not SNAME.match(name) or ("@" in name and kind == "mcp"):
            sys.exit(f"paas-market: '{a}' is not <skill|agent|mcp|plugin>/<name>")
        ids.append((kind, name))
    return ids


TOKEN_MODES = ("shared", "personal", "none")


def token_mode(entry):
    """shared: root's one token for everyone; personal: each person their own; none: no token"""
    return entry.get("token") or ("shared" if entry.get("server", {}).get("headers") else "none")


def mcp_ready(entry):
    """An MCP item can be added once root replaced the HOST (and, for a shared token, the TOKEN) placeholder."""
    cfg = entry.get("server", {})
    cmd = cfg.get("command", "")
    if os.path.isabs(cmd) and not os.path.exists(cmd):      # e.g. a venv that was never built on this VM
        return False
    return "HOST" not in cfg.get("url", "") and not (token_mode(entry) == "shared" and "TOKEN" in json.dumps(cfg.get("headers", {})))


def read_secret(prompt):
    """a token from stdin (the UI sends it there, never on the command line), or typed at a terminal"""
    if sys.stdin.isatty():
        return getpass.getpass(prompt).strip()
    return sys.stdin.read().strip()


def setup_mcp(name, url, token, mode="shared"):
    """root: set the address of an MCP item and how its token works, for everyone who adds it from now on."""
    p = item_path("mcp", name)
    if not os.path.exists(p):
        sys.exit(f"paas-market: mcp/{name} is not in the marketplace")
    if not re.match(r"^https?://[\w.-]+(:\d+)?(/\S*)?$", url):
        sys.exit("paas-market: the address must look like http://host:8000/mcp")
    if mode == "shared" and not token:
        sys.exit("paas-market: a shared token is needed (or: personal = each person their own, none = no token)")
    entry = json.load(open(p))
    entry["token"] = mode
    entry["server"] = {"type": "http", "url": url,
                       **({"headers": {"Authorization": f"Bearer {token}"}} if mode == "shared" else {})}
    json.dump(entry, open(p, "w"), indent=2)
    reindex()
    print(f"mcp/{name} set up: {url} ({ {'shared': 'one token for everyone', 'personal': 'each person adds their own token', 'none': 'no token'}[mode] })")


def import_mcp(pairs):
    """root: copy root's own MCP servers (user or project scope in ~/.claude.json) into the marketplace items"""
    try:
        cfg = json.load(open(os.path.expanduser("~/.claude.json")))
    except (OSError, ValueError):
        sys.exit("paas-market: no ~/.claude.json: add the MCP servers to your own Claude first (claude mcp add ...)")
    mine = dict(cfg.get("mcpServers", {}))
    for proj in cfg.get("projects", {}).values():
        for k, v in proj.get("mcpServers", {}).items():
            mine.setdefault(k, v)
    names = dict(p.split("=", 1) for p in pairs if "=" in p)
    done = 0
    for f in sorted(os.listdir(os.path.join(MARKET, "items", "mcp"))):
        item = f[:-5]
        src = names.get(item, item)
        if src not in mine:
            print(f"  mcp/{item}: you have no server '{src}'" + ("" if item in names else f" (map it: {item}=<your server name>)"))
            continue
        p = item_path("mcp", item)
        entry = json.load(open(p))
        entry["server"] = mine[src]
        entry.pop("token", None)                       # the token type follows root's server again (shared / none)
        json.dump(entry, open(p, "w"), indent=2)
        print(f"set up mcp/{item} from your '{src}'")
        done += 1
    reindex()
    print(f"{done} MCP servers ready for everyone. Your servers: {', '.join(sorted(mine)) or 'none'}")


def claude_cmd(*args, cwd=None):
    claude = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    try:
        return subprocess.run([claude, *args], capture_output=True, text=True, timeout=120, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(args, 1, "", str(e))


def mcp_cmd(*args):
    return claude_cmd("mcp", *args)


def plugin_cmd(action, name):
    """install / uninstall / enable / disable a plugin of the brain's offline plugin marketplace (or of a source:
    <plugin>@<source>) for this user"""
    name, _, src = name.partition("@")
    where = os.path.join(SOURCES, src) if src else PLUGINS
    mk = (source_market(src) if src else plugin_market())["name"]
    if not mk:
        sys.exit(f"paas-market: no plugin marketplace at {where}")
    if action == "install":
        claude_cmd("plugin", "marketplace", "add", where)         # once per user; harmless when already there
    r = claude_cmd("plugin", action, f"{name}@{mk}")
    if r.returncode:
        sys.exit(f"paas-market: plugin {action} {name}: {(r.stderr or r.stdout).strip()}")
    print(f"{action} plugin/{name}: done")


def clash(state, kind, name):
    """another marketplace's item with the same name you already added (they share ~/.claude/<kind>s/<name>)"""
    real = name.split("@")[0]
    return next((k for k in state["installed"] if k != f"{kind}/{name}" and k.split("@")[0] == f"{kind}/{real}"), None)


def add(ids, quiet=False, token=None):
    index = {(i["kind"], i["name"]): i for i in load_index() + source_items()}
    state = load_state()
    for kind, name in ids:
        it = index.get((kind, name))
        if not it:
            sys.exit(f"paas-market: {kind}/{name} is not in the marketplace")
        if kind == "plugin":
            if it.get("offline") is False:
                sys.exit(f"paas-market: plugin/{name} is fetched from the internet by Claude Code; it cannot be added here")
            plugin_cmd("install", name)
            continue
        src = it.get("path") or item_path(kind, name)
        real, from_source = name.split("@")[0], "@" in name
        other = clash(state, kind, name)
        if other:
            sys.exit(f"paas-market: you already added {other} with the same name; remove it first")
        if kind == "skill":
            dst = os.path.join(CLAUDE, "skills", real)
            if os.path.exists(dst) and f"skill/{name}" not in state["installed"] and (from_source or not already_have("skill", name)):
                sys.exit(f"paas-market: you already have a skill '{real}'; remove or rename it first")
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
        elif kind == "agent":
            dst = os.path.join(CLAUDE, "agents", real + ".md")
            if os.path.exists(dst) and f"agent/{name}" not in state["installed"] and (from_source or not already_have("agent", name)):
                sys.exit(f"paas-market: you already have an agent '{real}'; remove or rename it first")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
        else:
            entry = json.load(open(src))
            cfg = entry["server"]
            if not mcp_ready(entry):
                sys.exit(f"paas-market: mcp/{name} is not set up yet: root sets its address in the marketplace")
            if token_mode(entry) == "personal":
                t = token if token is not None else read_secret(f"your token for {name} (Enter: keep yours, or none): ")
                old = own_mcp(name) or {}
                headers = {"Authorization": f"Bearer {t}"} if t else old.get("headers", {})   # update keeps yours
                cfg = {**cfg, **({"headers": headers} if headers else {})}
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
        if f"{kind}/{name}" not in state["installed"] and ("@" in name or not already_have(kind, name)):
            sys.exit(f"paas-market: you do not have {kind}/{name}, or you created it yourself (remove it in the Brain tab)")
        name = name.split("@")[0]                          # a source's item lives under its own name
        if kind == "skill":
            d = os.path.join(CLAUDE, "skills", name)
            try:
                shutil.rmtree(d)
            except FileNotFoundError:
                pass
            except OSError as e:
                sys.exit(f"paas-market: could not remove {d}: {e.strerror}")
        elif kind == "agent":
            try:
                os.remove(os.path.join(CLAUDE, "agents", name + ".md"))
            except FileNotFoundError:
                pass
        else:
            mcp_cmd("remove", "-s", "user", name)
            for d in mcp_folders(name):                # also where it was added for one folder only
                claude_cmd("mcp", "remove", "-s", "local", name, cwd=d if os.path.isdir(d) else None)
            if own_mcp(name) is not None or mcp_folders(name):
                where = ", ".join(["your user settings"] * (own_mcp(name) is not None) + mcp_folders(name))
                sys.exit(f"paas-market: could not remove MCP server {name} ({where}): run claude mcp remove {name} there")
        key = next((k for k in state["installed"] if k.split("@")[0] == f"{kind}/{name}"), f"{kind}/{name}")
        state["installed"].pop(key, None)
        save_state(state)
        print(f"removed {key}")


def update():
    rows = listing()
    todo = [tuple(i["id"].split("/", 1)) for i in rows if i["update"] and not i.get("author")]
    others = [i["id"] for i in rows if i["update"] and i.get("author")]
    if others:                                         # someone else's change: look at it, then its own Update button
        print(f"not updated (shared by people, update each after a look): {', '.join(others)}")
    add(todo, token="")                                # personal tokens: everyone keeps theirs
    if not todo and not others:
        print("everything is up to date")


def defaults():
    try:
        ids = json.load(open(os.path.join(MARKET, "defaults.json")))
    except (OSError, ValueError):
        ids = []
    st = load_state()
    given = set(st.get("defaults_given", []))              # offered once: what a person removed stays removed
    try:                                                   # team plugin mode: the plugin carries docs-local itself
        plugin_mode = open(os.path.join(CLAUDE, "brain", "team-mode")).read().strip() == "plugin"
    except OSError:
        plugin_mode = os.path.exists(os.path.join(CLAUDE, "brain", "team")) and bool(shutil.which("claude"))
    skip = {"mcp/docs-local"} if plugin_mode else set()
    add(parse_ids([i for i in ids if i not in st["installed"] and i not in given and i not in skip]), token="")
    st = load_state()                                      # add() saved its own copy
    st["defaults_given"] = sorted(given | set(ids))
    save_state(st)


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
                   "agent/docs-researcher", "agent/Explore", "mcp/docs-local"], open(dfile, "w"), indent=2)
    else:                                       # Explore on Haiku (replaces the built-in one) for every new account
        ids = json.load(open(dfile))
        if "agent/Explore" not in ids:
            json.dump(ids + ["agent/Explore"], open(dfile, "w"), indent=2)
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


def connect(url, token, want=""):
    m = re.match(r"^https://([\w.-]+):(\d+)/?$", url)
    if not m:
        sys.exit("usage: paas-market connect https://<vm>:3443 [<token>] [--fingerprint SHA256:..]   (on that VM root reads the token: cat /etc/paas/market/token)")
    token = token.strip() or read_secret("marketplace token: ")
    if not token:
        sys.exit("paas-market: a token is needed")
    try:
        pem = ssl.get_server_certificate((m.group(1), int(m.group(2))))
    except OSError as e:
        sys.exit(f"paas-market: cannot reach {url}: {e}")
    fp = hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest().upper()
    shown = ":".join(fp[i:i + 2] for i in range(0, 64, 2))
    print(f"certificate of {m.group(1)}: SHA256 {shown}")
    print("  compare on that VM: openssl x509 -noout -fingerprint -sha256 -in /etc/paas/tls/paas-ui.crt")
    if want:                                       # the token is sent only to a certificate that was confirmed
        if re.sub(r"^SHA256[:=]|[:\s]", "", want.upper()) != fp:
            sys.exit("paas-market: the certificate does not match --fingerprint; nothing saved")
    elif sys.stdin.isatty() and input("same as on that VM? type yes: ").strip() != "yes":
        sys.exit("paas-market: not confirmed; nothing saved")
    old = os.umask(0o077)
    try:
        open(REMOTE_CRT, "w").write(pem)
        json.dump({"url": url.rstrip("/"), "token": token}, open(REMOTE_CFG, "w"))
    finally:
        os.umask(old)
    global REMOTE
    REMOTE = {"url": url.rstrip("/"), "token": token}
    try:
        pull()
    except BaseException:                          # nothing kept when the first download fails (wrong token, ...)
        for p in (REMOTE_CFG, REMOTE_CRT):
            os.remove(p)
        raise


def pull():
    """download the other VM's marketplace into MIRROR (whole copy, swapped in at the end)"""
    ctx = ssl.create_default_context(cafile=REMOTE_CRT)
    ctx.check_hostname = False                     # the certificate itself is pinned (connect), whatever name it carries
    stamp = os.path.join(MIRROR, ".pulled")
    try:
        url, etag = open(stamp).read().split("\n")[:2]            # the VM the copy is from, and its ETag
        etag = etag if url == REMOTE["url"] else ""
    except (OSError, ValueError):
        etag = ""
    req = urllib.request.Request(REMOTE["url"] + "/snapshot.tar.gz", headers={
        "Authorization": f"Bearer {REMOTE['token']}", **({"If-None-Match": etag} if etag else {})})
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=60)
        data, etag = r.read(), r.headers.get("ETag", "")
    except urllib.error.HTTPError as e:
        if e.code == 304:                          # unchanged: keep the copy, restart the 10 min clock
            os.utime(stamp)
            return
        sys.exit(f"paas-market: {REMOTE['url']}: {e.reason}")
    except Exception as e:
        sys.exit(f"paas-market: {REMOTE['url']}: {getattr(e, 'reason', e)}")
    new = MIRROR + ".new"
    shutil.rmtree(new, ignore_errors=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        for ti in t.getmembers():                  # only plain files and folders, inside the copy
            if not (ti.isfile() or ti.isdir()) or ti.name.startswith("/") or ".." in ti.name.split("/"):
                sys.exit(f"paas-market: refused {REMOTE['url']}: unexpected entry {ti.name!r}")
        t.extractall(new, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
    open(os.path.join(new, ".pulled"), "w").write(f"{REMOTE['url']}\n{etag}\n")
    shutil.rmtree(MIRROR + ".old", ignore_errors=True)
    if os.path.exists(MIRROR):
        os.rename(MIRROR, MIRROR + ".old")
    os.rename(new, MIRROR)
    shutil.rmtree(MIRROR + ".old", ignore_errors=True)
    n = len(json.load(open(os.path.join(MIRROR, "marketplace", "index.json"))))
    print(f"marketplace of {REMOTE['url']}: {n} items (+ plugins and shared items)", file=sys.stderr)


def fresh():
    """with another VM's marketplace: refresh the copy when it is 10 min old; keep the old copy if that VM is down"""
    stamp = os.path.join(MIRROR, ".pulled")
    if not REMOTE or (os.path.exists(stamp) and time.time() - os.path.getmtime(stamp) < 600):
        return
    if not os.path.exists(stamp):
        return pull()
    try:
        pull()
    except SystemExit as e:
        print(f"{e} (using the copy from {time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(stamp)))})", file=sys.stderr)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    if cmd == "connect":
        fp = args[args.index("--fingerprint") + 1] if "--fingerprint" in args[:-1] else ""
        args = [a for a in args if a != "--fingerprint" and a != fp]
        return connect(*(args + ["", ""])[:2], want=fp)
    if cmd == "disconnect":
        for p in (REMOTE_CFG, REMOTE_CRT):
            if os.path.exists(p):
                os.remove(p)
        shutil.rmtree(MIRROR, ignore_errors=True)
        return print("back to this VM's own marketplace")
    if cmd == "source" and not (REMOTE and args[:1] not in ([], ["list"])):
        return source_cmd(args)
    if cmd == "pull":
        return pull() if REMOTE else sys.exit("paas-market: not connected to another VM (paas-market connect)")
    if REMOTE and cmd in ("share", "unshare", "new", "edit", "publish", "setup-mcp", "import-mcp", "reindex", "source"):
        sys.exit(f"paas-market: the marketplace here is {REMOTE['url']} (read-only): create and share there")
    fresh()
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
    elif cmd == "view":
        ids = parse_ids(args)
        if len(ids) != 1:
            sys.exit("usage: paas-market view <kind>/<name>")
        view(*ids[0])
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
            sys.exit("usage: paas-market setup-mcp <name> <url> [shared|personal|none]   (root; a shared token on stdin)")
        mode = args[2] if len(args) > 2 else "none"     # no third argument: no token (as before)
        if mode not in TOKEN_MODES:                    # older form: setup-mcp <name> <url> <token>
            setup_mcp(args[0], args[1], mode, "shared")
        else:
            setup_mcp(args[0], args[1], read_secret("shared token: ") if mode == "shared" else "", mode)
    elif cmd == "import-mcp":
        if os.geteuid() != 0:
            sys.exit("paas-market: import-mcp is for root")
        import_mcp(args)
    elif cmd == "reindex":
        reindex()
    else:
        sys.exit(f"paas-market: unknown command '{cmd}' (paas-market --help)")


if __name__ == "__main__":
    main(sys.argv[1:])
