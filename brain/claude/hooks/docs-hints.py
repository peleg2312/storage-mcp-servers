#!/usr/bin/env python3
"""Claude Code PostToolUse hook (matcher mcp__.*): when a live MCP result names an event, alert or bug the
offline library documents (ONTAP EMS names, PowerMax SYMAPI_AEVENT2_* alerts, PowerFlex SIO dial-home codes,
CONTAP bugs, Dell DSA advisories), add its meaning next to the result, so Claude explains it from the docs
instead of guessing, without a search round trip.

Only identifiers the library really documents are reported (an EMS name must equal a documented event), at
most MAX_HINTS per result, each once per session; nothing is printed otherwise. Standard library only;
never fails the tool call (always exit 0). Library: ~/.claude/brain/library/docs.db (DOCS_HINTS_DB overrides).
"""
import json
import os
import re
import sqlite3
import sys
import tempfile
import zlib

MAX_HINTS = 4
MAX_ERR_HINTS = 2      # free-text error messages (CSI / Kubernetes / driver logs) looked up by their fixed words
ERR = re.compile(r"(?:desc = |\b(?:error|Error|ERROR|failed|Failed|FAILED)(?: to [a-z]+)?: )([^\n\"]{12,240})")
MAX_CANDIDATES = 60
DB = os.environ.get("DOCS_HINTS_DB") or os.path.expanduser("~/.claude/brain/library/docs.db")

EMS = re.compile(r"(?<![\w.\-/@:])([a-z][a-z0-9_]{1,30}(?:\.[A-Za-z][A-Za-z0-9_]{0,40}){1,5})(?![\w\-/@]|\.\w)")
CODES = [re.compile(p) for p in (r"\bSYMAPI_AEVENT2_UID_[A-Z0-9_]{4,}\b", r"\bSIO\d{2}\.\d{2}\.\d{7}\b",
                                  r"\bCONTAP-\d{5,7}\b", r"\bDSA-\d{4}-\d{2,4}\b")]


def strings(x, out):
    if isinstance(x, str):
        out.append(x)
    elif isinstance(x, dict):
        for v in x.values():
            strings(v, out)
    elif isinstance(x, list):
        for v in x:
            strings(v, out)
    return out


def words(ident):
    return " ".join(re.findall(r"[A-Za-z0-9]+", ident))


def ems_names(c):
    """Every documented EMS event name (lowercase), cached per library build: checking a dotted name in a big
    result is then a set lookup, not a query."""
    key = f"{zlib.crc32(DB.encode())}-{int(os.path.getmtime(DB))}"          # this library build
    cache = os.path.join(tempfile.gettempdir(), f"claude-docs-hints-ems-{key}.json")
    try:
        return set(json.load(open(cache)))
    except (OSError, ValueError):
        pass
    names = {r[0].strip().lower() for r in c.execute(
        "SELECT DISTINCT f.heading FROM docs d JOIN chunks ch ON ch.doc_id = d.id JOIN chunks_fts f ON f.rowid = ch.id "
        "WHERE d.product LIKE 'ontap-ems%'") if r[0] and "." in r[0] and " " not in r[0].strip()}
    try:
        with open(cache, "w") as f:
            json.dump(sorted(names), f)
    except OSError:
        pass
    return names


def ems_hint(c, name):
    """The documented EMS event whose section heading is exactly this name (newest EMS reference first)."""
    try:
        rows = c.execute("SELECT f.rowid, f.heading, f.text, d.product FROM chunks_fts f JOIN chunks ch ON ch.id = f.rowid "
                         "JOIN docs d ON d.id = ch.doc_id WHERE chunks_fts MATCH ? LIMIT 40",
                         ('heading : "' + words(name) + '"',)).fetchall()
    except sqlite3.OperationalError:
        return None
    rows = [r for r in rows if (r[1] or "").strip().lower() == name.lower()]
    if not rows:
        return None
    rows.sort(key=lambda r: (r[3] == "ontap-ems", r[3]), reverse=True)   # general reference, else newest version
    rowid, heading, text, product = rows[0]
    t = re.sub(r"\s+", " ", text)
    sev = re.search(r"\*Severity\*::\s*(\w+)", t)
    desc = re.search(r"\*Description\*::\s*(.*?)(?=\*\w[\w ]*\*::|$)", t)
    fix = re.search(r"\*Corrective Action\*::\s*(.*?)(?=\*\w[\w ]*\*::|$)", t)
    s = f"{heading} [{product}, chunk {rowid}]: {sev.group(1) + '. ' if sev else ''}"
    s += (desc.group(1).strip()[:220] if desc else t[:220])
    if fix and fix.group(1).strip() not in ("(None).", "(None)", ""):
        s += " Corrective action: " + fix.group(1).strip()[:200]
    return s


def code_hint(c, code):
    """Best section quoting this alert / dial-home code / bug / advisory: title or heading first."""
    try:
        rows = c.execute("SELECT f.rowid, d.vendor, d.product, d.title, f.heading, f.text, "
                         "bm25(chunks_fts, 6.0, 3.0, 1.0) FROM chunks_fts f JOIN chunks ch ON ch.id = f.rowid "
                         "JOIN docs d ON d.id = ch.doc_id WHERE chunks_fts MATCH ? ORDER BY 7 LIMIT 5",
                         ('"' + words(code) + '"',)).fetchall()
    except sqlite3.OperationalError:
        return None
    if not rows:
        return None
    rowid, vendor, product, title, heading, text, _ = rows[0]
    title = re.sub(r"\s*\|\s*Dell.*$", "", title or "")
    if code in title:      # an article about this code (KB, CONTAP): its title says it; point at its first content section
        first = c.execute("SELECT ch.id FROM chunks ch JOIN chunks_fts f ON f.rowid = ch.id WHERE ch.doc_id = "
                          "(SELECT doc_id FROM chunks WHERE id = ?) AND f.heading IN ('Summary', 'Symptoms', 'Symptom', "
                          "'Issue', 'Description', 'Cause') ORDER BY ch.seq LIMIT 1", (rowid,)).fetchone()
        return f"{code} [{vendor}/{product}, chunk {first[0] if first else rowid}]: {title[:150]}"
    t = re.sub(r"\s+", " ", text)
    i = t.find(code)
    near = t[i + len(code):i + len(code) + 180].strip() if i >= 0 else t[:180]
    return f"{code} [{vendor}/{product}, chunk {rowid}]: {title[:110]}" + (f" :: {near}" if near else "")


def err_phrase(msg):
    """Longest run of 4-10 fixed words in an error message (ids, names, numbers and paths dropped)."""
    best, cur = [], []
    for w in re.findall(r"[^\s,;:()\[\]{}'\"]+", msg):
        if re.fullmatch(r"[A-Za-z]+", w):                   # words; ids, numbers, paths and names with digits break the run
            cur.append(w)
            if len(cur) > len(best):
                best = cur[:]
        else:
            cur = []
    return " ".join(best[:10]) if len(best) >= 4 else None


def err_hint(c, phrase):
    """Where the library has this message: source code (the function raising it) or a doc / KB. Messages end
    in a variable (Go "...due to %s"), so the phrase is shortened word by word until it is found (4 words min)."""
    words, rows = phrase.split(), []
    while len(words) >= 4 and not rows:
        try:
            rows = c.execute("SELECT f.rowid, d.vendor, d.product, d.title, f.heading, d.path, bm25(chunks_fts, 6.0, 3.0, 1.0) "
                             "FROM chunks_fts f JOIN chunks ch ON ch.id = f.rowid JOIN docs d ON d.id = ch.doc_id "
                             "WHERE chunks_fts MATCH ? ORDER BY 7 LIMIT 6", ('"' + " ".join(words) + '"',)).fetchall()
        except sqlite3.OperationalError:
            return None
        if not rows:
            words = words[:-1]
    if not rows:
        return None
    phrase = " ".join(words)
    rows.sort(key=lambda r: r[5].endswith((".go", ".py", ".yaml", ".yml")))      # an explanation before the code
    rowid, vendor, product, title, heading, path, _ = rows[0]
    where = f"{title}" + (f" :: {heading[:90]}" if heading and heading != title else "")
    more = f" (+{len(rows) - 1} more places)" if len(rows) > 1 else ""
    return f'"{phrase}" [{vendor}/{product}, chunk {rowid}]: {re.sub(r"\s*\|\s*Dell.*$", "", where)[:160]}{more}'


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    if not tool.startswith("mcp__") or "docs" in tool.split("__")[1].lower() or not os.path.exists(DB):
        return 0
    text = "\n".join(strings(data.get("tool_response"), []))[:300_000]
    seen_file = os.path.join(tempfile.gettempdir(), f"claude-docs-hints-{re.sub(r'[^A-Za-z0-9-]', '', str(data.get('session_id', 'x')))}")
    try:
        seen = set(open(seen_file).read().split())
    except OSError:
        seen = set()
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    known = ems_names(c)
    found = [(m.start(), m.group(0)) for rx in CODES for m in rx.finditer(text)]
    found += [(m.start(1), m.group(1)) for m in EMS.finditer(text) if m.group(1).lower() in known]
    cands = [x for _, x in sorted(found)]                      # in the order the result shows them
    cands = [x for x in dict.fromkeys(cands) if x not in seen][:MAX_CANDIDATES]
    if not cands and not ERR.search(text):
        return 0
    hints, more = [], []
    for x in cands:
        h = code_hint(c, x) if any(rx.fullmatch(x) for rx in CODES) else ems_hint(c, x)
        if not h:
            continue
        seen.add(x)
        if len(hints) < MAX_HINTS:
            hints.append(h)
        else:
            more.append(x)                                     # named only: search_docs gives the detail
    if more:
        hints.append("also documented: " + ", ".join(more[:12]))
    errs = 0
    for m in ERR.finditer(text):
        phrase = err_phrase(m.group(1))
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)
        h = err_hint(c, phrase)
        if h:
            hints.append(h)
            errs += 1
        if errs >= MAX_ERR_HINTS:
            break
    if not hints:
        return 0
    try:
        with open(seen_file, "w") as f:
            f.write("\n".join(sorted(seen)))
    except OSError:
        pass
    ctx = ("Offline docs library on identifiers in this result (read_chunk <chunk> for the full text; check the "
           "version-specific reference for the installed release):\n" + "\n".join("- " + h for h in hints))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ctx}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
