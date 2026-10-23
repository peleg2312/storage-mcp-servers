#!/usr/bin/env python3
"""Peleg As A Service: the banner printed when Claude Code starts (the `claude` wrapper, brain/install.sh) and,
with --login, at every login on the VM (/etc/profile.d, install-vm.sh --login-banner).
Standard library only; fast (no network, no subprocess). Colours: 24-bit diagonal gradient when the terminal
supports it, 256-colour fallback, plain text with NO_COLOR or when stdout is not a terminal; ASCII letters when
the terminal is not UTF-8; compact layout below 90 columns.

    python3 paas-banner.py            Claude start: logo + brain card (library, skills, agents, mode)
    python3 paas-banner.py --login    VM login: logo + system card (host, OS, uptime, load, memory, disk)
"""
import getpass
import glob
import os
import re
import shutil
import socket
import sys
import time

PELEG = [
    "██████╗ ███████╗██╗     ███████╗ ██████╗ ",
    "██╔══██╗██╔════╝██║     ██╔════╝██╔════╝ ",
    "██████╔╝█████╗  ██║     █████╗  ██║  ███╗",
    "██╔═══╝ ██╔══╝  ██║     ██╔══╝  ██║   ██║",
    "██║     ███████╗███████╗███████╗╚██████╔╝",
    "╚═╝     ╚══════╝╚══════╝╚══════╝ ╚═════╝ ",
]
SERVICE = [
    " █████╗ ███████╗     █████╗     ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗",
    "██╔══██╗██╔════╝    ██╔══██╗    ██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝",
    "███████║███████╗    ███████║    ███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗  ",
    "██╔══██║╚════██║    ██╔══██║    ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝  ",
    "██║  ██║███████║    ██║  ██║    ███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗",
    "╚═╝  ╚═╝╚══════╝    ╚═╝  ╚═╝    ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝",
]
ASCII = [
    " ____      _               _          _       ____                  _          ",
    "|  _ \\ ___| | ___  __ _   / \\   ___  / \\     / ___|  ___ _ ____   _(_) ___ ___ ",
    "| |_) / _ \\ |/ _ \\/ _` | / _ \\ / __|/ _ \\    \\___ \\ / _ \\ '__\\ \\ / / |/ __/ _ \\",
    "|  __/  __/ |  __/ (_| |/ ___ \\\\__ \\ ___ \\    ___) |  __/ |   \\ V /| | (_|  __/",
    "|_|   \\___|_|\\___|\\__, /_/   \\_\\___/_/   \\_\\  |____/ \\___|_|    \\_/ |_|\\___\\___|",
    "                  |___/                                                       ",
]
TAGLINE = "storage brain for Claude Code"
STOPS = [(167, 139, 250), (129, 140, 248), (96, 165, 250), (34, 211, 238), (52, 211, 153)]  # violet -> mint
SHADOW = set("╔╗╚╝═║")                                   # the letters' 3-D edge: drawn darker


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def gradient(t):
    t = min(max(t, 0.0), 1.0) * (len(STOPS) - 1)
    i = min(int(t), len(STOPS) - 2)
    return lerp(STOPS[i], STOPS[i + 1], t - i)


def to256(rgb):
    r, g, b = (int(round(c / 255 * 5)) for c in rgb)
    return 16 + 36 * r + 6 * g + b


def colour_mode():
    if os.getenv("FORCE_COLOR") and not os.getenv("NO_COLOR"):
        return "truecolor"
    if os.getenv("NO_COLOR") or not sys.stdout.isatty() or os.getenv("TERM", "") in ("", "dumb"):
        return "plain"
    if os.getenv("COLORTERM", "").lower() in ("truecolor", "24bit") or os.getenv("TERM_PROGRAM") \
            or "direct" in os.getenv("TERM", ""):
        return "truecolor"
    return "256"


def utf8():
    """The locale decides (Python itself reports UTF-8 even in the C locale): no locale set = UTF-8."""
    loc = (os.getenv("LC_ALL") or os.getenv("LC_CTYPE") or os.getenv("LANG") or "").lower()
    return not loc or "utf" in loc


class Paint:
    def __init__(self, mode):
        self.m = mode

    def fg(self, rgb):
        if self.m == "plain":
            return ""
        return "\033[38;2;%d;%d;%dm" % rgb if self.m == "truecolor" else "\033[38;5;%dm" % to256(rgb)

    def sgr(self, code):
        return "" if self.m == "plain" else f"\033[{code}m"

    def art(self, lines, width, row0, rows):
        """Diagonal gradient (left to right, a little top to bottom); shadow edges darker."""
        out = []
        for y, line in enumerate(lines):
            buf, last = [], None
            for x, ch in enumerate(line):
                if ch == " " or self.m == "plain":
                    buf.append(ch)
                    continue
                rgb = gradient(x / max(width - 1, 1) * 0.85 + (row0 + y) / max(rows - 1, 1) * 0.15)
                if ch in SHADOW:
                    rgb = tuple(int(c * 0.45) for c in rgb)
                code = self.fg(rgb)
                if code != last:
                    buf.append(code)
                    last = code
                buf.append(ch)
            out.append("".join(buf) + self.sgr(0))
        return out

    def rule(self, n, ch):
        if self.m == "plain":
            return ch * n
        return "".join(self.fg(gradient(i / max(n - 1, 1))) + ch for i in range(n)) + self.sgr(0)


def visible(s):
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def center(s, cols):
    return " " * max((cols - visible(s)) // 2, 0) + s


def center_block(lines, width, cols):
    """One left margin for the whole block, so the letters stay aligned."""
    pad = " " * max((cols - width) // 2, 0)
    return [pad + l if l else "" for l in lines]


def human(n):
    for unit in ("B", "K", "M", "G", "T", "P"):
        if n < 1024 or unit == "P":
            return f"{n:.0f}{unit}" if unit in ("B", "K") else f"{n:.1f}{unit}"
        n /= 1024


def brain_facts():
    """Library version / documents, skills and agents of the install this banner belongs to."""
    here = os.path.dirname(os.path.abspath(__file__))
    home_claude = os.path.expanduser("~/.claude")
    base = os.path.dirname(here) if os.path.basename(os.path.dirname(here)) == ".claude" else home_claude
    lib = os.path.join(home_claude, "brain", "library")
    facts = []
    try:
        ver = open(os.path.join(lib, "VERSION")).read().strip()
        m = re.search(r"\*\*(\d+) unique documents", open(os.path.join(lib, "MANIFEST.md")).read(4000))
        facts.append(("library", f"{ver}" + (f" · {int(m.group(1)):,} docs" if m else "")))
    except OSError:
        facts.append(("library", "not installed"))
    skills = len(glob.glob(os.path.join(base, "skills", "*", "SKILL.md")))
    agents = len(glob.glob(os.path.join(base, "agents", "*.md")))
    if skills or agents:
        facts.append(("brain", f"{skills} skills · {agents} agents"))
    facts.append(("mode", "read-only · offline"))
    return facts


def system_facts():
    facts = [("host", socket.gethostname().split(".")[0]), ("user", getpass.getuser())]
    try:
        rel = dict(l.rstrip().split("=", 1) for l in open("/etc/os-release") if "=" in l)
        facts.append(("os", rel.get("PRETTY_NAME", "").strip('"')))
    except OSError:
        pass
    try:
        up = float(open("/proc/uptime").read().split()[0])
        d, h, mnt = int(up // 86400), int(up % 86400 // 3600), int(up % 3600 // 60)
        facts.append(("uptime", (f"{d}d " if d else "") + f"{h}h {mnt}m"))
    except OSError:
        pass
    try:
        facts.append(("load", " ".join(f"{x:.2f}" for x in os.getloadavg())))
    except (OSError, AttributeError):
        pass
    try:
        mem = {l.split(":")[0]: int(l.split()[1]) * 1024 for l in open("/proc/meminfo")}
        total, avail = mem["MemTotal"], mem.get("MemAvailable", mem.get("MemFree", 0))
        facts.append(("memory", f"{human(total - avail)} / {human(total)}"))
    except (OSError, KeyError, ValueError, IndexError):
        pass
    try:
        du = shutil.disk_usage("/")
        facts.append(("disk /", f"{human(du.used)} / {human(du.total)} ({du.used * 100 // du.total}%)"))
    except OSError:
        pass
    facts.append(("time", time.strftime("%a %d %b %Y %H:%M")))
    return facts


def card(facts, p, cols, uni):
    """Facts as 'key value' chips, wrapped to the terminal width and centred."""
    sep = "  ·  " if not uni else "  ◆  "
    chips = [p.sgr("2") + k + p.sgr(0) + " " + p.sgr("1") + v + p.sgr(0) for k, v in facts if v]
    lines, cur = [], ""
    for c in chips:
        cand = c if not cur else cur + p.sgr("2") + sep + p.sgr(0) + c
        if cur and visible(cand) > cols - 4:
            lines.append(cur)
            cur = c
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return [center(l, cols) for l in lines]


def main():
    try:                                   # piping the banner into head must not print a traceback
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass
    login = "--login" in sys.argv[1:]
    cols = shutil.get_terminal_size((100, 24)).columns
    p, uni = Paint(colour_mode()), utf8()
    out, logo_w = [""], 48
    if uni and cols >= 90:
        blocks = PELEG + [""] + SERVICE                  # one gradient over both words, each word centred
        art = p.art(blocks, max(len(l) for l in blocks), 0, len(blocks))
        out += center_block(art[:len(PELEG)], len(PELEG[0]), cols) + [""]
        out += center_block(art[len(PELEG) + 1:], len(SERVICE[0]), cols)
        logo_w = len(SERVICE[0])
    elif cols >= 82:
        width = max(len(l) for l in ASCII)
        out += center_block(p.art(ASCII, width, 0, len(ASCII)), width, cols)
        logo_w = width
    else:
        title = "✦  P E L E G   A S   A   S E R V I C E  ✦" if uni else "*  P E L E G   A S   A   S E R V I C E  *"
        out.append(center(p.art([title], len(title), 0, 1)[0], cols))
    n = min(cols - 4, logo_w)
    out.append(center(p.rule(n, "━" if uni else "-"), cols))
    tag = TAGLINE + (" · VM ready" if login else "")
    out.append(center(p.sgr("1") + p.fg(STOPS[3]) + ("✦ " if uni else "") + tag + (" ✦" if uni else "") + p.sgr(0), cols))
    out.append("")
    out += card(system_facts() if login else brain_facts(), p, cols, uni)
    if login and shutil.which("claude"):
        out.append("")
        out.append(center(p.sgr("2") + "type " + p.sgr(0) + p.sgr("1") + p.fg(STOPS[0]) + "claude" + p.sgr(0)
                          + p.sgr("2") + " to start the storage brain" + p.sgr(0), cols))
    out.append("")
    text = "\n".join(out)
    if not uni:                                          # non-UTF-8 terminal: nothing outside ASCII
        text = text.translate({0x00b7: "-", 0x25c6: "*", 0x2501: "-", 0x2726: "*"}).encode("ascii", "replace").decode()
    print(text)


if __name__ == "__main__":
    main()
