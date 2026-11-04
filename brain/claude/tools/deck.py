#!/usr/bin/env python3
"""Designed PowerPoint decks from a short JSON outline: the model writes the content, this tool does the design.

    deck.py spec.json [--out DIR|FILE.pptx] [--theme NAME] [--style clean|bold] [--look N|random] [--template company.pptx] [--preview]
    deck.py --example            a spec with every slide type (start from it)
    deck.py --themes             the built-in themes
    deck.py --icons              the icon names (cards, stats, iconlist, timeline, hero, section, takeaway)

Every slide is native PowerPoint (text boxes, shapes, real charts with their data, real tables), so the deck stays
editable. Text is fitted to its box (the font shrinks within limits); what still does not fit, or breaks a design rule
(too many bullets, a long title, a crowded chart), is reported as WARN lines: fix the spec and run again.
--template takes the company deck or .potx: its slide size, master (logo, background), colours and fonts are used, its
"Title Slide" / "Section Header" / "Title Only" layouts where they exist. --preview renders PNGs and one contact sheet
(LibreOffice + pdftoppm, when installed) next to the deck. Default output: ~/storage-reports/<date>-<title>/<title>.pptx.

Spec: {"title": "...", "theme": "midnight", "footer": "SAN team", "slides": [{"type": "title", ...}, ...]}
Slide types: title, agenda, section, hero, bullets, cards, iconlist, stats, chart, table, compare, timeline, process,
quote, image, closing (fields: deck.py --example). Styles: clean (calm, light slides) or bold (gradients, colour panels,
split layouts, a dark numbers slide). Icons are drawn as editable shapes (deck_icons.py), no image files.
Looks: every deck gets its own design from its title (layout variants of the title, section, agenda, cards and numbers
slides, a palette from the themes or built from a brand colour, a font pair, bullets), printed as "look: N"; the same
N gives the same design again, "random" a new one; "accent": "#RRGGBB" builds the palette from that colour. Any slide takes "notes" (speaker notes). Text takes **bold** inline.
Needs python-pptx (the devtools venv: ~/.claude/devtools-venv or /opt/paas/devtools-venv). Python 3.9+."""
import copy
import datetime as dt
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

VENVS = [os.path.expanduser("~/.claude/devtools-venv"), "/opt/paas/devtools-venv"]


def _reexec():
    """python-pptx lives in a devtools venv: run in the first one that really has it (an old personal venv without it
    must not hide the shared one)"""
    tried = []
    for v in VENVS:
        py = os.path.join(v, "bin", "python")
        # the venv itself, not its python: that is a link to the system python this very process may be running
        if not os.path.isfile(py) or os.path.realpath(v) == os.path.realpath(sys.prefix):
            continue
        tried.append(py)
        if subprocess.run([py, "-c", "import pptx"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            os.execv(py, [py] + sys.argv)
    sys.exit("deck: python-pptx is not installed in " + (", ".join(tried) or "any devtools venv (" + ", ".join(VENVS) + ")")
             + ". As root: DEVTOOLS_VENV=/opt/paas/devtools-venv sh brain/devtools/install-devtools.sh (multi-user VM), or"
             " <venv>/bin/python -m pip install --no-index --find-links brain/devtools/wheels python-pptx")


try:
    from lxml import etree
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_MARK
    from pptx.enum.dml import MSO_LINE_DASH_STYLE
    from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.oxml.ns import qn
    from pptx.util import Emu, Inches, Pt
except ImportError:
    if __name__ == "__main__":
        _reexec()
    raise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deck_icons  # noqa: E402  (the line icons, standard library)

# ---------------------------------------------------------------------------------------------------------- themes
# dark: title / section / closing background; bg / text / muted / surface / line: content slides; accents: charts, cards
THEMES = {
    "midnight": {"dark": "#0F1B2D", "dark2": "#16263D", "on_dark": "#FFFFFF", "on_dark_muted": "#9FB0C8",
                 "bg": "#FFFFFF", "text": "#14213D", "muted": "#5B6B82", "surface": "#F2F5F9", "line": "#DDE3EA",
                 "accents": ["#2A78D6", "#1BAF7A", "#EDA100", "#EB6834", "#6250D6", "#E87BA4"]},
    "graphite": {"dark": "#1C1D22", "dark2": "#26282F", "on_dark": "#FFFFFF", "on_dark_muted": "#A4A8B3",
                 "bg": "#FFFFFF", "text": "#1C1D22", "muted": "#5F6470", "surface": "#F3F4F6", "line": "#E1E3E8",
                 "accents": ["#14A3A3", "#F2A33A", "#5B7BE0", "#E5604D", "#8E6BD8", "#47B36B"]},
    "ocean":    {"dark": "#0B3C5D", "dark2": "#0E4A72", "on_dark": "#FFFFFF", "on_dark_muted": "#A9C6DC",
                 "bg": "#FFFFFF", "text": "#0B2A40", "muted": "#557086", "surface": "#EFF5FA", "line": "#D7E3EC",
                 "accents": ["#1D8FE1", "#19B5A5", "#F5B700", "#F0743E", "#7A5CD6", "#E05A8A"]},
    "emerald":  {"dark": "#0E3B2E", "dark2": "#134A3A", "on_dark": "#FFFFFF", "on_dark_muted": "#A6CBBE",
                 "bg": "#FFFFFF", "text": "#10291F", "muted": "#557365", "surface": "#F0F6F3", "line": "#D8E6DF",
                 "accents": ["#1BAF7A", "#2A78D6", "#EDA100", "#E5604D", "#6250D6", "#3FB8C9"]},
    "sunset":   {"dark": "#2B1B3D", "dark2": "#38244F", "on_dark": "#FFFFFF", "on_dark_muted": "#C3B3D6",
                 "bg": "#FFFFFF", "text": "#24172F", "muted": "#6B5C78", "surface": "#F7F3F9", "line": "#E7DFEC",
                 "accents": ["#EB6834", "#C2458F", "#F2B33D", "#6250D6", "#2A9D8F", "#3D7DD8"]},
    "light":    {"dark": "#FFFFFF", "dark2": "#F2F5F9", "on_dark": "#14213D", "on_dark_muted": "#5B6B82",
                 "bg": "#FFFFFF", "text": "#14213D", "muted": "#5B6B82", "surface": "#F2F5F9", "line": "#DDE3EA",
                 "accents": ["#2A78D6", "#1BAF7A", "#EDA100", "#EB6834", "#6250D6", "#E87BA4"]},
}
FONTS = {"head": "Segoe UI Semibold", "body": "Segoe UI"}
# head / body font pairs a look can use (Windows fonts; LibreOffice substitutes in previews), with the head font's glyph width
FONT_PAIRS = [("Segoe UI Semibold", "Segoe UI", 0.56), ("Georgia", "Segoe UI", 0.6), ("Bahnschrift SemiBold", "Segoe UI", 0.54),
              ("Trebuchet MS", "Segoe UI", 0.57)]
# brand colours a look can build its palette from (beside the fixed themes)
HUES = ["#2A78D6", "#7A3EF0", "#0F9AA8", "#E4572E", "#2E9E5B", "#C2185B", "#3D5AFE", "#C77D00", "#5C6BC0", "#00897B"]
GOOD, BAD = "#1A9E62", "#D64545"
CHAR = 0.52          # average glyph width / font size (Segoe UI, Calibri, Arial within a few percent)
BOLD_CHAR = 0.56

# ---------------------------------------------------------------------------------------------------------- helpers


def rgb(h):
    return RGBColor.from_string(h.lstrip("#").upper())


def mix(a, b, t):
    """a blended toward b by t (0..1), as #RRGGBB"""
    a, b = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join("%02X" % round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t) for i in (0, 2, 4))


def usep(unit):
    """a unit after a number: "%" sticks to it, others get a space"""
    return unit if unit in ("%", "x", "\u00b0") else " " + unit


def _lum(h):
    def f(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hls(h, l, s):
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def palette(accent):
    """a full theme from one brand colour: dark, text and surface tones of its hue, five companion accents around the
    colour wheel, every accent at least 3:1 against white (readable as a chart colour or on a white slide)"""
    import colorsys
    a = str(accent).lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", a):
        raise SystemExit(f"deck: accent {accent!r} is not a colour like #2A78D6")
    h, l, s = colorsys.rgb_to_hls(*(int(a[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    s = max(s, 0.5)

    def acc(hh, ll=0.5):
        c = _hls(hh, ll, min(0.78, s))
        while contrast(c, "#FFFFFF") < 3.0 and ll > 0.2:
            ll -= 0.03
            c = _hls(hh, ll, min(0.78, s))
        return c
    first = "#" + a.upper() if contrast("#" + a, "#FFFFFF") >= 3.0 else acc(h, l)
    return {"dark": _hls(h, 0.13, min(0.6, s)), "dark2": _hls(h, 0.18, min(0.55, s)), "on_dark": "#FFFFFF",
            "on_dark_muted": _hls(h, 0.8, 0.3), "bg": "#FFFFFF", "text": _hls(h, 0.15, 0.35), "muted": _hls(h, 0.4, 0.14),
            "surface": _hls(h, 0.965, 0.45), "line": _hls(h, 0.89, 0.22),
            "accents": [first] + [acc(h + d) for d in (0.45, 0.12, -0.09, 0.6, 0.3)]}


def make_look(seed):
    """the design choices of one deck, all from one number: the same number gives the same look again"""
    import random
    r = random.Random(seed)
    return {"seed": seed, "title": r.randrange(4), "section": r.randrange(3), "cards": r.randrange(3), "stats": r.randrange(3),
            "agenda": r.randrange(2), "chrome": r.randrange(3), "fonts": r.randrange(len(FONT_PAIRS)), "bullet": r.randrange(3),
            "palette": r.randrange(len(THEMES) - 1 + len(HUES)), "style": r.choice(("clean", "bold"))}


def plain(text):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", str(text))


def lines_for(text, size, width_in, char=CHAR):
    per_line = max(1, int(width_in * 72 / (size * char)))
    words, n, cur = plain(text).split(), 1, 0
    for w in words:
        need = len(w) + (1 if cur else 0)
        if cur + need > per_line and cur:
            n, cur = n + 1, len(w)
        else:
            cur += need
    return n


def fit(paras, width_in, height_in, hi, lo, spacing=1.15, gap=0.55, char=CHAR):
    """largest size in [lo, hi] at which the paragraphs (text, indent_in) fit the box; (size, fits)"""
    size = hi
    while True:
        h = sum(lines_for(t, size, width_in - ind, char) * size * spacing for t, ind in paras) + gap * size * max(0, len(paras) - 1)
        if h <= height_in * 72 or size <= lo:
            return size, h <= height_in * 72
        size -= 1


class Deck:
    def __init__(self, spec, theme=None, template=None, style=None, look=None):
        self.spec, self.warn = spec, []
        lk = look if look is not None else spec.get("look")
        if lk in (None, ""):                         # each deck its own look, the same one again for the same title
            import hashlib
            lk = int(hashlib.sha1(plain(spec.get("title", "")).encode()).hexdigest()[:8], 16) % 10000
        elif str(lk).lower() == "random":
            import random
            lk = random.randrange(10000)
        try:
            lk = int(lk)
        except (TypeError, ValueError):
            raise SystemExit(f"deck: look {lk!r}: a number (0-9999) or random")
        self.look = make_look(lk)
        self.style = style or spec.get("style") or self.look["style"]
        if self.style not in ("clean", "bold"):
            raise SystemExit(f"deck: unknown style {self.style!r}; clean or bold")
        self.template = template or spec.get("template")
        self.hc = BOLD_CHAR
        if self.template:
            self.prs = Presentation(os.path.expanduser(self.template))
            self._drop_slides()
            self.t = self._theme_from_template()
            self.theme_name = "template"
        else:
            self.prs = Presentation()
            self.prs.slide_width, self.prs.slide_height = Inches(13.333), Inches(7.5)
            name = theme or spec.get("theme")
            fp = FONT_PAIRS[self.look["fonts"]]
            fonts = {"head": fp[0], "body": fp[1]}
            if spec.get("accent") and not name:
                self.t = dict(palette(spec["accent"]), **fonts)
                self.theme_name = "accent " + str(spec["accent"])
            elif name:
                if name not in THEMES:
                    raise SystemExit(f"deck: unknown theme {name!r}; one of {', '.join(THEMES)}")
                self.t = dict(THEMES[name], **fonts)
                self.theme_name = name
            else:
                names = [k for k in THEMES if k != "light"]
                i = self.look["palette"]
                self.t = dict(THEMES[names[i]] if i < len(names) else palette(HUES[i - len(names)]), **fonts)
                self.theme_name = names[i] if i < len(names) else "accent " + HUES[i - len(names)]
            self.hc = fp[2]
        for k, v in (spec.get("colors") or {}).items():   # "colors": {"accents": [...], "dark": "#..."} overrides
            self.t[k] = v
        for k in ("head", "body"):
            if (spec.get("fonts") or {}).get(k):
                self.t[k] = spec["fonts"][k]
        self.W, self.H = self.prs.slide_width / 914400, self.prs.slide_height / 914400
        self.M = 0.65 * self.W / 13.333 if self.W < 12 else 0.65
        self.kicker, self.n, self.sections, self.alt = "", 0, 0, 0

    # -------------------------------------------------------------------------------------------- template support
    def _drop_slides(self):
        lst = self.prs.slides._sldIdLst
        for s in list(lst):
            self.prs.part.drop_rel(s.rId)
            lst.remove(s)

    def _theme_from_template(self):
        t = dict(THEMES["light"], **FONTS)
        try:
            root = etree.fromstring(self.prs.slide_master.part.part_related_by(RT.THEME).blob)
            ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
            col = {}
            for el in root.find(".//a:clrScheme", ns):
                c = el[0]
                col[etree.QName(el).localname] = "#" + (c.get("val") if etree.QName(c).localname == "srgbClr" else c.get("lastClr", "000000"))
            maj = root.find(".//a:majorFont/a:latin", ns)
            mnr = root.find(".//a:minorFont/a:latin", ns)
            acc = [col[k] for k in ("accent1", "accent2", "accent3", "accent4", "accent5", "accent6") if k in col]
            if acc:
                t["accents"] = acc
            dark = col.get("dk2") or col.get("dk1") or t["dark"]
            t.update(dark=dark, dark2=mix(dark, "#FFFFFF", 0.08), on_dark="#FFFFFF", on_dark_muted=mix("#FFFFFF", dark, 0.35),
                     text=col.get("dk1", t["text"]), muted=mix(col.get("dk1", t["text"]), "#FFFFFF", 0.38),
                     surface=mix(acc[0] if acc else "#2A78D6", "#FFFFFF", 0.93), line=mix(col.get("dk1", "#000000"), "#FFFFFF", 0.85))
            if maj is not None and maj.get("typeface") and not maj.get("typeface").startswith("+"):
                t["head"] = maj.get("typeface")
            if mnr is not None and mnr.get("typeface") and not mnr.get("typeface").startswith("+"):
                t["body"] = mnr.get("typeface")
        except Exception as e:
            self.warn.append(f"template theme not read ({e}); built-in colours used")
        return t

    def layout(self, kind):
        """the template's layout for title / section / title-only / blank, else None (the slide is drawn)"""
        lays = list(self.prs.slide_layouts)
        def phs(l):
            return {p.placeholder_format.type for p in l.placeholders}
        from pptx.enum.shapes import PP_PLACEHOLDER as P
        if kind == "blank":
            return min(lays, key=lambda l: len(l.placeholders))
        if not self.template:
            return None
        for l in lays:
            name = l.name.lower()
            if kind == "title" and (P.CENTER_TITLE in phs(l) or "title slide" in name):
                return l
            if kind == "section" and ("section" in name):
                return l
            if kind == "titleonly" and ("title only" in name or (phs(l) == {P.TITLE} or phs(l) <= {P.TITLE, P.DATE, P.FOOTER, P.SLIDE_NUMBER}) and P.TITLE in phs(l)):
                return l
        return None

    # ---------------------------------------------------------------------------------------------------- drawing
    @property
    def bold(self):
        return self.style == "bold"

    def new(self, kind="blank", dark=False, fill=None):
        """a slide; dark: the theme's dark background (bold style: a gradient), fill: one colour"""
        lay = self.layout(kind) or self.layout("blank")
        s = self.prs.slides.add_slide(lay)
        self.n += 1
        if self.template and kind != "blank":
            return s
        if fill:
            s.background.fill.solid()
            s.background.fill.fore_color.rgb = rgb(fill)
        elif dark and self.bold and self.t["dark"] != "#FFFFFF":
            self.gradient(s.background.fill, self.t["dark"], mix(self.t["accents"][0], self.t["dark"], 0.45), 315)
        elif dark:
            s.background.fill.solid()
            s.background.fill.fore_color.rgb = rgb(self.t["dark"])
        return s

    @staticmethod
    def gradient(fill, a, b, angle):
        fill.gradient()
        fill.gradient_angle = angle
        st = fill.gradient_stops
        st[0].color.rgb, st[0].position = rgb(a), 0
        st[1].color.rgb, st[1].position = rgb(b), 1.0

    def shape(self, s, kind, x, y, w, h, fill=None, line=None, alpha=None, radius=None, width=1):
        sh = s.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
        st = sh._element.find(qn("p:style"))
        if st is not None:
            sh._element.remove(st)               # no theme shadow / outline: every look is explicit
        if fill:
            sh.fill.solid()
            sh.fill.fore_color.rgb = rgb(fill)
            if alpha is not None:
                clr = sh._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
                etree.SubElement(clr, qn("a:alpha")).set("val", str(int(alpha * 100000)))
                sh.name = "decor %d" % sh.shape_id                 # translucent decoration: may bleed off the slide
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line)
            sh.line.width = Pt(width)
        else:
            sh.line.fill.background()
        if radius is not None and len(sh.adjustments):
            sh.adjustments[0] = radius
        return sh

    def icon(self, s, name, x, y, size, color, weight=2.0):
        """a line icon (deck_icons) as one editable shape with custom geometry; None when the name is not an icon"""
        n = deck_icons.resolve(name)
        if not n:
            return None
        sh = self.shape(s, MSO_SHAPE.RECTANGLE, x, y, size, size)
        spPr = sh._element.spPr
        geo = etree.Element(qn("a:custGeom"))
        for tag in ("a:avLst", "a:gdLst", "a:ahLst", "a:cxnLst"):
            etree.SubElement(geo, qn(tag))
        r = etree.SubElement(geo, qn("a:rect"))
        for k, v in (("l", "l"), ("t", "t"), ("r", "r"), ("b", "b")):
            r.set(k, v)
        pl = etree.SubElement(geo, qn("a:pathLst"))
        for path in deck_icons.paths(n):
            p = etree.SubElement(pl, qn("a:path"), w="2400", h="2400", fill="none")
            for op in path:
                if op[0] == "Z":
                    etree.SubElement(p, qn("a:close"))
                    continue
                el = etree.SubElement(p, qn({"M": "a:moveTo", "L": "a:lnTo", "C": "a:cubicBezTo"}[op[0]]))
                for i in range(1, len(op), 2):
                    etree.SubElement(el, qn("a:pt"), x=str(int(round(op[i] * 100))), y=str(int(round(op[i + 1] * 100))))
        prst = spPr.find(qn("a:prstGeom"))
        spPr.replace(prst, geo)
        sh.line.color.rgb = rgb(color)
        sh.line.width = Pt(max(0.75, size * 72 * weight / 24 * 0.9))
        ln = spPr.find(qn("a:ln"))
        ln.set("cap", "rnd")
        etree.SubElement(ln, qn("a:round"))
        sh.name = "icon " + n
        return sh

    def badge(self, s, name, x, y, d, color, fill):
        """an icon in a filled circle; False when name is not an icon"""
        if not deck_icons.resolve(name):
            return False
        self.shape(s, MSO_SHAPE.OVAL, x, y, d, d, fill=fill)
        k = 0.56
        self.icon(s, name, x + d * (1 - k) / 2, y + d * (1 - k) / 2, d * k, color)
        return True

    def text(self, s, x, y, w, h, paras, size, color, font=None, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             spacing=1.15, gap=0.55, bullets=False, bullet_color=None, spc=None, italic=False, shape=None, alpha=None):
        """paras: [str | (str, level)]; returns the text frame"""
        box = shape or s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        tf.auto_size = None
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        for i, p in enumerate(paras):
            txt, lvl = (p if isinstance(p, tuple) else (p, 0))
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.alignment = align
            para.line_spacing = spacing
            if i:
                para.space_before = Pt(size * gap * (0.6 if lvl else 1))
            sz = size - 2 * lvl
            for part in re.split(r"(\*\*.+?\*\*)", str(txt)):
                if not part:
                    continue
                r = para.add_run()
                r.text = part[2:-2] if part.startswith("**") and part.endswith("**") else part
                f = r.font
                f.size, f.name = Pt(sz), font or self.t["body"]
                f.bold = bold or part.startswith("**")
                f.italic = italic
                f.color.rgb = rgb(color if not lvl else self.t["muted"] if color == self.t["text"] else color)
                if alpha is not None:
                    etree.SubElement(f._rPr.find(qn("a:solidFill")).find(qn("a:srgbClr")), qn("a:alpha")).set("val", str(int(alpha * 100000)))
                if spc:
                    f._rPr.set("spc", str(spc))
            if bullets:
                ind = 0.28 + 0.3 * lvl
                pPr = para._p.get_or_add_pPr()
                pPr.set("marL", str(Inches(ind)))
                pPr.set("indent", str(-Inches(0.26)))
                bc = etree.SubElement(pPr, qn("a:buClr"))
                etree.SubElement(bc, qn("a:srgbClr")).set("val", (bullet_color or self.t["accents"][0]).lstrip("#"))
                etree.SubElement(pPr, qn("a:buSzPct")).set("val", "100000")
                etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
                etree.SubElement(pPr, qn("a:buChar")).set("char", ("\u2022", "\u25AA", "\u203A")[self.look["bullet"]] if lvl == 0 else "\u2013")
        return tf

    def frame(self, s, sl, title=True, dark=False, left=None, width=None):
        """content slide chrome: kicker (current section), action title, footer and page number; returns content top.
        dark: on a dark background; left / width: the title column (a split slide)"""
        t, M = self.t, self.M
        top = 1.75
        if self.template and self.layout("titleonly"):
            ph = next((p for p in s.placeholders if p.placeholder_format.type in (1, 3)), None)
            if ph is not None:
                ph.text = plain(sl.get("title", ""))
                top = (ph.top + ph.height) / 914400 + 0.3
                return top
        x = M if left is None else left
        w = (self.W - 2 * M) if width is None else width
        ch = self.look["chrome"]
        if ch == 1 and not dark:                     # a thin accent strip along the top
            self.shape(s, MSO_SHAPE.RECTANGLE, 0, 0, self.W, 0.08, fill=t["accents"][0])
        elif ch == 2 and not dark:                   # a rule over the footer
            self.shape(s, MSO_SHAPE.RECTANGLE, M, self.H - 0.6, self.W - 2 * M, 0.012, fill=t["line"])
        fg, mu = (t["on_dark"], t["on_dark_muted"]) if dark else (t["text"], t["muted"])
        if self.kicker:
            k = self.kicker.upper()
            if self.bold:
                kw = min(w, len(k) * 10 * 0.68 / 72 + 0.36)
                pill = self.shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, 0.36, kw, 0.3, fill=t["accents"][0], radius=0.5)
                self.text(s, 0, 0, 0, 0, [k], 10, "#FFFFFF", font=t["head"], spc=120, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=pill)
            else:
                self.text(s, x, 0.42, w, 0.3, [k], 11, t["accents"][0] if not dark else t["on_dark_muted"], font=t["head"], spc=150)
        if title:
            ttl = sl.get("title", "")
            hi, lo = (34, 24) if self.bold else (30, 22)
            th = 3.0 if dark and width is not None else 1.0
            size, ok = fit([(ttl, 0)], w, th, hi, lo, spacing=1.05, char=self.hc)
            if not ok or len(plain(ttl)) > 90:
                self.warn.append(f"slide {self.n}: title is long ({len(plain(ttl))} characters); say it in one line")
            self.text(s, x, 0.78 if self.bold else 0.72, w, th, [ttl], size, fg, font=t["head"], spacing=1.05)
        foot = self.spec.get("footer") or plain(self.spec.get("title", ""))
        self.text(s, M, self.H - 0.45, self.W * 0.5 - M, 0.25, [foot], 10, mu)
        self.text(s, self.W - M - 1, self.H - 0.45, 1, 0.25, [str(self.n)], 10, mu if dark and width is None else t["muted"], align=PP_ALIGN.RIGHT)
        return top + (0.1 if self.bold else 0)

    # ------------------------------------------------------------------------------------------------ slide types
    def s_title(self, sl):
        t = self.t
        lay = self.layout("title")
        if lay is not None:
            s = self.prs.slides.add_slide(lay)
            self.n += 1
            for p in s.placeholders:
                ty = p.placeholder_format.type
                if ty in (1, 3):
                    p.text = plain(sl.get("title", ""))
                elif ty == 4 or p.placeholder_format.idx == 1:
                    p.text = plain(" · ".join(x for x in (sl.get("subtitle"), sl.get("meta")) if x))
            return s
        v = self.look["title"]
        W, H = self.W, self.H
        a = t["accents"]
        title = sl.get("title", "")
        meta = sl.get("meta") or dt.date.today().strftime("%B %Y")
        if v == 3:                                   # editorial: light page, an accent edge, very large type
            s = self.new(fill=t["bg"])
            self.shape(s, MSO_SHAPE.RECTANGLE, 0, 0, 0.32, H, fill=a[0])
            self.shape(s, MSO_SHAPE.OVAL, W - 4.4, H - 4.6, 6.0, 6.0, fill=a[1 % len(a)], alpha=0.10)
            self.shape(s, MSO_SHAPE.OVAL, W - 2.9, -1.4, 3.6, 3.6, fill=a[0], alpha=0.12)
            if sl.get("icon"):
                self.icon(s, sl["icon"], 1.1, 1.0, 0.7, a[0], weight=1.8)
            size, ok = fit([(title, 0)], 9.2, 2.6, 62, 38, spacing=0.98, char=self.hc)
            self.text(s, 1.1, 1.95, 9.2, 2.6, [title], size, t["text"], font=t["head"], spacing=0.98, anchor=MSO_ANCHOR.BOTTOM)
            self.shape(s, MSO_SHAPE.RECTANGLE, 1.1, 4.75, 1.4, 0.08, fill=a[0])
            if sl.get("subtitle"):
                self.text(s, 1.1, 5.0, 8.5, 0.9, [sl["subtitle"]], 22, t["muted"])
            self.text(s, 1.1, H - 0.9, 8, 0.4, [meta.upper()], 12, a[0], font=t["head"], spc=150)
        elif v == 2:                                 # split: the title on the dark side, a colour block with a tile pattern
            s = self.new(dark=True)
            bx = W * 0.64
            self.shape(s, MSO_SHAPE.RECTANGLE, bx, 0, W - bx, H, fill=a[0])
            k = 0.78
            for r in range(6):
                for c in range(4):
                    if (r + c) % 3 == 0:
                        self.shape(s, MSO_SHAPE.RECTANGLE, bx + 0.45 + c * (k + 0.12), 0.35 + r * (k + 0.12), k, k, fill="#FFFFFF", alpha=0.14)
            if sl.get("icon"):
                self.icon(s, sl["icon"], bx + (W - bx) / 2 - 0.9, H / 2 - 0.9, 1.8, "#FFFFFF", weight=1.4)
            size, ok = fit([(title, 0)], bx - 1.6, 2.6, 54, 34, spacing=0.98, char=self.hc)
            self.shape(s, MSO_SHAPE.RECTANGLE, 0.9, 1.95, 0.9, 0.08, fill=a[1 % len(a)])
            self.text(s, 0.9, 2.2, bx - 1.6, 2.6, [title], size, t["on_dark"], font=t["head"], spacing=0.98)
            ys = 2.2 + min(2.6, (lines_for(title, size, bx - 1.6, self.hc) * size * 0.98 + 40) / 72)
            if sl.get("subtitle"):
                self.text(s, 0.9, ys, bx - 1.8, 1.0, [sl["subtitle"]], 20, t["on_dark_muted"])
            self.text(s, 0.9, H - 1.0, bx - 1.5, 0.4, [meta], 13, t["on_dark_muted"], spc=60)
        elif v == 1:                                 # bands: diagonal colour bands and a dot
            s = self.new(dark=True)
            band = self.shape(s, MSO_SHAPE.RECTANGLE, W - 6.2, -2.0, 3.2, 11.5, fill=a[0], alpha=0.30)
            band.rotation = 24
            band2 = self.shape(s, MSO_SHAPE.RECTANGLE, W - 3.3, -2.0, 1.4, 11.5, fill=a[1 % len(a)], alpha=0.35)
            band2.rotation = 24
            self.shape(s, MSO_SHAPE.OVAL, W - 2.6, H - 2.4, 1.3, 1.3, fill=a[2 % len(a)], alpha=0.9)
            if sl.get("icon"):
                self.icon(s, sl["icon"], 0.9, 1.05, 0.75, a[0], weight=1.8)
            self.shape(s, MSO_SHAPE.RECTANGLE, 0.9, 2.25, 1.2, 0.1, fill=a[0])
            size, ok = fit([(title, 0)], 7.9, 2.4, 58, 36, spacing=0.98, char=self.hc)
            self.text(s, 0.9, 2.55, 7.9, 2.4, [title], size, t["on_dark"], font=t["head"], spacing=0.98)
            ys = 2.55 + min(2.4, (lines_for(title, size, 7.9, self.hc) * size * 0.98 + 48) / 72)
            if sl.get("subtitle"):
                self.text(s, 0.9, ys, 7.4, 1.0, [sl["subtitle"]], 22, t["on_dark_muted"])
            self.text(s, 0.9, H - 1.0, 8, 0.4, [meta], 13, t["on_dark_muted"], spc=60)
        else:                                        # circles: three translucent circles
            s = self.new(dark=True)
            self.shape(s, MSO_SHAPE.OVAL, W - 5.2, -1.6, 7.0, 7.0, fill=a[0], alpha=0.22)
            self.shape(s, MSO_SHAPE.OVAL, W - 3.4, 2.9, 5.2, 5.2, fill=a[1 % len(a)], alpha=0.18)
            self.shape(s, MSO_SHAPE.OVAL, W - 6.3, 4.6, 1.5, 1.5, fill=a[2 % len(a)], alpha=0.35)
            if sl.get("icon"):
                self.icon(s, sl["icon"], 0.9, 1.2, 0.7, a[0], weight=1.8)
            self.shape(s, MSO_SHAPE.RECTANGLE, 0.9, 2.35, 0.9, 0.08, fill=a[0])
            size, ok = fit([(title, 0)], 7.6, 2.2, 48, 32, spacing=1.0, char=self.hc)
            self.text(s, 0.9, 2.6, 7.6, 2.2, [title], size, t["on_dark"], font=t["head"], spacing=1.0)
            if sl.get("subtitle"):
                self.text(s, 0.9, 4.85, 7.4, 1.0, [sl["subtitle"]], 20, t["on_dark_muted"])
            self.text(s, 0.9, H - 1.0, 8, 0.4, [meta], 13, t["on_dark_muted"], spc=60)
        if not ok:
            self.warn.append(f"slide {self.n}: the deck title is long; keep it under about 8 words")
        return s

    def s_section(self, sl):
        t = self.t
        self.sections += 1
        self.kicker = plain(sl.get("title", ""))
        lay = self.layout("section")
        if lay is not None:
            s = self.prs.slides.add_slide(lay)
            self.n += 1
            for p in s.placeholders:
                if p.placeholder_format.type in (1, 3):
                    p.text = plain(sl.get("title", ""))
                elif sl.get("subtitle"):
                    p.text = plain(sl["subtitle"])
            return s
        a = t["accents"][0]
        v = self.look["section"]
        num = "%02d" % self.sections
        if v == 1:                                   # full colour, the number very large and faint
            s = self.new(fill=mix(a, "#000000", 0.18))
            self.text(s, self.W - 7.2, self.H - 5.4, 6.9, 4.6, [num], 260, "#FFFFFF", font=t["head"], align=PP_ALIGN.RIGHT,
                      spacing=0.8, alpha=0.16)
            self.shape(s, MSO_SHAPE.RECTANGLE, 0.95, 3.35, 1.2, 0.1, fill="#FFFFFF")
            if sl.get("icon"):
                self.icon(s, sl["icon"], 0.95, 2.2, 0.8, "#FFFFFF", weight=1.8)
            self.text(s, 0.95, 3.7, self.W - 2.5, 1.6, [sl.get("title", "")], 50, "#FFFFFF", font=t["head"], spacing=1.0)
            if sl.get("subtitle"):
                self.text(s, 0.95, 5.25, self.W - 2.5, 1.0, [sl["subtitle"]], 22, mix("#FFFFFF", a, 0.2))
            return s
        if v == 2:                                   # light: a big accent number, a rule, the title beside it
            s = self.new(fill=t["bg"])
            self.shape(s, MSO_SHAPE.RECTANGLE, 0, self.H - 0.18, self.W, 0.18, fill=a)
            self.text(s, 0.8, 1.6, 4.2, 3.6, [num], 200, a, font=t["head"], spacing=0.85, anchor=MSO_ANCHOR.MIDDLE)
            self.shape(s, MSO_SHAPE.RECTANGLE, 5.1, 2.0, 0.04, 3.0, fill=t["line"])
            if sl.get("icon"):
                self.icon(s, sl["icon"], 5.6, 2.0, 0.65, a, weight=1.8)
            self.text(s, 5.6, 2.85, self.W - 6.4, 1.5, [sl.get("title", "")], 44, t["text"], font=t["head"], spacing=1.0)
            if sl.get("subtitle"):
                self.text(s, 5.6, 4.35, self.W - 6.4, 0.9, [sl["subtitle"]], 20, t["muted"])
            return s
        s = self.new(dark=True)                      # classic: a side bar, the number in colour
        self.shape(s, MSO_SHAPE.RECTANGLE, 0, 0, 0.35, self.H, fill=a)
        self.text(s, 0.95, 1.35, 6, 2.2, [num], 120, a, font=t["head"], spacing=0.9)
        if sl.get("icon"):
            self.icon(s, sl["icon"], self.W - 2.2, 1.4, 1.1, a, weight=1.6)
        self.text(s, 0.95, 3.75, self.W - 2.5, 1.5, [sl.get("title", "")], 40, t["on_dark"], font=t["head"], spacing=1.0)
        if sl.get("subtitle"):
            self.text(s, 0.95, 5.15, self.W - 2.5, 1.0, [sl["subtitle"]], 20, t["on_dark_muted"])
        return s

    def s_agenda(self, sl):
        t = self.t
        s = self.new("titleonly")
        sl = dict(sl, title=sl.get("title") or "Agenda")
        top = self.frame(s, sl)
        items = sl.get("items", [])
        if len(items) > 7:
            self.warn.append(f"slide {self.n}: {len(items)} agenda items; keep it to 7 or fewer")
        if self.look["agenda"] == 1 and 3 <= len(items) <= 6:      # a grid of large numbers
            cols = 2 if len(items) == 4 else 3
            rows = math.ceil(len(items) / cols)
            cw = (self.W - 2 * self.M - 0.4 * (cols - 1)) / cols
            rh = min(2.2, (self.H - 1.0 - top) / rows)
            for i, it in enumerate(items):
                x = self.M + (i % cols) * (cw + 0.4)
                y = top + 0.1 + (i // cols) * rh
                c = t["accents"][i % len(t["accents"])]
                self.shape(s, MSO_SHAPE.RECTANGLE, x, y, cw, 0.03, fill=c)
                self.text(s, x, y + 0.15, cw, 0.9, ["%02d" % (i + 1)], 40, c, font=t["head"])
                self.text(s, x, y + 1.05, cw, rh - 1.15, [it], 22, t["text"], font=t["head"], spacing=1.1)
            return s
        n = max(1, len(items))
        rows = min(n, 7)
        avail = self.H - 0.8 - top
        row = min(0.82, avail / rows)
        for i, it in enumerate(items[:7]):
            y = top + i * row
            c = t["accents"][i % len(t["accents"])]
            self.shape(s, MSO_SHAPE.OVAL, self.M, y + (row - 0.52) / 2, 0.52, 0.52, fill=c)
            self.text(s, self.M, y + (row - 0.52) / 2, 0.52, 0.52, [str(i + 1)], 16, "#FFFFFF", font=t["head"], align=PP_ALIGN.CENTER,
                      anchor=MSO_ANCHOR.MIDDLE)
            self.text(s, self.M + 0.85, y, self.W - 2 * self.M - 0.85, row, [it], 22, t["text"], anchor=MSO_ANCHOR.MIDDLE)
            if i < rows - 1:
                self.shape(s, MSO_SHAPE.RECTANGLE, self.M + 0.85, y + row - 0.01, self.W - 2 * self.M - 0.85, 0.012, fill=t["line"])
        return s

    def s_cards(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        cards = sl.get("cards", [])
        if not 2 <= len(cards) <= 6:
            self.warn.append(f"slide {self.n}: {len(cards)} cards; 2-6 look right")
        v = self.look["cards"]
        cols = len(cards) if len(cards) <= 4 else 3
        rows = math.ceil(max(1, len(cards)) / cols)
        cw = (self.W - 2 * self.M - 0.3 * (cols - 1)) / cols
        need = max([(2.85 if deck_icons.resolve(c.get("icon")) else 2.45) + 16 * 1.25 * lines_for(c.get("text", ""), 16, cw - 0.6) / 72 for c in cards] or [3])
        avail = self.H - 0.85 - (top + 0.05)
        ch_ = min(avail, max(3.0, need) * rows + 0.3 * (rows - 1))
        y0 = top + 0.05 + (avail - ch_) / 2 * 0.6
        cells = self.grid(max(1, len(cards)), y0, y0 + ch_, max_cols=4 if len(cards) == 4 else 3)
        for i, (c, (x, y, w, h)) in enumerate(zip(cards, cells)):
            col = t["accents"][i % len(t["accents"])]
            icon = c.get("icon")
            has_icon = bool(deck_icons.resolve(icon))
            if v == 1:                               # outlined, a colour band on top
                self.shape(s, MSO_SHAPE.RECTANGLE, x, y, w, h, fill=t["bg"], line=t["line"])
                self.shape(s, MSO_SHAPE.RECTANGLE, x, y, w, 0.12, fill=col)
                ic, bg = "#FFFFFF", col
            elif v == 2:                             # tinted with the card's own colour
                self.shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=mix(col, "#FFFFFF", 0.9), radius=0.08)
                ic, bg = "#FFFFFF", col
            else:                                    # quiet surface
                self.shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=t["surface"], radius=0.06)
                if not has_icon:
                    self.shape(s, MSO_SHAPE.RECTANGLE, x + 0.3, y + 0.3, 0.5, 0.06, fill=col)
                ic, bg = col, mix(col, "#FFFFFF", 0.84)
            compact = h < 2.9
            badge = icon or c.get("value") or str(i + 1)
            d = 0.62 if compact else 0.82
            iy = y + (0.42 if v == 1 else 0.32)
            if has_icon:
                self.badge(s, icon, x + 0.3, iy, d, ic, bg)
            if compact:
                bx = x + 0.3
                if has_icon:
                    bx += d + 0.2
                else:
                    self.text(s, bx, iy + 0.1, 0.9, 0.5, [badge], 20 if len(badge) <= 3 else 14, col, font=t["head"], anchor=MSO_ANCHOR.MIDDLE)
                    bx += 0.55 if len(badge) <= 2 else 1.0
                self.text(s, bx, iy, x + w - 0.3 - bx, d, [c.get("title", "")], 18, t["text"], font=t["head"], anchor=MSO_ANCHOR.MIDDLE)
                ty = iy + d + 0.2
            else:
                if not has_icon:
                    self.text(s, x + 0.3, y + 0.5, w - 0.6, 0.6, [badge], 26 if len(badge) <= 3 else 18, col, font=t["head"])
                elif c.get("value"):
                    self.text(s, x + 0.3 + d + 0.2, iy, w - d - 0.8, d, [c["value"]], 22, col, font=t["head"], anchor=MSO_ANCHOR.MIDDLE)
                hy = iy + d + 0.3 if has_icon else y + 1.15
                hs, _ = fit([(c.get("title", ""), 0)], w - 0.6, 0.8, 20, 15, char=self.hc)
                self.text(s, x + 0.3, hy, w - 0.6, 0.8, [c.get("title", "")], hs, mix(col, "#000000", 0.25) if v == 2 else t["text"],
                          font=t["head"], spacing=1.05)
                ty = hy + 0.75
            bh = y + h - 0.25 - ty
            size, ok = fit([(c.get("text", ""), 0)], w - 0.6, bh, 16, 11, spacing=1.2)
            if not ok:
                self.warn.append(f"slide {self.n}: card {i + 1} text is long; one or two sentences")
            self.text(s, x + 0.3, ty, w - 0.6, bh, [c.get("text", "")], size, t["muted"] if v != 2 else t["text"], spacing=1.2)
        return s

    def s_stats(self, sl):
        t = self.t
        v = self.look["stats"]
        stats = sl.get("stats", [])
        if v == 2 and len(stats) >= 2 and not self.template:
            return self.stats_lead(sl, stats)
        dark = self.bold and not self.template and v == 0
        s = self.new("titleonly", dark=dark)
        top = self.frame(s, sl, dark=dark)
        if not 1 <= len(stats) <= 4:
            self.warn.append(f"slide {self.n}: {len(stats)} numbers; 2-4 read best")
        n = max(1, len(stats))
        fg, mu, ln = (t["on_dark"], t["on_dark_muted"], mix(t["dark"], "#FFFFFF", 0.2)) if dark else (t["text"], t["muted"], t["line"])
        bottom = self.H - (1.6 if sl.get("note") else 0.9)
        gap = 0.3 if v == 1 else 0
        w = (self.W - 2 * self.M - gap * (n - 1)) / n
        icons = any(deck_icons.resolve(st.get("icon")) for st in stats)
        y = top + (bottom - top) / 2 - (1.75 if icons else 1.3)
        vs = min([fit([(str(st.get("value", "")), 0)], w - 0.7, 1.2, 72 if self.bold else 66, 34, char=0.6)[0] for st in stats] or [60])
        for i, st in enumerate(stats):
            x = self.M + i * (w + gap)
            col = t["accents"][i % len(t["accents"])] if sl.get("colorful") or self.bold or v == 1 else t["accents"][0]
            yy = y
            if v == 1:                               # tiles
                self.shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y - 0.3, w, (bottom - y) + 0.1, fill=t["surface"], radius=0.06)
                self.shape(s, MSO_SHAPE.RECTANGLE, x, y - 0.3, 0.08, (bottom - y) + 0.1, fill=col)
            elif i:
                self.shape(s, MSO_SHAPE.RECTANGLE, x, y + 0.1, 0.015, 2.4 + (0.9 if icons else 0), fill=ln)
            if icons:
                if deck_icons.resolve(st.get("icon")):
                    self.icon(s, st["icon"], x + 0.35, yy, 0.6, col)
                yy += 0.9
            val = str(st.get("value", ""))
            self.text(s, x + 0.35, yy, w - 0.6, 1.3, [val], vs, "#FFFFFF" if dark and self.bold and i == 0 else col, font=t["head"],
                      spacing=0.95, anchor=MSO_ANCHOR.BOTTOM)
            self.text(s, x + 0.35, yy + 1.45, w - 0.6, 0.8, [st.get("label", "")], 16, fg, spacing=1.1)
            self.stat_extras(s, st, x, yy + 2.15, w, col, ln)
        if sl.get("note"):
            self.shape(s, MSO_SHAPE.RECTANGLE, self.M, self.H - 1.45, self.W - 2 * self.M, 0.012, fill=ln)
            self.text(s, self.M, self.H - 1.3, self.W - 2 * self.M, 0.5, [sl["note"]], 15, mu)
        return s

    def stat_extras(self, s, st, x, ny, w, col, ln):
        """the progress bar and the delta under a number"""
        if st.get("progress") is not None:
            pv = st["progress"]
            pv = float(str(pv).rstrip("%")) / (100 if str(pv).endswith("%") or float(str(pv).rstrip("%")) > 1 else 1)
            pv = max(0.0, min(1.0, pv))
            bw = min(w - 0.7, 2.6)
            self.shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.35, ny + 0.05, bw, 0.1, fill=ln, radius=0.5)
            bar = BAD if st.get("good") is False and pv >= 0.8 else col
            if pv > 0:
                self.shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.35, ny + 0.05, max(0.1, bw * pv), 0.1, fill=bar, radius=0.5)
            ny += 0.35
        if st.get("delta"):
            d = str(st["delta"])
            good = st.get("good", not d.strip().startswith("-"))
            arrow = "▲ " if not d.strip().startswith("-") else "▼ "
            self.text(s, x + 0.35, ny, w - 0.6, 0.4, [arrow + d.lstrip("+-")], 14, GOOD if good else BAD, font=self.t["head"])

    def stats_lead(self, sl, stats):
        """the first number very large on the left, the others as rows on the right"""
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        if len(stats) > 5:
            self.warn.append(f"slide {self.n}: {len(stats)} numbers; 2-5 read best")
        bottom = self.H - (1.6 if sl.get("note") else 0.9)
        a = t["accents"][0]
        lw = (self.W - 2 * self.M) * 0.46
        first, rest = stats[0], stats[1:]
        self.shape(s, MSO_SHAPE.RECTANGLE, self.M, top, lw, bottom - top, fill=t["dark"] if t["dark"] != "#FFFFFF" else a)
        y = top + 0.45
        if deck_icons.resolve(first.get("icon")):
            self.icon(s, first["icon"], self.M + 0.45, y, 0.7, a if t["dark"] != "#FFFFFF" else "#FFFFFF")
            y += 0.95
        vs, _ = fit([(str(first.get("value", "")), 0)], lw - 0.9, 1.8, 110, 48, char=0.6)
        self.text(s, self.M + 0.45, y, lw - 0.9, 1.9, [str(first.get("value", ""))], vs, "#FFFFFF", font=t["head"], spacing=0.9,
                  anchor=MSO_ANCHOR.BOTTOM)
        self.text(s, self.M + 0.45, y + 2.0, lw - 0.9, 0.9, [first.get("label", "")], 20, mix("#FFFFFF", t["dark"], 0.2), spacing=1.1)
        self.stat_extras(s, first, self.M + 0.1, y + 2.9, lw, a, mix(t["dark"], "#FFFFFF", 0.25))
        rx = self.M + lw + 0.5
        rw = self.W - self.M - rx
        rh = (bottom - top) / max(1, len(rest))
        for i, st in enumerate(rest):
            yy = top + i * rh
            col = t["accents"][(i + 1) % len(t["accents"])]
            if i:
                self.shape(s, MSO_SHAPE.RECTANGLE, rx, yy, rw, 0.012, fill=t["line"])
            ix = rx
            if deck_icons.resolve(st.get("icon")):
                self.badge(s, st["icon"], rx, yy + (rh - 0.62) / 2, 0.62, col, mix(col, "#FFFFFF", 0.84))
                ix += 0.85
            vw = min(2.6, rw * 0.42)
            vs2, _ = fit([(str(st.get("value", "")), 0)], vw, rh * 0.7, 40, 22, char=0.6)
            self.text(s, ix, yy, vw, rh, [str(st.get("value", ""))], vs2, col, font=t["head"], anchor=MSO_ANCHOR.MIDDLE)
            lab = st.get("label", "") + ("  ·  " + str(st["delta"]) if st.get("delta") else "")
            self.text(s, ix + vw + 0.2, yy, rx + rw - ix - vw - 0.2, rh, [lab], 16, t["text"], anchor=MSO_ANCHOR.MIDDLE, spacing=1.1)
        if sl.get("note"):
            self.text(s, self.M, self.H - 1.3, self.W - 2 * self.M, 0.5, [sl["note"]], 15, t["muted"])
        return s

    def takeaway(self, s, x, y, w, h, text, label="Key point", filled=False, icon=None):
        t = self.t
        a = t["accents"][0]
        fg = "#FFFFFF" if filled else t["text"]
        if filled:
            self.shape(s, MSO_SHAPE.RECTANGLE, x, y, w, h, fill=a)
        else:
            self.shape(s, MSO_SHAPE.RECTANGLE, x, y, w, h, fill=t["surface"])
            self.shape(s, MSO_SHAPE.RECTANGLE, x, y, 0.07, h, fill=a)
        ty = y + 0.35
        if icon and deck_icons.resolve(icon):
            self.icon(s, icon, x + 0.35, ty, 0.55, fg if filled else a)
            ty += 0.8
        self.text(s, x + 0.35, ty, w - 0.6, 0.3, [label.upper()], 11, mix("#FFFFFF", a, 0.25) if filled else a, font=t["head"], spc=120)
        size, ok = fit([(text, 0)], w - 0.7, h - (ty - y) - 0.8, 26 if filled else 24, 15, spacing=1.2)
        if not ok:
            self.warn.append(f"slide {self.n}: the takeaway is long; one or two sentences")
        self.text(s, x + 0.35, ty + 0.45, w - 0.7, h - (ty - y) - 0.8, [text], size, fg, font=t["head"], spacing=1.2)

    def s_bullets(self, sl):
        t = self.t
        items = sl.get("bullets", [])
        if len(items) > 6:
            self.warn.append(f"slide {self.n + 1}: {len(items)} bullets; keep 3-6 (split the slide or use cards)")
        self.alt += 1
        if self.bold and not self.template and (self.alt % 2 == 0 or not sl.get("takeaway")):
            # split: the title on a dark column at the left, the points at the right
            s = self.new("titleonly")
            cw = self.W * 0.36
            self.shape(s, MSO_SHAPE.RECTANGLE, 0, 0, cw, self.H, fill=t["dark"] if t["dark"] != "#FFFFFF" else t["accents"][0])
            self.frame(s, sl, dark=True, left=self.M, width=cw - 2 * self.M + 0.2)
            if sl.get("icon"):
                self.icon(s, sl["icon"], self.M, self.H - 2.2, 0.7, t["accents"][0], weight=1.8)
            x = cw + 0.6
            paras = items + ([{"text": "**" + plain(sl["takeaway"]) + "**"}] if sl.get("takeaway") else [])
            self.body(s, x, 1.0, self.W - x - self.M, self.H - 1.85, paras, hi=28, what="the bullets", anchor=MSO_ANCHOR.MIDDLE)
            return s
        s = self.new("titleonly")
        panel = bool(sl.get("takeaway")) and self.bold and not self.template
        top = self.frame(s, sl, width=self.W * 0.64 - self.M - 0.4 if panel else None)
        bottom = self.H - 0.85
        if sl.get("takeaway"):
            if panel:
                tx = self.W * 0.64
                self.body(s, self.M, top + 0.1, tx - self.M - 0.5, bottom - top - 0.1, items, what="the bullets")
                self.takeaway(s, tx, 0, self.W - tx, self.H, sl["takeaway"], filled=True, icon=sl.get("icon"))
                return s
            w = (self.W - 2 * self.M) * 0.58
            self.body(s, self.M, top + 0.1, w, bottom - top - 0.1, items, what="the bullets")
            tx = self.M + w + 0.5
            self.takeaway(s, tx, top, self.W - self.M - tx, bottom - top, sl["takeaway"], icon=sl.get("icon"))
        else:
            self.body(s, self.M, top + 0.1, self.W - 2 * self.M - 1.5, bottom - top - 0.1, items, hi=24, what="the bullets")
        return s

    def s_hero(self, sl):
        """one big number or statement on a full-colour slide"""
        t = self.t
        a = t["accents"][0]
        s = self.new(fill=mix(a, "#000000", 0.18)) if self.bold else self.new(dark=True)
        fg = "#FFFFFF" if self.bold else t["on_dark"]
        mu = mix("#FFFFFF", a, 0.25) if self.bold else t["on_dark_muted"]
        big = a if not self.bold and t["dark"] != "#FFFFFF" else fg
        if self.bold:
            self.shape(s, MSO_SHAPE.OVAL, self.W - 4.5, -2.2, 7.0, 7.0, fill="#FFFFFF", alpha=0.07)
            self.shape(s, MSO_SHAPE.OVAL, self.W - 2.6, 3.6, 4.6, 4.6, fill="#FFFFFF", alpha=0.06)
        if self.kicker:
            self.text(s, 0.95, 0.6, 8, 0.3, [self.kicker.upper()], 11, mu, font=t["head"], spc=150)
        y = 1.45
        if deck_icons.resolve(sl.get("icon")):
            self.icon(s, sl["icon"], 0.95, y, 0.8, fg if self.bold else a, weight=1.8)
            y += 1.05
        val = str(sl.get("value", ""))
        vs, _ = fit([(val, 0)], self.W - 1.9, 2.4, 170, 60, spacing=0.9, char=0.62)
        self.text(s, 0.95, y, self.W - 1.9, 2.5, [val], vs, big, font=t["head"], spacing=0.9, anchor=MSO_ANCHOR.BOTTOM)
        size, ok = fit([(sl.get("text", ""), 0)], self.W - 3, 1.3, 32, 20, spacing=1.15)
        if not ok:
            self.warn.append(f"slide {self.n}: the statement is long; one sentence under the number")
        self.text(s, 0.95, y + 2.7, self.W - 3, 1.3, [sl.get("text", "")], size, fg, font=t["head"], spacing=1.15)
        if sl.get("sub"):
            self.text(s, 0.95, y + 4.05, self.W - 3, 0.8, [sl["sub"]], 17, mu)
        return s

    def s_iconlist(self, sl):
        """points with an icon each: [{icon, title, text}], 2-6 (two columns from 4)"""
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        items = sl.get("items", [])
        if not 2 <= len(items) <= 6:
            self.warn.append(f"slide {self.n}: {len(items)} items; 2-6 fit")
        cols = 2 if len(items) >= 4 else 1
        rows = math.ceil(max(1, len(items)) / cols)
        gap = 0.5
        cw = (self.W - 2 * self.M - gap * (cols - 1)) / cols
        rh = min(1.45, (self.H - 0.9 - top) / rows)
        for i, it in enumerate(items):
            col = t["accents"][i % len(t["accents"])] if sl.get("colorful", self.bold) else t["accents"][0]
            x = self.M + (i % cols) * (cw + gap)
            y = top + (i // cols) * rh
            d = 0.72
            if not self.badge(s, it.get("icon"), x, y + 0.05, d, "#FFFFFF" if self.bold else col, col if self.bold else mix(col, "#FFFFFF", 0.84)):
                self.shape(s, MSO_SHAPE.OVAL, x, y + 0.05, d, d, fill=col)
                self.text(s, x, y + 0.05, d, d, [str(i + 1)], 18, "#FFFFFF", font=t["head"], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            tx = x + d + 0.3
            self.text(s, tx, y + 0.02, cw - d - 0.3, 0.45, [it.get("title", "")], 20, t["text"], font=t["head"])
            size, ok = fit([(it.get("text", ""), 0)], cw - d - 0.3, rh - 0.65, 16, 12, spacing=1.2)
            if not ok:
                self.warn.append(f"slide {self.n}: item {i + 1} text is long; one sentence")
            self.text(s, tx, y + 0.5, cw - d - 0.3, rh - 0.6, [it.get("text", "")], size, t["muted"], spacing=1.2)
        return s

    # ------------------------------------------------------------------------------------------------------ charts
    @staticmethod
    def nice(v):
        """a round axis maximum at or above v, and its tick step (5 ticks)"""
        if v <= 0:
            return 1.0, 0.2
        step = 10 ** math.floor(math.log10(v / 5))
        for m in (1, 2, 2.5, 5, 10):
            if v / (m * step) <= 5:
                return m * step * 5, m * step
        return v, v / 5

    @staticmethod
    def plot_layout(ch, x, y, w, h):
        """the inner plot area at fixed fractions of the chart frame, so lines drawn over it land on the axis values"""
        pa = ch._chartSpace.chart.plotArea
        lay = pa.find(qn("c:layout"))
        if lay is None:
            lay = etree.Element(qn("c:layout"))
            pa.insert(0, lay)
        for c in list(lay):
            lay.remove(c)
        ml = etree.SubElement(lay, qn("c:manualLayout"))
        for tag, val in (("layoutTarget", "inner"), ("xMode", "edge"), ("yMode", "edge"), ("x", x), ("y", y), ("w", w), ("h", h)):
            etree.SubElement(ml, qn("c:" + tag)).set("val", str(round(val, 4)) if isinstance(val, float) else str(val))

    @staticmethod
    def number_format(values, unit=""):
        vals = [abs(v) for v in values if v is not None]
        mx = max(vals or [0])
        if any(v % 1 for v in vals):
            f = "#,##0.0" if mx < 1000 else "#,##0"
        elif mx >= 10_000_000:
            f = '#,##0.0,,"M"'
        elif mx >= 100_000:
            f = '#,##0,"k"'
        else:
            f = "#,##0"
        return f, (f + f'"{usep(unit)}"' if unit else f)

    def chart(self, s, x, y, w, h, c):
        t = self.t
        kinds = {"column": XL_CHART_TYPE.COLUMN_CLUSTERED, "bar": XL_CHART_TYPE.BAR_CLUSTERED,
                 "stacked": XL_CHART_TYPE.COLUMN_STACKED, "stacked_bar": XL_CHART_TYPE.BAR_STACKED,
                 "line": XL_CHART_TYPE.LINE_MARKERS, "area": XL_CHART_TYPE.AREA,
                 "pie": XL_CHART_TYPE.PIE, "doughnut": XL_CHART_TYPE.DOUGHNUT}
        kind = c.get("kind", "column")
        if kind not in kinds:
            raise SystemExit(f"deck: slide {self.n}: chart kind {kind!r}; one of {', '.join(kinds)}")
        cats, series = [str(v) for v in c.get("categories", [])], c.get("series", [])
        if not cats or not series:
            raise SystemExit(f"deck: slide {self.n}: a chart needs categories and series")
        cd = CategoryChartData()
        cd.categories = cats
        allv = []
        for se in series:
            vals = se.get("values", [])
            if len(vals) != len(cats):
                raise SystemExit(f"deck: slide {self.n}: series {se.get('name')!r} has {len(vals)} values for {len(cats)} categories")
            fv = [None if v is None else float(v) for v in vals]
            allv += [v for v in fv if v is not None]
            cd.add_series(se.get("name", ""), fv)
        if len(series) > 5:
            self.warn.append(f"slide {self.n}: {len(series)} series; more than 5 colours is hard to read")
        if kind in ("pie", "doughnut") and len(cats) > 6:
            self.warn.append(f"slide {self.n}: {len(cats)} slices; a pie reads up to 6 (use a bar chart)")
        gf = s.shapes.add_chart(kinds[kind], Inches(x), Inches(y), Inches(w), Inches(h), cd)
        ch = gf.chart
        ch.has_title = False
        ch.font.size, ch.font.name = Pt(12), t["body"]
        ch.font.color.rgb = rgb(t["muted"])
        pal = t["accents"]
        hl = c.get("highlight")
        plot = ch.plots[0]
        unit = c.get("unit", "")
        fmt, axis_fmt = (c["format"], c["format"]) if c.get("format") else self.number_format(allv, unit)
        if kind in ("pie", "doughnut"):
            for i, pt in enumerate(plot.series[0].points):
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = rgb(pal[i % len(pal)])
                pt.format.line.color.rgb = rgb(t["bg"])
                pt.format.line.width = Pt(2.5)
            plot.has_data_labels = True
            dl = plot.data_labels
            dl.show_percentage, dl.show_value, dl.show_category_name = True, False, False
            dl.number_format, dl.number_format_is_linked = "0%", False
            dl.font.size, dl.font.bold = Pt(13), True
            dl.font.color.rgb = rgb("#FFFFFF")
            side = min(w * 0.58, h * 0.94)
            self.plot_layout(ch, 0.03, (h - side) / 2 / h, side / w, side / h)
            if kind == "doughnut":
                hole = ch._chartSpace.find(".//" + qn("c:holeSize"))
                if hole is not None:
                    hole.set("val", "62")
                total = c.get("center")
                if total is None:
                    tv = sum(allv[:len(cats)])
                    total = (f"{tv:,.1f}" if tv % 1 else f"{tv:,.0f}") + (usep(unit) if unit else "")
                cx, cy = x + w * 0.03 + side / 2, y + h / 2
                self.text(s, cx - side * 0.3, cy - 0.5, side * 0.6, 0.6, [str(total)], 26, t["text"], font=t["head"], align=PP_ALIGN.CENTER,
                          anchor=MSO_ANCHOR.BOTTOM)
                self.text(s, cx - side * 0.3, cy + 0.12, side * 0.6, 0.4, [c.get("center_label", "total")], 12, t["muted"], align=PP_ALIGN.CENTER)
            ch.has_legend = True
            ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.RIGHT, False
            ch.legend.font.size = Pt(14)
            ch.legend.font.color.rgb = rgb(t["text"])
            return gf
        stacked = kind.startswith("stacked")
        horizontal = kind in ("bar", "stacked_bar")
        direct = kind == "line" and len(series) <= 5 and c.get("direct", True)
        for i, se in enumerate(plot.series):
            col = pal[i % len(pal)]
            if kind == "line":
                se.format.line.color.rgb = rgb(col)
                se.format.line.width = Pt(3)
                se.smooth = bool(c.get("smooth"))
                se.marker.style = XL_MARKER_STYLE.NONE
                last = max(j for j, v in enumerate(series[i]["values"]) if v is not None)
                pt = se.points[last]
                pt.marker.style, pt.marker.size = XL_MARKER_STYLE.CIRCLE, 9
                pt.marker.format.fill.solid()
                pt.marker.format.fill.fore_color.rgb = rgb(col)
                pt.marker.format.line.color.rgb = rgb(t["bg"])
                pt.marker.format.line.width = Pt(1.5)
                if direct:                                 # the series named at its last value: no legend to look up
                    v = float(series[i]["values"][last])
                    dl = pt.data_label
                    dl.has_text_frame = True
                    dl.text_frame.text = f"{series[i].get('name', '')}  " + (f"{v:,.1f}" if v % 1 else f"{v:,.0f}") + (usep(unit) if unit else "")
                    dl.position = XL_LABEL_POSITION.RIGHT
                    dl.font.size, dl.font.bold = Pt(12), True
                    dl.font.color.rgb = rgb(col)
            elif kind == "area":
                se.format.fill.solid()
                se.format.fill.fore_color.rgb = rgb(mix(col, "#FFFFFF", 0.35 if len(series) > 1 else 0.15))
            else:
                se.format.fill.solid()
                se.format.fill.fore_color.rgb = rgb(col)
                if hl is not None and len(series) == 1:
                    idx = cats.index(str(hl)) if str(hl) in cats else int(hl) if str(hl).isdigit() else -1
                    for j, pt in enumerate(se.points):
                        pt.format.fill.solid()
                        pt.format.fill.fore_color.rgb = rgb(col if j == idx else mix(col, "#FFFFFF", 0.62))
        if kind not in ("line", "area"):
            plot.gap_width = 50 if len(series) == 1 else 80
            if stacked:
                plot.overlap = 100
        va, ca = ch.value_axis, ch.category_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = rgb(t["line"])
        va.major_gridlines.format.line.width = Pt(0.75)
        va.format.line.fill.background()
        va.major_tick_mark = va.minor_tick_mark = XL_TICK_MARK.NONE
        ca.major_tick_mark = ca.minor_tick_mark = XL_TICK_MARK.NONE
        va.tick_labels.font.size = Pt(11)
        va.tick_labels.number_format = axis_fmt
        va.tick_labels.number_format_is_linked = False
        ca.format.line.color.rgb = rgb(mix(t["line"], t["text"], 0.25))
        ca.tick_labels.font.size = Pt(12)
        ca.tick_labels.font.color.rgb = rgb(t["text"])
        ca.has_major_gridlines = False
        if horizontal:
            ca.reverse_order = True                    # first category on top, as it is read
        # a fixed scale: round numbers, and a target line that lands on its value
        if stacked:
            top_v = max(sum(float(se["values"][j] or 0) for se in series) for j in range(len(cats)))
        else:
            top_v = max(allv or [0])
        target = c.get("target")
        vmin = float(c["min"]) if c.get("min") is not None else min(0.0, min(allv or [0]))
        want = max(top_v, float(target) if target is not None else top_v) * (1.12 if kind in ("column", "bar") else 1.04)
        vmax, step = (float(c["max"]), None) if c.get("max") is not None else self.nice(want - vmin)
        if c.get("max") is None:
            vmax += vmin
        va.minimum_scale, va.maximum_scale = vmin, vmax
        if step:
            va.major_unit = step
        labels = c.get("labels", len(series) == 1 and len(cats) <= 8 and kind in ("column", "bar"))
        if labels:
            plot.has_data_labels = True
            dl = plot.data_labels
            dl.number_format, dl.number_format_is_linked = fmt + (f'"{usep(unit)}"' if unit else ""), False
            dl.font.size, dl.font.bold = Pt(12), True
            dl.font.color.rgb = rgb(t["text"])
            if kind in ("column", "bar"):
                dl.position = XL_LABEL_POSITION.OUTSIDE_END
                va.has_major_gridlines = False
                va.visible = False
        ch.has_legend = len(series) > 1 and not direct
        if ch.has_legend:
            ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.TOP, False
            ch.legend.font.size = Pt(12)
            ch.legend.font.color.rgb = rgb(t["text"])
        longest = max(len(cc) for cc in cats)
        axis_room = 0.0 if (labels and kind in ("column", "bar")) else 0.075
        if horizontal:
            left = min(0.32, 0.03 + longest * 12 * 0.55 / 72 / w)
            bottom = 0.02 if not axis_room else 0.09
        else:
            left = axis_room or 0.02
            bottom = 0.1
        topm = 0.11 if ch.has_legend else 0.05
        right = 0.2 if direct else 0.03
        pw, ph = 1 - left - right, 1 - topm - bottom
        self.plot_layout(ch, left, topm, pw, ph)
        if target is not None:
            T = float(target)
            px, py, pww, phh = x + left * w, y + topm * h, pw * w, ph * h
            lab = c.get("target_label") or ("Target " + (f"{T:,.1f}" if T % 1 else f"{T:,.0f}") + (usep(unit) if unit else ""))
            tc = c.get("target_color") or (BAD if c.get("target_bad", True) else t["text"])
            if horizontal:
                xx = px + pww * (T - vmin) / (vmax - vmin)
                ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(xx), Inches(py), Inches(xx), Inches(py + phh))
                self.text(s, xx - 1.5, py - 0.32, 3.0, 0.3, [lab], 11, tc, font=t["head"], align=PP_ALIGN.CENTER)
            else:
                yy = py + phh * (1 - (T - vmin) / (vmax - vmin))
                ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(px), Inches(yy), Inches(px + pww), Inches(yy))
                self.text(s, px + 0.1, yy - 0.32, 3.0, 0.28, [lab], 11, tc, font=t["head"])
            ln.line.color.rgb = rgb(tc)
            ln.line.width = Pt(1.75)
            ln.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            ln.name = "target line"
        return gf

    def s_chart(self, sl):
        t = self.t
        s = self.new("titleonly")
        panel = bool(sl.get("takeaway")) and self.bold and not self.template
        top = self.frame(s, sl, width=self.W * 0.68 - self.M - 0.4 if panel else None)
        bottom = self.H - 0.8
        c = sl.get("chart") or {}
        if sl.get("takeaway"):
            if panel:
                tx = self.W * 0.68
                self.chart(s, self.M - 0.1, top, tx - self.M - 0.3, bottom - top, c)
                self.takeaway(s, tx, 0, self.W - tx, self.H, sl["takeaway"], label=sl.get("label", "What it shows"), filled=True, icon=sl.get("icon"))
            else:
                w = (self.W - 2 * self.M) * 0.66
                self.chart(s, self.M - 0.1, top, w, bottom - top, c)
                tx = self.M + w + 0.4
                self.takeaway(s, tx, top, self.W - self.M - tx, bottom - top, sl["takeaway"], label=sl.get("label", "What it shows"), icon=sl.get("icon"))
        else:
            self.chart(s, self.M - 0.1, top, self.W - 2 * self.M + 0.2, bottom - top, c)
        if c.get("source"):
            self.text(s, self.M, self.H - 0.78, self.W * 0.6 - self.M, 0.25, ["Source: " + c["source"]], 10, t["muted"], italic=True)
        return s

    # ------------------------------------------------------------------------------------------------------ tables
    STATUS = {"ok": GOOD, "healthy": GOOD, "online": GOOD, "up": GOOD, "normal": GOOD, "pass": GOOD, "passed": GOOD, "done": GOOD,
              "green": GOOD, "active": GOOD, "in sync": GOOD, "synced": GOOD, "compliant": GOOD,
              "warning": "#C98500", "warn": "#C98500", "degraded": "#C98500", "amber": "#C98500", "at risk": "#C98500",
              "pending": "#C98500", "lagging": "#C98500", "minor": "#C98500", "major": "#E5604D",
              "critical": BAD, "failed": BAD, "fail": BAD, "down": BAD, "error": BAD, "offline": BAD, "red": BAD,
              "blocked": BAD, "broken": BAD, "out of sync": BAD, "non-compliant": BAD}

    @staticmethod
    def cell_lines(cell, bottom=None, top=None):
        """cell borders: none on every side but the ones given as (colour, points)"""
        tcPr = cell._tc.get_or_add_tcPr()
        for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
            for old in tcPr.findall(qn(tag)):
                tcPr.remove(old)
        for i, (tag, spec) in enumerate((("a:lnL", None), ("a:lnR", None), ("a:lnT", top), ("a:lnB", bottom))):
            ln = etree.Element(qn(tag))
            if spec:
                ln.set("w", str(int(spec[1] * 12700)))
                f = etree.SubElement(ln, qn("a:solidFill"))
                etree.SubElement(f, qn("a:srgbClr")).set("val", spec[0].lstrip("#"))
            else:
                ln.set("w", "0")
                etree.SubElement(ln, qn("a:noFill"))
            tcPr.insert(i, ln)

    def s_table(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        cols, rows = sl.get("columns", []), [list(r) for r in sl.get("rows", [])]
        if not cols:
            raise SystemExit(f"deck: slide {self.n}: a table needs columns")
        if len(rows) > 12:
            self.warn.append(f"slide {self.n}: {len(rows)} rows; keep 12 or fewer (top N here, the rest in the Excel export)")
        if len(cols) > 7:
            self.warn.append(f"slide {self.n}: {len(cols)} columns; keep 7 or fewer")
        for r in rows:
            r += [""] * (len(cols) - len(r))
        nr = len(rows) + 1
        bottom = self.H - (1.5 if sl.get("note") else 0.85)
        rh = min(0.52, (bottom - top) / nr)
        size = 14 if rh >= 0.45 else 12 if rh >= 0.36 else 10
        w = self.W - 2 * self.M
        gf = s.shapes.add_table(nr, len(cols), Inches(self.M), Inches(top), Inches(w), Inches(rh * nr))
        tbl = gf.table
        tblPr = gf._element.graphic.graphicData.tbl.tblPr
        sid = tblPr.find(qn("a:tableStyleId"))
        if sid is None:
            sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
        sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"       # No Style, No Grid: every cell styled here
        num = re.compile(r"^[\s$€£+-]*[\d.,]+\s*(%|[A-Za-z/]{1,6})?\s*$")
        numeric = [all(num.match(str(r[j])) for r in rows if str(r[j]).strip()) and any(str(r[j]).strip() for r in rows)
                   for j in range(len(cols))]

        def value(v):
            m = re.search(r"-?[\d,]*\.?\d+", str(v))
            try:
                return float(m.group(0).replace(",", "")) if m else None
            except ValueError:
                return None
        heat = sl.get("heat") or []
        heat = {cols.index(h) if h in cols else int(h) for h in ([heat] if isinstance(heat, (str, int)) else heat) if h in cols or str(h).isdigit()}
        ranges = {}
        for j in heat:
            vs = [value(r[j]) for r in rows if value(r[j]) is not None]
            ranges[j] = (min(vs), max(vs)) if vs else (0, 0)
        body_rows = rows[:-1] if sl.get("total") and rows else rows
        for j in heat:
            vs = [value(r[j]) for r in body_rows if value(r[j]) is not None]
            ranges[j] = (min(vs), max(vs)) if vs else (0, 0)
        heat_to = BAD if sl.get("heat_color", "bad") == "bad" else t["accents"][0]
        widths = [max([len(plain(cols[j]))] + [len(plain(r[j])) for r in rows]) for j in range(len(cols))]
        widths = [max(5, x) * (0.85 if numeric[j] else 1) for j, x in enumerate(widths)]
        tot = sum(widths)
        for j in range(len(cols)):
            tbl.columns[j].width = Emu(int(Inches(w) * widths[j] / tot))
        hl = sl.get("highlight")
        total = bool(sl.get("total"))
        head_fill = t["accents"][0] if self.bold or t["dark"] == "#FFFFFF" else t["dark"]
        for i in range(nr):
            tbl.rows[i].height = Inches(rh)
            last = i == nr - 1
            for j in range(len(cols)):
                cell = tbl.cell(i, j)
                val = cols[j] if i == 0 else rows[i - 1][j]
                cell.margin_left = cell.margin_right = Inches(0.14)
                cell.margin_top = cell.margin_bottom = Inches(0.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                if i == 0:
                    self.cell_lines(cell)
                elif total and last:
                    self.cell_lines(cell, top=(t["text"], 1.5))
                else:
                    self.cell_lines(cell, bottom=(t["line"], 0.75) if not (total and i == nr - 2) else None)
                cell.fill.solid()
                fill = t["bg"]
                if i == 0:
                    fill = head_fill
                elif hl is not None and i - 1 == hl:
                    fill = mix(t["accents"][0], "#FFFFFF", 0.84)
                elif j in heat and not (total and last) and value(val) is not None and ranges[j][1] > ranges[j][0]:
                    k = (value(val) - ranges[j][0]) / (ranges[j][1] - ranges[j][0])
                    fill = mix(t["bg"], heat_to, 0.06 + 0.5 * k)
                elif sl.get("zebra") and i % 2 == 0:
                    fill = t["surface"]
                cell.fill.fore_color.rgb = rgb(fill)
                tf = cell.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.RIGHT if numeric[j] else PP_ALIGN.LEFT
                text = plain(val)
                status = self.STATUS.get(text.strip().lower()) if i else None
                if status:
                    r = p.add_run()
                    r.text = "● "
                    r.font.size, r.font.color.rgb = Pt(size), rgb(status)
                r = p.add_run()
                r.text = text
                strong = i == 0 or (hl is not None and i - 1 == hl) or (total and last) or (j == 0 and sl.get("first_bold", True)) or str(val).startswith("**")
                r.font.size, r.font.name = Pt(size - (1 if i == 0 else 0)), t["head"] if strong else t["body"]
                r.font.color.rgb = rgb("#FFFFFF" if i == 0 else status if status else t["text"])
                r.font.bold = i == 0 or bool(status) or (total and last)
                if i == 0:
                    r.font._rPr.set("spc", "40")
        if sl.get("note"):
            self.text(s, self.M, self.H - 1.3, self.W - 2 * self.M, 0.5, [sl["note"]], 14, t["muted"])
        return s

    def s_timeline(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        items = sl.get("items", [])
        if not 2 <= len(items) <= 6:
            self.warn.append(f"slide {self.n}: {len(items)} milestones; 3-6 fit")
        n = max(1, len(items))
        w = (self.W - 2 * self.M) / n
        ly = top + max(1.25, (self.H - 0.9 - top - 3.2) / 2 + 0.9)
        self.shape(s, MSO_SHAPE.RECTANGLE, self.M, ly - 0.015, self.W - 2 * self.M, 0.03, fill=t["line"])
        done = [it.get("done", True) for it in items]
        if self.bold and True in done:                 # the part of the line already travelled, in colour
            k = max(i for i, d in enumerate(done) if d)
            self.shape(s, MSO_SHAPE.RECTANGLE, self.M, ly - 0.025, k * w + 0.2, 0.05, fill=t["accents"][0])
        for i, it in enumerate(items):
            x = self.M + i * w
            col = t["accents"][i % len(t["accents"])] if sl.get("colorful") else (t["accents"][0] if it.get("done", True) else mix(t["muted"], "#FFFFFF", 0.4))
            self.text(s, x, ly - 0.95 - (0.15 if deck_icons.resolve(it.get("icon")) else 0), w - 0.25, 0.6, [it.get("date", "")], 18, col,
                      font=t["head"], anchor=MSO_ANCHOR.BOTTOM)
            if deck_icons.resolve(it.get("icon")):
                self.badge(s, it["icon"], x - 0.05, ly - 0.3, 0.6, "#FFFFFF", col)
            else:
                self.shape(s, MSO_SHAPE.OVAL, x, ly - 0.16, 0.32, 0.32, fill=col)
                self.shape(s, MSO_SHAPE.OVAL, x + 0.09, ly - 0.07, 0.14, 0.14, fill=t["bg"])
            self.text(s, x, ly + 0.45, w - 0.3, 0.8, [it.get("title", "")], 18, t["text"], font=t["head"], spacing=1.05)
            bh = self.H - 0.9 - (ly + 1.3)
            size, ok = fit([(it.get("text", ""), 0)], w - 0.3, bh, 15, 11)
            if not ok:
                self.warn.append(f"slide {self.n}: milestone {i + 1} text is long")
            self.text(s, x, ly + 1.3, w - 0.3, bh, [it.get("text", "")], size, t["muted"], spacing=1.2)
        return s

    def s_quote(self, sl):
        t = self.t
        s = self.new(dark=True)
        a = t["accents"][0]
        self.text(s, 0.9, 0.6, 2, 2, ["“"], 200 if self.bold else 160, a, font="Georgia", spacing=0.8)
        q = sl.get("quote", "")
        size, ok = fit([(q, 0)], self.W - 2.6, 3.4, 40 if self.bold else 34, 22, spacing=1.2)
        if not ok:
            self.warn.append(f"slide {self.n}: the quote is long; two or three lines")
        self.text(s, 1.3, 2.0, self.W - 2.6, 3.4, [q], size, t["on_dark"], font=t["head"], spacing=1.2, anchor=MSO_ANCHOR.MIDDLE)
        if sl.get("by"):
            self.shape(s, MSO_SHAPE.RECTANGLE, 1.3, 5.75, 0.6, 0.05, fill=a)
            self.text(s, 2.1, 5.55, self.W - 3.5, 0.5, [sl["by"]], 16, t["on_dark_muted"])
        return s

    def s_closing(self, sl):
        t = self.t
        s = self.new(dark=True)
        a = t["accents"]
        if self.bold:
            band = self.shape(s, MSO_SHAPE.RECTANGLE, self.W - 4.2, -2.0, 2.6, 11.5, fill=a[0], alpha=0.28)
            band.rotation = 24
        else:
            self.shape(s, MSO_SHAPE.OVAL, -2.2, self.H - 3.2, 5.5, 5.5, fill=a[0], alpha=0.2)
            self.shape(s, MSO_SHAPE.OVAL, self.W - 2.4, -1.8, 4.2, 4.2, fill=a[1 % len(a)], alpha=0.16)
        self.text(s, 1.2, 1.2, self.W - 2.4, 1.3, [sl.get("title", "Thank you")], 50 if self.bold else 44, t["on_dark"], font=t["head"])
        y = 2.6
        if sl.get("subtitle"):
            self.text(s, 1.2, y, self.W - 2.4, 0.8, [sl["subtitle"]], 20, t["on_dark_muted"])
            y += 0.9
        if sl.get("bullets"):
            self.shape(s, MSO_SHAPE.RECTANGLE, 1.2, y + 0.1, 0.9, 0.06, fill=a[0])
            self.body(s, 1.2, y + 0.45, self.W - 3.2, self.H - y - 1.3, sl["bullets"], hi=24 if self.bold else 22, lo=14, color=t["on_dark"],
                      what="the closing points")
        if sl.get("contact"):
            self.text(s, 1.2, self.H - 1.0, self.W - 2.4, 0.4, [sl["contact"]], 14, t["on_dark_muted"])
        return s

    def body(self, s, x, y, w, h, items, hi=22, lo=14, color=None, what="text", anchor=MSO_ANCHOR.TOP):
        """bullets (strings, or {"text", "sub": [...]}) fitted to the box"""
        paras = []
        for it in items:
            if isinstance(it, dict):
                paras.append((it.get("text", ""), 0))
                paras += [(x2, 1) for x2 in it.get("sub", [])]
            else:
                paras.append((it, 0))
        size, ok = fit([(p, 0.28 + 0.3 * l) for p, l in paras], w, h, hi, lo)
        if not ok:
            self.warn.append(f"slide {self.n}: {what} does not fit even at {lo} pt; shorten it or split the slide")
        self.text(s, x, y, w, h, paras, size, color or self.t["text"], bullets=True, anchor=anchor, gap=0.75 if anchor != MSO_ANCHOR.TOP else 0.55)
        return size

    def notes(self, s, sl):
        if sl.get("notes"):
            s.notes_slide.notes_text_frame.text = sl["notes"]

    def grid(self, n, top, bottom, max_cols=3, gap=0.3):
        cols = n if n <= max_cols else math.ceil(n / 2)
        rows = math.ceil(n / cols)
        w = (self.W - 2 * self.M - gap * (cols - 1)) / cols
        h = (bottom - top - gap * (rows - 1)) / rows
        return [(self.M + (i % cols) * (w + gap), top + (i // cols) * (h + gap), w, h) for i in range(n)]

    def s_compare(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        gap = 0.4
        w = (self.W - 2 * self.M - gap) / 2
        need = 1.5 + max(sum(lines_for(b if isinstance(b, str) else b.get("text", ""), 20, w - 1.0) for b in (side or {}).get("bullets", [])) * 20 * 1.6 / 72
                         for side in (sl.get("left"), sl.get("right")))
        bottom = min(self.H - (1.75 if sl.get("verdict") else 0.85), top + max(2.6, need))
        for i, side in enumerate((sl.get("left") or {}, sl.get("right") or {})):
            x = self.M + i * (w + gap)
            col = t["accents"][i % len(t["accents"])]
            self.shape(s, MSO_SHAPE.RECTANGLE, x, top, w, bottom - top, fill=t["surface"])
            self.shape(s, MSO_SHAPE.RECTANGLE, x, top, w, 0.09, fill=col)
            self.text(s, x + 0.35, top + 0.35, w - 0.7, 0.6, [side.get("title", "")], 22, col, font=t["head"])
            self.body(s, x + 0.35, top + 1.1, w - 0.7, bottom - top - 1.3, side.get("bullets", []), hi=20, lo=12,
                      what=f"the {'left' if i == 0 else 'right'} side")
        if sl.get("verdict"):
            vy = bottom + 0.35
            self.shape(s, MSO_SHAPE.RECTANGLE, self.M, vy, self.W - 2 * self.M, 0.75, fill=t["dark"] if t["dark"] != "#FFFFFF" else t["accents"][0])
            self.text(s, self.M + 0.35, vy, self.W - 2 * self.M - 0.7, 0.75, [sl["verdict"]], 17, "#FFFFFF", font=t["head"],
                      anchor=MSO_ANCHOR.MIDDLE)
        return s

    def s_process(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        steps = sl.get("steps", [])
        if not 2 <= len(steps) <= 5:
            self.warn.append(f"slide {self.n}: {len(steps)} steps; 3-5 fit")
        n = max(1, len(steps))
        w = (self.W - 2 * self.M + 0.25 * (n - 1)) / n
        top = top + max(0, (self.H - 0.9 - top - 3.4) / 2)
        for i, st in enumerate(steps):
            x = self.M + i * (w - 0.25)
            col = t["accents"][0] if not sl.get("colorful") else t["accents"][i % len(t["accents"])]
            shade = mix(col, t["dark"] if t["dark"] != "#FFFFFF" else "#000000", 0.12 * i) if not sl.get("colorful") else col
            kind = MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON
            sh = self.shape(s, kind, x, top + 0.2, w, 1.15, fill=shade)
            if len(sh.adjustments):
                sh.adjustments[0] = 0.32
            self.text(s, x + (0.3 if i == 0 else 0.55), top + 0.2, w - 0.9, 1.15, ["%d  %s" % (i + 1, plain(st.get("title", "")))], 18,
                      "#FFFFFF", font=t["head"], anchor=MSO_ANCHOR.MIDDLE, spacing=1.0)
            bh = self.H - 0.9 - (top + 1.75)
            size, ok = fit([(st.get("text", ""), 0)], w - 0.5, bh, 17, 11)
            if not ok:
                self.warn.append(f"slide {self.n}: step {i + 1} text is long")
            self.text(s, x + 0.1, top + 1.75, w - 0.5, bh, [st.get("text", "")], size, t["text"], spacing=1.2)
        return s

    def s_image(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        path = os.path.expanduser(sl.get("image", ""))
        if not os.path.isfile(path):
            raise SystemExit(f"deck: slide {self.n}: image {path!r} not found")
        bottom = self.H - 0.85
        cap = sl.get("caption")
        bw = (self.W - 2 * self.M) * (0.64 if cap else 1)
        bh = bottom - top
        try:
            from PIL import Image
            iw, ih = Image.open(path).size
        except Exception:
            iw, ih = 16, 9
        scale = min(bw / iw, bh / ih)
        w, h = iw * scale, ih * scale
        s.shapes.add_picture(path, Inches(self.M + (bw - w) / 2 if not cap else self.M), Inches(top + (bh - h) / 2), Inches(w), Inches(h))
        if cap:
            tx = self.M + bw + 0.5
            self.takeaway(s, tx, top, self.W - self.M - tx, bh, cap, label=sl.get("label", "What to look at"))
        return s

    # ---------------------------------------------------------------------------------------------------- build
    def build(self):
        slides = self.spec.get("slides")
        if not isinstance(slides, list) or not slides:
            raise SystemExit('deck: the spec needs "slides": [ ... ] (see deck.py --example)')
        for i, sl in enumerate(slides, 1):
            kind = sl.get("type", "bullets")
            fn = getattr(self, "s_" + kind, None)
            if fn is None:
                raise SystemExit(f"deck: slide {i}: unknown type {kind!r}; one of {', '.join(TYPES)}")
            s = fn(sl)
            self.notes(s, sl)
        if len(slides) > 25:
            self.warn.append(f"{len(slides)} slides; a deck people read is 8-20")
        return self.prs


TYPES = [n[2:] for n in dir(Deck) if n.startswith("s_")]

EXAMPLE = {
    "title": "SAN capacity review Q4",
    "footer": "SAN team \u00b7 capacity review",
    "slides": [
        {"type": "title", "title": "SAN capacity review Q4", "subtitle": "Where the growth went and what we buy next", "meta": "SAN team \u00b7 November 2026"},
        {"type": "agenda", "items": ["Where we are", "What grew", "Risks", "The ask"]},
        {"type": "section", "title": "Where we are", "subtitle": "Four arrays, two sites", "icon": "database"},
        {"type": "stats", "title": "Usable capacity is **78% used** across the four arrays",
         "stats": [{"value": "1.9 PB", "label": "usable capacity", "icon": "database"},
                   {"value": "78%", "label": "used", "delta": "+6 pts in 90 days", "good": False, "progress": "78%", "icon": "gauge"},
                   {"value": "4.1:1", "label": "data reduction", "icon": "layers"},
                   {"value": "14", "label": "months to full at this rate", "icon": "calendar"}],
         "note": "Source: Unisphere, 2026-11-01"},
        {"type": "hero", "value": "14 months", "text": "until the arrays are full at today's growth", "sub": "Unless we reclaim or expand", "icon": "clock"},
        {"type": "chart", "title": "Prod-A grew fastest: 40 TB a month since July",
         "chart": {"kind": "column", "categories": ["PMAX-A", "PMAX-B", "ONTAP-1", "ONTAP-2"], "series": [{"name": "TB added", "values": [160, 70, 55, 30]}],
                   "unit": "TB", "highlight": "PMAX-A", "source": "Unisphere / Harvest"},
         "takeaway": "Prod-A takes **half** of all new capacity; the database refresh drives it.", "icon": "trend-up"},
        {"type": "chart", "title": "PMAX-A reaches the 80% line in March",
         "chart": {"kind": "line", "categories": ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov"],
                   "series": [{"name": "PMAX-A", "values": [62, 66, 69, 72, 75, 78]}, {"name": "PMAX-B", "values": [48, 49, 51, 52, 54, 55]}],
                   "unit": "%", "target": 80, "target_label": "80% limit", "max": 100}},
        {"type": "chart", "title": "Half of the space is databases",
         "chart": {"kind": "doughnut", "categories": ["Databases", "VMware", "File", "Other"], "series": [{"name": "TB", "values": [620, 410, 180, 90]}],
                   "unit": "TB"}, "takeaway": "Databases grow 3% a month; everything else is flat."},
        {"type": "bullets", "title": "Three things drive the growth",
         "bullets": ["**Database refresh** copies on Prod-A: 12 new 4 TB LUNs", {"text": "Snapshot retention moved from 7 to 30 days", "sub": ["policy change in August"]},
                     "Two new VMware clusters on ONTAP-1"],
         "takeaway": "Reclaiming old refresh copies frees about **90 TB** without buying anything.", "icon": "idea"},
        {"type": "cards", "title": "Our options", "cards": [
            {"title": "Reclaim", "text": "Remove unmapped LUNs and old refresh copies.", "icon": "archive", "value": "90 TB"},
            {"title": "Rebalance", "text": "Move test workloads from PMAX-A to PMAX-B.", "icon": "replication", "value": "60 TB"},
            {"title": "Expand", "text": "Add one engine of capacity to PMAX-A in Q1.", "icon": "server", "value": "300 TB"}]},
        {"type": "iconlist", "title": "What we check before a reclaim", "items": [
            {"icon": "search", "title": "No I/O for 90 days", "text": "Unisphere and host-side, both."},
            {"icon": "users", "title": "The owner agrees", "text": "In the change ticket, in writing."},
            {"icon": "shield", "title": "A snapshot is kept", "text": "14 days, so an unmap can be undone."},
            {"icon": "check", "title": "The space is recorded", "text": "Freed TB per array in the capacity sheet."}]},
        {"type": "compare", "title": "Reclaim first, then expand",
         "left": {"title": "Reclaim + rebalance", "bullets": ["No purchase", "Done in 3 weeks", "Buys about 5 months"]},
         "right": {"title": "Expand now", "bullets": ["Purchase order and lead time", "Done in 10 weeks", "Buys 2+ years"]},
         "verdict": "Do both: reclaim now, order the expansion for Q1."},
        {"type": "table", "title": "Arrays at a glance", "columns": ["Array", "Site", "Used %", "Free TB", "Replication"],
         "rows": [["PMAX-A", "Prod", "78%", "118", "In sync"], ["PMAX-B", "Prod", "55%", "290", "In sync"],
                  ["ONTAP-1", "DR", "64%", "150", "Lagging"], ["ONTAP-2", "DR", "41%", "260", "Failed"], ["Total", "", "62%", "818", ""]],
         "heat": ["Used %"], "total": True, "note": "Replication: SRDF and SnapMirror state on 2026-11-01"},
        {"type": "timeline", "title": "Plan", "items": [
            {"date": "Nov", "title": "Reclaim", "text": "Unmap and remove, with owners' approval.", "icon": "archive"},
            {"date": "Dec", "title": "Rebalance", "text": "Move test SGs to PMAX-B.", "icon": "replication"},
            {"date": "Jan", "title": "Order", "text": "Expansion PO.", "done": False, "icon": "money"},
            {"date": "Mar", "title": "Install", "text": "New capacity online.", "done": False, "icon": "server"}]},
        {"type": "process", "title": "How a reclaim is approved", "steps": [
            {"title": "Find", "text": "unused-luns report lists candidates."},
            {"title": "Ask", "text": "Owner confirms within 5 days."},
            {"title": "Unmap", "text": "Change ticket, unmap, wait 14 days."},
            {"title": "Delete", "text": "Remove and record the space freed."}]},
        {"type": "quote", "quote": "The cheapest terabyte is the one you already own.", "by": "Storage team motto"},
        {"type": "closing", "title": "The ask", "bullets": ["Approve the reclaim plan", "Budget the Q1 expansion"], "contact": "san-team@corp"},
    ],
}

def slug(s):
    return re.sub(r"[^\w-]+", "-", plain(s).lower()).strip("-")[:60] or "deck"


def preview(path):
    """PNG per slide + a contact sheet next to the deck (LibreOffice + pdftoppm); the paths, or a reason"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice or not shutil.which("pdftoppm"):
        return None, "preview skipped: LibreOffice (soffice) and pdftoppm are needed"
    out = os.path.join(os.path.dirname(path), "preview")
    os.makedirs(out, exist_ok=True)
    prof = tempfile.mkdtemp(prefix="deck-lo-")                 # own profile: two people converting at once do not clash
    try:
        r = subprocess.run([soffice, f"-env:UserInstallation=file://{prof}", "--headless", "--convert-to", "pdf", "--outdir", out, path],
                           capture_output=True, text=True, timeout=180)
        pdf = os.path.join(out, os.path.splitext(os.path.basename(path))[0] + ".pdf")
        if not os.path.isfile(pdf):
            return None, "preview failed: " + (r.stderr or r.stdout).strip()[-200:]
        for f in glob.glob(os.path.join(out, "slide-*.png")):
            os.remove(f)
        subprocess.run(["pdftoppm", "-png", "-r", "60", pdf, os.path.join(out, "slide")], check=True, timeout=180)
        pngs = sorted(glob.glob(os.path.join(out, "slide-*.png")))
    except (subprocess.SubprocessError, OSError) as e:
        return None, f"preview failed: {e}"
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    try:
        from PIL import Image
        ims = [Image.open(p) for p in pngs]
        w, h = ims[0].size
        cols = 3
        sheet = Image.new("RGB", (cols * w + (cols + 1) * 16, math.ceil(len(ims) / cols) * (h + 16) + 16), "#D9DDE3")
        for i, im in enumerate(ims):
            sheet.paste(im, (16 + (i % cols) * (w + 16), 16 + (i // cols) * (h + 16)))
        sp = os.path.join(out, "contact-sheet.png")
        sheet.save(sp)
        return [sp] + pngs, None
    except Exception:
        return pngs, None


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="deck.py", description=__doc__.split("\n")[0])
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--theme")
    ap.add_argument("--style", choices=["clean", "bold"])
    ap.add_argument("--look")
    ap.add_argument("--icons", action="store_true")
    ap.add_argument("--template")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--example", action="store_true")
    ap.add_argument("--themes", action="store_true")
    a = ap.parse_args(argv)
    if a.example:
        print(json.dumps(EXAMPLE, indent=1, ensure_ascii=False))
        return 0
    if a.icons:
        print("icons: " + ", ".join(sorted(deck_icons.ICONS)))
        print("aliases: " + ", ".join(f"{k}={v}" for k, v in sorted(deck_icons.ALIASES.items())))
        return 0
    if a.themes:
        for k, v in THEMES.items():
            print(f"{k:10} dark {v['dark']}  accents {' '.join(v['accents'][:4])}")
        print("or --template company.pptx: its master, colours and fonts")
        return 0
    if not a.spec:
        ap.error("a spec file (deck.py --example > spec.json)")
    try:
        spec = json.load(open(os.path.expanduser(a.spec), encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"deck: {a.spec}: {e}")
    d = Deck(spec, theme=a.theme, template=a.template, style=a.style, look=a.look)
    prs = d.build()
    name = slug(spec.get("title") or spec["slides"][0].get("title", "deck"))
    out = os.path.expanduser(a.out) if a.out else os.path.expanduser(f"~/storage-reports/{dt.date.today()}-{name}")
    path = out if out.endswith(".pptx") else os.path.join(out, name + ".pptx")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    prs.save(path)
    print(f"deck: {path} ({d.n} slides)")
    print(f"look: {d.look['seed']} ({d.style}, {d.theme_name}, {d.t['head']}); the same again: \"look\": {d.look['seed']}, another: \"look\": \"random\"")
    for w in d.warn:
        print("WARN " + w)
    if not d.warn:
        print("checks: ok (every text fits its box, no design rule broken)")
    if a.preview:
        files, why = preview(path)
        print(why or "preview: " + files[0] + (f" (+ {len(files) - 1} slide images)" if len(files) > 1 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
