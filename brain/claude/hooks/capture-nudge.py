#!/usr/bin/env python3
"""Claude Code Stop hook: after a substantial session (20+ tool calls) that captured nothing, ask Claude ONCE
whether it learned something durable and, if so, to write a capture (brain-learn skill). One marker per session
under ~/.claude/brain/.nudged keeps it from asking twice. Off with BRAIN_NUDGE_DISABLE=1; threshold in
BRAIN_NUDGE_MIN_TOOLS. Silent on any error; exit 0 always."""
import json
import os
import re
import sys
import time

REASON = (
    "This was a substantial session and nothing was captured. Check whether it produced durable, non-obvious "
    "knowledge: a root cause, a workaround, a quirk of this environment, a procedure that worked, a wrong "
    "assumption corrected, a fixed problem. If yes, write a capture with the brain-learn skill (a file under "
    "~/.claude/brain/captures/<date>-<slug>.md with symptom, cause, fix, scope, how we know, confidence) and tell "
    "the user in two lines. If not, reply with one short line saying nothing needed capturing and stop. "
    "Do not repeat your previous answer.")


def main():
    if os.environ.get("BRAIN_NUDGE_DISABLE") == "1":
        return 0
    try:
        data = json.load(sys.stdin)
        if data.get("stop_hook_active"):
            return 0
        need = int(os.environ.get("BRAIN_NUDGE_MIN_TOOLS") or 20)
        sid = os.path.basename(str(data.get("session_id") or ""))
        text = open(data.get("transcript_path") or "", encoding="utf-8", errors="replace").read()
    except (OSError, ValueError):
        return 0
    if not sid or text.count('"type":"tool_use"') + text.count('"type": "tool_use"') < need:
        return 0
    # a capture or note was written this session (a mention of the paths in prose does not count)
    if re.search(r'"file_path"\s*:\s*"[^"]*brain/(?:captures/|notes/|notes\.md)', text):
        return 0
    d = os.path.expanduser("~/.claude/brain/.nudged")
    try:
        os.makedirs(d, mode=0o700, exist_ok=True)
        for f in os.listdir(d):
            p = os.path.join(d, f)
            if time.time() - os.path.getmtime(p) > 14 * 86400:
                os.remove(p)
        marker = os.path.join(d, sid)
        if os.path.exists(marker):
            return 0
        open(marker, "w").close()
    except OSError:
        return 0
    print(json.dumps({"decision": "block", "reason": REASON}))
    return 0


if __name__ == "__main__":
    # a team plugin on a VM whose managed settings run this hook for every account: that copy is the enforced one
    if len(sys.argv) == 1 and os.environ.get("CLAUDE_PLUGIN_ROOT"):
        try:
            if os.path.basename(__file__) in open(os.environ.get("PAAS_MANAGED_SETTINGS") or "/etc/claude-code/managed-settings.json").read():
                sys.exit(0)
        except OSError:
            pass
    sys.exit(main())
