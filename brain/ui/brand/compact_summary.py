#!/usr/bin/env python3
"""The web UI draws a compaction summary as a message the user sent when the CLI stores it as a list of text blocks
(newer CLIs) or when it arrives live without its isCompactSummary flag: upstream only recognises a plain-string,
flagged summary. This folds such a row into one flagged string before the upstream normaliser sees it, so it is drawn
as the compaction row's summary.

    python3 compact_summary.py <claude-sessions.provider.js>         an installed bundle (dist-server), in place
    python3 compact_summary.py <claude-sessions.provider.ts> --ts    a checkout, before the build (brand.py)

Idempotent: a file that already has it is left alone. Exit 1 when the upstream text is not found."""
import re
import sys

PREAMBLE = "This session is being continued from a previous conversation"


def helper(ts):
    a = ": any" if ts else ""
    return (
        f"function paasCompactSummary(raw{a}){a} {{\n"
        "  // brain: a compaction summary stored as text blocks, or live without its flag, becomes one flagged string\n"
        "  if (!raw || typeof raw !== 'object' || raw.isMeta === true || raw.message?.role !== 'user') return raw;\n"
        "  const c = raw.message.content;\n"
        f"  const text = Array.isArray(c) && c.length > 0 && c.every((p{a}) => p && p.type === 'text')\n"
        f"    ? c.map((p{a}) => p.text || '').join('\\n') : typeof c === 'string' ? c : null;\n"
        f"  if (text === null || !(raw.isCompactSummary === true || /^{PREAMBLE}/.test(text.trim()))) return raw;\n"
        "  return { ...raw, isCompactSummary: true, message: { ...raw.message, content: text } };\n"
        "}\n\n")


def patch(path, ts=False):
    s = open(path, encoding="utf-8").read()
    if "paasCompactSummary" in s:
        return False
    call = re.compile(r"(normalizeMessage\(rawMessage(?:: unknown)?, sessionId(?:: string \| null)?\)(?:: NormalizedMessage\[\])? \{\n)(\s*)(const messages = this\.normalizeMessageRows\(rawMessage, sessionId\);)")
    anchor = re.compile(r"^function isInternalContent\(", re.M)
    if not call.search(s) or not anchor.search(s):
        sys.exit(f"compact_summary: upstream text not found in {path} (update brain/ui/brand/compact_summary.py)")
    s = call.sub(lambda m: f"{m.group(1)}{m.group(2)}rawMessage = paasCompactSummary(rawMessage);\n{m.group(2)}{m.group(3)}", s, count=1)
    m = anchor.search(s)
    s = s[:m.start()] + helper(ts) + s[m.start():]
    open(path, "w", encoding="utf-8").write(s)
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print("compact summary: " + ("patched " if patch(sys.argv[1], "--ts" in sys.argv) else "already in ") + sys.argv[1])
