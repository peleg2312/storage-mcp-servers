#!/usr/bin/env python3
"""MCP server (stdio) "deck": designed PowerPoint decks for Claude. The model sends a JSON outline, deck.py (next to this
file) does the design; the reply lists what to fix (WARN) or the finished file. Shipped by the "presentations" plugin
(brain/plugins/presentations: this server, the make-deck skill, the deck-designer agent, /presentations:deck).

Tools: deck_guide (the rules, slide types and an example), deck_build (outline -> .pptx under ~/storage-reports/),
deck_read (the text, tables and charts of any .pptx: a deck to restyle, or a check of the result), deck_icons,
deck_deliver (queue the file for the PC download, as report.py --send). Writes only under ~/storage-reports/; reads only
the files it is given. Standard library (Python 3.9); deck.py runs in the devtools venv that has python-pptx."""
import datetime as dt
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.join(HERE, "deck.py")
REPORTS = os.path.expanduser("~/storage-reports")

INSTRUCTIONS = (
    "Designed PowerPoint decks. Workflow: deck_guide once (rules, slide types, example), then deck_build with the outline; "
    "fix every warning in the outline and call deck_build again until warnings is empty; then deck_deliver. One message "
    "per slide, the title states the conclusion, facts only from tool results or documents. Never draw slides yourself.")

RULES = """Design rules (deck.py does layout, colours, fonts, fitting):
- 8-15 slides: title, agenda (optional), a section per part, evidence, closing (the ask / next steps).
- One message per slide; the TITLE SAYS THE CONCLUSION ("Prod-A grew fastest: 40 TB a month"), not the topic. **bold** the key number.
- 3-6 bullets of one line; card / step / milestone / list texts are one sentence. Vary the types: never three bullet slides in a row.
- Numbers come from tool results or saved data, never invented; a chart: one measure, <= 5 series, unit set; highlight the bar that matters;
  target for a limit line (80% capacity, an SLA).
- style: "bold" for management, kick-offs, proposals; "clean" for ops reviews, technical walkthroughs, handovers; incident: clean + theme graphite.
- Leave colours to the look (each deck its own design), or accent "#RRGGBB" (a brand colour), or theme; template = the company deck (wins).
- Icons: one per card / stat / list item / milestone, matching its meaning (deck_icons).
Slide types and fields:
title {title, subtitle, meta, icon} | agenda {items <=7} | section {title, subtitle, icon} | hero {value, text, sub, icon}
stats {title, stats:[{value, label, delta, good, progress, icon}] 2-4, note} | chart {title, chart:{kind column|bar|stacked|stacked_bar|
line|area|pie|doughnut, categories, series:[{name, values}], unit, highlight, target, target_label, source, min, max}, takeaway, icon}
bullets {title, bullets:[text | {text, sub:[..]}], takeaway, icon} | cards {title, cards:[{title, text, icon, value}] 2-6}
iconlist {title, items:[{icon, title, text}] 2-6} | compare {title, left:{title, bullets}, right:{title, bullets}, verdict}
table {title, columns, rows <=12, highlight (row index), heat [column names], total, zebra, note} | timeline {title, items:[{date, title,
text, done, icon}] 3-6} | process {title, steps:[{title, text}] 3-5} | quote {quote, by} | image {title, image (path), caption} |
closing {title, subtitle, bullets, contact}. Any slide: notes (speaker notes). Deck: title, footer, style, look, theme, accent, template."""

TOOLS = [
    {"name": "deck_guide", "description": "The design rules, every slide type with its fields, the icon names and a complete example "
     "outline. Call once before the first deck_build.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "deck_build", "description": "Build a designed, editable .pptx from an outline (deck_guide shows the format). Returns the "
     "file path, the look number (to repeat a design), the slide list and warnings: text that does not fit, too many bullets, long "
     "titles, crowded charts. Fix every warning in the outline and build again until warnings is empty.",
     "inputSchema": {"type": "object", "required": ["spec"], "properties": {
         "spec": {"type": "object", "description": "the outline: {title, footer, style, slides: [{type, ...}]}"},
         "folder": {"type": "string", "description": "a folder name under ~/storage-reports (default: <date>-<title>)"},
         "template": {"type": "string", "description": "path of the company .pptx / .potx (its master, colours, fonts, layouts)"},
         "style": {"type": "string", "enum": ["clean", "bold"]},
         "look": {"type": ["integer", "string"], "description": "a look number to repeat a design, or 'random'"},
         "preview": {"type": "boolean", "description": "also render PNGs and a contact sheet (needs LibreOffice)"}}}},
    {"name": "deck_read", "description": "The text, tables, chart data and notes of every slide of a .pptx: a deck the user gave you "
     "(to restyle or summarise) or the one just built (a check that reads it back).",
     "inputSchema": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}},
    {"name": "deck_icons", "description": "The icon names (and aliases) for cards, stats, lists, timelines, hero and section slides.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "deck_deliver", "description": "Queue a finished deck for the user's PC (the Reports tab / get-reports.ps1) and get the "
     "line to copy it by hand. Call it once the deck has no warnings.",
     "inputSchema": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}},
]


def run(args, timeout=300):
    r = subprocess.run([sys.executable, DECK] + args, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, (r.stderr or "").strip()


def slug(s):
    return re.sub(r"[^\w-]+", "-", re.sub(r"\*\*(.+?)\*\*", r"\1", str(s)).lower()).strip("-")[:60] or "deck"


def inside_reports(path):
    p = os.path.realpath(os.path.expanduser(path))
    return p.startswith(os.path.realpath(REPORTS) + os.sep)


def call(name, a):
    if name == "deck_guide":
        rc, ex, err = run(["--example"])
        rc2, ic, _ = run(["--icons"])
        if rc:
            return {"error": err or "deck.py --example failed"}
        return {"rules": RULES, "icons": ic.strip(), "example": json.loads(ex)}
    if name == "deck_icons":
        rc, ic, err = run(["--icons"])
        return {"icons": ic.strip()} if rc == 0 else {"error": err}
    if name == "deck_build":
        spec = a.get("spec")
        if isinstance(spec, str):                      # a model that sends the outline as text
            try:
                spec = json.loads(spec)
            except ValueError as e:
                return {"error": f"spec is not JSON: {e}"}
        if not isinstance(spec, dict) or not isinstance(spec.get("slides"), list) or not spec["slides"]:
            return {"error": 'spec needs "slides": [ ... ] (deck_guide shows the format)'}
        folder = a.get("folder") or f"{dt.date.today()}-{slug(spec.get('title') or spec['slides'][0].get('title', 'deck'))}"
        folder = re.sub(r"[^\w.-]+", "-", folder).strip(".-") or "deck"
        out = os.path.join(REPORTS, folder)
        os.makedirs(out, exist_ok=True)
        sp = os.path.join(out, "deck.json")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=1, ensure_ascii=False)
        args = [sp, "--out", out, "--json"]
        for k in ("template", "style"):
            if a.get(k):
                args += ["--" + k, str(a[k])]
        if a.get("look") not in (None, ""):
            args += ["--look", str(a["look"])]
        if a.get("preview"):
            args.append("--preview")
        rc, so, err = run(args)
        if rc:
            return {"error": (err or so).strip()[-1500:], "outline_file": sp,
                    "next": "fix the outline as the error says and call deck_build again"}
        res = json.loads(so.strip().splitlines()[-1])
        res["outline_file"] = sp
        res["next"] = ("fix each warning in the outline (shorten or split) and call deck_build again" if res["warnings"]
                       else "done: deck_deliver the path, then answer with the path, the slide list and what the user should check")
        return res
    if name == "deck_read":
        p = os.path.expanduser(str(a.get("path", "")))
        if not p.lower().endswith((".pptx", ".potx")) or not os.path.isfile(p):
            return {"error": f"no .pptx at {p}"}
        rc, so, err = run(["--outline", p])
        return json.loads(so) if rc == 0 else {"error": err}
    if name == "deck_deliver":
        p = os.path.expanduser(str(a.get("path", "")))
        if not os.path.isfile(p) or not inside_reports(p):
            return {"error": f"{p}: only a file under {REPORTS} is delivered"}
        r = subprocess.run([sys.executable, os.path.join(HERE, "report.py"), "--send", p], capture_output=True, text=True, timeout=60)
        return {"delivered": r.returncode == 0, "message": (r.stdout + r.stderr).strip()[-800:], "path": p}
    return {"error": f"unknown tool {name}"}


def main():
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        mid, method = msg.get("id"), msg.get("method")
        if method == "initialize":
            res = {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2024-11-05"),
                   "capabilities": {"tools": {}}, "serverInfo": {"name": "deck", "version": "1.0"}, "instructions": INSTRUCTIONS}
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            p = msg.get("params", {})
            try:
                out = call(p.get("name"), p.get("arguments") or {})
            except Exception as e:                     # a reply, never a dead server
                out = {"error": f"{type(e).__name__}: {e}"}
            res = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=1)}], "isError": "error" in out}
        elif method == "ping":
            res = {}
        elif method in ("prompts/list", "resources/list"):
            res = {method.split("/")[0]: []}
        else:
            if mid is None:
                continue                               # a notification
            print(json.dumps({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"no method {method}"}}), flush=True)
            continue
        if mid is not None:
            print(json.dumps({"jsonrpc": "2.0", "id": mid, "result": res}), flush=True)


if __name__ == "__main__":
    main()
