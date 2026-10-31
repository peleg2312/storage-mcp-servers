"""
docs-search MCP: read-only full-text search over the local documentation library
(NetApp ONTAP / SAN host / VMware integration docs, Dell PowerMax & PowerFlex PDFs, KB pointers,
your own runbooks). BM25 ranking via SQLite FTS5; no data leaves the pod at query time.
"""

import logging
import os
import sys
import threading
from typing import List, Optional

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import search_cli as lib  # noqa: E402  (in the library folder it is search.py)
except ImportError:
    import search as lib  # noqa: E402
import docs_text  # noqa: E402

log = logging.getLogger("docs-search")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# One or more indexes, comma-separated: e.g. the vendor library baked into the offline image plus a
# local index of the team's own runbooks / saved KB articles:  /bundle/docs.db,/data/local/local.db
DBS = [p.strip() for p in os.getenv("INDEX_DB", "/data/index/docs.db").split(",") if p.strip()]
RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
ID_BASE = 10 ** 10            # chunk ids are made unique across indexes: db_number * ID_BASE + local id

_cons, _lock = {}, threading.Lock()


def con(i: int):
    """Read-only connection to index i; reopened when the indexer swaps in a new file. None if absent."""
    path = DBS[i]
    with _lock:
        try:
            m = os.path.getmtime(path)
        except OSError:
            _cons.pop(i, None)             # not closed: a request may still be using it; GC closes it
            return None
        cur = _cons.get(i)
        if cur is None or cur[1] != m:     # (a replaced connection is not closed either, same reason)
            _cons[i] = (lib.connect(path, shared=True), m)
            log.info("opened index %s", path)
        return _cons[i][0]


def all_cons():
    out = [(i, c) for i in range(len(DBS)) for c in [con(i)] if c is not None]
    if not out:
        raise RuntimeError(f"No index found at {DBS}. Build or import the documentation index (see README).")
    return out


def split_id(gid: int):
    i, local = divmod(int(gid), ID_BASE)
    if gid < 0 or i >= len(DBS) or con(i) is None:
        raise LookupError(f"chunk {gid} not found (index missing or rebuilt; search again)")
    return i, con(i), local


def _search(q, vendor, product, limit):
    """lib.search_docs over every index, merged by relevance; chunk ids made unique per index."""
    rows, full, unmatched, facet = [], False, None, {}
    for i, c in all_cons():
        out = lib.search_docs(c, q, vendor, product, limit)
        for k, v in out.get("by_product", {}).items():   # where the strong candidates are, over every index
            facet[k] = facet.get(k, 0) + v
        full = full or out["match_mode"] == "all words"
        miss = out.get("unmatched", []) if out["results"] else None     # a library with no hits says nothing
        if miss is not None:
            unmatched = miss if unmatched is None else [w for w in unmatched if w in miss]
        for d in out["results"]:
            d["chunk_id"] = i * ID_BASE + d["chunk_id"]
            if len(DBS) > 1:
                d["library"] = "local" if i > 0 else "main"
            rows.append(d)
    def cover(r):                          # BM25 scores of differently sized indexes don't compare: coverage first
        h, _, n = r["matched"].partition("/")
        return int(h) / int(n) if n else 1.0
    rows.sort(key=lambda r: (-cover(r), -r["score"]))
    out = {"match_mode": "all words" if full else "partial", "results": rows[:max(1, min(int(limit), 50))]}
    if len(facet) > 1 and max(facet.values()) < 0.9 * sum(facet.values()):
        out["by_product"] = dict(sorted(facet.items(), key=lambda kv: -kv[1])[:6])
    if unmatched:
        out["unmatched"] = unmatched
    return out


def _text(gid):
    i, c, local = split_id(gid)
    return lib.read_chunk(c, local, 0, i * ID_BASE)["sections"][0]["text"]


mcp = FastMCP("docs-search", instructions=docs_text.INSTRUCTIONS)


@mcp.tool(annotations=RO, description=docs_text.SEARCH_DOC)
def search_docs(query: str = "", vendor: str = "", product: str = "", limit: int = 8, read_top: int = 0,
                queries: Optional[List[str]] = None) -> dict:
    qs = lib.query_list(query, queries)
    if not qs[0]:
        raise ValueError("give query or queries")
    outs = [(q, _search(q, vendor, product, limit)) for q in qs]
    return lib.finish_search(outs[0][1] if len(outs) == 1 else lib.merge_queries(outs, limit), read_top, _text)


@mcp.tool(annotations=RO, description=docs_text.EXPLAIN_DOC)
def explain_code(code: str) -> dict:
    for i, c in all_cons():
        out = lib.explain_code(c, code, i * ID_BASE)
        if out.get("kind"):
            return out
    return {"code": code.strip(), "documented": False}


@mcp.tool(annotations=RO)
def read_chunk(chunk_id: int, context: int = 1) -> dict:
    """Read a search hit in full, plus `context` neighbouring sections before and after (0-3) from the
    same document, in order."""
    i, c, local = split_id(chunk_id)
    return lib.read_chunk(c, local, context, i * ID_BASE)


@mcp.tool(annotations=RO)
def read_document(path: str = "", url: str = "", start: int = 0, max_sections: int = 15) -> dict:
    """Read a whole document in order, by its path (from search results) or its url. Use start to page
    through long documents (PDF chunks are pages)."""
    if not (path or url):
        raise ValueError("give path or url")
    for i, c in all_cons():
        try:
            return lib.read_doc(c, path, url, start, max_sections, i * ID_BASE)
        except LookupError:
            pass
    raise LookupError("document not found in the index")


@mcp.tool(annotations=RO, description=docs_text.RELATED_DOC)
def related_docs(chunk_id: int = 0, path: str = "", url: str = "", limit: int = 10) -> dict:
    if chunk_id:
        i, c, local = split_id(chunk_id)
        return lib.related_docs(c, local, limit=limit)
    for i, c in all_cons():
        try:
            return lib.related_docs(c, 0, path, url, limit)
        except LookupError:
            pass
    raise LookupError("document not found in the index")


@mcp.tool(annotations=RO)
def list_sources(vendor: str = "") -> dict:
    """What is in the library: documents per vendor and product ("product documents, ..."), and when it
    was indexed. vendor: list one vendor only."""
    return {"libraries": [{"library": "local" if i > 0 else "main", **lib.sources(c, vendor)} for i, c in all_cons()]}


@mcp.prompt()
def explain_error(error_text: str) -> str:
    """Find what an error / event / alert means and how to fix it."""
    return (f"Explain this storage error and how to resolve it: {error_text!r}. Search the docs with the exact "
            "event/error name first (search_docs), then the key words; read the best 2-3 hits (read_chunk); also "
            "search vendor 'kb'. Answer: what it means, likely causes, how to verify on the live system (which "
            "MCP tool), the fix, and the source links. Say clearly if the docs do not cover it.")


@mcp.prompt()
def how_to(task: str, platform: str = "") -> str:
    """Find the documented procedure for a task."""
    return (f"Find the official documented procedure for: {task!r}{(' on ' + platform) if platform else ''}. "
            "Search, read the procedure fully (read_document if needed), and give the steps with the exact "
            "commands, prerequisites and warnings, citing the source and version.")


if __name__ == "__main__":
    import mcp_auth
    mcp_auth.run(mcp)
