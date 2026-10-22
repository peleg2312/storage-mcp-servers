"""
docs-search MCP: read-only full-text search over the local documentation library
(NetApp ONTAP / SAN host / VMware integration docs, Dell PowerMax & PowerFlex PDFs, KB pointers,
your own runbooks). BM25 ranking via SQLite FTS5; no data leaves the pod at query time.
"""

import logging
import os
import re
import sqlite3
import threading

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

log = logging.getLogger("docs-search")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

DB = os.getenv("INDEX_DB", "/data/index/docs.db")
RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

_con, _mtime, _lock = None, None, threading.Lock()


def con():
    """Read-only connection; reopened automatically when the indexer swaps in a new index."""
    global _con, _mtime
    with _lock:
        try:
            m = os.path.getmtime(DB)
        except OSError:
            raise RuntimeError(f"No index at {DB} yet. Run the sync/index job (see README).") from None
        if _con is None or m != _mtime:
            if _con is not None:
                _con.close()
            _con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)
            _con.row_factory = sqlite3.Row
            _mtime = m
            log.info("opened index %s", DB)
        return _con


def fts_query(q: str, mode: str = "and") -> str:
    """Turn free text into a safe FTS5 query. "quoted phrases" stay phrases; tokens with dots or
    dashes (naa.600a0980, wafl.vol.full, lun-map) become phrases of their parts."""
    if mode == "or":  # fallback: any individual word
        words = list(dict.fromkeys(w.lower() for w in re.findall(r"\w+", q) if len(w) > 1))
        if not words:
            raise ValueError("empty query")
        return " OR ".join('"' + w + '"' for w in words)
    parts = []
    for m in re.finditer(r'"([^"]+)"|(\S+)', q):
        raw = m.group(1) or m.group(2)
        words = re.findall(r"\w+", raw)
        if not words:
            continue
        parts.append('"' + " ".join(words) + '"' if len(words) > 1 else '"' + words[0] + '"')
    if not parts:
        raise ValueError("empty query")
    return " ".join(parts)


def _search(q, vendor, product, limit, mode):
    sql = ("SELECT c.id AS chunk_id, d.vendor, d.product, d.title, chunks_fts.heading AS section, d.url, d.path, "
           "snippet(chunks_fts, 2, '«', '»', ' … ', 40) AS snippet, bm25(chunks_fts, 6.0, 3.0, 1.0) AS score "
           "FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid JOIN docs d ON d.id = c.doc_id "
           "WHERE chunks_fts MATCH ?")
    args = [fts_query(q, mode)]
    if vendor:
        sql += " AND d.vendor = ?"
        args.append(vendor.lower())
    if product:
        sql += " AND d.product LIKE ?"
        args.append(f"%{product}%")
    sql += " ORDER BY score LIMIT ?"
    args.append(max(1, min(int(limit), 50)))
    return [dict(r) for r in con().execute(sql, args)]


INSTRUCTIONS = """\
Read-only search over the team's local documentation library: NetApp ONTAP (SAN administration,
NVMe, SAN host configuration for ESXi/Linux/Windows, ONTAP tools for VMware, SnapMirror active sync,
MetroCluster, EMS event reference, REST API, technical reports), Dell PowerMax/VMAX and PowerFlex
documents (product, Unisphere, Solutions Enabler, REST, SRDF, SnapVX, VMware papers), curated KB
pointers (vendor "kb"), and any runbooks the team added.

HOW TO USE
- search_docs first. Use the exact technical terms: command names (lun mapping show, symdev,
  esxcli storage core device), EMS / event names (callhome.hm.alarm), error text, KB numbers,
  feature names. Filter with vendor ("netapp", "dell", "kb", or the team's own folder) and product
  (e.g. "ontap", "ontap-sanhost", "ontap-ems-9171", "powermax", "powerflex").
- Then read_chunk on the best hits before answering - snippets are partial. read_document reads a
  whole document in order (use start to page through long PDFs).
- Answer from what you read and cite the document title and url for every claim. If nothing
  relevant is found, say so and suggest the official link or a live KB lookup; do not invent
  commands or settings.
- Mind versions: ONTAP docs are for current ONTAP 9 releases, EMS references are per release
  (ontap-ems-9131/9161/9171), PowerFlex docs exist for 3.6, 4.x and 5.x, PowerMax for several
  PowerMaxOS/Unisphere releases. Say which version a statement comes from.
- Live state (what a system is doing now) comes from the PowerMax / ONTAP / Harvest / MDS / UCS /
  vCenter MCP servers; this server is for how things work, settings, procedures and error meanings.
"""

mcp = FastMCP("docs-search", instructions=INSTRUCTIONS)


@mcp.tool(annotations=RO)
def search_docs(query: str, vendor: str = "", product: str = "", limit: int = 10) -> dict:
    """Full-text search (BM25) over all indexed documentation. query: words, "exact phrases",
    command names, error/EMS names, KB numbers. vendor: netapp | dell | kb | <your folder>.
    product: substring of the product/repo (ontap, ontap-sanhost, ontap-ems-9171, powermax, powerflex...).
    All words must match; if nothing matches, falls back to any-word match. Returns chunk_ids for
    read_chunk, with title, section, snippet (matches in «»), url."""
    rows = _search(query, vendor, product, limit, "and")
    mode = "all words"
    if not rows:
        rows = _search(query, vendor, product, limit, "or")
        mode = "any word (no document contained all words)"
    return {"query": query, "match_mode": mode, "results": rows}


@mcp.tool(annotations=RO)
def read_chunk(chunk_id: int, context: int = 1) -> dict:
    """Read a search hit in full, plus `context` neighbouring sections before and after (0-3) from the
    same document, in order."""
    c = con()
    row = c.execute("SELECT doc_id, seq FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    if not row:
        raise LookupError(f"chunk {chunk_id} not found (the index may have been rebuilt; search again)")
    ctx = max(0, min(int(context), 3))
    doc = dict(c.execute("SELECT title, url, path, vendor, product, chunks FROM docs WHERE id = ?",
                         (row["doc_id"],)).fetchone())
    parts = c.execute("SELECT c.id, c.seq, f.heading, f.text FROM chunks c JOIN chunks_fts f ON f.rowid = c.id "
                      "WHERE c.doc_id = ? AND c.seq BETWEEN ? AND ? ORDER BY c.seq",
                      (row["doc_id"], row["seq"] - ctx, row["seq"] + ctx)).fetchall()
    return {**doc, "sections": [{"chunk_id": p["id"], "seq": p["seq"], "section": p["heading"],
                                 "text": p["text"], "is_hit": p["id"] == chunk_id} for p in parts]}


@mcp.tool(annotations=RO)
def read_document(path: str = "", url: str = "", start: int = 0, max_sections: int = 15) -> dict:
    """Read a whole document in order, by its path (from search results) or its url. Use start to page
    through long documents (PDF chunks are pages)."""
    c = con()
    if path:
        d = c.execute("SELECT * FROM docs WHERE path = ?", (path,)).fetchone()
    elif url:
        d = c.execute("SELECT * FROM docs WHERE url = ?", (url,)).fetchone()
    else:
        raise ValueError("give path or url")
    if not d:
        raise LookupError("document not found in the index")
    n = max(1, min(int(max_sections), 40))
    parts = c.execute("SELECT c.id, c.seq, f.heading, f.text FROM chunks c JOIN chunks_fts f ON f.rowid = c.id "
                      "WHERE c.doc_id = ? AND c.seq >= ? ORDER BY c.seq LIMIT ?", (d["id"], int(start), n)).fetchall()
    return {"title": d["title"], "url": d["url"], "path": d["path"], "total_sections": d["chunks"],
            "start": int(start), "next_start": int(start) + len(parts) if int(start) + len(parts) < d["chunks"] else None,
            "sections": [{"chunk_id": p["id"], "seq": p["seq"], "section": p["heading"], "text": p["text"]} for p in parts]}


@mcp.tool(annotations=RO)
def list_sources() -> dict:
    """What is in the library: documents and sections per vendor/product, and when it was indexed."""
    c = con()
    rows = c.execute("SELECT vendor, product, count(*) AS documents, sum(chunks) AS sections FROM docs "
                     "GROUP BY vendor, product ORDER BY vendor, documents DESC").fetchall()
    meta = dict(c.execute("SELECT key, value FROM meta").fetchall())
    return {"indexed_at": meta.get("indexed_at"), "totals": {"documents": sum(r["documents"] for r in rows),
            "sections": sum(r["sections"] or 0 for r in rows)}, "sources": [dict(r) for r in rows]}


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
