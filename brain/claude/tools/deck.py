#!/usr/bin/env python3
"""Designed PowerPoint decks from a short JSON outline: the model writes the content, this tool does the design.

    deck.py spec.json [--out DIR|FILE.pptx] [--theme NAME] [--template company.pptx] [--preview]
    deck.py --example            a spec with every slide type (start from it)
    deck.py --themes             the built-in themes

Every slide is native PowerPoint (text boxes, shapes, real charts with their data, real tables), so the deck stays
editable. Text is fitted to its box (the font shrinks within limits); what still does not fit, or breaks a design rule
(too many bullets, a long title, a crowded chart), is reported as WARN lines: fix the spec and run again.
--template takes the company deck or .potx: its slide size, master (logo, background), colours and fonts are used, its
"Title Slide" / "Section Header" / "Title Only" layouts where they exist. --preview renders PNGs and one contact sheet
(LibreOffice + pdftoppm, when installed) next to the deck. Default output: ~/storage-reports/<date>-<title>/<title>.pptx.

Spec: {"title": "...", "theme": "midnight", "footer": "SAN team", "slides": [{"type": "title", ...}, ...]}
Slide types: title, agenda, section, bullets, cards, stats, chart, table, compare, timeline, process, quote, image,
closing (fields: deck.py --example). Any slide takes "notes" (speaker notes). Text takes **bold** inline.
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
    """python-pptx lives in the devtools venv: run there when this python does not have it"""
    for v in VENVS:
        py = os.path.join(v, "bin", "python")
        if os.path.isfile(py) and os.path.realpath(py) != os.path.realpath(sys.executable) and not os.environ.get("DECK_REEXEC"):
            os.environ["DECK_REEXEC"] = "1"
            os.execv(py, [py] + sys.argv)
    sys.exit("deck: python-pptx is not installed (the devtools venv: sh brain/devtools/install-devtools.sh)")


try:
    from lxml import etree
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_MARKER_STYLE
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.oxml.ns import qn
    from pptx.util import Emu, Inches, Pt
except ImportError:
    if __name__ == "__main__":
        _reexec()
    raise

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
    def __init__(self, spec, theme=None, template=None):
        self.spec, self.warn = spec, []
        self.template = template or spec.get("template")
        if self.template:
            self.prs = Presentation(os.path.expanduser(self.template))
            self._drop_slides()
            self.t = self._theme_from_template()
        else:
            self.prs = Presentation()
            self.prs.slide_width, self.prs.slide_height = Inches(13.333), Inches(7.5)
            name = theme or spec.get("theme") or "midnight"
            if name not in THEMES:
                raise SystemExit(f"deck: unknown theme {name!r}; one of {', '.join(THEMES)}")
            self.t = dict(THEMES[name], **FONTS)
        for k, v in (spec.get("colors") or {}).items():   # "colors": {"accents": [...], "dark": "#..."} overrides
            self.t[k] = v
        for k in ("head", "body"):
            if (spec.get("fonts") or {}).get(k):
                self.t[k] = spec["fonts"][k]
        self.W, self.H = self.prs.slide_width / 914400, self.prs.slide_height / 914400
        self.M = 0.65 * self.W / 13.333 if self.W < 12 else 0.65
        self.kicker, self.n, self.sections = "", 0, 0

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
    def new(self, kind="blank", dark=False):
        lay = self.layout(kind) or self.layout("blank")
        s = self.prs.slides.add_slide(lay)
        self.n += 1
        if dark and not (self.template and kind != "blank"):
            s.background.fill.solid()
            s.background.fill.fore_color.rgb = rgb(self.t["dark"])
        return s

    def shape(self, s, kind, x, y, w, h, fill=None, line=None, alpha=None, radius=None):
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
            sh.line.width = Pt(1)
        else:
            sh.line.fill.background()
        if radius is not None and len(sh.adjustments):
            sh.adjustments[0] = radius
        return sh

    def text(self, s, x, y, w, h, paras, size, color, font=None, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             spacing=1.15, gap=0.55, bullets=False, bullet_color=None, spc=None, italic=False, shape=None):
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
                etree.SubElement(pPr, qn("a:buChar")).set("char", "•" if lvl == 0 else "–")
        return tf

    def frame(self, s, sl, title=True):
        """content slide chrome: kicker (current section), action title, footer and page number; returns content top"""
        t, M = self.t, self.M
        top = 1.75
        if self.template and self.layout("titleonly"):
            ph = next((p for p in s.placeholders if p.placeholder_format.type in (1, 3)), None)
            if ph is not None:
                ph.text = plain(sl.get("title", ""))
                top = (ph.top + ph.height) / 914400 + 0.3
                return top
        if self.kicker:
            self.text(s, M, 0.42, self.W - 2 * M, 0.3, [self.kicker.upper()], 11, t["accents"][0], font=t["head"], spc=150)
        if title:
            ttl = sl.get("title", "")
            size, ok = fit([(ttl, 0)], self.W - 2 * M, 1.0, 30, 22, spacing=1.05, char=BOLD_CHAR)
            if not ok or len(plain(ttl)) > 90:
                self.warn.append(f"slide {self.n}: title is long ({len(plain(ttl))} characters); say it in one line")
            self.text(s, M, 0.72, self.W - 2 * M, 1.0, [ttl], size, t["text"], font=t["head"], spacing=1.05, anchor=MSO_ANCHOR.TOP)
        foot = self.spec.get("footer") or plain(self.spec.get("title", ""))
        self.text(s, M, self.H - 0.45, self.W * 0.6, 0.25, [foot], 10, t["muted"])
        self.text(s, self.W - M - 1, self.H - 0.45, 1, 0.25, [str(self.n)], 10, t["muted"], align=PP_ALIGN.RIGHT)
        return top

    def body(self, s, x, y, w, h, items, hi=22, lo=14, color=None, what="text"):
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
        self.text(s, x, y, w, h, paras, size, color or self.t["text"], bullets=True)
        return size

    def notes(self, s, sl):
        if sl.get("notes"):
            s.notes_slide.notes_text_frame.text = sl["notes"]

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
        s = self.new(dark=True)
        W, H = self.W, self.H
        a = t["accents"]
        self.shape(s, MSO_SHAPE.OVAL, W - 5.2, -1.6, 7.0, 7.0, fill=a[0], alpha=0.22)
        self.shape(s, MSO_SHAPE.OVAL, W - 3.4, 2.9, 5.2, 5.2, fill=a[1 % len(a)], alpha=0.18)
        self.shape(s, MSO_SHAPE.OVAL, W - 6.3, 4.6, 1.5, 1.5, fill=a[2 % len(a)], alpha=0.35)
        self.shape(s, MSO_SHAPE.RECTANGLE, 0.9, 2.35, 0.9, 0.08, fill=a[0])
        size, ok = fit([(sl.get("title", ""), 0)], 7.6, 2.2, 48, 32, spacing=1.0, char=BOLD_CHAR)
        if not ok:
            self.warn.append(f"slide {self.n}: the deck title is long; keep it under about 8 words")
        self.text(s, 0.9, 2.6, 7.6, 2.2, [sl.get("title", "")], size, t["on_dark"], font=t["head"], spacing=1.0)
        if sl.get("subtitle"):
            self.text(s, 0.9, 4.85, 7.4, 1.0, [sl["subtitle"]], 20, t["on_dark_muted"])
        meta = sl.get("meta") or dt.date.today().strftime("%B %Y")
        self.text(s, 0.9, H - 1.0, 8, 0.4, [meta], 13, t["on_dark_muted"], spc=60)
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
        s = self.new(dark=True)
        a = t["accents"][0]
        self.shape(s, MSO_SHAPE.RECTANGLE, 0, 0, 0.35, self.H, fill=a)
        self.text(s, 0.95, 1.35, 6, 2.2, ["%02d" % self.sections], 120, a, font=t["head"], spacing=0.9)
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

    def takeaway(self, s, x, y, w, h, text, label="Key point"):
        t = self.t
        self.shape(s, MSO_SHAPE.RECTANGLE, x, y, w, h, fill=t["surface"])
        self.shape(s, MSO_SHAPE.RECTANGLE, x, y, 0.07, h, fill=t["accents"][0])
        self.text(s, x + 0.35, y + 0.35, w - 0.6, 0.3, [label.upper()], 11, t["accents"][0], font=t["head"], spc=120)
        size, ok = fit([(text, 0)], w - 0.7, h - 1.1, 24, 15, spacing=1.2)
        if not ok:
            self.warn.append(f"slide {self.n}: the takeaway is long; one or two sentences")
        self.text(s, x + 0.35, y + 0.8, w - 0.7, h - 1.1, [text], size, t["text"], font=t["head"], spacing=1.2)

    def s_bullets(self, sl):
        s = self.new("titleonly")
        top = self.frame(s, sl)
        items = sl.get("bullets", [])
        if len(items) > 6:
            self.warn.append(f"slide {self.n}: {len(items)} bullets; keep 3-6 (split the slide or use cards)")
        bottom = self.H - 0.85
        if sl.get("takeaway"):
            w = (self.W - 2 * self.M) * 0.58
            self.body(s, self.M, top + 0.1, w, bottom - top - 0.1, items, what="the bullets")
            tx = self.M + w + 0.5
            self.takeaway(s, tx, top, self.W - self.M - tx, bottom - top, sl["takeaway"])
        else:
            self.body(s, self.M, top + 0.1, self.W - 2 * self.M - 1.5, bottom - top - 0.1, items, hi=24, what="the bullets")
        return s

    def grid(self, n, top, bottom, max_cols=3, gap=0.3):
        cols = n if n <= max_cols else math.ceil(n / 2)
        rows = math.ceil(n / cols)
        w = (self.W - 2 * self.M - gap * (cols - 1)) / cols
        h = (bottom - top - gap * (rows - 1)) / rows
        return [(self.M + (i % cols) * (w + gap), top + (i // cols) * (h + gap), w, h) for i in range(n)]

    def s_cards(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        cards = sl.get("cards", [])
        if not 2 <= len(cards) <= 6:
            self.warn.append(f"slide {self.n}: {len(cards)} cards; 2-6 look right")
        cols = len(cards) if len(cards) <= 4 else 3
        rows = math.ceil(max(1, len(cards)) / cols)
        cw = (self.W - 2 * self.M - 0.3 * (cols - 1)) / cols
        need = max([2.35 + 16 * 1.2 * lines_for(c.get("text", ""), 16, cw - 0.6) / 72 for c in cards] or [3])
        avail = self.H - 0.85 - (top + 0.05)
        ch_ = min(avail, max(2.9, need) * rows + 0.3 * (rows - 1))
        y0 = top + 0.05 + (avail - ch_) / 2 * 0.6
        cells = self.grid(max(1, len(cards)), y0, y0 + ch_, max_cols=4 if len(cards) == 4 else 3)
        for i, (c, (x, y, w, h)) in enumerate(zip(cards, cells)):
            col = t["accents"][i % len(t["accents"])]
            self.shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=t["surface"], radius=0.06)
            self.shape(s, MSO_SHAPE.RECTANGLE, x + 0.3, y + 0.3, 0.5, 0.06, fill=col)
            badge = c.get("icon") or str(i + 1)
            compact = h < 2.9                          # two rows of cards: badge beside the title
            if compact:
                self.text(s, x + 0.3, y + 0.5, 0.9, 0.5, [badge], 20 if len(badge) <= 3 else 14, col, font=t["head"], anchor=MSO_ANCHOR.MIDDLE)
                bx = x + 0.3 + (0.55 if len(badge) <= 2 else 1.0)
                self.text(s, bx, y + 0.5, x + w - 0.3 - bx, 0.5, [c.get("title", "")], 18, t["text"], font=t["head"], anchor=MSO_ANCHOR.MIDDLE)
                ty = y + 1.15
            else:
                self.text(s, x + 0.3, y + 0.5, w - 0.6, 0.6, [badge], 26 if len(badge) <= 3 else 18, col, font=t["head"])
                hs, _ = fit([(c.get("title", ""), 0)], w - 0.6, 0.8, 20, 15, char=BOLD_CHAR)
                self.text(s, x + 0.3, y + 1.15, w - 0.6, 0.8, [c.get("title", "")], hs, t["text"], font=t["head"], spacing=1.05)
                ty = y + 1.95
            bh = y + h - 0.25 - ty
            size, ok = fit([(c.get("text", ""), 0)], w - 0.6, bh, 16, 11, spacing=1.2)
            if not ok:
                self.warn.append(f"slide {self.n}: card {i + 1} text is long; one or two sentences")
            self.text(s, x + 0.3, ty, w - 0.6, bh, [c.get("text", "")], size, t["muted"], spacing=1.2)
        return s

    def s_stats(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        stats = sl.get("stats", [])
        if not 1 <= len(stats) <= 4:
            self.warn.append(f"slide {self.n}: {len(stats)} numbers; 2-4 read best")
        n = max(1, len(stats))
        bottom = self.H - (1.6 if sl.get("note") else 0.9)
        w = (self.W - 2 * self.M) / n
        y = top + (bottom - top) / 2 - 1.3
        vs = min([fit([(str(st.get("value", "")), 0)], w - 0.6, 1.2, 66, 34, char=0.6)[0] for st in stats] or [60])
        for i, st in enumerate(stats):
            x = self.M + i * w
            col = t["accents"][i % len(t["accents"])] if sl.get("colorful") else t["accents"][0]
            if i:
                self.shape(s, MSO_SHAPE.RECTANGLE, x, y + 0.1, 0.015, 2.4, fill=t["line"])
            val = str(st.get("value", ""))
            self.text(s, x + 0.35, y, w - 0.6, 1.3, [val], vs, col, font=t["head"], spacing=0.95, anchor=MSO_ANCHOR.BOTTOM)
            self.text(s, x + 0.35, y + 1.45, w - 0.6, 0.8, [st.get("label", "")], 16, t["text"], spacing=1.1)
            if st.get("delta"):
                d = str(st["delta"])
                good = st.get("good", not d.strip().startswith("-"))
                arrow = "▲ " if not d.strip().startswith("-") else "▼ "
                self.text(s, x + 0.35, y + 2.15, w - 0.6, 0.4, [arrow + d.lstrip("+-")], 14, GOOD if good else BAD, font=t["head"])
        if sl.get("note"):
            self.shape(s, MSO_SHAPE.RECTANGLE, self.M, self.H - 1.45, self.W - 2 * self.M, 0.012, fill=t["line"])
            self.text(s, self.M, self.H - 1.3, self.W - 2 * self.M, 0.5, [sl["note"]], 15, t["muted"])
        return s

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
        for se in series:
            vals = se.get("values", [])
            if len(vals) != len(cats):
                raise SystemExit(f"deck: slide {self.n}: series {se.get('name')!r} has {len(vals)} values for {len(cats)} categories")
            cd.add_series(se.get("name", ""), [None if v is None else float(v) for v in vals])
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
        fmt = c.get("format") or ('#,##0.0' if any(float(v) % 1 for se in series for v in se["values"] if v is not None) else '#,##0')
        if kind in ("pie", "doughnut"):
            for i, pt in enumerate(plot.series[0].points):
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = rgb(pal[i % len(pal)])
                pt.format.line.color.rgb = rgb(t["bg"])
                pt.format.line.width = Pt(2)
            plot.has_data_labels = True
            dl = plot.data_labels
            dl.show_percentage, dl.show_value, dl.show_category_name = True, False, False
            dl.number_format, dl.number_format_is_linked = "0%", False
            dl.font.size, dl.font.bold = Pt(13), True
            dl.font.color.rgb = rgb("#FFFFFF")
            if kind == "doughnut":
                hole = ch._chartSpace.find(".//" + qn("c:holeSize"))
                if hole is not None:
                    hole.set("val", "58")
            ch.has_legend = True
            ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.RIGHT, False
            ch.legend.font.size = Pt(13)
            return gf
        for i, se in enumerate(plot.series):
            col = pal[i % len(pal)]
            if kind == "line":
                se.format.line.color.rgb = rgb(col)
                se.format.line.width = Pt(2.75)
                se.smooth = False
                se.marker.style, se.marker.size = XL_MARKER_STYLE.CIRCLE, 7
                se.marker.format.fill.solid()
                se.marker.format.fill.fore_color.rgb = rgb(col)
                se.marker.format.line.color.rgb = rgb(t["bg"])
            else:
                se.format.fill.solid()
                se.format.fill.fore_color.rgb = rgb(col)
                if hl is not None and len(series) == 1:
                    idx = cats.index(str(hl)) if str(hl) in cats else int(hl) if str(hl).isdigit() else -1
                    for j, pt in enumerate(se.points):
                        pt.format.fill.solid()
                        pt.format.fill.fore_color.rgb = rgb(col if j == idx else mix(col, "#FFFFFF", 0.62))
        if kind not in ("line", "area"):
            plot.gap_width = 55 if len(series) == 1 else 80
            if kind.startswith("stacked"):
                plot.overlap = 100
        va, ca = ch.value_axis, ch.category_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = rgb(t["line"])
        va.major_gridlines.format.line.width = Pt(0.75)
        va.format.line.fill.background()
        va.tick_labels.font.size = Pt(11)
        va.tick_labels.number_format = fmt + (f'" {unit}"' if unit else "")
        va.tick_labels.number_format_is_linked = False
        ca.format.line.color.rgb = rgb(t["line"])
        ca.tick_labels.font.size = Pt(12)
        ca.has_major_gridlines = False
        if kind in ("bar", "stacked_bar"):
            ca.reverse_order = True                    # first category on top, as it is read
        if c.get("min") is not None:
            va.minimum_scale = float(c["min"])
        if c.get("max") is not None:
            va.maximum_scale = float(c["max"])
        labels = c.get("labels", len(series) == 1 and len(cats) <= 8 and kind in ("column", "bar"))
        if labels:
            plot.has_data_labels = True
            dl = plot.data_labels
            dl.number_format, dl.number_format_is_linked = fmt, False
            dl.font.size, dl.font.bold = Pt(12), True
            dl.font.color.rgb = rgb(t["text"])
            if kind in ("column", "bar"):
                dl.position = XL_LABEL_POSITION.OUTSIDE_END
                va.has_major_gridlines = False
                va.visible = False
                if unit:
                    dl.number_format = fmt + f'" {unit}"'
        ch.has_legend = len(series) > 1
        if ch.has_legend:
            ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.TOP, False
            ch.legend.font.size = Pt(12)
        return gf

    def s_chart(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        bottom = self.H - 0.8
        c = sl.get("chart") or {}
        if sl.get("takeaway"):
            w = (self.W - 2 * self.M) * 0.66
            self.chart(s, self.M - 0.1, top, w, bottom - top, c)
            tx = self.M + w + 0.4
            self.takeaway(s, tx, top, self.W - self.M - tx, bottom - top, sl["takeaway"], label=sl.get("label", "What it shows"))
        else:
            self.chart(s, self.M - 0.1, top, self.W - 2 * self.M + 0.2, bottom - top, c)
        if c.get("source"):
            self.text(s, self.M, self.H - 0.78, self.W - 2 * self.M, 0.25, ["Source: " + c["source"]], 10, t["muted"], italic=True)
        return s

    def s_table(self, sl):
        t = self.t
        s = self.new("titleonly")
        top = self.frame(s, sl)
        cols, rows = sl.get("columns", []), sl.get("rows", [])
        if not cols:
            raise SystemExit(f"deck: slide {self.n}: a table needs columns")
        if len(rows) > 12:
            self.warn.append(f"slide {self.n}: {len(rows)} rows; keep 12 or fewer (top N here, the rest in the Excel export)")
        if len(cols) > 7:
            self.warn.append(f"slide {self.n}: {len(cols)} columns; keep 7 or fewer")
        nr = len(rows) + 1
        bottom = self.H - (1.5 if sl.get("note") else 0.85)
        rh = min(0.5, (bottom - top) / nr)
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
        numeric = [all(num.match(str(r[j])) for r in rows if j < len(r) and str(r[j]).strip()) and any(j < len(r) for r in rows)
                   for j in range(len(cols))]
        widths = [max([len(plain(cols[j]))] + [len(plain(r[j])) for r in rows if j < len(r)]) for j in range(len(cols))]
        tot = sum(max(4, x) for x in widths)
        for j in range(len(cols)):
            tbl.columns[j].width = Emu(int(Inches(w) * max(4, widths[j]) / tot))
        hl = sl.get("highlight")
        for i in range(nr):
            tbl.rows[i].height = Inches(rh)
            for j in range(len(cols)):
                cell = tbl.cell(i, j)
                val = cols[j] if i == 0 else (rows[i - 1][j] if j < len(rows[i - 1]) else "")
                cell.margin_left = cell.margin_right = Inches(0.12)
                cell.margin_top = cell.margin_bottom = Inches(0.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.fill.solid()
                if i == 0:
                    cell.fill.fore_color.rgb = rgb(t["dark"] if t["dark"] != "#FFFFFF" else t["accents"][0])
                elif hl is not None and i - 1 == hl:
                    cell.fill.fore_color.rgb = rgb(mix(t["accents"][0], "#FFFFFF", 0.82))
                else:
                    cell.fill.fore_color.rgb = rgb(t["surface"] if i % 2 == 0 else t["bg"])
                tf = cell.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.RIGHT if numeric[j] and i else PP_ALIGN.LEFT
                r = p.add_run()
                r.text = plain(val)
                r.font.size, r.font.name = Pt(size), t["head"] if i == 0 or (hl is not None and i - 1 == hl) else t["body"]
                r.font.color.rgb = rgb("#FFFFFF" if i == 0 else t["text"])
                r.font.bold = i == 0 or str(val).startswith("**")
        if sl.get("note"):
            self.text(s, self.M, self.H - 1.3, self.W - 2 * self.M, 0.5, [sl["note"]], 14, t["muted"])
        return s

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
        for i, it in enumerate(items):
            x = self.M + i * w
            col = t["accents"][0] if not it.get("done", True) is False else t["muted"]
            col = t["accents"][i % len(t["accents"])] if sl.get("colorful") else (t["accents"][0] if it.get("done", True) else mix(t["muted"], "#FFFFFF", 0.4))
            self.text(s, x, ly - 0.95, w - 0.25, 0.6, [it.get("date", "")], 18, col, font=t["head"], anchor=MSO_ANCHOR.BOTTOM)
            self.shape(s, MSO_SHAPE.OVAL, x, ly - 0.16, 0.32, 0.32, fill=col)
            self.shape(s, MSO_SHAPE.OVAL, x + 0.09, ly - 0.07, 0.14, 0.14, fill=t["bg"])
            self.text(s, x, ly + 0.45, w - 0.3, 0.8, [it.get("title", "")], 18, t["text"], font=t["head"], spacing=1.05)
            bh = self.H - 0.9 - (ly + 1.3)
            size, ok = fit([(it.get("text", ""), 0)], w - 0.3, bh, 15, 11)
            if not ok:
                self.warn.append(f"slide {self.n}: milestone {i + 1} text is long")
            self.text(s, x, ly + 1.3, w - 0.3, bh, [it.get("text", "")], size, t["muted"], spacing=1.2)
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

    def s_quote(self, sl):
        t = self.t
        s = self.new(dark=True)
        a = t["accents"][0]
        self.text(s, 0.9, 0.6, 2, 2, ["“"], 160, a, font="Georgia", spacing=0.8)
        q = sl.get("quote", "")
        size, ok = fit([(q, 0)], self.W - 2.6, 3.4, 34, 22, spacing=1.2)
        if not ok:
            self.warn.append(f"slide {self.n}: the quote is long; two or three lines")
        self.text(s, 1.3, 2.0, self.W - 2.6, 3.4, [q], size, t["on_dark"], font=t["head"], spacing=1.2, anchor=MSO_ANCHOR.MIDDLE)
        if sl.get("by"):
            self.shape(s, MSO_SHAPE.RECTANGLE, 1.3, 5.75, 0.6, 0.05, fill=a)
            self.text(s, 2.1, 5.55, self.W - 3.5, 0.5, [sl["by"]], 16, t["on_dark_muted"])
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

    def s_closing(self, sl):
        t = self.t
        s = self.new(dark=True)
        a = t["accents"]
        self.shape(s, MSO_SHAPE.OVAL, -2.2, self.H - 3.2, 5.5, 5.5, fill=a[0], alpha=0.2)
        self.shape(s, MSO_SHAPE.OVAL, self.W - 2.4, -1.8, 4.2, 4.2, fill=a[1 % len(a)], alpha=0.16)
        self.text(s, 1.2, 1.2, self.W - 2.4, 1.3, [sl.get("title", "Thank you")], 44, t["on_dark"], font=t["head"])
        y = 2.6
        if sl.get("subtitle"):
            self.text(s, 1.2, y, self.W - 2.4, 0.8, [sl["subtitle"]], 20, t["on_dark_muted"])
            y += 0.9
        if sl.get("bullets"):
            self.shape(s, MSO_SHAPE.RECTANGLE, 1.2, y + 0.1, 0.9, 0.06, fill=a[0])
            self.body(s, 1.2, y + 0.45, self.W - 3.2, self.H - y - 1.3, sl["bullets"], hi=22, lo=14, color=t["on_dark"], what="the closing points")
        if sl.get("contact"):
            self.text(s, 1.2, self.H - 1.0, self.W - 2.4, 0.4, [sl["contact"]], 14, t["on_dark_muted"])
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
    "theme": "midnight",
    "footer": "SAN team · capacity review",
    "slides": [
        {"type": "title", "title": "SAN capacity review Q4", "subtitle": "Where the growth went and what we buy next", "meta": "SAN team · November 2026"},
        {"type": "agenda", "items": ["Where we are", "What grew", "Risks", "The ask"]},
        {"type": "section", "title": "Where we are", "subtitle": "Four arrays, two sites"},
        {"type": "stats", "title": "Usable capacity is **78% used** across the four arrays",
         "stats": [{"value": "1.9 PB", "label": "usable capacity"}, {"value": "78%", "label": "used", "delta": "+6 pts in 90 days", "good": False},
                   {"value": "4.1:1", "label": "data reduction"}, {"value": "14", "label": "months to full at this rate"}],
         "note": "Source: Unisphere, 2026-11-01"},
        {"type": "chart", "title": "Prod-A grew fastest: 40 TB a month since July",
         "chart": {"kind": "column", "categories": ["PMAX-A", "PMAX-B", "ONTAP-1", "ONTAP-2"], "series": [{"name": "TB added", "values": [160, 70, 55, 30]}],
                   "unit": "TB", "highlight": "PMAX-A", "source": "Unisphere / Harvest"},
         "takeaway": "Prod-A takes **half** of all new capacity; the database refresh drives it."},
        {"type": "chart", "title": "Used capacity per month",
         "chart": {"kind": "line", "categories": ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov"],
                   "series": [{"name": "PMAX-A", "values": [410, 450, 492, 530, 571, 610]}, {"name": "PMAX-B", "values": [380, 392, 401, 415, 430, 452]}], "unit": "TB"}},
        {"type": "bullets", "title": "Three things drive the growth",
         "bullets": ["**Database refresh** copies on Prod-A: 12 new 4 TB LUNs", {"text": "Snapshot retention moved from 7 to 30 days", "sub": ["policy change in August"]},
                     "Two new VMware clusters on ONTAP-1"],
         "takeaway": "Reclaiming old refresh copies frees about **90 TB** without buying anything."},
        {"type": "cards", "title": "Our options", "cards": [
            {"title": "Reclaim", "text": "Remove unmapped LUNs and old refresh copies.", "icon": "90 TB"},
            {"title": "Rebalance", "text": "Move test workloads from PMAX-A to PMAX-B.", "icon": "60 TB"},
            {"title": "Expand", "text": "Add one engine of capacity to PMAX-A in Q1.", "icon": "300 TB"}]},
        {"type": "compare", "title": "Reclaim first, then expand",
         "left": {"title": "Reclaim + rebalance", "bullets": ["No purchase", "Done in 3 weeks", "Buys about 5 months"]},
         "right": {"title": "Expand now", "bullets": ["Purchase order and lead time", "Done in 10 weeks", "Buys 2+ years"]},
         "verdict": "Do both: reclaim now, order the expansion for Q1."},
        {"type": "table", "title": "Top unmapped LUNs on PMAX-A", "columns": ["LUN", "Size", "Last I/O", "Owner"],
         "rows": [["00A1F", "4 TB", "2026-03-02", "DB refresh"], ["00A20", "4 TB", "2026-03-02", "DB refresh"], ["00B07", "2 TB", "2025-11-19", "unknown"]],
         "highlight": 2, "note": "Full list: unused-luns report (Excel)"},
        {"type": "timeline", "title": "Plan", "items": [
            {"date": "Nov", "title": "Reclaim", "text": "Unmap and remove, with owners' approval."},
            {"date": "Dec", "title": "Rebalance", "text": "Move test SGs to PMAX-B."},
            {"date": "Jan", "title": "Order", "text": "Expansion PO.", "done": False},
            {"date": "Mar", "title": "Install", "text": "New capacity online.", "done": False}]},
        {"type": "process", "title": "How a reclaim is approved", "steps": [
            {"title": "Find", "text": "unused-luns report lists candidates."},
            {"title": "Ask", "text": "Owner confirms within 5 days."},
            {"title": "Unmap", "text": "Change ticket, unmap, wait 14 days."},
            {"title": "Delete", "text": "Remove and record the space freed."}]},
        {"type": "quote", "quote": "The cheapest terabyte is the one you already own.", "by": "Storage team motto"},
        {"type": "closing", "title": "The ask", "bullets": ["Approve the reclaim plan", "Budget the Q1 expansion"], "contact": "san-team@corp"},
    ],
}

# ---------------------------------------------------------------------------------------------------------- output


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
    ap.add_argument("--template")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--example", action="store_true")
    ap.add_argument("--themes", action="store_true")
    a = ap.parse_args(argv)
    if a.example:
        print(json.dumps(EXAMPLE, indent=1, ensure_ascii=False))
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
    d = Deck(spec, theme=a.theme, template=a.template)
    prs = d.build()
    name = slug(spec.get("title") or spec["slides"][0].get("title", "deck"))
    out = os.path.expanduser(a.out) if a.out else os.path.expanduser(f"~/storage-reports/{dt.date.today()}-{name}")
    path = out if out.endswith(".pptx") else os.path.join(out, name + ".pptx")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    prs.save(path)
    print(f"deck: {path} ({d.n} slides)")
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
