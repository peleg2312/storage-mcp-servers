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

Implements MCP over stdio (JSON-RPC 2.0, one message per line): initialize, ping, tools/list,
tools/call, and empty prompts/resources lists. Read-only.
"""

import argparse
import json
import os
import sys
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
    def __init__(self, db, brain_db=None):
        self.con = lib.connect(db)
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
                self.brain_con = lib.connect(self.brain_path)
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
            outs.append((q, lib.search_docs(self.con, q, vendor, product, limit)))
            if b is not None:
                o = lib.search_docs(b, q, vendor, product, limit)
                for r in o["results"]:
                    r["chunk_id"] += ID_BASE
                    r["library"] = "team knowledge"
                outs.append((q, o))
        out = outs[0][1] if len(outs) == 1 else lib.merge_queries(outs, limit)
        if b is not None and len(qs) > 1 or (b is not None and "by_query" in out):   # one entry per query, both indexes counted
            byq = {}
            for e in out.get("by_query", []):
                m = byq.setdefault(e["q"], {"q": e["q"], "hits": 0})
                m["hits"] += e["hits"]
                for k in ("partial", "unmatched"):
                    if k in e:
                        m[k] = e[k]
            out["by_query"] = list(byq.values())
            if len(qs) == 1:
                out.pop("by_query", None)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db")
    ap.add_argument("--brain-db")
    a = ap.parse_args()
    srv = Server(lib.find_db(a.db), a.brain_db)
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
