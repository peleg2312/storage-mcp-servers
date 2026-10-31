#!/usr/bin/env python3
"""
docs-search as a **stdio MCP server with no dependencies** (Python 3 standard library only): the same
tools as server.py (search_docs, explain_code, read_chunk, read_document, related_docs, list_sources) over the library index,
for a VM that runs Claude Code but has no pip, no containers and no internet.

    claude mcp add docs-local -s user -- python3 ~/.claude/brain/library/mcp_stdio.py
    python3 mcp_stdio.py --db /path/to/docs.db          (index: --db, else $INDEX_DB, else next to the script)
    --brain-db PATH   a second, small index of the person's team knowledge (notes pages, incidents; built by
                      `add-docs --brain`), searched together with the library: --brain-db, else $BRAIN_DB, else
                      ~/.claude/brain/brain.db; opened when the file exists, so it may appear later. Its chunk ids are
                      offset by ID_BASE as server.py does for several indexes.
    --knowledge DIR   the brain folder (~/.claude/brain): its notes/*.md and incidents are indexed into the --brain-db
                      index at start when they changed since the last run (one or two seconds for a team's pages, nothing
                      otherwise), so the team knowledge is searched with the library without any other step. Without a
                      library (--db missing: a laptop) the knowledge index is the only index (knowledge-only mode).
    --shared-knowledge DIR   a multi-user VM: the docs service keeps one index per team under DIR (/var/lib/paas-docs,
                      <team>.db + .stamp); when it is as fresh as this person's clone it is used as is, so twenty people
                      do not each rebuild the same index; otherwise the person's own index is built as usual.
    --http [HOST:]PORT  serve the same tools to other machines over MCP's Streamable HTTP (POST /mcp, JSON answers,
                      GET /health), still standard library only: the VM's docs-search for laptops and other VMs.
      --token-file F    bearer token every /mcp request must carry (one line; 401 otherwise)
      --tls-cert C --tls-key K   HTTPS with the gate's certificate
      --teams-dir D     /mcp?team=<name> searches that team's knowledge too: D/<name>/team.json names the team's git
                        remote, the server keeps its own clone and index under --state-dir, pulled and rebuilt every
                        --refresh-minutes (default 10) and at once on POST /refresh?team=<name> (the notes hook sends it
                        after every push); a team without a remote is indexed from D/<name>/knowledge

Implements MCP over stdio (JSON-RPC 2.0, one message per line): initialize, ping, tools/list,
tools/call, and empty prompts/resources lists. Read-only.
"""

import argparse
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import search_cli as lib  # noqa: E402  (in the repo: search_cli.py; in the library folder: search.py)
except ImportError:
    import search as lib  # noqa: E402
from docs_text import EXPLAIN_DOC, INSTRUCTIONS, RELATED_DOC, SEARCH_DOC  # noqa: E402

TOOLS = [
    {"name": "search_docs",
     "description": SEARCH_DOC,
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string"}, "queries": {"type": "array", "items": {"type": "string"}},
         "vendor": {"type": "string", "default": ""}, "product": {"type": "string", "default": ""},
         "limit": {"type": "integer", "default": 8}, "read_top": {"type": "integer", "default": 0}}},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "explain_code",
     "description": EXPLAIN_DOC,
     "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "read_chunk",
     "description": "Read a search hit in full, plus `context` neighbouring sections before and after (0-3) "
                    "from the same document, in order.",
     "inputSchema": {"type": "object", "properties": {
         "chunk_id": {"type": "integer"}, "context": {"type": "integer", "default": 1}}, "required": ["chunk_id"]},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "read_document",
     "description": "Read a whole document in order, by its path (from search results) or its url. Use start "
                    "to page through long documents (PDF chunks are pages).",
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string", "default": ""}, "url": {"type": "string", "default": ""},
         "start": {"type": "integer", "default": 0}, "max_sections": {"type": "integer", "default": 15}}},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "related_docs",
     "description": RELATED_DOC,
     "inputSchema": {"type": "object", "properties": {
         "chunk_id": {"type": "integer", "default": 0}, "path": {"type": "string", "default": ""},
         "url": {"type": "string", "default": ""}, "limit": {"type": "integer", "default": 10}}},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "list_sources",
     "description": "What is in the library: documents per vendor and product (\"product documents, ...\"), and "
                    "when it was indexed. vendor: list one vendor only.",
     "inputSchema": {"type": "object", "properties": {"vendor": {"type": "string", "default": ""}}},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
]


ID_BASE = 10 ** 10            # chunk ids of the team-knowledge index: ID_BASE + local id (server.py's rule for several indexes)


def default_brain_db():
    return os.environ.get("BRAIN_DB") or os.path.join(os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude"), "brain", "brain.db")


class Server:
    def __init__(self, db, brain_db=None, shared=False):
        self.shared = shared                                  # HTTP mode: requests arrive on several threads (one at a time, locked)
        self.con = lib.connect(db, shared)
        self.brain_path = brain_db or default_brain_db()
        self.brain_con = None
        self.brain_mtime = None

    def brain(self):
        """the team-knowledge index when its file exists; reopened when add-docs --brain rebuilt it"""
        try:
            st = os.stat(self.brain_path)
        except OSError:
            self.brain_con = None
            return None
        if self.brain_con is None or st.st_mtime != self.brain_mtime:
            try:
                self.brain_con = lib.connect(self.brain_path, self.shared)
                self.brain_mtime = st.st_mtime
            except Exception:
                self.brain_con = None
        return self.brain_con

    def where(self, chunk_id):
        """(connection, local id, id base) of a chunk id"""
        if chunk_id >= ID_BASE and self.brain():
            return self.brain_con, chunk_id - ID_BASE, ID_BASE
        return self.con, chunk_id, 0

    def search(self, args):
        qs = lib.query_list(args.get("query", ""), args.get("queries"))
        vendor, product, limit = args.get("vendor", ""), args.get("product", ""), args.get("limit", 8)
        outs = []
        b = self.brain()
        for q in qs:
            o = lib.search_docs(self.con, q, vendor, product, limit)
            if b is not None:                                 # the team knowledge joins the library's answer for this query
                ob = lib.search_docs(b, q, vendor, product, limit)
                for r in ob["results"]:
                    r["chunk_id"] += ID_BASE
                    r["library"] = "team knowledge"
                o["results"] = sorted(o["results"] + ob["results"], key=lambda r: -r["score"])
                if ob.get("match_mode", "all words") == "all words":
                    o["match_mode"] = "all words"
                for k, v in ob.get("by_product", {}).items():
                    o.setdefault("by_product", {})[k] = o.get("by_product", {}).get(k, 0) + v
            outs.append((q, o))
        if len(outs) == 1 and b is not None:
            out = lib.merge_queries(outs, limit)              # the per-document rule and the limit over both indexes
            out.pop("by_query", None)
        else:
            out = outs[0][1] if len(outs) == 1 else lib.merge_queries(outs, limit)
        return lib.finish_search(out, args.get("read_top", 0),
                                 lambda cid: lib.read_chunk(self.where(cid)[0], self.where(cid)[1], 0)["sections"][0]["text"])

    def call(self, name, args):
        if name == "search_docs":
            if not (args.get("query") or args.get("queries")):
                raise ValueError("give query or queries")
            return self.search(args)
        if name == "explain_code":
            return lib.explain_code(self.con, args["code"])
        if name == "read_chunk":
            c, local, base = self.where(int(args["chunk_id"]))
            return lib.read_chunk(c, local, args.get("context", 1), base)
        if name == "read_document":
            if not (args.get("path") or args.get("url")):
                raise ValueError("give path or url")
            path = args.get("path", "")
            if path.startswith("brain/") and self.brain():
                return lib.read_doc(self.brain_con, path, args.get("url", ""), args.get("start", 0), args.get("max_sections", 15), ID_BASE)
            try:
                return lib.read_doc(self.con, path, args.get("url", ""), args.get("start", 0), args.get("max_sections", 15))
            except LookupError:
                if not self.brain():
                    raise
                return lib.read_doc(self.brain_con, path, args.get("url", ""), args.get("start", 0), args.get("max_sections", 15), ID_BASE)
        if name == "related_docs":
            cid = int(args.get("chunk_id", 0))
            path = args.get("path", "")
            if (cid >= ID_BASE or path.startswith("brain/")) and self.brain():
                return lib.related_docs(self.brain_con, cid - ID_BASE if cid else 0, path, args.get("url", ""), args.get("limit", 10))
            return lib.related_docs(self.con, cid, path, args.get("url", ""), args.get("limit", 10))
        if name == "list_sources":
            libs = [{"library": "main", **lib.sources(self.con, args.get("vendor", ""))}]
            if self.brain():
                libs.append({"library": "team knowledge", **lib.sources(self.brain_con, args.get("vendor", ""))})
            return {"libraries": libs}
        raise ValueError(f"unknown tool {name}")

    def handle(self, msg):
        method, params, mid = msg.get("method"), msg.get("params") or {}, msg.get("id")
        if method == "initialize":
            return {"protocolVersion": params.get("protocolVersion", "2025-06-18"),
                    "capabilities": {"tools": {"listChanged": False}, "prompts": {}, "resources": {}},
                    "serverInfo": {"name": "docs-search", "version": "1.2-stdio"},
                    "instructions": INSTRUCTIONS}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": TOOLS}
        if method in ("prompts/list", "resources/list", "resources/templates/list"):
            return {method.split("/")[0]: []} if method != "resources/templates/list" else {"resourceTemplates": []}
        if method == "tools/call":
            try:
                out = self.call(params.get("name"), params.get("arguments") or {})
                return {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, separators=(",", ":"))}],
                        "isError": False}
            except Exception as e:
                return {"content": [{"type": "text", "text": f"{e.__class__.__name__}: {e}"}], "isError": True}
        if mid is None:
            return None                      # notification (notifications/initialized etc.)
        raise LookupError(method)


# ---- HTTP mode ---------------------------------------------------------------------------------------------------

def _docs_index():
    """docs_index.py: beside this file (repository), in the library folder, or in the brain's tools"""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    home = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")
    for p in (os.path.join(here, "docs_index.py"), os.path.join(home, "tools", "docs_index.py"), "/opt/paas/tools/docs_index.py"):
        if os.path.isfile(p):
            spec = importlib.util.spec_from_file_location("docs_index", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def refresh_knowledge(brain_dir, db_path):
    """notes/*.md and incidents/**/*.md of the brain folder into db_path (prefix brain/, products brain-notes and
    brain-incidents), rebuilt only when the set of files or their newest mtime changed (stamp beside the db). Returns the
    db path, or None when there is nothing to index and no index exists."""
    import glob
    import shutil
    files = knowledge_files(brain_dir)
    stamp = db_path + ".stamp"
    state = knowledge_state(brain_dir, files)

    def fresh():
        try:
            return open(stamp).read().strip() == state and os.path.exists(db_path)
        except OSError:
            return False
    if fresh():
        return db_path
    if not files and not os.path.exists(stamp):
        return db_path if os.path.exists(db_path) else None   # no pages and no index of ours: leave whatever is there alone
    di = _docs_index()
    if di is None:
        return db_path if os.path.exists(db_path) else None
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    lock = open(db_path + ".lock", "w")                       # two sessions starting together: one builds, the other waits
    try:
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_EX)
    except (ImportError, OSError):
        pass
    try:
        if fresh():
            return db_path
        return _rebuild(files, db_path, stamp, state, di, shutil)
    finally:
        lock.close()


def _rebuild(files, db_path, stamp, state, di, shutil):
    staging = db_path + ".staging"
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(os.path.join(staging, "local", "brain-notes"))
    os.makedirs(os.path.join(staging, "local", "brain-incidents"))
    for f in files:
        if os.sep + "notes" + os.sep in f:
            shutil.copy2(f, os.path.join(staging, "local", "brain-notes", os.path.basename(f)))
        else:
            shutil.copy2(f, os.path.join(staging, "local", "brain-incidents", os.path.basename(os.path.dirname(f)) + "-" + os.path.basename(f)))
    try:
        di.build(staging, db_path, log=lambda *_: None, prefix="brain/")
        with open(stamp, "w") as f:
            f.write(state + "\n")
    except Exception as e:
        print(f"knowledge index not rebuilt: {e}", file=sys.stderr)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return db_path if os.path.exists(db_path) else None


def knowledge_files(root):
    """notes/*.md and incidents/**/*.md under a brain or knowledge folder: regular files inside it only (a symlink pushed
    into a team repository could point at anything the indexing process can read: never followed)"""
    import glob
    real_root = os.path.realpath(root)
    out = []
    for f in sorted(glob.glob(os.path.join(root, "notes", "*.md"))) + sorted(glob.glob(os.path.join(root, "incidents", "**", "*.md"), recursive=True)):
        if os.path.islink(f) or not os.path.isfile(f):
            continue
        if any(os.path.islink(os.path.join(root, part)) for part in ("notes", "incidents")) and not os.path.realpath(f).startswith(real_root + os.sep):
            continue                                   # a symlinked folder is fine (the brain's own links) as long as the file sits inside the real root
        out.append(f)
    return out


def knowledge_state(brain_dir, files):
    """a fingerprint of the knowledge pages that is the same in every clone of the same commit (names and contents, not
    mtimes), so the service's index and a member's clone can be compared; cheap: a team's pages are small"""
    import hashlib
    h = hashlib.sha1()
    for f in files:
        h.update(os.path.relpath(f, brain_dir).encode())
        try:
            with open(f, "rb") as fh:
                h.update(fh.read())
        except OSError:
            pass
    return "%d:%s" % (len(files), h.hexdigest()[:16])


def shared_knowledge(brain_dir, shared_dir):
    """the service's index of the person's active team, when its stamp matches the clone's pages (same count and newest
    mtime, as refresh_knowledge computes it); None otherwise"""
    import glob
    try:
        team = open(os.path.join(brain_dir, "team")).read().strip()
    except OSError:
        return None
    db = os.path.join(shared_dir, team + ".db")
    try:
        files = knowledge_files(brain_dir)
        state = knowledge_state(brain_dir, files)
        if open(db + ".stamp").read().strip() == state and os.access(db, os.R_OK):
            return db
    except OSError:
        pass
    return None


def empty_index(db_path):
    """an index with no documents (a laptop before its first note), so docs-local still answers"""
    import shutil
    import tempfile
    di = _docs_index()
    if di is None:
        sys.exit("no library and no team knowledge to index yet")
    tmp = tempfile.mkdtemp()
    try:
        di.build(tmp, db_path, log=lambda *_: None, prefix="brain/")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return db_path


class Teams:
    """Team knowledge for the HTTP server: one clone and one small index per team, refreshed from the team repository."""

    def __init__(self, teams_dir, state_dir, log):
        self.dir, self.state, self.log = teams_dir, state_dir, log
        self.servers = {}
        self.lock = __import__("threading").Lock()
        self.refresh_lock = __import__("threading").Lock()

    def names(self):
        try:
            return sorted(d for d in os.listdir(self.dir) if os.path.isfile(os.path.join(self.dir, d, "team.json")))
        except OSError:
            return []

    def db(self, team):
        return os.path.join(self.state, "index", team + ".db")      # index/: readable by members' docs-local; the clones are not

    def refresh(self, only=None):
        """pull every team's repository (its own clone under the state dir) and rebuild its index when the knowledge
        changed; only=<team>: that team alone (POST /refresh?team=<team>, sent by the notes hook right after a push)"""
        import glob
        import shutil
        import subprocess
        di = _docs_index()
        with self.refresh_lock:
            self._refresh(only, glob, shutil, subprocess, di)

    def _refresh(self, only, glob, shutil, subprocess, di):
        for team in ([only] if only else self.names()):
            if team not in self.names():
                continue
            try:
                meta = json.load(open(os.path.join(self.dir, team, "team.json")))
                remote = meta.get("remote")
                clone = os.path.join(self.state, "teams", team)
                env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
                if remote:
                    if os.path.isdir(os.path.join(clone, ".git")):
                        subprocess.run(["git", "-C", clone, "pull", "-q", "--ff-only"], env=env, timeout=120, capture_output=True)
                    else:
                        os.makedirs(os.path.dirname(clone), exist_ok=True)
                        r = subprocess.run(["git", "clone", "-q", "--", remote, clone], env=dict(env, GIT_ALLOW_PROTOCOL="https:ssh:file"), timeout=300, capture_output=True, text=True)
                        if r.returncode:
                            shown = re.sub(r"://[^/@]+@", "://", remote)          # never a credential in the journal
                            self.log(f"team {team}: clone of {shown} failed: {re.sub(r'://[^/@]+@', '://', r.stderr.strip()[-160:])}")
                            clone = os.path.join(self.dir, team)
                else:
                    clone = os.path.join(self.dir, team)       # no remote: the VM's copy is all there is
                k = os.path.join(clone, "knowledge")
                files = knowledge_files(k)
                state = knowledge_state(k, files)
                stamp = self.db(team) + ".stamp"
                try:
                    if open(stamp).read().strip() == state and os.path.exists(self.db(team)):
                        continue
                except OSError:
                    pass
                if di is None:
                    self.log("docs_index.py not found: team knowledge is not indexed")
                    return
                index_dir = os.path.dirname(self.db(team))
                os.makedirs(index_dir, exist_ok=True)
                os.chmod(index_dir, 0o755)                 # members read the indexes; the clones (team folders) stay private
                staging = os.path.join(self.state, "staging-" + team)
                shutil.rmtree(staging, ignore_errors=True)
                try:
                    os.makedirs(os.path.join(staging, "local", "brain-notes"))
                    os.makedirs(os.path.join(staging, "local", "brain-incidents"))
                    for f in files:
                        if os.sep + "notes" + os.sep in f:
                            shutil.copy2(f, os.path.join(staging, "local", "brain-notes", os.path.basename(f)), follow_symlinks=False)
                        else:
                            shutil.copy2(f, os.path.join(staging, "local", "brain-incidents", os.path.basename(os.path.dirname(f)) + "-" + os.path.basename(f)), follow_symlinks=False)
                    di.build(staging, self.db(team), log=lambda *_: None, prefix="brain/")
                finally:
                    shutil.rmtree(staging, ignore_errors=True)
                with open(stamp, "w") as f:
                    f.write(state + "\n")
                for p in (self.db(team), stamp):
                    os.chmod(p, 0o644)
                self.log(f"team {team}: knowledge index rebuilt ({len(files)} pages)")
            except Exception as e:
                self.log(f"team {team}: refresh failed: {e}")

    def server(self, team, main):
        """one Server per team: the library connection is the main server's (one cache for all teams), the team index its own"""
        with self.lock:
            if team not in self.servers:
                srv = Server.__new__(Server)
                srv.shared, srv.con, srv.brain_path, srv.brain_con, srv.brain_mtime = True, main.con, self.db(team), None, None
                self.servers[team] = srv
            return self.servers[team]


def serve_http(db, bind, token_file=None, tls_cert=None, tls_key=None, teams_dir=None, state_dir=None, refresh_minutes=10):
    import hmac
    import ssl
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse

    log = lambda m: print(time.strftime("%Y-%m-%dT%H:%M:%S ") + m, flush=True)
    token = open(token_file).read().strip() if token_file else ""
    if token_file and len(token) < 16:
        sys.exit(f"{token_file}: the token must be at least 16 characters (an empty file would mean no authentication)")
    state_dir = state_dir or os.path.join(os.path.expanduser("~"), ".cache", "paas-docs")
    teams = Teams(teams_dir, state_dir, log) if teams_dir else None
    lock = threading.Lock()                         # sqlite connections are used from one thread at a time
    main_srv = Server(db, os.path.join(state_dir, "none.db"), shared=True)   # no personal index in HTTP mode
    refresh_pending = {"flag": False}

    def pick(team):
        if team and teams and team in teams.names():
            return teams.server(team, main_srv)
        return main_srv

    class H(BaseHTTPRequestHandler):
        server_version = "docs-search/1.2-http"
        timeout = 30                                # an idle or slow client releases its thread

        def log_message(self, fmt, *a):            # one quiet line per request, never the body
            log(f"{self.client_address[0]} {self.command} {self.path.split('?')[0]} {a[1] if len(a) > 1 else ''}")

        def send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            if not token:
                return True
            got = self.headers.get("Authorization", "")
            return got.startswith("Bearer ") and hmac.compare_digest(got[7:].strip(), token)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/health":                    # alive, and the team list only to a token holder
                return self.send(200, {"ok": True, **({"teams": teams.names()} if teams and self.authorized() else {})})
            if path == "/mcp":
                if not self.authorized():
                    return self.send(401, {"error": "bearer token required"})
                return self.send(405, {"error": "this server answers POST /mcp with JSON (no event stream)"})
            self.send(404, {"error": "not found"})

        def refresh_now(self, team):
            """POST /refresh[?team=<team>]: pull and re-index at once (the notes hook calls it after a push)"""
            if not self.authorized():
                return self.send(401, {"error": "bearer token required"})
            if not teams:
                return self.send(404, {"error": "no team knowledge on this server"})
            if team and team not in teams.names():
                return self.send(404, {"error": f"unknown team {team}"})
            if not refresh_pending["flag"]:            # many pushes in a row: one refresh runs, the others ride on it
                refresh_pending["flag"] = True

                def go():
                    try:
                        teams.refresh(team or None)
                    finally:
                        refresh_pending["flag"] = False
                threading.Thread(target=go, daemon=True).start()
            self.send(202, {"refreshing": [team] if team else teams.names()})

        def do_DELETE(self):
            self.send(200, {})

        def do_POST(self):
            u = urlparse(self.path)
            if u.path == "/refresh":
                return self.refresh_now((parse_qs(u.query).get("team") or [""])[0])
            if u.path != "/mcp":
                return self.send(404, {"error": "not found"})
            if not self.authorized():
                return self.send(401, {"error": "bearer token required"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = -1
            if n < 0 or n > 1_000_000:
                return self.send(413 if n > 0 else 400, {"error": "bad or too large body"})
            try:
                msg = json.loads(self.rfile.read(n) or b"null")
            except ValueError:
                return self.send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            team = (parse_qs(u.query).get("team") or [""])[0]
            srv = pick(team)
            msgs = msg if isinstance(msg, list) else [msg]
            answers = []
            for m in msgs:
                if not isinstance(m, dict):
                    continue
                mid = m.get("id")
                try:
                    with lock:
                        result = srv.handle(m)
                    if mid is None:
                        continue
                    answers.append({"jsonrpc": "2.0", "id": mid, "result": result})
                except LookupError:
                    answers.append({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {m.get('method')}"}})
                except Exception as e:
                    answers.append({"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": f"{e.__class__.__name__}: {e}"}})
            if not answers:
                return self.send(202, b"")
            self.send(200, answers if isinstance(msg, list) else answers[0])

    if teams:
        def loop():
            while True:
                teams.refresh()
                time.sleep(max(1, refresh_minutes) * 60)
        threading.Thread(target=loop, daemon=True).start()
    host, _, port = bind.rpartition(":")
    httpd = ThreadingHTTPServer((host or "0.0.0.0", int(port)), H)
    if tls_cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(tls_cert, tls_key)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True, do_handshake_on_connect=False)   # the handshake runs in the request thread
    log(f"docs-search listening on {'https' if tls_cert else 'http'}://{host or '0.0.0.0'}:{port}/mcp"
        + (f" (token)" if token else " (no token)") + (f", teams from {teams_dir}" if teams_dir else ""))
    httpd.serve_forever()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db")
    ap.add_argument("--brain-db")
    ap.add_argument("--http", metavar="[HOST:]PORT")
    ap.add_argument("--token-file")
    ap.add_argument("--tls-cert")
    ap.add_argument("--tls-key")
    ap.add_argument("--teams-dir")
    ap.add_argument("--state-dir")
    ap.add_argument("--refresh-minutes", type=int, default=10)
    ap.add_argument("--knowledge", metavar="DIR")
    ap.add_argument("--shared-knowledge", metavar="DIR")
    a = ap.parse_args()
    if not a.http:                                            # every docs-local indexes the person's team knowledge at start
        knowledge = a.knowledge or os.path.dirname(a.brain_db or default_brain_db())
        shared = shared_knowledge(knowledge, a.shared_knowledge) if a.shared_knowledge else None
        a.brain_db = shared or refresh_knowledge(knowledge, a.brain_db or default_brain_db())
        lib_db = lib.locate_db(a.db)
        if not lib_db:                                        # a laptop: the team knowledge is the whole index
            if not a.brain_db:
                a.brain_db = empty_index(os.path.join(knowledge, "brain.db"))
            return serve_stdio(Server(a.brain_db, "/nonexistent-brain-db"))
        a.db = lib_db
    if a.http:
        return serve_http(lib.find_db(a.db), a.http if ":" in a.http else "0.0.0.0:" + a.http, a.token_file, a.tls_cert, a.tls_key,
                          a.teams_dir, a.state_dir, a.refresh_minutes)
    srv = Server(lib.find_db(a.db), a.brain_db)
    return serve_stdio(srv)


def serve_stdio(srv):
    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        mid = msg.get("id")
        try:
            result = srv.handle(msg)
            if mid is None:
                continue
            resp = {"jsonrpc": "2.0", "id": mid, "result": result}
        except LookupError as e:
            resp = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {e}"}}
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            resp = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}}
        out.write(json.dumps(resp, ensure_ascii=False) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
