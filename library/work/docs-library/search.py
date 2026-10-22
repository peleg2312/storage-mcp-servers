#!/usr/bin/env python3
"""
Offline command-line search over the documentation library index (docs.db). Standard library only:
works on any machine with python3, no MCP server, no internet, no pip. Same ranking, query syntax and
results as the docs-search MCP server (search_docs / read_chunk / read_document / list_sources).

    python3 search_cli.py search "lun mapping show" [--vendor netapp] [--product ontap] [--limit 10]
    python3 search_cli.py read-chunk 12345 [--context 1]
    python3 search_cli.py read-doc --path netapp/ontap/san-admin/map-lun-task.adoc [--start 0] [--max 15]
    python3 search_cli.py read-doc --url https://docs.netapp.com/us-en/ontap/san-admin/map-lun-task.html
    python3 search_cli.py sources
    python3 search_cli.py search "..." --json          (machine-readable output)

Index file: --db, else $INDEX_DB, else docs.db next to this script, else ~/.claude/brain/library/docs.db.
"""

import argparse
import json
import os
import re
import sqlite3
import sys


def find_db(arg):
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [arg, os.getenv("INDEX_DB", "").split(",")[0], os.path.join(here, "docs.db"),
             os.path.expanduser("~/.claude/brain/library/docs.db"), "/data/index/docs.db", "/bundle/docs.db"]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    sys.exit("no index found: give --db <docs.db> (built by docs_index.py or extracted from library/)")


def connect(path):
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def fts_query(q, mode="and"):
    if mode == "or":
        words = list(dict.fromkeys(w.lower() for w in re.findall(r"\w+", q) if len(w) > 1))
        if not words:
            raise ValueError("empty query")
        return " OR ".join('"' + w + '"' for w in words)
    parts = []
    for m in re.finditer(r'"([^"]+)"|(\S+)', q):
        raw = m.group(1) or m.group(2)
        words = re.findall(r"\w+", raw)
        if words:
            parts.append('"' + " ".join(words) + '"')
    if not parts:
        raise ValueError("empty query")
    return " ".join(parts)


def search(c, q, vendor="", product="", limit=10, mode="and"):
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
    return [dict(r) for r in c.execute(sql, args)]


def read_chunk(c, chunk_id, context=1):
    row = c.execute("SELECT doc_id, seq FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    if not row:
        sys.exit(f"chunk {chunk_id} not found")
    ctx = max(0, min(int(context), 3))
    doc = dict(c.execute("SELECT title, url, path, vendor, product, chunks FROM docs WHERE id = ?",
                         (row["doc_id"],)).fetchone())
    parts = c.execute("SELECT c.id, c.seq, f.heading, f.text FROM chunks c JOIN chunks_fts f ON f.rowid = c.id "
                      "WHERE c.doc_id = ? AND c.seq BETWEEN ? AND ? ORDER BY c.seq",
                      (row["doc_id"], row["seq"] - ctx, row["seq"] + ctx)).fetchall()
    doc["sections"] = [{"chunk_id": p["id"], "seq": p["seq"], "section": p["heading"], "text": p["text"],
                        "is_hit": p["id"] == chunk_id} for p in parts]
    return doc


def read_doc(c, path="", url="", start=0, max_sections=15):
    d = c.execute("SELECT * FROM docs WHERE path = ?", (path,)).fetchone() if path else \
        c.execute("SELECT * FROM docs WHERE url = ?", (url,)).fetchone()
    if not d:
        sys.exit("document not found in the index")
    n = max(1, min(int(max_sections), 40))
    parts = c.execute("SELECT c.id, c.seq, f.heading, f.text FROM chunks c JOIN chunks_fts f ON f.rowid = c.id "
                      "WHERE c.doc_id = ? AND c.seq >= ? ORDER BY c.seq LIMIT ?", (d["id"], int(start), n)).fetchall()
    nxt = int(start) + len(parts)
    return {"title": d["title"], "url": d["url"], "path": d["path"], "total_sections": d["chunks"],
            "start": int(start), "next_start": nxt if nxt < d["chunks"] else None,
            "sections": [{"chunk_id": p["id"], "seq": p["seq"], "section": p["heading"], "text": p["text"]}
                         for p in parts]}


def sources(c):
    rows = [dict(r) for r in c.execute("SELECT vendor, product, count(*) AS documents, sum(chunks) AS sections "
                                       "FROM docs GROUP BY vendor, product ORDER BY vendor, documents DESC")]
    meta = dict(c.execute("SELECT key, value FROM meta").fetchall())
    return {"indexed_at": meta.get("indexed_at"), "bundle": meta.get("bundle"),
            "documents": sum(r["documents"] for r in rows), "sections": sum(r["sections"] or 0 for r in rows),
            "sources": rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", help="index file (docs.db)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="full-text search (all words; falls back to any word)")
    s.add_argument("query")
    s.add_argument("--vendor", default="", help="netapp | dell | kb | <your folder>")
    s.add_argument("--product", default="", help="substring of the product/repo, e.g. ontap-ems-9171, trident, csm")
    s.add_argument("--limit", type=int, default=10)
    r = sub.add_parser("read-chunk", help="a hit in full with neighbouring sections")
    r.add_argument("chunk_id", type=int)
    r.add_argument("--context", type=int, default=1)
    d = sub.add_parser("read-doc", help="a whole document in order (page with --start)")
    d.add_argument("--path", default="")
    d.add_argument("--url", default="")
    d.add_argument("--start", type=int, default=0)
    d.add_argument("--max", type=int, default=15)
    sub.add_parser("sources", help="what is in the library")
    a = ap.parse_args()

    c = connect(find_db(a.db))
    if a.cmd == "search":
        rows, mode = search(c, a.query, a.vendor, a.product, a.limit), "all words"
        if not rows:
            rows, mode = search(c, a.query, a.vendor, a.product, a.limit, "or"), "any word"
        out = {"query": a.query, "match_mode": mode, "results": rows}
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return
        print(f"{len(rows)} results ({mode}) for: {a.query}")
        for i, h in enumerate(rows, 1):
            print(f"\n[{i}] chunk {h['chunk_id']}  {h['vendor']}/{h['product']}  score {h['score']:.1f}")
            print(f"    {h['title']}  ::  {h['section']}")
            print(f"    {h['url'] or h['path']}")
            print("    " + re.sub(r"\s+", " ", h["snippet"]).strip())
    elif a.cmd == "read-chunk":
        out = read_chunk(c, a.chunk_id, a.context)
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return
        print(f"# {out['title']}\n{out['url'] or ''}\npath: {out['path']}  ({out['chunks']} sections)")
        for s_ in out["sections"]:
            print(f"\n## {s_['section']}  [chunk {s_['chunk_id']}, seq {s_['seq']}{', HIT' if s_['is_hit'] else ''}]\n")
            print(s_["text"])
    elif a.cmd == "read-doc":
        if not (a.path or a.url):
            sys.exit("give --path or --url")
        out = read_doc(c, a.path, a.url, a.start, a.max)
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return
        print(f"# {out['title']}\n{out['url'] or ''}\npath: {out['path']}  sections {out['start']}.. of {out['total_sections']}")
        for s_ in out["sections"]:
            print(f"\n## {s_['section']}  [seq {s_['seq']}]\n\n{s_['text']}")
        if out["next_start"] is not None:
            print(f"\n... continue with --start {out['next_start']}")
    else:
        out = sources(c)
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return
        print(f"library bundle {out['bundle']} indexed {out['indexed_at']}: {out['documents']} documents, "
              f"{out['sections']} sections")
        for r_ in out["sources"]:
            print(f"  {r_['vendor']:8} {r_['product']:34} {r_['documents']:7} docs {r_['sections'] or 0:8} sections")


if __name__ == "__main__":
    main()
