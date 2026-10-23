#!/usr/bin/env python3
"""Claude Code PreToolUse hook: safety net that blocks MCP tool calls that look like changes.

The storage MCP servers are read-only on their own; this also protects against third-party MCPs
(ONTAP, Aria, kuparashit...) that may expose write tools. Exit code 2 = blocked, the reason goes back
to Claude. False positive? Add the exact tool name (or a glob) to allowed-tools.txt next to this hook
(~/.claude/hooks/ for a user install, <project>/.claude/hooks/ for install-vm.sh --project).
"""
import fnmatch
import json
import os
import re
import sys

READ_FIRST = {"get", "list", "show", "describe", "search", "query", "read", "find", "lookup", "fetch",
              "count", "explain", "resolve", "trace", "check", "audit", "report", "summarize", "summary",
              "inventory", "health", "status", "stats", "metrics", "performance", "investigate", "scan",
              "validate", "diff", "compare", "what", "test", "ping", "ls", "cat", "display", "view"}
WRITE = {"create", "delete", "destroy", "remove", "rm", "update", "modify", "set", "patch", "put", "apply",
         "add", "provision", "unmap", "resize", "expand", "shrink", "rename", "move", "migrate", "restore",
         "revert", "rollback", "clone", "enable", "disable", "reboot", "restart", "shutdown", "poweron",
         "poweroff", "power", "attach", "detach", "mount", "unmount", "write", "edit", "assign",
         "unassign", "associate", "disassociate", "commit", "deploy", "install", "upgrade", "reset",
         "clear", "kill", "terminate", "start", "stop", "suspend", "resume", "failover", "failback",
         "establish", "split", "swap", "unlink", "offline", "online", "purge", "format", "wipe", "acknowledge",
         "ack", "cancel"}
CLI_KEYS = {"command", "cmd", "cli", "cli_command", "commands"}
CLI_READ = {"show", "get", "list", "display", "dir", "ls", "cat", "describe", "terminal"}
METHOD_KEYS = {"method", "http_method", "verb"}
SQL_KEYS = {"sql", "query", "statement"}
# anywhere in the text, not only at the start: "SELECT 1; DELETE FROM x" and "WITH t AS (...) DELETE ..." are writes too
SQL_WRITE = re.compile(r"\b(insert\s+(or\s+\w+\s+)?into|replace\s+into|update\s+\S+\s+set|delete\s+from|"
                       r"drop\s+(table|database|view|index|trigger)|alter\s+table|truncate\s+table?|"
                       r"create\s+(temp\w*\s+)?(table|index|database|view|trigger)|grant\s|revoke\s|merge\s+into|"
                       r"attach\s+database|vacuum\b|pragma\s+\w+\s*=)", re.I)


def tokens(name):
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [t for t in re.split(r"[_\-.\s]+", name.lower()) if t]


def allowed(tool):
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "allowed-tools.txt")  # next to this hook (~/.claude or <project>/.claude)
    if not os.path.exists(f):
        return False
    pats = [line.strip() for line in open(f) if line.strip() and not line.startswith("#")]
    return any(fnmatch.fnmatch(tool, p) for p in pats)


def reason_for(tool_name, tool_input):
    tool = tool_name.split("__", 2)[-1]
    toks = tokens(tool)
    if toks and toks[0] not in READ_FIRST:
        bad = [t for t in toks if t in WRITE]
        if bad:
            return f"tool name looks like a change ({', '.join(bad)})"
    if isinstance(tool_input, dict):
        for k, v in tool_input.items():
            if k.lower() in METHOD_KEYS and str(v).strip().upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                return f"HTTP {str(v).upper()} request"
            if k.lower() in SQL_KEYS and isinstance(v, str) and SQL_WRITE.search(v):
                return "SQL statement that changes data"
            if k.lower() in CLI_KEYS:
                for cmd in (v if isinstance(v, list) else [v]):
                    first = str(cmd).strip().split(None, 1)[0].lower() if str(cmd).strip() else ""
                    if first and first not in CLI_READ:
                        return f"CLI command does not start with show/get/list: {str(cmd)[:80]!r}"
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    name = data.get("tool_name", "")
    if not name.startswith("mcp__") or allowed(name):
        return 0
    r = reason_for(name, data.get("tool_input") or {})
    if r:
        print(f"BLOCKED by the read-only policy: {name}: {r}. This environment is read-only; give the user "
              f"the steps to run himself instead. (False positive? the user can add the tool name to "
              f"{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'allowed-tools.txt')})", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
