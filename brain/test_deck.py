"""deck.py (make-deck skill): python3 brain/test_deck.py  (needs python-pptx: the devtools venv; SKIP without it)"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "claude", "tools", "deck.py")
try:
    from pptx import Presentation
    from pptx.oxml.ns import qn
    from pptx.util import Inches
except ImportError:
    for v in (os.path.expanduser("~/.claude/devtools-venv"), "/opt/paas/devtools-venv"):
        py = os.path.join(v, "bin", "python")
        if os.path.isfile(py) and os.path.realpath(v) != os.path.realpath(sys.prefix):
            os.execv(py, [py] + sys.argv)
    print("skipped: python-pptx is not installed (ImportError)")
    sys.exit(77)

tmp = tempfile.mkdtemp()


def deck(*args, ok=True):
    r = subprocess.run([sys.executable, TOOL] + list(args), capture_output=True, text=True, env=dict(os.environ, HOME=tmp))
    assert (r.returncode == 0) == ok, r.stdout + r.stderr
    return r.stdout + r.stderr


ex = json.loads(deck("--example"))
types = {s["type"] for s in ex["slides"]}
spec = os.path.join(tmp, "ex.json")
json.dump(ex, open(spec, "w"))

# every theme: builds, every check passes on the example, 16:9, native charts and tables, nothing drawn as a picture
for theme, style in (("midnight", "clean"), ("graphite", "bold"), ("ocean", "clean"), ("emerald", "bold"), ("sunset", "clean"),
                     ("light", "bold"), ("midnight", "bold"), ("light", "clean")):
    out = os.path.join(tmp, f"{theme}-{style}.pptx")
    o = deck(spec, "--theme", theme, "--style", style, "--out", out)
    assert "checks: ok" in o and "WARN" not in o, (theme, o)
    p = Presentation(out)
    assert len(p.slides) == len(ex["slides"]) and round(p.slide_width / 914400, 2) == 13.33
    shapes = [sh for s in p.slides for sh in s.shapes]
    assert sum(sh.has_chart for sh in shapes) == 3 and sum(sh.has_table for sh in shapes) == 1
    icons = [sh for sh in shapes if sh.name.startswith("icon ")]
    assert len(icons) >= 15 and all(sh._element.spPr.find(qn("a:custGeom")) is not None for sh in icons), (theme, len(icons))
    assert sum(sh.name == "target line" for sh in shapes) == 1
    assert not any(sh.shape_type == 13 for sh in shapes), "a picture where native shapes belong"
    for s in p.slides:                                   # every shape inside the slide
        for sh in s.shapes:
            if not sh.name.startswith("decor"):        # the decorative circles bleed off on purpose
                l, t_, w, h = sh.left, sh.top, sh.width, sh.height
                if getattr(sh, "rotation", 0) in (90.0, 270.0):  # a rotated label: its box turned about its centre
                    l, t_, w, h = l + (w - h) // 2, t_ + (h - w) // 2, h, w
                assert l >= 0 and t_ >= 0 and l + w <= p.slide_width + 10 and t_ + h <= p.slide_height + 10, (theme, sh.name)
print("themes and styles ok:", len(types), "slide types")

# the chart keeps its data (editable in PowerPoint) and the highlight
p = Presentation(os.path.join(tmp, "midnight-clean.pptx"))
ch = next(sh.chart for s in p.slides for sh in s.shapes if sh.has_chart)
assert list(ch.plots[0].categories) == ["PMAX-A", "PMAX-B", "ONTAP-1", "ONTAP-2"] and list(ch.plots[0].series[0].values) == [160, 70, 55, 30]
# a line chart names its series at the last point (no legend); a table colours status words and keeps the total row plain
line = [sh.chart for s in p.slides for sh in s.shapes if sh.has_chart][1]
assert not line.has_legend and line.plots[0].series[0].points[5].data_label.text_frame.text.startswith("PMAX-A")
tbl = next(sh.table for s in p.slides for sh in s.shapes if sh.has_table)
assert tbl.cell(4, 4).text.endswith("Failed") and tbl.cell(4, 4).text_frame.paragraphs[0].runs[0].text == "\u25CF "
print("chart data, direct labels, table status ok")
o = deck("--icons")
assert "database" in o and "storage=database" in o
print("icons list ok")

# the default output goes to ~/storage-reports/<date>-<slug>/<slug>.pptx
o = deck(spec)
assert "storage-reports" in o and o.split("deck: ")[1].split(" (")[0].endswith("san-capacity-review-q4.pptx"), o
print("default path ok")

# warnings: too many bullets, a long card text, text that cannot fit; the deck is still written
bad = {"title": "t", "slides": [
    {"type": "bullets", "title": "x", "bullets": ["b%d" % i for i in range(9)]},
    {"type": "bullets", "title": "y", "bullets": ["word " * 900]},
    {"type": "cards", "title": "z", "cards": [{"title": "a", "text": "long " * 200}, {"title": "b", "text": "ok"}]},
    {"type": "chart", "title": "pie", "chart": {"kind": "pie", "categories": list("abcdefgh"), "series": [{"name": "n", "values": list(range(1, 9))}]}},
]}
bf = os.path.join(tmp, "bad.json")
json.dump(bad, open(bf, "w"))
o = deck(bf, "--out", os.path.join(tmp, "bad.pptx"))
for needle in ("9 bullets", "does not fit", "card 1 text is long", "8 slices"):
    assert needle in o, (needle, o)
print("warnings ok")

# errors are clear, no traceback
for s, needle in (({"slides": [{"type": "chart", "chart": {"categories": ["a"], "series": [{"name": "s", "values": [1, 2]}]}}]}, "2 values for 1 categories"),
                  ({"slides": []}, '"slides"'), ({"theme": "pink", "slides": [{"type": "title"}]}, "unknown theme")):
    f = os.path.join(tmp, "e.json")
    json.dump(s, open(f, "w"))
    o = deck(f, "--out", os.path.join(tmp, "e.pptx"), ok=False)
    assert needle in o and "Traceback" not in o, o
print("errors ok")
f = os.path.join(tmp, "e.json")
json.dump({"slides": [{"type": "nope", "title": "x", "bullets": ["a", "b"]}]}, open(f, "w"))
o = deck(f, "--out", os.path.join(tmp, "e.pptx"))
assert "fixed slide 1: type 'nope' -> 'bullets'" in o, o

# company template: its size, layouts and theme fonts are used, its old slides are gone
tpl = os.path.join(tmp, "corp.pptx")
t = Presentation()
t.slides.add_slide(t.slide_layouts[0]).shapes.title.text = "old slide"
t.save(tpl)
out = os.path.join(tmp, "corp-deck.pptx")
o = deck(spec, "--template", tpl, "--style", "bold", "--out", out)
assert "checks: ok" in o, o
p = Presentation(out)
assert p.slide_width == Inches(10) and len(p.slides) == len(ex["slides"])
assert p.slides[0].slide_layout.name == "Title Slide" and p.slides[0].shapes.title.text == ex["slides"][0]["title"]
assert not any(sh.has_text_frame and sh.text_frame.text == "old slide" for s in p.slides for sh in s.shapes)
fonts = {r.font.name for s in p.slides for sh in s.shapes if sh.has_text_frame for para in sh.text_frame.paragraphs for r in para.runs}
assert "Calibri" in fonts and "Segoe UI" not in fonts, fonts
print("template ok")

# looks: the same number gives the same deck design, other numbers other designs; a generated palette stays readable
sys.path.insert(0, os.path.dirname(TOOL))
import deck as D  # noqa: E402
looks = {json.dumps({k: v for k, v in D.make_look(n).items() if k != "seed"}, sort_keys=True) for n in range(40)}
assert D.make_look(7) == D.make_look(7) and len(looks) >= 35, len(looks)
for h in D.HUES + ["#FFEE00", "#00FFAA", "#111111"]:
    assert all(D.contrast(c, "#FFFFFF") >= 3.0 for c in D.palette(h)["accents"]), h
plainspec = dict(ex)
plainspec.pop("theme", None), plainspec.pop("style", None)
f = os.path.join(tmp, "looks.json")
json.dump(plainspec, open(f, "w"))
seen = set()
for n in (1, 2, 3, 4, 5, 6):
    o = deck(f, "--look", str(n), "--out", os.path.join(tmp, f"look{n}.pptx"))
    assert "checks: ok" in o and f"look: {n} (" in o, o
    seen.add(o.split("look: ")[1].split(";")[0].split(" ", 1)[1])
assert len(seen) >= 4, seen
o1 = deck(f, "--out", os.path.join(tmp, "auto1.pptx"))
o2 = deck(f, "--out", os.path.join(tmp, "auto2.pptx"))
assert o1.split("look: ")[1].split(" ")[0] == o2.split("look: ")[1].split(" ")[0], "the same title keeps its look"
json.dump(dict(plainspec, accent="#7A3EF0"), open(f, "w"))
assert "accent #7A3EF0" in deck(f, "--out", os.path.join(tmp, "acc.pptx"))
print("looks ok:", len(looks), "different looks of 40; designs seen:", len(seen))

# speaker notes
s = {"slides": [{"type": "bullets", "title": "n", "bullets": ["a"], "notes": "say this"}]}
f = os.path.join(tmp, "n.json")
json.dump(s, open(f, "w"))
deck(f, "--out", os.path.join(tmp, "n.pptx"))
assert Presentation(os.path.join(tmp, "n.pptx")).slides[0].notes_slide.notes_text_frame.text == "say this"
print("notes ok")
print("deck ok")

# the deck MCP server (plugin presentations): tools listed, guide, build with warnings and without, read back, deliver only reports
mcp = os.path.join(os.path.dirname(TOOL), "deck_mcp.py")


def mcp_calls(*calls):
    msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"}, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}]
    msgs += [{"jsonrpc": "2.0", "id": 10 + i, "method": "tools/call", "params": {"name": n, "arguments": a}} for i, (n, a) in enumerate(calls)]
    r = subprocess.run([sys.executable, mcp], input="\n".join(json.dumps(m) for m in msgs) + "\n", capture_output=True, text=True,
                       env=dict(os.environ, HOME=tmp), timeout=600)
    out = [json.loads(line) for line in r.stdout.splitlines()]
    assert [o["id"] for o in out] == [0, 1] + [10 + i for i in range(len(calls))], r.stdout[-500:] + r.stderr[-500:]
    return out[1]["result"]["tools"], [json.loads(o["result"]["content"][0]["text"]) for o in out[2:]]


short = {"title": "MCP test", "slides": [{"type": "title", "title": "MCP test"}, {"type": "bullets", "title": "Eight jobs failed on 2 nights", "bullets": ["b%d" % i for i in range(8)]}]}
fixed = {"title": "MCP test", "slides": [{"type": "title", "title": "MCP test"}, {"type": "bullets", "title": "Three jobs failed on 2 nights", "bullets": ["a", "b", "c"]}]}
tools, (g, b1, b2, bad) = mcp_calls(("deck_guide", {}), ("deck_build", {"spec": short, "style": "bold"}),
                                    ("deck_build", {"spec": json.dumps(fixed), "look": 5}), ("deck_build", {"spec": {"slides": []}}))
assert {t["name"] for t in tools} == {"deck_guide", "deck_build", "deck_read", "deck_icons", "deck_deliver"}
assert "SLIDE TYPES AND THEIR FIELDS" in g["rules"] and g["example"]["slides"] and "database" in g["icons"] and "copy" in g["next"]
assert not b1["warnings"] and any("8 bullets -> 2 slides" in x for x in b1["fixed"]) and b1["style"] == "bold" and "deck_deliver" in b1["next"]
assert not b2["warnings"] and b2["look"] == 5 and b2["path"].startswith(os.path.join(tmp, "storage-reports")) and os.path.isfile(b2["path"])
assert "error" in bad
_, (rd, dl, nope) = mcp_calls(("deck_read", {"path": b2["path"]}), ("deck_deliver", {"path": b2["path"]}), ("deck_deliver", {"path": TOOL}))
assert rd["slides"] == 2 and "MCP test" in rd["deck"][0]["texts"][0]
assert "path" in dl and "error" in nope
# a Hebrew guide, an outline sent in a ```json fence, the outline sent as the arguments, a title too long: a warning to act on
long = {"title": "x", "slides": [{"type": "bullets", "title": "A very long title " * 8, "bullets": ["a", "b", "c"]}]}
_, (gh, fence, flat, lw) = mcp_calls(("deck_guide", {"lang": "he"}),
                                     ("deck_build", {"spec": "```json\n" + json.dumps(fixed) + "\n```"}),
                                     ("deck_build", dict(fixed)), ("deck_build", {"spec": long}))
assert "סקירת" in gh["example"]["title"] and gh["example"]["slides"][0]["type"] == "title"
assert fence.get("path") and flat.get("path"), (fence, flat)
assert lw["warnings"] and "title is long" in lw["warnings"][0] and "change the outline" in lw["next"]
print("deck MCP server ok")

# right to left: a Hebrew outline gives RTL paragraphs with he-IL runs and a Hebrew-capable complex-script font, a mirrored
# layout (the title on the right half), a table whose first column is on the right, chevrons pointing left
he = json.loads(subprocess.run([sys.executable, TOOL, "--example", "he"], capture_output=True, text=True).stdout)
hf = os.path.join(tmp, "he.json")
json.dump(he, open(hf, "w"), ensure_ascii=False)
he["slides"].append({"type": "process", "title": "תהליך שחזור", "steps": [{"title": "בחירה", "text": "הגיבוי האחרון"}, {"title": "בדיקה", "text": "BSL זמין"}, {"title": "שחזור", "text": "oc create"}]})
json.dump(he, open(hf, "w"), ensure_ascii=False)
o = deck(hf, "--out", os.path.join(tmp, "he.pptx"))
assert "direction: right to left (he)" in o, o
hp = Presentation(os.path.join(tmp, "he.pptx"))
from pptx.oxml.ns import qn as _qn
W = hp.slide_width
rtl_paras = langs = 0
for sl in hp.slides:
    for sh in sl.shapes:
        if sh.has_text_frame:
            for para in sh.text_frame.paragraphs:
                txt = "".join(r.text for r in para.runs)
                if any("\u0590" <= ch <= "\u05FF" for ch in txt):
                    assert para._p.pPr is not None and para._p.pPr.get("rtl") == "1", txt
                    rtl_paras += 1
                for r in para.runs:
                    if any("\u0590" <= ch <= "\u05FF" for ch in r.text):
                        assert r.font._rPr.get("lang") == "he-IL", r.text
                        cs = r.font._rPr.find(_qn("a:cs"))
                        assert cs is not None and cs.get("typeface") in ("Segoe UI", "Segoe UI Semibold", "Arial", "Tahoma"), r.text
                        langs += 1
                if txt == "312 TB":
                    assert para._p.pPr is None or para._p.pPr.get("rtl") != "1", "a value alone keeps its own order"
assert rtl_paras > 20 and langs > 20, (rtl_paras, langs)
si = next(i for i, x in enumerate(he["slides"]) if x["type"] == "stats")
title = next(sh for sh in hp.slides[si].shapes if sh.has_text_frame and "97.8%" in sh.text_frame.text and sh.top < 914400 * 1.5)
assert title.left + title.width > W * 0.9, "the title of a right-to-left slide starts at the right edge"
tbl = next(sh for sl in hp.slides for sh in sl.shapes if getattr(sh, "has_table", False) and sh.has_table).table
assert tbl.cell(0, len(tbl.columns) - 1).text == "MediaAgent", "the first column is on the right"
chev = [sh for sh in hp.slides[-1].shapes if sh._element.tag == _qn("p:sp") and sh._element.spPr.find(_qn("a:prstGeom")) is not None
        and sh._element.spPr.find(_qn("a:prstGeom")).get("prst") in ("chevron", "homePlate")]
assert chev and all(c._element.spPr.find(_qn("a:xfrm")).get("flipH") == "1" for c in chev)
print("right to left ok")

# a small model's outline: aliases, strings, empty items, unknown icons, emoji, too many items -> repaired, never a crash,
# and no text box ever holds more than fits
sloppy = {"slides": [{"type": "summary", "heading": "Why", "points": "One. Two. Three."},
                     {"type": "cards", "title": "Options", "cards": ["Fix DNS", {"heading": "Move", "description": "To another bucket", "icon": "🪣"}, {"title": "", "text": ""}]},
                     {"type": "stats", "title": "Numbers", "stats": [{"value": 12345678, "label": "files"}, {"value": "3", "label": "x", "icon": "incident"}]},
                     {"type": "bullets", "title": "Many", "bullets": ["✅ item %d with some words" % k for k in range(9)]},
                     {"type": "chart", "title": "Trend", "chart": {"type": "line", "labels": ["a", "b"], "data": ["3", "5"]}},
                     {"type": "table", "title": "T", "columns": ["A", "B"], "rows": [{"A": 1, "B": 2}]},
                     {"type": "compare", "title": "A vs B", "left": ["x", "y"], "right": "z. w."}]}
sf = os.path.join(tmp, "sloppy.json")
json.dump(sloppy, open(sf, "w"))
o = deck(sf, "--out", os.path.join(tmp, "sloppy.pptx"))
for needle in ("points was one string, split into 3 items", "an empty item dropped", "icon '🪣' -> arrow-right",
               "9 bullets -> 2 slides", "chart data -> series", "table row was an object", "left was a list"):
    assert needle in o, (needle, o)
sp = Presentation(os.path.join(tmp, "sloppy.pptx"))
alltext = " ".join(sh.text_frame.text for sl in sp.slides for sh in sl.shapes if sh.has_text_frame)
assert "✅" not in alltext and "🪣" not in alltext and "12345678" in alltext
print("sloppy outline ok")

# the plugin: manifest, MCP wiring, agent tools in the plugin's MCP names, the command, the skill moved here
P = os.path.join(HERE, "plugins", "presentations")
assert json.load(open(os.path.join(P, ".claude-plugin", "plugin.json")))["name"] == "presentations"
assert json.load(open(os.path.join(P, ".mcp.json")))["mcpServers"]["deck"]["command"] == "${CLAUDE_PLUGIN_ROOT}/bin/deck-mcp"
assert os.access(os.path.join(P, "bin", "deck-mcp"), os.X_OK)
ag = open(os.path.join(P, "agents", "deck-designer.md")).read()
assert all(f"mcp__plugin_presentations_deck__{t}" in ag for t in ("deck_guide", "deck_build", "deck_read", "deck_deliver"))
assert os.path.isfile(os.path.join(P, "commands", "deck.md")) and os.path.isfile(os.path.join(P, "skills", "make-deck", "SKILL.md"))
assert not os.path.exists(os.path.join(HERE, "claude", "skills", "make-deck")), "one make-deck skill: the plugin's"
mk = json.load(open(os.path.join(HERE, "plugins", ".claude-plugin", "marketplace.json")))
assert any(p["name"] == "presentations" and p["source"] == "./presentations" for p in mk["plugins"])
print("presentations plugin ok")

# v4: the new slide types, sparklines, callouts, transitions, notes made from the slide, premium themes, story plans, the
# storyline check, the real fit check (LibreOffice) with its repair and the PDF copy
for t_ in ("summary", "status", "diagram", "matrix", "beforeafter"):
    assert t_ in types, t_
p = Presentation(os.path.join(tmp, "midnight-clean.pptx"))
names = [sh.name for s_ in p.slides for sh in s_.shapes]
assert sum(n.startswith("decor sparkline") for n in names) == 1
conn = [sh for s_ in p.slides for sh in s_.shapes if sh._element.tag == qn("p:cxnSp") and sh._element.spPr.find(qn("a:ln")).find(qn("a:tailEnd")) is not None]
assert len(conn) == 4, "the diagram's four links are arrows"
assert all(s_._element.find(qn("p:transition")) is not None for s_ in p.slides), "a fade on every slide"
notes = [s_.notes_slide.notes_text_frame.text for s_ in p.slides if s_.has_notes_slide]
assert len(notes) == len(p.slides) and any("PMAX-A 160" in n for n in notes), "notes made from the slide's own words"
for th in ("executive", "ivory", "noir"):
    o = deck(spec, "--theme", th, "--out", os.path.join(tmp, f"{th}.pptx"))
    assert "checks: ok" in o and "WARN" not in o, (th, o)
iv = Presentation(os.path.join(tmp, "ivory.pptx"))
assert iv.slides[2].background.fill.fore_color.rgb == D.rgb("#FBF8F2"), "a content slide on the theme's paper colour"
json.dump(dict(ex, transition="none"), open(f, "w"))
deck(f, "--out", os.path.join(tmp, "nt.pptx"))
assert all(s_._element.find(qn("p:transition")) is None for s_ in Presentation(os.path.join(tmp, "nt.pptx")).slides)
# aliases of the new types and their fields
v4 = {"slides": [{"type": "title", "title": "v4"},
                 {"type": "exec-summary", "title": "Backups are 97.8% good this month", "text": "Most is fine.", "items": ["env2 fails", "DNS"]},
                 {"type": "topology", "title": "Data flows from clients to S3", "nodes": ["Clients", "MediaAgents", "S3"]},
                 {"type": "2x2", "title": "Reclaim wins on speed and on effect", "quadrants": {"top_left": "a", "top_right": "b", "bottom_left": "c", "bottom_right": "d"}},
                 {"type": "before-after", "title": "RTO dropped to 42 minutes", "before": "3.5 h", "after": {"value": "42 min"}},
                 {"type": "dashboard", "title": "Two systems up, one down today", "systems": [{"name": "a", "status": "OK"}, {"name": "b", "status": "נכשל"}]},
                 {"type": "chart", "title": "env2 fails most: 23 of 41", "chart": {"kind": "column", "categories": ["env1", "env2"],
                  "series": [{"name": "f", "values": [9, 23]}], "callout": {"at": "env2", "text": "DNS loss"}}},
                 {"type": "closing", "title": "Next steps", "bullets": ["Fix DNS"]}]}
f = os.path.join(tmp, "v4.json")
json.dump(v4, open(f, "w"))
o = deck(f, "--out", os.path.join(tmp, "v4.pptx"))
for needle in ("'exec-summary' -> 'summary'", "'items' -> 'points'", "'topology' -> 'diagram'", "boxes chained in order",
               "'2x2' -> 'matrix'", "'before-after' -> 'beforeafter'", "'dashboard' -> 'status'", "'systems' -> 'items'"):
    assert needle in o, (needle, o)
assert "WARN" not in o, o
v4p = Presentation(os.path.join(tmp, "v4.pptx"))
assert any(sh.has_text_frame and sh.text_frame.text == "DNS loss" for sh in v4p.slides[6].shapes), "the callout is drawn"
# the storyline check: a topic title, two bullets slides in a row, a placeholder, no closing
story = {"slides": [{"type": "title", "title": "x"}, {"type": "bullets", "title": "Failures", "bullets": ["a <number>"]},
                    {"type": "bullets", "title": "More failures here today", "bullets": ["b"]}, {"type": "hero", "value": "1"},
                    {"type": "hero", "value": "2"}, {"type": "hero", "value": "3"}]}
json.dump(story, open(f, "w"))
o = deck(f, "--out", os.path.join(tmp, "st.pptx"))
for needle in ("names a topic", "two bullets slides in a row", "a placeholder is left in", "no closing slide"):
    assert needle in o, (needle, o)
assert "monthly-review" in deck("--stories")
plan = json.loads(deck("--story", "dr-drill"))
assert plan["plan"][1]["type"] == "summary" and all(x["type"] in types for x in plan["plan"])
deck("--story", "nope", ok=False)
_, (gs,) = mcp_calls(("deck_guide", {"story": "incident-review"}))
assert gs["story"]["plan"][0]["type"] == "title" and "story.plan" in gs["next"]
print("v4 types, sparklines, callouts, transitions, notes, themes, stories ok")

# the real fit check: LibreOffice draws the deck, a text drawn outside its box is made smaller until it fits; a PDF copy
import shutil as _sh  # noqa: E402
if _sh.which("soffice") and _sh.which("pdftotext"):
    from pptx.util import Pt  # noqa: E402
    out = os.path.join(tmp, "fit.pptx")
    o = deck(spec, "--out", out, "--check")
    assert "pdf: " in o and os.path.isfile(out[:-5] + ".pdf") and "WARN" not in o, o
    fp = Presentation(out)
    big = next(sh for sh in fp.slides[12].shapes if sh.has_text_frame and "Remove unmapped" in sh.text_frame.text)
    for para in big.text_frame.paragraphs:
        for r in para.runs:
            r.font.size = Pt(26)
    fp.save(out)
    assert D.spills(out, D.to_pdf(out)[0]), "a spill is found"
    pdf, warns, repaired, note = D.fit_check(out)
    assert pdf and repaired and not warns and note is None, (warns, repaired, note)
    assert not D.spills(out, pdf)
    print("fit check ok:", len(repaired), "repairs")
else:
    print("fit check skipped: LibreOffice / pdftotext not installed")

# mixed Hebrew / English lines: a number keeps its unit and its sign ("2 TB" not "TB 2", "-12" not "12-"), a short English
# phrase wraps as one piece; what already reads right gets no mark (brackets, dates, versions, Hebrew prefixes)
L, NB = "‎", " "
cases = {"שחזור DB של 2 TB לפני": f"שחזור DB של {L}2{NB}TB לפני", "עבודות שנכשלו: -12 לעומת": f"עבודות שנכשלו: {L}-12 לעומת",
         "גדל ב-+6% תוך": f"גדל ב-{L}+6% תוך", "ירד ב-12% החודש": "ירד ב-12% החודש", "מספרים: 2 TB ו-312 TB": f"מספרים: {L}2{NB}TB ו-{L}312{NB}TB",
         "דוח 2026-11-01 עד 2026-11-30": "דוח 2026-11-01 עד 2026-11-30", "מתוך 41 (56%)": "מתוך 41 (56%)",
         "נכשל אחרי failover של Always On.": f"נכשל אחרי failover של Always{NB}On.", "MA-SITEB-03 מאבד DNS": "MA-SITEB-03 מאבד DNS"}
for k, v in cases.items():
    assert D.bidi_marks(k) == v, (k, D.bidi_marks(k).encode("unicode_escape"))
o = deck(hf, "--out", os.path.join(tmp, "he2.pptx"))
txt = [r.text for s_ in Presentation(os.path.join(tmp, "he2.pptx")).slides for sh in s_.shapes if sh.has_text_frame
       for para in sh.text_frame.paragraphs for r in para.runs]
assert any(f"{L}2{NB}TB" in t for t in txt) and any(f"{L}-12" in t for t in txt), "the Hebrew example keeps 2 TB and -12 in order"
assert not any(L in t or NB in t for t in txt if not D.RTL_RX.search(t)), "marks only in right-to-left lines"
print("mixed Hebrew / English lines ok")
