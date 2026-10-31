#!/usr/bin/env python3
"""Claude Code PostToolUse hook (matcher mcp__.*): when a live MCP result names an event, alert or bug the
offline library documents (ONTAP EMS names, PowerMax SYMAPI_AEVENT2_* alerts, PowerFlex SIO dial-home codes,
CONTAP bugs, Dell DSA advisories), add its meaning next to the result, so Claude explains it from the docs
instead of guessing, without a search round trip.

Only identifiers the library really documents are reported (an EMS name must equal a documented event), at
most MAX_HINTS per result, each once per session; nothing is printed otherwise. Standard library only;
never fails the tool call (always exit 0). Library: ~/.claude/brain/library/docs.db (DOCS_HINTS_DB overrides).
"""
import glob
import json
import os
import re
import sqlite3
import stat
import sys
import tempfile
import zlib

MAX_HINTS = 3
MAX_ERR_HINTS = 2      # free-text error messages (CSI / Kubernetes / driver logs) looked up by their fixed words
ERR = re.compile(r"(?:desc = |\b(?:error|Error|ERROR|failed|Failed|FAILED)(?: to [a-z]+)?: )([^\n\"]{12,240})")
MAX_CANDIDATES = 60
DB = os.environ.get("DOCS_HINTS_DB") or os.path.expanduser("~/.claude/brain/library/docs.db")

try:   # the shared lookups live in the library's search engine (search.py next to docs.db; search_cli.py in the repo)
    sys.path[:0] = [os.path.dirname(os.path.abspath(DB)), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "docs-search-mcp")]
    try:
        import search as lib
    except ImportError:
        import search_cli as lib
except ImportError:
    lib = None

EMS = re.compile(r"(?<![\w.\-/@:])([a-z][a-z0-9_]{1,30}(?:\.[A-Za-z][A-Za-z0-9_]{0,40}){1,5})(?![\w\-/@]|\.\w)")
CODES = list(lib.CODE_RX.values()) if lib else []


def tmpdir():
    """Private per-user dir for the session and cache files (a shared /tmp name can be a planted symlink); an
    unusable dir comes back as a path that does not exist, so every open() below just fails with OSError."""
    d = os.path.join(tempfile.gettempdir(), f"claude-brain-{os.getuid()}")
    try:
        os.makedirs(d, mode=0o700, exist_ok=True)
        st = os.lstat(d)
        if st.st_uid == os.getuid() and stat.S_ISDIR(st.st_mode):
            return d
    except OSError:
        pass
    return os.path.join(os.devnull, "x")


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


def ems_names(c):
    """Every documented EMS event name (lowercase), cached per library build: checking a dotted name in a big
    result is then a set lookup, not a query."""
    key = f"{zlib.crc32(DB.encode())}-{int(os.path.getmtime(DB))}"          # this library build
    cache = os.path.join(tmpdir(), f"claude-docs-hints-ems-{key}.json")
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
        for old in glob.glob(os.path.join(os.path.dirname(cache), "claude-docs-hints-ems-*.json")):   # older library builds
            if old != cache:
                os.remove(old)
    except OSError:
        pass
    return names


def ems_hint(c, name):
    """The documented EMS event whose section heading is exactly this name (newest EMS reference first)."""
    e = lib.ems_lookup(c, name)
    if not e:
        return None
    sev, fix = e["severity"], e["corrective_action"]
    s = f"{e['heading']} [{e['product']}, chunk {e['chunk_id']}]: {sev + '. ' if sev else ''}"
    d = re.sub(r"^This message occurs when\s+", "", e["description"] or e["text"])
    s += first_sentence(d[:1].upper() + d[1:], 160)
    if fix:
        s += " Fix: " + first_sentence(fix, 140)
    return s


def first_sentence(text, limit):
    """Its first sentence when that is short enough and says something, else cut at a word boundary (read_chunk has
    the rest): the meaning in fewer tokens, not a mid-word cut."""
    m = re.match(r"(.{40,}?[.!?])(\s|$)", text)
    if m and len(m.group(1)) <= limit:
        return m.group(1)
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def code_hint(c, code):
    """Best section quoting this alert / dial-home code / bug / advisory: title or heading first."""
    h = lib.code_lookup(c, code)
    if not h:
        return None
    title = re.sub(r"\s*\|\s*Dell.*$", "", h["title"] or "")
    where = f"{code} [{h['vendor']}/{h['product']}, chunk "
    if h["first_id"]:      # an article about this code (KB, CONTAP): its title says it; point at its first content section
        return f"{where}{h['first_id']}]: {title[:150]}"
    t = re.sub(r"\s+", " ", h["text"])
    i = t.find(code)
    near = t[i + len(code):i + len(code) + 120].strip() if i >= 0 else t[:120]
    return f"{where}{h['chunk_id']}]: {title[:110]}" + (f" :: {near}" if near else "")


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
    where = re.sub(r"\s*\|\s*Dell.*$", "", where)[:160]       # outside the f-string: Python < 3.12 (RHEL 9: 3.9)
    return f'"{phrase}" [{vendor}/{product}, chunk {rowid}]: {where}{more}'


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    if not tool.startswith("mcp__") or "docs" in tool.split("__")[1].lower() or not os.path.exists(DB) or lib is None:
        return 0
    text = "\n".join(strings(data.get("tool_response"), []))[:300_000]
    seen_file = os.path.join(tmpdir(), f"claude-docs-hints-{re.sub(r'[^A-Za-z0-9-]', '', str(data.get('session_id', 'x')))}")
    try:
        seen = set(filter(None, open(seen_file).read().splitlines()))   # one entry per line: error phrases have spaces
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
        hints.append("also documented: " + ", ".join(more[:5]))
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
    ctx = ("Docs on identifiers in this result (read_chunk <chunk> for the full text; versions differ):\n"
           + "\n".join("- " + h for h in hints))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ctx}}))
    return 0


if __name__ == "__main__":
    # a team plugin's copy on a VM whose managed settings run this hook for every account steps aside: the enforced copy
    # under /opt/paas/hooks answers. The enforced copy itself never steps aside, whatever the environment says.
    if len(sys.argv) == 1 and os.environ.get("CLAUDE_PLUGIN_ROOT") and not os.path.realpath(__file__).startswith("/opt/paas/hooks/"):
        try:
            if os.path.basename(__file__) in open(os.environ.get("PAAS_MANAGED_SETTINGS") or "/etc/claude-code/managed-settings.json").read():
                sys.exit(0)
        except OSError:
            pass
    try:   # switched off by this person in the web UI (Brain tab, MCP & hooks)
        if "docs-hints" in open(os.path.expanduser("~/.claude/brain/hooks-off")).read().split():
            sys.exit(0)
    except OSError:
        pass
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
