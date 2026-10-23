#!/usr/bin/env python3
"""
docs-search as a **stdio MCP server with no dependencies** (Python 3 standard library only): the same
four tools as server.py (search_docs, read_chunk, read_document, list_sources) over the library index,
for a VM that runs Claude Code but has no pip, no containers and no internet.

    claude mcp add docs-local -s user -- python3 ~/.claude/brain/library/mcp_stdio.py
    python3 mcp_stdio.py --db /path/to/docs.db          (index: --db, else $INDEX_DB, else next to the script)

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

INSTRUCTIONS = """\
Read-only, fully OFFLINE search over the team's storage documentation library: NetApp ONTAP / EMS /
SAN hosts / Trident docs and KB, Dell PowerMax / PowerFlex / PowerScale / CSM docs and KB, the CSI
driver and Kubernetes CSI sidecar source code, Dell CSM pull requests (the fixes) and the Trident /
Harvest issue trackers. Nothing here needs internet; the urls are for the humans.
1. search_docs with the exact technical terms (error text in "quotes", EMS / event names, commands,
   KB / CONTAP / DSA numbers). Old and new product names and common acronyms match each other.
   Filter by vendor / product when the platform is known (list_sources gives the names).
2. read_chunk the best 2-3 hits before answering; read_document for a whole page or PDF.
3. Cite title + url + version for every statement; never invent commands, settings or bug numbers.
   "matched" shows how many query words a hit contains: a partial match is weak evidence."""

TOOLS = [
    {"name": "search_docs",
     "description": "Search all indexed documentation, KB articles, bug trackers, pull requests and source "
                    "code. query: technical words; \"quoted text\" must appear verbatim (use it for error "
                    "messages); other words are ranked by how many a section contains, with synonyms (Isilon = "
                    "PowerScale, ScaleIO = PowerFlex, VMAX = PowerMax, RDP, SRDF, CSM...). vendor: netapp | dell | "
                    "kubernetes | vmware | kb. product: substring of the product (ontap-ems-9151, kb-ontap, "
                    "trident-2510, csm, csi-powermax, csm-prs, powerflex, external-attacher...). Returns up to "
                    "`limit` hits (max 2 per document) with chunk_id for read_chunk, title, section, snippet "
                    "(matches in «»), url, matched (query words found / total) and also_in (identical copies in "
                    "other versions).",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string"}, "vendor": {"type": "string", "default": ""},
         "product": {"type": "string", "default": ""}, "limit": {"type": "integer", "default": 10}},
         "required": ["query"]},
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
    {"name": "list_sources",
     "description": "What is in the library: documents and sections per vendor/product, and when it was indexed.",
     "inputSchema": {"type": "object", "properties": {}},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
]


class Server:
    def __init__(self, db):
        self.con = lib.connect(db)

    def call(self, name, args):
        if name == "search_docs":
            return lib.search_docs(self.con, args["query"], args.get("vendor", ""), args.get("product", ""),
                                   args.get("limit", 10))
        if name == "read_chunk":
            return lib.read_chunk(self.con, int(args["chunk_id"]), args.get("context", 1))
        if name == "read_document":
            if not (args.get("path") or args.get("url")):
                raise ValueError("give path or url")
            return lib.read_doc(self.con, args.get("path", ""), args.get("url", ""), args.get("start", 0),
                                args.get("max_sections", 15))
        if name == "list_sources":
            s = lib.sources(self.con)
            return {"libraries": [{"library": "main", **s}]}
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
                return {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=1)}],
                        "isError": False}
            except SystemExit as e:          # search_cli uses sys.exit for "not found"
                return {"content": [{"type": "text", "text": str(e)}], "isError": True}
            except Exception as e:
                return {"content": [{"type": "text", "text": f"{e.__class__.__name__}: {e}"}], "isError": True}
        if mid is None:
            return None                      # notification (notifications/initialized etc.)
        raise LookupError(method)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db")
    a = ap.parse_args()
    srv = Server(lib.find_db(a.db))
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
