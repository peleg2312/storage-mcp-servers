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
import functools
import json
import os
import math
import re
import sqlite3
import sys
from pathlib import Path


def find_db(arg):
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [arg, os.getenv("INDEX_DB", "").split(",")[0], os.path.join(here, "docs.db"),
             os.path.expanduser("~/.claude/brain/library/docs.db"), "/data/index/docs.db", "/bundle/docs.db"]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    sys.exit("no index found: give --db <docs.db> (built by docs_index.py or extracted from library/)")


class _Conn(sqlite3.Connection):
    """Holds the idf counts of its own index (another index, or a swapped file, has other counts)."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.df = {}


def connect(path, shared=False):
    """Read-only connection; shared=True for a connection used from several threads (server.py)."""
    c = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, check_same_thread=not shared, factory=_Conn)
    c.row_factory = sqlite3.Row
    return c


# Storage-domain synonyms: a query word matches any member of its group (old product names, acronyms).
SYNONYMS = [
    ["powerflex", "vxflex", "scaleio", "pflex"], ["powermax", "vmax", "symmetrix", "pmax"],
    ["powerscale", "isilon", "onefs"], ["sdc", "scini"], ["pfmp", "powerflex management platform"],
    ["mdm", "meta data manager"], ["sds", "storage data server"], ["rdp", "replication data pointer"],
    ["srdf", "remote data facility"], ["symcli", "solutions enabler"], ["unisphere", "u4p"],
    ["dsa", "dell security advisory"], ["csm", "container storage modules"],
    ["csi", "container storage interface"], ["k8s", "kubernetes"], ["ocp", "openshift"],
    ["pvc", "persistent volume claim"], ["fc", "fibre channel"], ["hu", "host utilities"],
    ["mcc", "metrocluster"], ["sfo", "storage failover"], ["gdd", "granular data distribution"],
    ["sm-as", "snapmirror active sync", "smbc"], ["snapmirror", "snap mirror"],
    ["air gapped", "airgapped", "airgap", "offline", "disconnected", "dark site"],
]

_SYN = {w: g for g in SYNONYMS for w in g}
CODE_EXT = (".go", ".py", ".proto", ".yaml", ".yml", ".sh")
SOURCE_EXT = (".go", ".py", ".proto", ".sh")
LEGACY = {"ontap-7mode-transition", "ontap-system-manager-classic"}      # old releases: only when asked for
FIX_WORDS = {"pr", "fix", "fixed", "fixes", "bug", "bugs", "issue", "merged", "release", "released", "regression",
             "broken", "known", "workaround", "changelog", "version", "first"}
INTENT = {"best", "practice", "practices", "recommend", "recommended", "recommendation", "recommendations",
          "guideline", "guidelines", "tips", "advice", "should", "work", "works", "explain", "overview", "difference"}
INTENT_W = 0.3   # measured: neutral on every eval set, fixes "<topic> design best practices" picking any BP title
CODE_WORDS = {"code", "function", "func", "functions", "implementation", "implemented", "implement", "source",
              "golang", "method", "calls", "codebase", "exec", "runs"}
API_WORDS = {"rest", "api", "endpoint", "curl", "json", "uuid", "http", "https", "swagger", "patch", "post"}
VERSION = re.compile(r"\bv?(\d+(?:\.\d+)+)\b")
# question type -> page type (NetApp / Dell name their pages so): "what is / why / should I" wants the concept
# page, "how to / configure / install" the task page
ASK_CONCEPT = re.compile(r"^(what|why|which|should|does|is|are|can|when)\b|\b(what is|what are|what happens|how does|"
                         r"how do .{0,40} work|difference|vs|versus|explain|overview|architecture|concepts?)\b")
ASK_TASK = re.compile(r"\b(how to|how do i|steps?|set ?up|configure|install|create|enable|disable|apply|add|remove|"
                      r"replace|upgrade|collect|deploy|run|migrate|mount|map|expand|resize)\b")
PAGE_CONCEPT = re.compile(r"(concept|overview|definition|architecture|getting-to-know|introduction|/index\.|_index\.|"
                          r"what-is|understand)", re.I)
PAGE_TASK = re.compile(r"(-task\b|\btask_|-task\.|/task-)", re.I)
# measured on 241 questions (dev sets chose, held-out sets confirmed: MRR 0.792 -> 0.816, hit@1 0.70 -> 0.74);
# tried and dropped: concept pages by title, everyday verb synonyms (neutral), document-level aggregation (worse)
W_TITLE, W_SECTION = 6.0, 3.0   # BM25 field weights (text = 1)
COVER_EXP = 2.0                 # how hard a missing query word costs
POOL = (100, 150)               # candidates: all-words chunks, any-word chunks
TYPE_W = 1.3     # boost of a page whose type matches the question type
TITLE_W = 1.5    # weight of the share of query words in the title / section heading
PROX_W = 0.3     # bonus when the matched words sit close together in the section
STOP = set("a an the of for to in on with and or is are was were how what why when where which does do did "
           "my i it its from by at after be can could will this that there into vs via about please".split())


def _terms(q):
    """(required phrases, optional term groups): "quoted" text must match; every other word (or dotted /
    dashed token such as sfo.takeover or naa.600a0980, kept as a phrase) is a group of synonyms."""
    req, groups = [], []
    for m in re.finditer(r'"([^"]+)"|(\S+)', q):
        words = re.findall(r"\w+", (m.group(1) or m.group(2)).lower())
        if not words:
            continue
        if m.group(1):
            req.append(" ".join(words))
            continue
        raw = (m.group(2) or "").lower().strip(".,;:!?()")
        if len(words) == 1 and words[0] in STOP:
            continue
        key = raw if raw in _SYN else " ".join(words)
        alts = _SYN.get(key, [key])
        if re.fullmatch(r"v?\d+(\.\d+)+", raw):          # 2.16.2 is also written v2.16.2 (folders, image tags)
            v = raw.lstrip("v")
            alts = [" ".join(v.split(".")), "v" + " ".join(v.split("."))]
        groups.append([" ".join(re.findall(r"\w+", a)) for a in alts])
    # two words that together form a synonym ("snap mirror", "air gapped") become one group
    i = 0
    while i < len(groups) - 1:
        pair = groups[i][0] + " " + groups[i + 1][0]
        if pair in _SYN:
            groups[i:i + 2] = [_SYN[pair]]
        i += 1
    return req, groups


def _stem(w):
    if len(w) > 5:
        return w[:max(4, len(w) - 3)]
    return w[:-1] if len(w) == 4 and w.endswith("s") and not w.endswith("ss") else w   # logs -> log, LUNs -> lun


@functools.lru_cache(maxsize=None)
def _pat(w):
    return re.compile(r"\b" + re.escape(_stem(w)))


def _proximity(text, groups, found):
    """1 when the matched query words sit together (a window of their count), falling to 0 when spread out."""
    pos = []
    for g, f in zip(groups, found):
        if not f:
            continue
        p = [m.start() for a in g for m in _pat(a.split()[0]).finditer(text)]
        if p:
            pos.append(sorted(p))
    if len(pos) < 2:
        return 0.0
    best, idx = 10 ** 9, [0] * len(pos)                 # smallest character window holding one of each
    while True:
        cur = [pos[i][idx[i]] for i in range(len(pos))]
        lo = min(cur)
        best = min(best, max(cur) - lo)
        i = cur.index(lo)
        idx[i] += 1
        if idx[i] >= len(pos[i]):
            break
    return min(1.0, 12.0 * len(pos) / (best + 1))


def _has(text, alt):
    return all(_pat(w).search(text) for w in alt.split())




def _idf(c, group):
    """BM25-style inverse document frequency of a word group over all chunks (cached per connection)."""
    d, key = c.df, tuple(group)
    if key not in d:
        if "N" not in d:
            d["N"] = c.execute("SELECT count(*) FROM chunks").fetchone()[0] or 1
        match = " OR ".join('"' + a + '"' for a in group)
        try:
            d[key] = c.execute("SELECT count(*) FROM chunks_fts WHERE chunks_fts MATCH ?", (match,)).fetchone()[0]
        except sqlite3.OperationalError:
            d[key] = 0
    n, df = d["N"], d[key]
    return math.log((n - df + 0.5) / (df + 0.5) + 1)


def search_docs(c, q, vendor="", product="", limit=8):
    """The search_docs tool. Candidates: chunks containing the quoted phrases and any query word (or a
    synonym); ranking: BM25 (title incl. folder context x6, section x3, text x1) x the squared share of
    query words the chunk covers (all-word matches lead, a strong near-miss still shows) x (1 + 1.5 x share of
    them in the title / section heading) x proximity of the words x question type = page type (concept /
    task) x 0.5 for source code; at most two chunks per document."""
    req, groups = _terms(q)
    if not req and not groups:
        raise ValueError("empty query")
    phrase = lambda s: '"' + s + '"'  # noqa: E731
    sql = ("SELECT c.id AS chunk_id, d.id AS doc_id, d.vendor, d.product, d.title, chunks_fts.heading AS section, "
           "d.url, d.path, "
           f"bm25(chunks_fts, {W_TITLE}, {W_SECTION}, 1.0) AS score, chunks_fts.title AS ctx, chunks_fts.text AS body "
           "FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid JOIN docs d ON d.id = c.doc_id "
           "WHERE chunks_fts MATCH ?")
    filters = []
    if vendor:
        sql += " AND d.vendor = ?"
        filters.append(vendor.lower())
    if product:   # the document itself or any identical copy (alias) in a matching product
        sql += " AND (d.product LIKE ? OR EXISTS (SELECT 1 FROM docs a WHERE a.dup_of = d.id AND a.product LIKE ?))"
        filters += [f"%{product}%", f"%{product}%"]
    sql += " ORDER BY score LIMIT ?"

    def any_match(groups):
        return " AND ".join([phrase(r) for r in req] +
                            (["(" + " OR ".join(phrase(a) for g in groups for a in g) + ")"] if groups else []))

    def candidates(groups):
        # chunks holding every word group (a short page with all words is never crowded out by long pages
        # repeating common words), plus the best chunks holding any of them
        every = [phrase(r) for r in req] + ["(" + " OR ".join(phrase(a) for a in g) + ")" for g in groups]
        found = {}
        for match, n in ((" AND ".join(every), POOL[0]), (any_match(groups), POOL[1])):
            for r in c.execute(sql, [match] + filters + [n]):
                found.setdefault(r["chunk_id"], dict(r))
        return found

    qwords = set(re.findall(r"\w+", q.lower()))
    ql = q.lower()
    want = "concept" if ASK_CONCEPT.search(ql) else "task" if ASK_TASK.search(ql) else ""
    versions = VERSION.findall(q.lower())
    # a version in the question ("3.0", "2.16.2", "9.15.1") must win over its neighbours ("3.3"), which FTS
    # cannot tell apart (it splits on dots); docs folders write it with dots, dashes or none (ontap-ems-9151)
    vforms = [{v, v.replace(".", "-"), v.replace(".", "")} for v in versions]
    cands = candidates(groups)
    if not cands and any(" " in a for g in groups for a in g):   # near miss on a dotted / multi-word term:
        groups = [[w] for g in groups for w in g[0].split()]     # try its words one by one
        cands = candidates(groups)
    lim = max(1, min(int(limit), 50))
    idf = [_idf(c, g) ** 0.25 * (INTENT_W if g[0] in INTENT else 1.0) for g in groups]   # rare words weigh more
    # than filler ("very", "find"; 0.25 measured best); phrasing words ("best practices", "recommended") weigh
    # little, so a question about VMFS datastore size is not answered by any document titled "Best Practices"
    total = sum(idf) or 1.0
    scored = []
    for r in cands.values():
        title = f"{r.pop('ctx')}\n{r['section'] or ''}".lower()
        text = f"{title}\n{r.pop('body')}".lower()
        found = [any(_has(text, a) for a in g) for g in groups]
        hit = sum(found)
        cover = sum(w for w, f in zip(idf, found) if f) / total if groups else 1.0
        in_title = sum(w for w, g in zip(idf, groups) if any(_has(title, a) for a in g)) / total if groups else 0.0
        r["matched"] = f"{hit}/{len(groups)}" if groups else "phrases"
        r["_found"] = found
        # document-type priors: docs first; code wins on exact error text, config samples (yaml) a little less
        weight = 0.5 if r["path"].endswith(SOURCE_EXT) else 0.8 if r["path"].endswith(CODE_EXT) else 1.0
        if qwords & CODE_WORDS and r["path"].endswith(SOURCE_EXT):
            weight = 1.2                                          # "how does the driver code ..." wants the code
        if r["product"] == "ontap-restapi":
            weight *= 1.5 if qwords & API_WORDS else 0.6          # API reference when asked for the API
        if r["product"] in LEGACY and not qwords & {"7", "mode", "7mode", "transition", "classic"}:
            weight *= 0.6
        if r["product"].endswith("-prs") and not qwords & FIX_WORDS:
            weight *= 0.7                                         # pull requests answer "fixed in / known bug"
        if vforms:
            where = f"{r['path']} {title}".lower()
            weight *= 1 + sum(any(re.search(r"(?<![\d.])" + re.escape(f) + r"(?![\d])", where) for f in fs)
                              for fs in vforms) / len(vforms)
        if want:
            kind = "concept" if PAGE_CONCEPT.search(r["path"]) else "task" if PAGE_TASK.search(r["path"]) else ""
            if kind == want:
                weight *= TYPE_W
        if hit > 1:
            weight *= 1 + PROX_W * _proximity(text, groups, found)
        scored.append((-r["score"] * cover ** COVER_EXP * weight * (1 + TITLE_W * in_title), cover, r))
    scored.sort(key=lambda t: -t[0])
    rows, per_doc, found_in, by_key = [], {}, [], {}
    for final, cover, r in scored:
        if per_doc.get(r["doc_id"], 0) >= 2:
            continue
        # the same page in another version / copy (same title and section, different file): one result, the
        # others listed in also_in by path, so they cost no result slot (measured: 10% of slots were such repeats)
        key = (r["vendor"], _norm_title(r["title"]), _norm_title(r["section"] or ""))
        if key in by_key and by_key[key]["doc_id"] != r["doc_id"]:
            keep = by_key[key]
            if r["path"] not in keep.setdefault("also_in", []) and len(keep["also_in"]) < 6:
                keep["also_in"].append(r["path"])
            continue
        per_doc[r["doc_id"]] = per_doc.get(r["doc_id"], 0) + 1
        by_key.setdefault(key, r)
        found_in.append(r.pop("_found"))
        r["score"] = round(final, 2)                    # relevance, for merging libraries (callers drop it)
        if r["section"] == r["title"]:
            r.pop("section")                            # token economy: no repeated text, no empty fields
        alias = also_in(c, r["path"])
        if alias:
            r["also_in"] = alias
        rows.append(r)
        if len(rows) >= lim:
            break
    if rows:                                            # the snippet is cut only for the rows returned
        ids = [r["chunk_id"] for r in rows]
        snip = dict(c.execute("SELECT rowid, snippet(chunks_fts, 2, '«', '»', ' … ', 40) FROM chunks_fts WHERE chunks_fts "
                              f"MATCH ? AND rowid IN ({','.join('?' * len(ids))})", [any_match(groups)] + ids))
    for r in rows:
        r.pop("doc_id", None)
        r["snippet"] = snip[r["chunk_id"]]
    facet = {}
    for _, _, r in scored[:60]:                         # where the strong candidates live: the next product filter
        facet[r["product"]] = facet.get(r["product"], 0) + 1
    full = bool(scored) and scored[0][1] == 1.0
    mode = "all words" if full else "partial: no chunk contains every word; best coverage first (see matched)"
    out = {"match_mode": mode, "results": rows}
    if not product and len(facet) > 1 and max(facet.values()) < 0.9 * sum(facet.values()):
        out["by_product"] = dict(sorted(facet.items(), key=lambda kv: -kv[1])[:6])
    # words no returned hit holds: the agent's cue to rephrase exactly those with the vendor's term
    missing = [g[0] for i, g in enumerate(groups) if rows and not any(f[i] for f in found_in)]
    if missing:
        out["unmatched"] = missing
    return out


def for_agent(out):
    """The search answer as an agent reads it: no internal score, the path only when there is no url (read_document
    takes either; citations use the url), no title repeated at the start of the snippet, `matched` only on partial
    hits, `partial: true` instead of the match_mode text. ~25% fewer tokens."""
    if out.pop("match_mode", "all words") != "all words":
        out["partial"] = True
    for r in out.get("results", []):
        r.pop("score", None)
        h, _, n = (r.get("matched") or "").partition("/")
        if h == n or h == "phrases":
            r.pop("matched", None)
        if r.get("url"):
            r.pop("path", None)
        sn, t = r.get("snippet") or "", re.sub(r"\s+", " ", r.get("title") or "").strip()
        flat = re.sub(r"[«»]", "", sn).lstrip()
        if t and flat.startswith(t):
            n = 0
            for i, ch in enumerate(sn):                 # skip the title, keeping the «» marks after it
                if ch not in "«»":
                    n += 1
                if n >= len(t) + (len(sn) - len(sn.lstrip())):
                    r["snippet"] = sn[i + 1:].lstrip(" \n:-")
                    break
    return out


def _norm_title(t):
    """Title without version / product decoration: "PowerFlex API 5.1.0: Map a volume" = "... 4.5.5-...: Map a volume"."""
    t = re.sub(r"\s*\|\s*dell.*$", "", (t or "").lower())
    t = re.sub(r"\bv?\d+(\.\d+)+[\w.-]*", " ", t)
    return re.sub(r"\W+", " ", t).strip()


def also_in(c, path):
    """Products / versions holding an identical copy of this document (folded by the indexer)."""
    try:
        row = c.execute("SELECT id FROM docs WHERE path = ?", (path,)).fetchone()
        if not row:
            return []
        return [f"{r[0]}/{r[1]}" for r in c.execute("SELECT vendor, product FROM docs WHERE dup_of = ? ORDER BY product", (row[0],))]
    except sqlite3.OperationalError:
        return []


def read_chunk(c, chunk_id, context=1, id_base=0):
    """id_base: server.py makes chunk ids unique across indexes (index number x ID_BASE + id)."""
    row = c.execute("SELECT doc_id, seq FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    if not row:
        raise LookupError(f"chunk {chunk_id} not found (the index may have been rebuilt; search again)")
    ctx = max(0, min(int(context), 3))
    doc = dict(c.execute("SELECT title, url, path, vendor, product, chunks FROM docs WHERE id = ?",
                         (row["doc_id"],)).fetchone())
    parts = c.execute("SELECT c.id, c.seq, f.heading, f.text FROM chunks c JOIN chunks_fts f ON f.rowid = c.id "
                      "WHERE c.doc_id = ? AND c.seq BETWEEN ? AND ? ORDER BY c.seq",
                      (row["doc_id"], row["seq"] - ctx, row["seq"] + ctx)).fetchall()
    doc["sections"] = [{"chunk_id": id_base + p["id"], "seq": p["seq"], "section": p["heading"], "text": p["text"],
                        "is_hit": p["id"] == chunk_id} for p in parts]
    return doc


def read_doc(c, path="", url="", start=0, max_sections=15, id_base=0):
    start = max(0, int(start))
    d = c.execute("SELECT * FROM docs WHERE path = ?", (path,)).fetchone() if path else \
        c.execute("SELECT * FROM docs WHERE url = ? ORDER BY dup_of IS NOT NULL", (url,)).fetchone()   # a url can repeat: canonical copy first
    if not d:
        raise LookupError("document not found in the index")
    try:
        if d["dup_of"] is not None:
            d = c.execute("SELECT * FROM docs WHERE id = ?", (d["dup_of"],)).fetchone()
    except (IndexError, KeyError):
        pass
    n = max(1, min(int(max_sections), 40))
    parts = c.execute("SELECT c.id, c.seq, f.heading, f.text FROM chunks c JOIN chunks_fts f ON f.rowid = c.id "
                      "WHERE c.doc_id = ? AND c.seq >= ? ORDER BY c.seq LIMIT ?", (d["id"], start, n)).fetchall()
    nxt = start + len(parts)
    return {"title": d["title"], "url": d["url"], "path": d["path"], "also_in": also_in(c, d["path"]),
            "total_sections": d["chunks"], "start": start, "next_start": nxt if nxt < d["chunks"] else None,
            "sections": [{"chunk_id": id_base + p["id"], "seq": p["seq"], "section": p["heading"], "text": p["text"]}
                         for p in parts]}


def sources(c, vendor=""):
    """What is in the index: {vendor: "product documents, ..."} (products by size), optionally one vendor."""
    rows = c.execute("SELECT vendor, product, count(*) AS n FROM docs" + (" WHERE vendor = ?" if vendor else "") +
                     " GROUP BY vendor, product ORDER BY vendor, n DESC", [vendor.lower()] if vendor else [])
    by, total = {}, 0
    for v, p, n in rows:
        by.setdefault(v, []).append(f"{p} {n}")
        total += n
    meta = dict(c.execute("SELECT key, value FROM meta").fetchall())
    return {"indexed_at": meta.get("indexed_at"), "bundle": meta.get("bundle"), "documents": total,
            "by_vendor": {v: ", ".join(p) for v, p in by.items()}}


def main():
    try:                                   # `search.py ... | head` must not print a traceback
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", help="index file (docs.db)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="full-text search (all words; falls back to any word)")
    s.add_argument("query")
    s.add_argument("--vendor", default="", help="netapp | dell | kb | <your folder>")
    s.add_argument("--product", default="", help="substring of the product/repo, e.g. ontap-ems-9171, trident, csm")
    s.add_argument("--limit", type=int, default=8)
    r = sub.add_parser("read-chunk", help="a hit in full with neighbouring sections")
    r.add_argument("chunk_id", type=int)
    r.add_argument("--context", type=int, default=1)
    d = sub.add_parser("read-doc", help="a whole document in order (page with --start)")
    d.add_argument("--path", default="")
    d.add_argument("--url", default="")
    d.add_argument("--start", type=int, default=0)
    d.add_argument("--max", type=int, default=15)
    sub.add_parser("sources", help="what is in the library").add_argument("--vendor", default="")
    a = ap.parse_args()

    try:
        run(a, connect(find_db(a.db)))
    except LookupError as e:
        sys.exit(str(e))


def run(a, c):
    if a.cmd == "search":
        out = search_docs(c, a.query, a.vendor, a.product, a.limit)
        rows, mode = out["results"], out["match_mode"]
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return
        print(f"{len(rows)} results ({mode}) for: {a.query}")
        for i, h in enumerate(rows, 1):
            print(f"\n[{i}] chunk {h['chunk_id']}  {h['vendor']}/{h['product']}  score {h['score']:.1f}  matched {h['matched']}")
            print(f"    {h['title']}  ::  {h.get('section', h['title'])}")
            print(f"    {h['url'] or h['path']}")
            if h.get("also_in"):
                print(f"    also in: {', '.join(h['also_in'])}")
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
        out = sources(c, a.vendor)
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return
        print(f"library bundle {out['bundle']} indexed {out['indexed_at']}: {out['documents']} documents")
        for v, p in out["by_vendor"].items():
            print(f"  {v}: {p}")


if __name__ == "__main__":
    main()
