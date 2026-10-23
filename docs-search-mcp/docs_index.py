"""
Build / update the full-text index of the documentation library.

    python docs_index.py [--docs /data/docs] [--db /data/index/docs.db] [--full]

Layout under --docs (one folder per vendor, one sub-folder per product/repo):
    netapp/<repo>/**/*.adoc|*.md        NetApp docs-as-code (from sync-netapp.sh)
    dell/<product>/*.pdf|*.html         Dell PowerMax / PowerFlex (from sync_dell.py, with manifest.json)
    kb/*.md                             curated KB pointers
    <anything>/<product>/**/*.md|txt|pdf|html  your own runbooks, exports, notes

Incremental: only new/changed files are re-parsed. The index is built in a copy and swapped in
atomically, so the running search server never sees a half-written index.
"""

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from html.parser import HTMLParser

TEXT_EXT = (".adoc", ".md", ".rst", ".txt")
CODE_EXT = (".go", ".py", ".proto", ".yaml", ".yml", ".sh")       # source code (sync-git.sh "code" lines)
CODE_START = re.compile(r"^(func |type |def |class |async def |message |service |rpc |enum |[\w-]+\(\) ?\{)")
MAX_CHUNK = 2400
SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(id INTEGER PRIMARY KEY, path TEXT UNIQUE, vendor TEXT, product TEXT,
  title TEXT, url TEXT, mtime REAL, size INTEGER, chunks INTEGER, hash TEXT, dup_of INTEGER);
CREATE INDEX IF NOT EXISTS docs_hash ON docs(hash);
CREATE INDEX IF NOT EXISTS docs_dup ON docs(dup_of);
CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY, doc_id INTEGER, seq INTEGER);
CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(doc_id, seq);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(title, heading, text,
  tokenize='porter unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""


# ---------------------------------------------------------------------------
# Parsers -> list of (heading, text)
# ---------------------------------------------------------------------------

def _split(sections, title):
    """Split long sections into <= MAX_CHUNK pieces on paragraph boundaries."""
    out = []
    for heading, body in sections:
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if not body:
            continue
        paras, cur = body.split("\n\n"), ""
        for p in paras:
            if len(cur) + len(p) > MAX_CHUNK and cur:
                out.append((heading, cur.strip()))
                cur = ""
            while len(p) > MAX_CHUNK:
                out.append((heading, p[:MAX_CHUNK]))
                p = p[MAX_CHUNK:]
            cur += p + "\n\n"
        if cur.strip():
            out.append((heading, cur.strip()))
    return out or [(title, "")]


_ADOC_DROP = re.compile(r"^(:[\w-]+:.*|//.*|include::.*|image::.*|ifdef::.*|ifndef::.*|endif::.*|"
                        r"\[\.?[\w\-#=\"', ]*\]|\|===|====+|----+|\*\*\*\*+|\+)$")


def _adoc_inline(s):
    s = re.sub(r"(?:link|xref|https?):(\S*?)\[([^\]]*)\]", lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"image:\S+\[[^\]]*\]", "", s)
    s = re.sub(r"\{[\w-]+\}", "", s)
    return s.replace("`", "")


class SkipDocument(Exception):
    pass


def _front_matter(text):
    """Strip a leading YAML front-matter block; return (meta dict, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text[end + 4:]


def parse_adoc(text, fallback):
    meta, text = _front_matter(text)
    if "redirect" in meta:
        raise SkipDocument("redirect stub")
    title, sections, heading, buf = None, [], None, []
    if meta.get("summary"):
        buf.append(meta["summary"].strip("'\""))
    for line in text.splitlines():
        m = re.match(r"^(=+)\s+(.+)$", line)
        if m:
            if len(m.group(1)) == 1 and title is None:
                title = _adoc_inline(m.group(2)).strip()
                heading = title
                continue
            sections.append((heading, "\n".join(buf)))
            heading, buf = _adoc_inline(m.group(2)).strip(), []
            continue
        s = line.rstrip()
        if _ADOC_DROP.match(s.strip()):
            continue
        if s.startswith("|"):
            s = " | ".join(c.strip() for c in s.split("|") if c.strip())
        buf.append(_adoc_inline(s))
    sections.append((heading, "\n".join(buf)))
    title = title or fallback
    return title, _split([(h or title, b) for h, b in sections], title)


def parse_md(text, fallback):
    meta, text = _front_matter(text)
    if "redirect" in meta:
        raise SkipDocument("redirect stub")
    text = re.sub(r"\{\{[<%].*?[%>]\}\}", "", text)          # Hugo shortcodes
    title, sections, heading, buf = None, [], None, []
    if meta.get("title"):
        title = heading = meta["title"].strip("'\"")
        if meta.get("description"):
            buf.append(meta["description"].strip("'\""))
    for line in text.splitlines():
        m = re.match(r"^(#+)\s+(.+)$", line)
        if m:
            if title is None and len(m.group(1)) == 1:
                title = heading = m.group(2).strip()
                continue
            sections.append((heading, "\n".join(buf)))
            heading, buf = m.group(2).strip(), []
            continue
        buf.append(line)
    sections.append((heading, "\n".join(buf)))
    title = title or fallback
    return title, _split([(h or title, b) for h, b in sections], title)


class _HTMLText(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "noscript", "svg"}

    def __init__(self):
        super().__init__()
        self.parts, self.skip, self.title, self._in_title = [], 0, "", False
        self.heading = None
        self.sections = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag == "title":
            self._in_title = True
        if tag in ("h1", "h2", "h3") and not self.skip:
            self.sections.append((self.heading, "".join(self.parts)))
            self.parts, self.heading = [], ""
        if tag in ("p", "br", "li", "tr", "div", "pre"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            if self.heading == "":
                self.heading = data.strip() or ""
            self.parts.append(data)


def parse_html(text, fallback):
    p = _HTMLText()
    p.feed(text)
    p.sections.append((p.heading, "".join(p.parts)))
    title = re.sub(r"\s+", " ", html.unescape(p.title)).strip() or fallback
    secs = [((h or title).strip() or title, re.sub(r"[ \t]+", " ", b)) for h, b in p.sections]
    return title, _split(secs, title)


def parse_pdf(path, fallback):
    from pypdf import PdfReader
    r = PdfReader(path)
    title = fallback
    try:
        if r.metadata and r.metadata.title and len(r.metadata.title.strip()) > 3:
            title = r.metadata.title.strip()
    except Exception:
        pass
    secs = []
    for i, page in enumerate(r.pages, 1):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        secs.append((f"page {i}", t))
    return title, _split(secs, title)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def load_manifests(root):
    """manifest.json files written by sync_dell.py: {relative_file: {url, title, hub}}"""
    out = {}
    for dirpath, _, files in os.walk(root):
        if "manifest.json" in files:
            try:
                data = json.load(open(os.path.join(dirpath, "manifest.json")))
            except Exception:
                continue
            for name, meta in data.items():
                out[os.path.normpath(os.path.join(dirpath, name))] = meta
    return out


SOURCE_URLS = {}


def load_source_urls(root):
    """<vendor>/<product>/.source_url written by sync-git.sh -> link to the file on GitHub."""
    for vendor in os.listdir(root):
        vd = os.path.join(root, vendor)
        if not os.path.isdir(vd):
            continue
        for product in os.listdir(vd):
            f = os.path.join(vd, product, ".source_url")
            if os.path.isfile(f):
                SOURCE_URLS[(vendor.lower(), product)] = open(f).read().strip()


def url_for(vendor, product, rel_in_product, manifest_meta):
    if manifest_meta and manifest_meta.get("url"):
        return manifest_meta["url"]
    src = SOURCE_URLS.get((vendor, product), "")
    if rel_in_product.endswith(".adoc") and "github.com/NetAppDocs/" in src:
        return f"https://docs.netapp.com/us-en/{product}/{rel_in_product[:-5]}.html"
    if src == "https://github.com/dell/csm-docs" and rel_in_product.startswith("content/"):
        # Hugo site dell.github.io/csm-docs: content/docs/a/b.md -> /docs/a/b/, content/v3/... -> /v3/...
        page = rel_in_product[len("content/"):-3]
        page = page[:-len("_index")] if page.endswith("_index") else page + "/"
        return f"https://dell.github.io/csm-docs/{page}"
    if src.startswith("https://github.com/"):
        return f"{src}/blob/HEAD/{rel_in_product}"
    if vendor == "netapp" and rel_in_product.endswith(".adoc"):
        return f"https://docs.netapp.com/us-en/{product}/{rel_in_product[:-5]}.html"
    return None


def iter_files(root):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("_include", "node_modules")]
        for f in files:
            if f.startswith(("_", ".")) or f == "manifest.json":
                continue
            p = os.path.join(dirpath, f)
            if f.lower().endswith(TEXT_EXT + CODE_EXT + (".pdf", ".html", ".htm")) and os.path.isfile(p):
                yield p                                  # isfile: a dangling symlink (sparse checkout) is skipped


def parse_code(text, path):
    """Source file -> one section per top-level func / type / class (heading = its first line), so a
    search for an error string lands on the function that raises it. Title: <dir>/<file>."""
    title = "/".join(path.replace(os.sep, "/").split("/")[-2:])
    sections, head, cur = [], title, []
    for line in text.splitlines():
        if CODE_START.match(line) and cur:
            sections.append((head, "\n".join(cur)))
            head, cur = line.strip().rstrip("{").strip()[:160], []
        elif CODE_START.match(line):
            head = line.strip().rstrip("{").strip()[:160]
        cur.append(line)
    if cur:
        sections.append((head, "\n".join(cur)))
    return title, _split(sections, title)


def parse_file(path):
    fallback = os.path.splitext(os.path.basename(path))[0].replace("-", " ").replace("_", " ")
    low = path.lower()
    if low.endswith(".pdf"):
        return parse_pdf(path, fallback)
    text = open(path, encoding="utf-8", errors="replace").read()
    if low.endswith(".adoc"):
        return parse_adoc(text, fallback)
    if low.endswith((".html", ".htm")):
        return parse_html(text, fallback)
    if low.endswith((".md", ".rst")):
        return parse_md(text, fallback)
    if low.endswith(CODE_EXT):
        return parse_code(text, path)
    return fallback, _split([(fallback, text)], fallback)


# ---------------------------------------------------------------------------
# Index build
# ---------------------------------------------------------------------------

def build(docs_root, db_path, full=False, log=print):
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    tmp = db_path + ".building"
    if os.path.exists(tmp):
        os.remove(tmp)
    if os.path.exists(db_path) and not full:
        shutil.copyfile(db_path, tmp)
    con = sqlite3.connect(tmp)
    con.executescript(SCHEMA)
    known = {p: (i, m, s) for i, p, m, s in con.execute("SELECT id, path, mtime, size FROM docs")}
    manifests = load_manifests(docs_root)
    load_source_urls(docs_root)
    seen, added, updated, errors = set(), 0, 0, 0
    t0 = time.time()
    for path in iter_files(docs_root):
        rel = os.path.relpath(path, docs_root)
        parts = rel.split(os.sep)
        vendor = parts[0].lower()
        product = parts[1] if len(parts) > 2 else parts[0]
        st = os.stat(path)
        seen.add(rel)
        old = known.get(rel)
        if old and old[1] == st.st_mtime and old[2] == st.st_size:
            continue
        try:
            title, chunks = parse_file(path)
        except SkipDocument:
            seen.discard(rel)
            continue
        except Exception as e:
            errors += 1
            log(f"skip {rel}: {e.__class__.__name__}: {e}")
            continue
        rel_in_product = "/".join(parts[2:]) if len(parts) > 2 else parts[-1]
        meta = manifests.get(os.path.normpath(path))
        if meta and meta.get("title") and _real_title(meta["title"]):
            title = meta["title"]
        if not _real_title(title):
            title = os.path.splitext(os.path.basename(path))[0].replace("-", " ").replace("_", " ")
        url = url_for(vendor, product, rel_in_product, meta)
        if old:
            _delete_doc(con, old[0])
            updated += 1
        else:
            added += 1
        doc_id = _insert_doc(con, rel, vendor, product, title, url, st, chunks)
        if (added + updated) % 2000 == 0:
            con.commit()
            log(f"... {added + updated} documents parsed ({time.time() - t0:.0f}s)")
    removed = 0
    for rel, (doc_id, _, _) in known.items():
        if rel not in seen:
            _delete_doc(con, doc_id)
            removed += 1
    deduped = _dedupe(con, docs_root, log)
    con.execute("INSERT OR REPLACE INTO meta VALUES ('indexed_at', ?)", (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),))
    if os.getenv("BUNDLE_LABEL"):
        con.execute("INSERT OR REPLACE INTO meta VALUES ('bundle', ?)", (os.getenv("BUNDLE_LABEL"),))
    con.commit()
    if added or updated or removed or deduped:
        con.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('optimize')")
        con.commit()
        con.execute("VACUUM")                 # give freed pages back: smaller file to ship
    con.close()
    os.replace(tmp, db_path)
    docs, chunks = sqlite3.connect(db_path).execute(
        "SELECT (SELECT count(*) FROM docs), (SELECT count(*) FROM chunks)").fetchone()
    log(f"index {db_path}: {docs} documents ({deduped} identical copies folded), {chunks} chunks (+{added} new, "
        f"{updated} updated, -{removed} removed, {errors} errors) in {time.time() - t0:.0f}s")
    return {"documents": docs, "chunks": chunks, "added": added, "updated": updated,
            "removed": removed, "errors": errors, "deduped": deduped}


GENERIC_TITLES = {"pdf", "download", "view", "link", "here", "click here", "document", "english", "en-us", "untitled"}


def _real_title(t):
    t = (t or "").strip()
    return len(t) >= 4 and t.lower() not in GENERIC_TITLES


def _text_hash(chunks):
    m = hashlib.sha1()
    for heading, text in chunks:
        m.update((heading or "").encode()); m.update(b"\x1f"); m.update((text or "").encode()); m.update(b"\x1e")
    return m.hexdigest()


def _context_title(rel, vendor, product, title):
    """What the FTS title column holds: the title plus where the document sits (vendor, product, folders,
    file name), so a page titled just "Troubleshooting" in csm/.../replication/ matches "csm replication
    troubleshooting" and a PDF titled "pdf" matches its file name. Display still uses docs.title."""
    seen = set(re.findall(r"\w+", title.lower()))
    words = []
    for w in re.findall(r"[A-Za-z0-9]+", os.path.splitext(rel)[0]):
        lw = w.lower()
        if lw in seen or (len(w) == 8 and re.fullmatch(r"[0-9a-f]+", lw)) or lw in ("content", "docs", "md", "html"):
            continue
        seen.add(lw)
        words.append(w)
    return f"{title} | {' '.join(words)}" if words else title


def _insert_doc(con, rel, vendor, product, title, url, st, chunks):
    cur = con.execute("INSERT INTO docs(path, vendor, product, title, url, mtime, size, chunks, hash) "
                      "VALUES (?,?,?,?,?,?,?,?,?)", (rel, vendor, product, title, url, st.st_mtime,
                                                      st.st_size, len(chunks), _text_hash(chunks)))
    doc_id = cur.lastrowid
    ctx_title = _context_title(rel, vendor, product, title)
    for seq, (heading, text) in enumerate(chunks):
        cid = con.execute("INSERT INTO chunks(doc_id, seq) VALUES (?,?)", (doc_id, seq)).lastrowid
        con.execute("INSERT INTO chunks_fts(rowid, title, heading, text) VALUES (?,?,?,?)",
                    (cid, ctx_title, heading, text))
    return doc_id


def _canonical_rank(product, path):
    """Which copy of identical text to keep: the unversioned product (ontap-ems, trident, content/docs)
    first, then the newest version (highest number), then the shortest path."""
    m = re.search(r"(\d+)$", product)
    versioned = 1 if m else 0
    ver = -int(m.group(1)) if m else 0
    cur = 0 if "/content/docs/" in path or "/content/docs" in path else (1 if re.search(r"/content/v\d+/", path) else 0)
    return (versioned, ver, cur, len(path))


def _dedupe(con, docs_root, log):
    """Documents with identical text keep ONE copy of their chunks (the canonical one); the others become
    aliases (dup_of -> canonical, chunks = 0) so a search shows the page once, filtering by any of the
    products still finds it, and read_document on an alias path reads the canonical copy."""
    # aliases whose canonical disappeared or changed hash: re-parse them
    orphans = con.execute("SELECT a.id, a.path FROM docs a LEFT JOIN docs c ON c.id = a.dup_of "
                          "WHERE a.dup_of IS NOT NULL AND (c.id IS NULL OR c.hash != a.hash OR c.dup_of IS NOT NULL)").fetchall()
    for doc_id, rel in orphans:
        path = os.path.join(docs_root, rel)
        row = con.execute("SELECT vendor, product, url FROM docs WHERE id = ?", (doc_id,)).fetchone()
        _delete_doc(con, doc_id)
        if os.path.exists(path):
            try:
                title, chunks = parse_file(path)
            except Exception:
                continue
            _insert_doc(con, rel, row[0], row[1], title, row[2], os.stat(path), chunks)
    folded = 0
    groups = con.execute("SELECT hash FROM docs WHERE hash IS NOT NULL GROUP BY hash HAVING count(*) > 1").fetchall()
    for (h,) in groups:
        rows = con.execute("SELECT id, product, path, dup_of, chunks FROM docs WHERE hash = ?", (h,)).fetchall()
        rows.sort(key=lambda r: _canonical_rank(r[1], r[2]))
        canon = rows[0]
        if canon[3] is not None:                      # canonical must own chunks: promote it
            con.execute("UPDATE docs SET dup_of = NULL WHERE id = ?", (canon[0],))
            if canon[4] == 0:                         # has no chunks: take them from a sibling that has
                donor = next((r for r in rows[1:] if r[3] is None and r[4] > 0), None)
                if donor:
                    con.execute("UPDATE chunks SET doc_id = ? WHERE doc_id = ?", (canon[0], donor[0]))
                    con.execute("UPDATE docs SET chunks = ? WHERE id = ?", (donor[4], canon[0]))
                    con.execute("UPDATE docs SET chunks = 0, dup_of = ? WHERE id = ?", (canon[0], donor[0]))
        for r in rows[1:]:
            if r[0] == canon[0]:
                continue
            if r[3] != canon[0]:
                if r[4] > 0 and r[3] is None:
                    con.execute("DELETE FROM chunks_fts WHERE rowid IN (SELECT id FROM chunks WHERE doc_id=?)", (r[0],))
                    con.execute("DELETE FROM chunks WHERE doc_id=?", (r[0],))
                con.execute("UPDATE docs SET dup_of = ?, chunks = 0 WHERE id = ?", (canon[0], r[0]))
            folded += 1
    con.commit()
    return folded


def _delete_doc(con, doc_id):
    con.execute("DELETE FROM chunks_fts WHERE rowid IN (SELECT id FROM chunks WHERE doc_id=?)", (doc_id,))
    con.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
    con.execute("DELETE FROM docs WHERE id=?", (doc_id,))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=os.getenv("DOCS_DIR", "/data/docs"))
    ap.add_argument("--db", default=os.getenv("INDEX_DB", "/data/index/docs.db"))
    ap.add_argument("--full", action="store_true", help="rebuild from scratch")
    a = ap.parse_args()
    if not os.path.isdir(a.docs):
        sys.exit(f"docs directory {a.docs} not found")
    build(a.docs, a.db, a.full)
