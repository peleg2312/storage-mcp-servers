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
    "Designed PowerPoint decks. You write the CONTENT as a JSON outline, the tools do ALL the design (layout, colours, fonts, "
    "right-to-left for Hebrew). Steps: 1) deck_guide once (lang 'he' for a Hebrew deck): it returns the rules and an example "
    "outline - copy the example and change its content. 2) deck_build with the outline. 3) 'fixed' in the reply = already done "
    "for you, nothing to do; each 'warnings' line = change that slide in the outline and call deck_build again (at most 3 "
    "rounds). 4) deck_deliver the path. Facts only from tool results or documents; never draw slides yourself.")

RULES = """HOW TO WRITE THE OUTLINE (follow every line)
1. Start from the example deck_guide gives. Keep its JSON shape exactly: {"title", "footer", "slides": [{"type": ..., ...}]}.
2. 8-12 slides: title, agenda, then the evidence (a section slide before each new part), closing last.
3. Every slide title says the conclusion in one short line (max 60 characters): "env2 has most failures: 23 of 41",
   not "Failures". Put the key number in **bold**.
4. Short texts. Max: bullet 90 characters, card or step text 80, item title 30, stat label 30, stat value 12 ("97.8%", "312 TB").
5. Counts per slide: bullets 3-5, cards 3-4 (max 6), stats 2-4, iconlist items 3-5, timeline items 3-5, process steps 3-5,
   agenda items 3-6, table rows max 10 and columns max 6. More items: make two slides.
6. Never two bullets slides in a row: use stats for numbers, chart for comparisons or trends, cards for options, iconlist
   for checks, timeline for plans, process for procedures, table for lists of systems, compare for A vs B.
7. Every card, stat, iconlist item and timeline item gets an "icon" from the icon list (pick the closest meaning).
8. Numbers come from tool results only. Chart "values" are plain numbers: [9, 23, 5], never "23 jobs".
9. Hebrew deck: write all text in Hebrew; keep product names, IDs and commands in English exactly as they are (Commvault,
   MA-SITEB-03, oc get backups). Do NOT set direction, fonts or alignment: the deck turns right-to-left by itself.
10. Do NOT add: emoji, bullet signs ("•", "-") or numbers at the start of a line, HTML, Markdown other than **bold**,
    colours, font names, positions or sizes.
11. "style": "bold" for managers and proposals, "clean" for technical reviews. Leave colours out (each deck gets its own look).
SLIDE TYPES AND THEIR FIELDS
title {title, subtitle, meta} | agenda {items: [text]} | section {title, subtitle, icon} | hero {value, text, sub, icon}
stats {title, stats: [{value, label, delta, good, progress, icon}], note}
chart {title, chart: {kind: column|bar|line|area|pie|doughnut|stacked|stacked_bar, categories: [..], series: [{name, values: [numbers]}],
       unit, highlight, target, source}, takeaway, icon}
bullets {title, bullets: [text | {text, sub: [text]}], takeaway, icon} | cards {title, cards: [{title, text, icon, value}]}
iconlist {title, items: [{icon, title, text}]} | compare {title, left: {title, bullets}, right: {title, bullets}, verdict}
table {title, columns: [..], rows: [[..], ..], heat: [column names], total, note} | timeline {title, items: [{date, title, text, done, icon}]}
process {title, steps: [{title, text}]} | quote {quote, by} | image {title, image, caption} | closing {title, bullets, contact}
Any slide may have "notes" (speaker notes)."""

TOOLS = [
    {"name": "deck_guide", "description": "The rules, every slide type with its fields, the icon names and a complete example outline "
     "to copy. Call once before the first deck_build; lang 'he' gives the example in Hebrew.",
     "inputSchema": {"type": "object", "properties": {"lang": {"type": "string", "description": "en (default) or he"}}}},
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
        he = str(a.get("lang") or "").lower().startswith(("he", "iw"))
        rc, ex, err = run(["--example", "he" if he else "en"])
        rc2, ic, _ = run(["--icons"])
        if rc:
            return {"error": err or "deck.py --example failed"}
        icons = ic.strip().splitlines()[0] if ic.strip() else ""
        return {"rules": RULES, "icons": icons, "example": json.loads(ex),
                "next": "copy 'example', replace its content with your facts (same JSON shape), then call deck_build"}
    if name == "deck_icons":
        rc, ic, err = run(["--icons"])
        return {"icons": ic.strip()} if rc == 0 else {"error": err}
    if name == "deck_build":
        spec = a.get("spec")
        if spec is None and isinstance(a.get("slides"), list):      # the outline sent as the arguments themselves
            spec = {k: v for k, v in a.items() if k not in ("folder", "template", "style", "look", "preview")}
        if isinstance(spec, str):                      # a model that sends the outline as text, maybe in a ```json fence
            txt = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", spec.strip())
            try:
                spec = json.loads(txt)
            except ValueError as e:
                return {"error": f"spec is not valid JSON ({e}); send the outline as a JSON object, the same shape as deck_guide's example"}
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
        res["fixed_note"] = "'fixed' lists what the tool already repaired in your outline: nothing to do about it"
        res["next"] = ("change the outline for each line in 'warnings' (shorten the text, or split the slide), then call deck_build "
                       "again with the whole outline; after 3 rounds deliver anyway and tell the user which warnings are left"
                       if res["warnings"] else
                       "done: call deck_deliver with this path, then answer with the path, the slide list and what the user should check")
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
