#!/usr/bin/env python3
"""Peleg As A Service: the Claude Code status line (settings.json "statusLine", set by brain/install.sh).
Claude Code pipes a JSON object on stdin (model, workspace, context_window, cost...); every field is
optional here, so it never breaks when the format changes. Standard library only."""
import json
import os
import sys

V, B, C, G, D, R = "\033[38;5;141m", "\033[1m", "\033[38;5;80m", "\033[38;5;78m", "\033[2m", "\033[0m"
Y, RED = "\033[38;5;221m", "\033[38;5;203m"


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        d = {}
    model = (d.get("model") or {}).get("display_name") or (d.get("model") or {}).get("id") or ""
    cwd = (d.get("workspace") or {}).get("current_dir") or d.get("cwd") or os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    ctx = d.get("context_window") or {}
    left = ctx.get("remaining_percentage")
    if left is None and ctx.get("used_percentage") is not None:
        left = 100 - ctx["used_percentage"]
    parts = [V + B + "✦ Peleg As A Service ✦" + R]
    if model:
        parts.append(C + model + R)
    parts.append(G + cwd + R)
    if left is not None:                     # green, then yellow below 50%, red below 20%: time to /compact
        col = G if left >= 50 else Y if left >= 20 else RED
        parts.append(col + f"context {int(left)}% left" + R)
    cost = (d.get("cost") or {}).get("total_cost_usd")
    if isinstance(cost, (int, float)) and cost > 0:
        parts.append(D + f"${cost:.2f}" + R)
    print((D + " │ " + R).join(parts))


if __name__ == "__main__":
    main()
