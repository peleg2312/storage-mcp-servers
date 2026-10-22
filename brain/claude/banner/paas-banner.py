#!/usr/bin/env python3
"""Peleg As A Service: the banner printed every time Claude Code is started (see brain/install.sh).
Standard library only. Colours: 24-bit gradient when the terminal supports it, 256-colour fallback,
plain text with NO_COLOR or when stdout is not a terminal. Layout adapts to the terminal width."""
import os
import shutil
import sys

ART = {
 "peleg": [
  "██████╗ ███████╗██╗     ███████╗ ██████╗ ",
  "██╔══██╗██╔════╝██║     ██╔════╝██╔════╝ ",
  "██████╔╝█████╗  ██║     █████╗  ██║  ███╗",
  "██╔═══╝ ██╔══╝  ██║     ██╔══╝  ██║   ██║",
  "██║     ███████╗███████╗███████╗╚██████╔╝",
  "╚═╝     ╚══════╝╚══════╝╚══════╝ ╚═════╝ "
 ],
 "service": [
  " █████╗ ███████╗     █████╗     ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗",
  "██╔══██╗██╔════╝    ██╔══██╗    ██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝",
  "███████║███████╗    ███████║    ███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗  ",
  "██╔══██║╚════██║    ██╔══██║    ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝  ",
  "██║  ██║███████║    ██║  ██║    ███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗",
  "╚═╝  ╚═╝╚══════╝    ╚═╝  ╚═╝    ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝"
 ],
 "service_small": [
  "   _           _     ___              _        ",
  "  /_\\   ___   /_\\   / __| ___ _ ___ _(_)__ ___ ",
  " / _ \\ (_-<  / _ \\  \\__ \\/ -_) '_\\ V / / _/ -_)",
  "/_/ \\_\\/__/ /_/ \\_\\ |___/\\___|_|  \\_/|_\\__\\___|"
 ]
}
TAGLINE = "storage brain for Claude Code  \u00b7  read-only  \u00b7  offline library"
# gradient stops (violet -> blue -> cyan -> mint)
STOPS = [(167, 139, 250), (96, 165, 250), (34, 211, 238), (52, 211, 153)]


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def colour_at(x, width):
    if width <= 1:
        return STOPS[0]
    pos = x / (width - 1) * (len(STOPS) - 1)
    i = min(int(pos), len(STOPS) - 2)
    return lerp(STOPS[i], STOPS[i + 1], pos - i)


def to256(rgb):
    r, g, b = (int(round(c / 255 * 5)) for c in rgb)
    return 16 + 36 * r + 6 * g + b


def mode():
    if os.getenv("NO_COLOR") or not sys.stdout.isatty() or os.getenv("TERM", "") in ("", "dumb"):
        return "plain"
    if os.getenv("COLORTERM", "").lower() in ("truecolor", "24bit") or os.getenv("TERM_PROGRAM"):
        return "truecolor"
    return "256"


def paint(line, width, m):
    if m == "plain":
        return line
    out, last = [], None
    for x, ch in enumerate(line):
        if ch == " ":
            out.append(ch)
            continue
        c = colour_at(x, width)
        code = "\033[38;2;%d;%d;%dm" % c if m == "truecolor" else "\033[38;5;%dm" % to256(c)
        if code != last:
            out.append(code)
            last = code
        out.append(ch)
    out.append("\033[0m")
    return "".join(out)


def main():
    try:                                   # piping the banner into head must not print a traceback
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass
    cols = shutil.get_terminal_size((80, 24)).columns
    m = mode()
    bold, dim, reset = ("\033[1m", "\033[2m", "\033[0m") if m != "plain" else ("", "", "")
    if cols >= 88:
        blocks = [ART["peleg"], ART["service"]]
    elif cols >= 70:
        blocks = [ART["peleg"], ART["service_small"]]
    else:
        blocks = None
    print()
    if blocks:
        width = max(len(l) for b in blocks for l in b)
        for b in blocks:
            for l in b:
                print("  " + paint(l, width, m))
        rule = "\u2500" * min(width, cols - 4)
        print("  " + paint(rule, width, m))
        print("  " + dim + TAGLINE + reset)
    else:
        print("  " + paint("\u2726  P E L E G   A S   A   S E R V I C E  \u2726", 44, m))
        print("  " + dim + TAGLINE + reset)
    print()


if __name__ == "__main__":
    main()
