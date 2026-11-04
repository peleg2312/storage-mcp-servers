"""deck.py (make-deck skill): python3 brain/test_deck.py  (needs python-pptx: the devtools venv; SKIP without it)"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "claude", "tools", "deck.py")
try:
    from pptx import Presentation
    from pptx.util import Inches
except ImportError:
    for v in (os.path.expanduser("~/.claude/devtools-venv"), "/opt/paas/devtools-venv"):
        py = os.path.join(v, "bin", "python")
        if os.path.isfile(py) and os.path.realpath(py) != os.path.realpath(sys.executable):
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
for theme in ("midnight", "graphite", "ocean", "emerald", "sunset", "light"):
    out = os.path.join(tmp, theme + ".pptx")
    o = deck(spec, "--theme", theme, "--out", out)
    assert "checks: ok" in o and "WARN" not in o, (theme, o)
    p = Presentation(out)
    assert len(p.slides) == len(ex["slides"]) and round(p.slide_width / 914400, 2) == 13.33
    shapes = [sh for s in p.slides for sh in s.shapes]
    assert sum(sh.has_chart for sh in shapes) == 2 and sum(sh.has_table for sh in shapes) == 1
    assert not any(sh.shape_type == 13 for sh in shapes), "a picture where native shapes belong"
    for s in p.slides:                                   # every shape inside the slide
        for sh in s.shapes:
            if not sh.name.startswith("decor"):        # the decorative circles bleed off on purpose
                assert sh.left >= 0 and sh.top >= 0 and sh.left + sh.width <= p.slide_width + 10 and sh.top + sh.height <= p.slide_height + 10, (theme, sh.name)
print("themes ok:", len(types), "slide types")

# the chart keeps its data (editable in PowerPoint) and the highlight
p = Presentation(os.path.join(tmp, "midnight.pptx"))
ch = next(sh.chart for s in p.slides for sh in s.shapes if sh.has_chart)
assert list(ch.plots[0].categories) == ["PMAX-A", "PMAX-B", "ONTAP-1", "ONTAP-2"] and list(ch.plots[0].series[0].values) == [160, 70, 55, 30]
print("chart data ok")

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
for s, needle in (({"slides": [{"type": "nope"}]}, "unknown type"),
                  ({"slides": [{"type": "chart", "chart": {"categories": ["a"], "series": [{"name": "s", "values": [1, 2]}]}}]}, "2 values for 1 categories"),
                  ({"slides": []}, '"slides"'), ({"theme": "pink", "slides": [{"type": "title"}]}, "unknown theme")):
    f = os.path.join(tmp, "e.json")
    json.dump(s, open(f, "w"))
    o = deck(f, "--out", os.path.join(tmp, "e.pptx"), ok=False)
    assert needle in o and "Traceback" not in o, o
print("errors ok")

# company template: its size, layouts and theme fonts are used, its old slides are gone
tpl = os.path.join(tmp, "corp.pptx")
t = Presentation()
t.slides.add_slide(t.slide_layouts[0]).shapes.title.text = "old slide"
t.save(tpl)
out = os.path.join(tmp, "corp-deck.pptx")
o = deck(spec, "--template", tpl, "--out", out)
assert "checks: ok" in o, o
p = Presentation(out)
assert p.slide_width == Inches(10) and len(p.slides) == len(ex["slides"])
assert p.slides[0].slide_layout.name == "Title Slide" and p.slides[0].shapes.title.text == ex["slides"][0]["title"]
assert not any(sh.has_text_frame and sh.text_frame.text == "old slide" for s in p.slides for sh in s.shapes)
fonts = {r.font.name for s in p.slides for sh in s.shapes if sh.has_text_frame for para in sh.text_frame.paragraphs for r in para.runs}
assert "Calibri" in fonts and "Segoe UI" not in fonts, fonts
print("template ok")

# speaker notes
s = {"slides": [{"type": "bullets", "title": "n", "bullets": ["a"], "notes": "say this"}]}
f = os.path.join(tmp, "n.json")
json.dump(s, open(f, "w"))
deck(f, "--out", os.path.join(tmp, "n.pptx"))
assert Presentation(os.path.join(tmp, "n.pptx")).slides[0].notes_slide.notes_text_frame.text == "say this"
print("notes ok")
print("deck ok")
