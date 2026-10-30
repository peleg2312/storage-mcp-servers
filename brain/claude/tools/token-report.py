#!/usr/bin/env python3
"""Where do the tokens go? Reads Claude Code's own session logs (~/.claude/projects/**/*.jsonl, nothing is sent
anywhere) and prints, for the last N days:
  - per session: requests, fresh input, cache writes, cache reads, output (the API usage Claude Code recorded)
  - per tool: how many calls and how much text their results put into the conversation (~chars/4 tokens);
    every later request re-reads that text from the cache until /clear or /compact
  - per hook / skill listing / memory attachment: how much text it injected
Each API response and tool result is counted once, even when a resumed session copied it into another file.
usage: token-report.py [--days 7] [--top 15] [--dir ~/.claude/projects]
Standard library only (Python 3.9)."""
import argparse
import glob
import json
import os
import time
from collections import defaultdict


def text_len(content):
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(text_len(c.get("text", "") if c.get("type") == "text" else c.get("content", ""))
                   for c in content if isinstance(c, dict))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--dir", default=os.path.expanduser("~/.claude/projects"))
    a = ap.parse_args()
    since = time.time() - a.days * 86400
    sessions, tools, hooks = [], defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    names, seen, seen_tool = {}, set(), set()
    paths = [p for p in glob.glob(os.path.join(a.dir, "**", "*.jsonl"), recursive=True) if os.path.getmtime(p) >= since]
    for path in sorted(paths, key=os.path.getmtime):             # a copied message is credited to the oldest file
        u = defaultdict(int)
        for line in open(path, encoding="utf-8", errors="replace"):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            m = e.get("message") or {}
            at = e.get("attachment") if e.get("type") == "attachment" else None
            if isinstance(at, dict) and isinstance(at.get("content"), str) and \
                    at.get("type") in ("hook_success", "skill_listing", "nested_memory"):
                h = hooks[(at.get("hookEvent") or at["type"]) + ":" + (at.get("hookName") or "")]
                h[0] += 1
                h[1] += len(at["content"])
            elif e.get("type") == "assistant" and isinstance(m, dict):
                us = m.get("usage") or {}
                mid = m.get("id")
                if us and m.get("model") != "<synthetic>" and not (mid and mid in seen):  # logged once per content block
                    if mid:
                        seen.add(mid)
                    u["requests"] += 1
                    for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"):
                        u[k] += us.get(k) or 0
                for c in m.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        names[c.get("id")] = c.get("name", "?")
            elif e.get("type") == "user" and isinstance(m.get("content"), list):
                for c in m["content"]:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        tid = c.get("tool_use_id")
                        if tid and tid in seen_tool:
                            continue
                        seen_tool.add(tid)
                        t = tools[names.get(c.get("tool_use_id"), "?")]
                        t[0] += 1
                        t[1] += text_len(c.get("content"))
        if u["requests"]:
            sessions.append((os.path.basename(path)[:8], os.path.basename(os.path.dirname(path))[-40:], u))
    if not sessions:
        print(f"no sessions in the last {a.days:g} days under {a.dir}")
        return
    tot = defaultdict(int)
    for _, _, u in sessions:
        for k, v in u.items():
            tot[k] += v
    print(f"{len(sessions)} sessions, last {a.days:g} days")
    print(f"{'session':10}{'requests':>9}{'input':>10}{'cache write':>12}{'cache read':>12}{'output':>9}  project")
    rows = sorted(sessions, key=lambda s: -s[2]["cache_read_input_tokens"])[:a.top]
    for sid, proj, u in rows + [("TOTAL", "", tot)]:
        print(f"{sid:10}{u['requests']:>9}{u['input_tokens']:>10}{u['cache_creation_input_tokens']:>12}"
              f"{u['cache_read_input_tokens']:>12}{u['output_tokens']:>9}  {proj}")
    print(f"\nTool results put into conversations (~tokens = chars/4; each is re-read on every later request):")
    print(f"{'tool':58}{'calls':>7}{'~tokens':>10}{'avg':>8}")
    for name, (n, chars) in sorted(tools.items(), key=lambda kv: -kv[1][1])[:a.top]:
        print(f"{name[:57]:58}{n:>7}{chars // 4:>10}{chars // 4 // max(n, 1):>8}")
    if hooks:
        print(f"\nHook / skill-listing / memory text injected into conversations (~tokens = chars/4):")
        print(f"{'source':58}{'events':>7}{'~tokens':>10}{'avg':>8}")
        for name, (n, chars) in sorted(hooks.items(), key=lambda kv: -kv[1][1])[:a.top]:
            print(f"{name[:57]:58}{n:>7}{chars // 4:>10}{chars // 4 // max(n, 1):>8}")


if __name__ == "__main__":
    main()
