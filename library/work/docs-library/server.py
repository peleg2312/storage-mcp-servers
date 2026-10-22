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
            if i in _cons:
                _cons.pop(i)[0].close()
            return None
        cur = _cons.get(i)
        if cur is None or cur[1] != m:
            if cur is not None:
                cur[0].close()
            c = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
            c.row_factory = sqlite3.Row
            _cons[i] = (c, m)
            log.info("opened index %s", path)
        return _cons[i][0]


def all_cons():
    out = [(i, c) for i in range(len(DBS)) for c in [con(i)] if c is not None]
    if not out:
        raise RuntimeError(f"No index found at {DBS}. Build or import the documentation index (see README).")
    return out


def split_id(gid: int):
    i, local = divmod(int(gid), ID_BASE)
    if i >= len(DBS) or con(i) is None:
        raise LookupError(f"chunk {gid} not found (index missing or rebuilt; search again)")
    return i, con(i), local


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
    lim = max(1, min(int(limit), 50))
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
    args.append(lim)
    rows = []
    for i, c in all_cons():
        for r in c.execute(sql, args):
            d = dict(r)
            d["chunk_id"] = i * ID_BASE + d["chunk_id"]
            d["library"] = "local" if i > 0 else "main"
            rows.append(d)
    rows.sort(key=lambda r: r["score"])
    return rows[:lim]


INSTRUCTIONS = """\
Read-only, fully OFFLINE search over the team's documentation library. Nothing here needs internet.

WHAT IS IN IT (vendor / product names to filter on; list_sources shows the exact set and dates)
- netapp: ontap (ONTAP 9: SAN admin, NVMe, data protection, release notes), ontap-sanhost (ESXi /
  Linux / Windows / AIX host settings, multipathing), ontap-tools-vmware-vsphere*, sc-plugin-vmware-vsphere,
  snapcenter, ontap-metrocluster, ontap-ems-9131/9161/9171 (EMS event reference: meaning + corrective
  action), ontap-automation (REST), ontap-fli, ontap-systems (hardware), asa-r2, ontap-technical-reports,
  e-series, storagegrid, active-iq-unified-manager, trident (Trident CSI docs), harvest.
- netapp trident-issues / harvest-issues and dell csm-issues: the public GitHub bug trackers -
  every reported bug with its discussion, workaround and fix version. Search these for error messages.
- dell: powermax (product, Unisphere, Solutions Enabler, REST, SRDF, SnapVX, VMware papers),
  powerflex (3.6/4.x/5.x guides, release notes with fixed/known issues), csm (Dell Container Storage
  Modules: CSI PowerMax/PowerFlex/PowerScale/PowerStore/Unity, replication, observability, authorization),
  pyu4v.
- kb: curated KB pointers (ID + one-line answer + link).
- library "local": the team's own runbooks and KB articles saved from the vendor portals.

HOW TO USE
- search_docs first, with the exact technical terms: error text, EMS/event names, command names
  (lun mapping show, symdev, esxcli storage core device, tridentctl), CSI/CSM error strings, KB numbers.
  Filter by vendor/product when you know the platform (e.g. product="trident-issues" for a Trident error).
- read_chunk on the best hits before answering - snippets are partial. read_document reads a whole
  document in order (page through long PDFs with start).
- Answer from what you read and cite title + url for every claim (urls are for the humans; you cannot
  open them - there is no internet). If nothing relevant is found, say so; never invent commands,
  settings or bug numbers.
- Mind versions: say which ONTAP / PowerMaxOS / PowerFlex / Trident / CSM version a statement is from.
  For bugs, report the affected and fixed versions from the issue or release notes.
- Live state comes from the PowerMax / ONTAP / Harvest / MDS / UCS / vCenter MCP servers; this server
  explains how things work, what errors mean, known bugs, and documented procedures.
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
    i, c, local = split_id(chunk_id)
    row = c.execute("SELECT doc_id, seq FROM chunks WHERE id = ?", (local,)).fetchone()
    if not row:
        raise LookupError(f"chunk {chunk_id} not found (the index may have been rebuilt; search again)")
    ctx = max(0, min(int(context), 3))
    doc = dict(c.execute("SELECT title, url, path, vendor, product, chunks FROM docs WHERE id = ?",
                         (row["doc_id"],)).fetchone())
    parts = c.execute("SELECT c.id, c.seq, f.heading, f.text FROM chunks c JOIN chunks_fts f ON f.rowid = c.id "
                      "WHERE c.doc_id = ? AND c.seq BETWEEN ? AND ? ORDER BY c.seq",
                      (row["doc_id"], row["seq"] - ctx, row["seq"] + ctx)).fetchall()
    return {**doc, "sections": [{"chunk_id": i * ID_BASE + p["id"], "seq": p["seq"], "section": p["heading"],
                                 "text": p["text"], "is_hit": p["id"] == local} for p in parts]}


@mcp.tool(annotations=RO)
def read_document(path: str = "", url: str = "", start: int = 0, max_sections: int = 15) -> dict:
    """Read a whole document in order, by its path (from search results) or its url. Use start to page
    through long documents (PDF chunks are pages)."""
    if not (path or url):
        raise ValueError("give path or url")
    d, c, i = None, None, 0
    for i, c in all_cons():
        d = c.execute("SELECT * FROM docs WHERE path = ?", (path,)).fetchone() if path else \
            c.execute("SELECT * FROM docs WHERE url = ?", (url,)).fetchone()
        if d:
            break
    if not d:
        raise LookupError("document not found in the index")
    n = max(1, min(int(max_sections), 40))
    parts = c.execute("SELECT c.id, c.seq, f.heading, f.text FROM chunks c JOIN chunks_fts f ON f.rowid = c.id "
                      "WHERE c.doc_id = ? AND c.seq >= ? ORDER BY c.seq LIMIT ?", (d["id"], int(start), n)).fetchall()
    return {"title": d["title"], "url": d["url"], "path": d["path"], "total_sections": d["chunks"],
            "start": int(start), "next_start": int(start) + len(parts) if int(start) + len(parts) < d["chunks"] else None,
            "sections": [{"chunk_id": i * ID_BASE + p["id"], "seq": p["seq"], "section": p["heading"], "text": p["text"]}
                         for p in parts]}


@mcp.tool(annotations=RO)
def list_sources() -> dict:
    """What is in the library: documents and sections per vendor/product, and when it was indexed."""
    libs = []
    for i, c in all_cons():
        rows = [dict(r) for r in c.execute("SELECT vendor, product, count(*) AS documents, sum(chunks) AS sections "
                                           "FROM docs GROUP BY vendor, product ORDER BY vendor, documents DESC")]
        meta = dict(c.execute("SELECT key, value FROM meta").fetchall())
        libs.append({"library": "local" if i > 0 else "main", "index": DBS[i], "indexed_at": meta.get("indexed_at"),
                     "bundle": meta.get("bundle"), "documents": sum(r["documents"] for r in rows),
                     "sections": sum(r["sections"] or 0 for r in rows), "sources": rows})
    return {"libraries": libs}


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
