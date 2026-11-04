"""Offline line icons for deck.py: drawn as editable PowerPoint shapes (custom geometry), so they recolour and scale in
PowerPoint like any shape. Original drawings on a 24 x 24 grid, 2-unit strokes, round caps. Standard library only.

Primitives: ("circle", cx, cy, r) ("ellipse", cx, cy, rx, ry) ("rect", x, y, w, h, r) ("line", x1, y1, x2, y2)
("poly", [(x, y), ...], closed) ("arc", cx, cy, rx, ry, a0, a1)   (degrees, 0 = right, 90 = down)
("path", [("M", x, y), ("L", x, y), ("C", x1, y1, x2, y2, x, y), ("A", cx, cy, rx, ry, a0, a1), ("Z",)])"""
import math


def _star(n, ro, ri, cx=12, cy=12.5):
    pts = []
    for i in range(2 * n):
        a = math.pi * i / n - math.pi / 2
        r = ro if i % 2 == 0 else ri
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return ("poly", pts, True)


def _gear():
    pts = []
    for i in range(32):
        a = 2 * math.pi * i / 32 - math.pi / 2
        r = 9.5 if (i // 2) % 2 == 0 else 7.2
        pts.append((12 + r * math.cos(a), 12 + r * math.sin(a)))
    return ("poly", pts, True)


ICONS = {
    "database": [("ellipse", 12, 5, 8, 3), ("line", 4, 5, 4, 19), ("line", 20, 5, 20, 19), ("arc", 12, 19, 8, 3, 0, 180),
                 ("arc", 12, 12, 8, 3, 0, 180)],
    "server": [("rect", 3, 3, 18, 7, 2), ("rect", 3, 14, 18, 7, 2), ("circle", 7, 6.5, 0.7), ("circle", 7, 17.5, 0.7),
               ("line", 11, 6.5, 17, 6.5), ("line", 11, 17.5, 17, 17.5)],
    "disk": [("rect", 3, 5, 18, 14, 2), ("line", 3, 13, 21, 13), ("circle", 17, 16, 0.7), ("circle", 13.5, 16, 0.7)],
    "network": [("circle", 12, 5, 2.5), ("circle", 5, 19, 2.5), ("circle", 19, 19, 2.5), ("line", 12, 7.5, 12, 13),
                ("poly", [(5, 16.5), (5, 13), (19, 13), (19, 16.5)], False)],
    "switch": [("rect", 2, 8, 20, 8, 2), ("circle", 6, 12, 0.7), ("circle", 9.5, 12, 0.7), ("circle", 13, 12, 0.7),
               ("line", 16.5, 12, 18.5, 12)],
    "cloud": [("path", [("M", 6.5, 18), ("A", 6.5, 14.5, 3.5, 3.5, 90, 270), ("A", 12, 10, 5.5, 5.5, 169.7, 350),
                        ("A", 17.5, 13.5, 4.5, 4.5, 269, 450), ("Z",)])],
    "monitor": [("rect", 3, 4, 18, 12, 2), ("line", 8, 20, 16, 20), ("line", 12, 16, 12, 20)],
    "cpu": [("rect", 6, 6, 12, 12, 1.5), ("rect", 9.5, 9.5, 5, 5, 0.5)]
           + [("line", x, a, x, b) for x in (9, 12, 15) for a, b in ((2, 6), (18, 22))]
           + [("line", a, y, b, y) for y in (9, 12, 15) for a, b in ((2, 6), (18, 22))],
    "layers": [("poly", [(12, 3), (21, 8), (12, 13), (3, 8)], True), ("poly", [(3, 12.5), (12, 17.5), (21, 12.5)], False),
               ("poly", [(3, 17), (12, 22), (21, 17)], False)],
    "archive": [("rect", 3, 4, 18, 5, 1), ("poly", [(5, 9), (5, 20), (19, 20), (19, 9)], False), ("line", 10, 13, 14, 13)],
    "shield": [("path", [("M", 12, 3), ("L", 19.5, 6), ("L", 19.5, 11), ("C", 19.5, 16, 16, 19.5, 12, 21),
                         ("C", 8, 19.5, 4.5, 16, 4.5, 11), ("L", 4.5, 6), ("Z",)]), ("poly", [(9, 12), (11.2, 14.2), (15, 10)], False)],
    "lock": [("rect", 5, 11, 14, 10, 2), ("path", [("M", 8, 11), ("L", 8, 7.5), ("A", 12, 7.5, 4, 4, 180, 360), ("L", 16, 11)]),
             ("line", 12, 15, 12, 17)],
    "key": [("circle", 7.5, 15.5, 4), ("line", 10.4, 12.6, 20, 3), ("line", 17, 6, 19.5, 8.5), ("line", 14.5, 8.5, 16.5, 10.5)],
    "check": [("circle", 12, 12, 9), ("poly", [(8, 12.5), (11, 15.2), (16.2, 9.5)], False)],
    "alert": [("path", [("M", 12, 3.5), ("L", 21.5, 20), ("L", 2.5, 20), ("Z",)]), ("line", 12, 9.5, 12, 14), ("circle", 12, 17, 0.7)],
    "error": [("circle", 12, 12, 9), ("line", 9, 9, 15, 15), ("line", 15, 9, 9, 15)],
    "info": [("circle", 12, 12, 9), ("line", 12, 11, 12, 16.5), ("circle", 12, 7.8, 0.7)],
    "clock": [("circle", 12, 12, 9), ("poly", [(12, 7), (12, 12), (15.5, 14)], False)],
    "calendar": [("rect", 3, 5, 18, 16, 2), ("line", 3, 10, 21, 10), ("line", 8, 3, 8, 7), ("line", 16, 3, 16, 7)],
    "chart": [("line", 3, 20.5, 21, 20.5), ("rect", 5, 13, 3, 7.5, 0.6), ("rect", 10.5, 7, 3, 13.5, 0.6), ("rect", 16, 10.5, 3, 10, 0.6)],
    "trend-up": [("poly", [(3, 17), (9, 11), (13, 15), (21, 7)], False), ("poly", [(15, 7), (21, 7), (21, 13)], False)],
    "trend-down": [("poly", [(3, 7), (9, 13), (13, 9), (21, 17)], False), ("poly", [(15, 17), (21, 17), (21, 11)], False)],
    "gauge": [("arc", 12, 15, 9, 9, 180, 360), ("line", 3, 15, 21, 15), ("line", 12, 15, 16.5, 9.5), ("circle", 12, 15, 1)],
    "money": [("circle", 12, 12, 9), ("path", [("M", 15, 9.2), ("C", 15, 7.8, 13.7, 7, 12, 7), ("C", 10.2, 7, 9, 7.9, 9, 9.3),
                                                ("C", 9, 12.2, 15, 11.6, 15, 14.7), ("C", 15, 16.1, 13.8, 17, 12, 17), ("C", 10.2, 17, 9, 16.2, 9, 14.8)]),
              ("line", 12, 5.2, 12, 7), ("line", 12, 17, 12, 18.8)],
    "users": [("circle", 9, 8, 3.5), ("path", [("M", 2.5, 20), ("C", 2.5, 16, 5.5, 14, 9, 14), ("C", 12.5, 14, 15.5, 16, 15.5, 20)]),
              ("circle", 17, 8.5, 2.5), ("path", [("M", 17.5, 13.5), ("C", 20, 13.8, 21.5, 15.8, 21.5, 19)])],
    "user": [("circle", 12, 8, 4), ("path", [("M", 4, 21), ("C", 4, 16.5, 7.5, 14, 12, 14), ("C", 16.5, 14, 20, 16.5, 20, 21)])],
    "gear": [_gear(), ("circle", 12, 12, 3)],
    "search": [("circle", 10.5, 10.5, 6.5), ("line", 15.3, 15.3, 21, 21)],
    "document": [("poly", [(14, 3), (6, 3), (6, 21), (18, 21), (18, 7), (14, 3)], True), ("poly", [(14, 3), (14, 7), (18, 7)], False),
                 ("line", 9, 12, 15, 12), ("line", 9, 16, 15, 16)],
    "folder": [("path", [("M", 3, 6), ("L", 9.5, 6), ("L", 11.5, 8.5), ("L", 21, 8.5), ("L", 21, 19), ("L", 3, 19), ("Z",)])],
    "lightning": [("poly", [(13, 2), (4, 14), (12, 14), (11, 22), (20, 10), (12, 10)], True)],
    "target": [("circle", 12, 12, 9), ("circle", 12, 12, 5), ("circle", 12, 12, 1)],
    "idea": [("path", [("M", 7.76, 13.74), ("A", 12, 9.5, 6, 6, 135, 405), ("L", 15, 17), ("L", 9, 17), ("Z",)]), ("line", 9.5, 20.5, 14.5, 20.5)],
    "flag": [("line", 5, 21, 5, 3), ("path", [("M", 5, 4), ("L", 19, 4), ("L", 16, 8.5), ("L", 19, 13), ("L", 5, 13)])],
    "globe": [("circle", 12, 12, 9), ("line", 3, 12, 21, 12), ("ellipse", 12, 12, 4, 9)],
    "mail": [("rect", 3, 5, 18, 14, 2), ("poly", [(3.5, 6.5), (12, 13), (20.5, 6.5)], False)],
    "star": [_star(5, 9.5, 4.2)],
    "link": [("rect", 2, 8.5, 11, 7, 3.5), ("rect", 11, 8.5, 11, 7, 3.5)],
    "arrow-right": [("line", 4, 12, 20, 12), ("poly", [(14, 6), (20, 12), (14, 18)], False)],
    "rocket": [("path", [("M", 12, 2.5), ("C", 15.5, 5, 16.5, 9, 16, 14), ("L", 8, 14), ("C", 7.5, 9, 8.5, 5, 12, 2.5), ("Z",)]),
               ("circle", 12, 8.5, 1.6), ("poly", [(8, 12), (5, 15), (5, 18), (8.5, 16)], False),
               ("poly", [(16, 12), (19, 15), (19, 18), (15.5, 16)], False), ("line", 10.5, 17.5, 10.5, 21), ("line", 13.5, 17.5, 13.5, 21)],
    "replication": [("rect", 2.5, 4, 8, 6, 1.5), ("rect", 13.5, 14, 8, 6, 1.5), ("path", [("M", 6.5, 10), ("L", 6.5, 17), ("L", 13.5, 17)]),
                    ("poly", [(11, 14.5), (13.5, 17), (11, 19.5)], False)],
}
ALIASES = {"storage": "database", "array": "database", "ok": "check", "done": "check", "warning": "alert", "risk": "alert",
           "fail": "error", "time": "clock", "security": "shield", "cost": "money", "growth": "trend-up", "decline": "trend-down",
           "team": "users", "person": "user", "settings": "gear", "doc": "document", "file": "document", "power": "lightning",
           "fast": "lightning", "goal": "target", "plan": "calendar", "fabric": "switch", "vm": "monitor", "host": "server",
           "backup": "archive", "performance": "gauge", "capacity": "chart", "dr": "replication", "launch": "rocket"}


ALIASES.update({"success": "check", "pass": "check", "passed": "check", "complete": "check", "completed": "check", "yes": "check",
                "failed": "error", "failure": "error", "down": "error", "broken": "error", "incident": "alert", "issue": "alert",
                "problem": "alert", "danger": "alert", "warn": "alert", "restore": "replication", "recovery": "replication",
                "replicate": "replication", "sync": "replication", "copy": "replication", "snapshot": "layers", "snapshots": "layers",
                "clone": "layers", "volume": "disk", "lun": "disk", "drive": "disk", "library": "archive", "tape": "archive",
                "s3": "cloud", "bucket": "cloud", "object": "cloud", "files": "folder", "file-server": "folder", "share": "folder",
                "nfs": "folder", "cifs": "folder", "db": "database", "sql": "database", "oracle": "database", "postgres": "database",
                "postgresql": "database", "exchange": "mail", "email": "mail", "k8s": "layers", "kubernetes": "layers",
                "openshift": "layers", "cluster": "server", "node": "server", "mediaagent": "server", "proxy": "server",
                "commserve": "server", "vbr": "server", "network": "network", "dns": "network", "lan": "network", "move": "arrow-right",
                "next": "arrow-right", "step": "arrow-right", "migrate": "arrow-right", "upgrade": "rocket", "new": "star",
                "best": "star", "quality": "star", "speed": "lightning", "slow": "clock", "schedule": "calendar", "date": "calendar",
                "deadline": "flag", "milestone": "flag", "report": "document", "docs": "document", "policy": "document",
                "audit": "search", "scan": "search", "check-up": "search", "find": "search", "review": "search", "cpu": "cpu",
                "compute": "cpu", "encryption": "lock", "password": "key", "access": "key", "permission": "key", "compliance": "shield",
                "protect": "shield", "protection": "shield", "budget": "money", "price": "money", "money-bag": "money",
                "trend": "trend-up", "up": "trend-up", "increase": "trend-up", "decrease": "trend-down", "drop": "trend-down",
                "metric": "gauge", "kpi": "gauge", "sla": "gauge", "rpo": "clock", "rto": "clock", "people": "users", "owner": "user",
                "contact": "mail", "global": "globe", "site": "globe", "region": "globe", "link": "link", "integration": "link",
                "nothing": "info", "note": "info", "question": "info", "tip": "idea", "solution": "idea", "fix": "gear",
                "configuration": "gear", "config": "gear", "tool": "gear", "automation": "gear", "monitoring": "monitor",
                "dashboard": "monitor", "screen": "monitor"})
# Hebrew words a model may give as an icon name or write in the item (matched on the word)
HEBREW = {"גיבוי": "archive", "גיבויים": "archive", "שחזור": "replication", "שחזורים": "replication", "שכפול": "replication",
          "בדיקה": "search", "בדיקות": "search", "סריקה": "search", "אבטחה": "shield", "הגנה": "shield", "תקלה": "alert",
          "תקלות": "alert", "כשל": "error", "כשלים": "error", "שגיאה": "error", "הצלחה": "check", "תקין": "check", "בוצע": "check",
          "זמן": "clock", "שעה": "clock", "לוח": "calendar", "תאריך": "calendar", "כסף": "money", "עלות": "money", "תקציב": "money",
          "צוות": "users", "אנשים": "users", "משתמש": "user", "שרת": "server", "שרתים": "server", "רשת": "network",
          "אחסון": "database", "מסד": "database", "נתונים": "database", "ענן": "cloud", "קיבולת": "chart", "נפח": "chart",
          "ביצועים": "gauge", "מדד": "gauge", "יעד": "target", "מטרה": "target", "שדרוג": "rocket", "אוטומציה": "gear",
          "הגדרות": "gear", "מסמך": "document", "דוח": "document", "מדיניות": "document", "מפתח": "key", "הצפנה": "lock",
          "תיקיה": "folder", "קבצים": "folder", "רעיון": "idea", "פתרון": "idea", "צעד": "arrow-right", "שלב": "arrow-right"}


def resolve(name):
    n = str(name or "").strip().lower()
    n = ALIASES.get(n, HEBREW.get(n, n))
    return n if n in ICONS else None


def guess(name="", *context):
    """the icon for a name a model made up ("restore-db", "warning_sign", "גיבוי") or, without one, for the item's own words:
    the name itself, then each word of it, then the words of the context (title, text); None when nothing matches"""
    hit = resolve(name)
    if hit:
        return hit
    import re
    for src in (str(name or ""),) + tuple(str(c or "") for c in context):
        for w in re.split("[^a-z0-9\u0590-\u05FF]+", src.lower()):
            if not w:
                continue
            hit = resolve(w) or (resolve(w[:-1]) if w.endswith("s") else None)
            if hit:
                return hit
            if w.startswith(("ה", "ב", "ל", "מ", "ו", "ש")) and len(w) > 3:      # Hebrew prefixes: "הגיבוי", "בשרת"
                hit = resolve(w[1:])
                if hit:
                    return hit
    return None


def _arc(cx, cy, rx, ry, a0, a1):
    """cubic segments (<= 90 degrees each) of an elliptical arc from a0 to a1 (degrees, either direction)"""
    out = []
    n = max(1, int(math.ceil(abs(a1 - a0) / 90.0)))
    step = math.radians(a1 - a0) / n
    t = math.radians(a0)
    k = 4.0 / 3.0 * math.tan(step / 4)
    for _ in range(n):
        t2 = t + step
        p0 = (cx + rx * math.cos(t), cy + ry * math.sin(t))
        p3 = (cx + rx * math.cos(t2), cy + ry * math.sin(t2))
        c1 = (p0[0] - k * rx * math.sin(t), p0[1] + k * ry * math.cos(t))
        c2 = (p3[0] + k * rx * math.sin(t2), p3[1] - k * ry * math.cos(t2))
        out.append(("C",) + c1 + c2 + p3)
        t = t2
    return out


def paths(name):
    """the icon as a list of paths, each [("M", x, y) | ("L", x, y) | ("C", ...) | ("Z",)], closed flag"""
    out = []
    for p in ICONS[name]:
        kind = p[0]
        if kind in ("circle", "ellipse"):
            cx, cy = p[1], p[2]
            rx, ry = (p[3], p[3]) if kind == "circle" else (p[3], p[4])
            out.append([("M", cx + rx, cy)] + _arc(cx, cy, rx, ry, 0, 360) + [("Z",)])
        elif kind == "arc":
            cx, cy, rx, ry, a0, a1 = p[1:]
            out.append([("M", cx + rx * math.cos(math.radians(a0)), cy + ry * math.sin(math.radians(a0)))] + _arc(cx, cy, rx, ry, a0, a1))
        elif kind == "rect":
            x, y, w, h, r = p[1:]
            r = min(r, w / 2, h / 2)
            seg = [("M", x + r, y), ("L", x + w - r, y)] + (_arc(x + w - r, y + r, r, r, 270, 360) if r else []) + [("L", x + w, y + h - r)]
            seg += (_arc(x + w - r, y + h - r, r, r, 0, 90) if r else []) + [("L", x + r, y + h)]
            seg += (_arc(x + r, y + h - r, r, r, 90, 180) if r else []) + [("L", x, y + r)]
            seg += (_arc(x + r, y + r, r, r, 180, 270) if r else []) + [("Z",)]
            out.append(seg)
        elif kind == "line":
            out.append([("M", p[1], p[2]), ("L", p[3], p[4])])
        elif kind == "poly":
            pts, closed = p[1], p[2]
            out.append([("M",) + tuple(pts[0])] + [("L",) + tuple(q) for q in pts[1:]] + ([("Z",)] if closed else []))
        elif kind == "path":
            seg = []
            for op in p[1]:
                if op[0] == "A":
                    cx, cy, rx, ry, a0, a1 = op[1:]
                    if not seg:
                        seg.append(("M", cx + rx * math.cos(math.radians(a0)), cy + ry * math.sin(math.radians(a0))))
                    seg += _arc(cx, cy, rx, ry, a0, a1)
                else:
                    seg.append(op)
            out.append(seg)
    return out
