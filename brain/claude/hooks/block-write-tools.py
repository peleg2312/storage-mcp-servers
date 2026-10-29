#!/usr/bin/env python3
"""Claude Code PreToolUse hook: safety net for the read-only rule.

MCP tools: blocks calls that look like changes (exception: the "databases" server's pg_execute / mongo_write on the
user's own application databases are asked, not blocked) (the storage MCP servers are read-only on their own; this also
covers third-party MCPs such as the official ONTAP MCP, Aria, kuparashit that expose write tools).
Shell (Bash) commands, two levels, because the VM is also used for development:
  - blocked: commands whose only purpose is changing storage / fabric / virtualization infrastructure
    (PowerMax sym* and PowerFlex scli writes, esxcli / govc changes, switch or ONTAP config over ssh,
    host storage: mkfs / wipefs / dd on /dev, multipath -f, iSCSI login / logout, nvme disconnect, /sys writes);
  - asked (the user confirms in Claude Code): general tools that change things - oc / kubectl / helm
    apply-delete-scale..., terraform / ansible runs, systemctl start-stop, curl / wget writes to another host
    (writes to localhost, i.e. testing your own service, pass).
Exit code 2 = blocked, the reason goes back to Claude. False positive? Add the tool name (or a glob) to
allowed-tools.txt next to this hook; for a shell command a line "Bash:<glob of the command>".
"""
import fnmatch
import json
import os
import re
import shlex
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


# ---------------------------------------------------------------- shell commands
WRAPPERS = {"sudo", "time", "nohup", "env", "nice", "ionice", "timeout", "watch", "xargs", "exec", "command", "stdbuf"}
K8S_CHANGE = {"apply", "create", "delete", "edit", "patch", "replace", "scale", "set", "label", "annotate", "drain",
              "cordon", "uncordon", "taint", "expose", "run", "autoscale", "new-app", "new-build", "start-build",
              "import-image", "tag", "rsync", "cp"}
K8S_ADM_READ = {"top", "must-gather", "inspect", "node-logs", "release", "who-can"}
HELM_CHANGE = {"install", "upgrade", "uninstall", "delete", "del", "un", "rollback"}
SYM_CHANGE = WRITE | {"convert", "link", "relink", "establish", "terminate", "sync", "activate", "deactivate",
                      "setup", "compress", "uncompress", "ready", "not_ready", "write_disable", "rw_enable", "half_swap"}
SCLI_CHANGE = re.compile(r"^--(add|remove|map|unmap|modify|set|rename|delete|create|clear|reset|start|stop|activate|"
                         r"deactivate|enable|disable|restore|unlock|lock|switch|replace|move|abort|upgrade|migrate|"
                         r"overwrite|snapshot|format|mark|unmark|assign|unassign)", re.I)
REMOTE_CONFIG = re.compile(r"\b(conf(ig(ure)?)?\s+t(erm(inal)?)?|copy\s+run\S*\s+start|write\s+mem(ory)?|reload|"
                           r"install\s+all|zoneset\s+activate|system\s+node\s+(reboot|halt|takeover|giveback))\b", re.I)
SSH_ARG_OPTS = set("pilFoJbcDEeLmOQRSWw")
NVME_CHANGE = {"connect", "connect-all", "disconnect", "disconnect-all", "format", "sanitize", "write",
               "write-zeroes", "dsm", "set-feature", "create-ns", "delete-ns", "attach-ns", "detach-ns", "reset",
               "subsystem-reset", "ns-rescan"}
MPATHD_CHANGE = {"del", "remove", "add", "reconfigure", "resize", "fail", "reinstate", "suspend", "resume",
                 "disablequeueing", "restorequeueing", "shutdown"}
HOST_DISK = {"wipefs", "sgdisk", "mkswap", "xfs_growfs", "xfs_repair", "resize2fs", "e2fsck", "pvcreate", "pvremove",
             "vgcreate", "vgremove", "vgextend", "vgreduce", "lvcreate", "lvremove", "lvextend", "lvreduce",
             "lvresize", "blkdiscard", "sg_format", "umount", "vmkfstools"}
POWERCLI_CHANGE = re.compile(r"\b(Set|Remove|New|Start|Stop|Restart|Move|Mount|Dismount|Invoke|Update|Add|Clear|Format|"
                             r"Initialize|Install|Uninstall|Enable|Disable|Suspend|Resume|Register|Unregister|Rename|"
                             r"Reset|Restore)-[A-Za-z]+")
LOCAL_HOST = re.compile(r"^(https?://)?(localhost|127\.\d+\.\d+\.\d+|\[?::1\]?|0\.0\.0\.0|[\w.-]+\.localhost)([:/]|$)", re.I)


def _words(seg):
    try:
        return shlex.split(seg)
    except ValueError:
        return seg.split()


def _program(w):
    """(program, its arguments): the first word that is not VAR=x, a wrapper (sudo, timeout...) or its option."""
    for i, t in enumerate(w):
        if re.match(r"^\w+=", t) or t.startswith("-") or re.fullmatch(r"[\d.]+[smhd]?", t):
            continue
        base = os.path.basename(t)
        if base in WRAPPERS:
            continue
        return base, w[i + 1:]
    return "", []


def _first(args):
    return next((a for a in args if not a.startswith("-")), "")


def shell_check(cmd, depth=0):
    """("block" | "ask" | None, reason) for one shell command line."""
    worst = (None, "")
    if re.search(r"(>{1,2}|\btee\s+(-a\s+)?)\s*/(sys|proc/sys)/", cmd):
        return "block", "writes to /sys or /proc/sys (SCSI rescan / delete, kernel settings)"
    if re.search(r"\b(pwsh|powershell|Connect-VIServer)\b", cmd, re.I) and POWERCLI_CHANGE.search(cmd):
        return "block", "PowerCLI / PowerShell command that changes something"
    for seg in re.split(r"\|\||&&|[;|&\n]|\$\(|`|\)", cmd):
        prog, args = _program(_words(seg))
        low = [a.lower() for a in args]
        sub = _first(low)
        r = (None, "")
        if prog in ("oc", "kubectl"):
            if sub in K8S_CHANGE:
                r = ("ask", f"{prog} {sub} changes the cluster")
            elif sub == "rollout" and any(a in ("restart", "undo", "pause", "resume") for a in low):
                r = ("ask", f"{prog} rollout restart / undo changes the cluster")
            elif sub == "adm" and _first(low[low.index("adm") + 1:]) not in K8S_ADM_READ:
                r = ("ask", f"{prog} adm changes the cluster")
            elif sub in ("exec", "rsh", "debug") and "--" in args and depth < 2:
                r = shell_check(" ".join(shlex.quote(a) for a in args[args.index("--") + 1:]), depth + 1)
        elif prog == "helm" and sub in HELM_CHANGE:
            r = ("ask", f"helm {sub} changes the cluster")
        elif prog in ("curl", "wget"):
            method = ""
            for i, a in enumerate(args):
                if a in ("-X", "--request", "--method") and i + 1 < len(args):
                    method = args[i + 1].upper()
                elif a.startswith(("--request=", "--method=")) or (a.startswith("-X") and len(a) > 2):
                    method = a.split("=", 1)[-1].upper() if "=" in a else a[2:].upper()
                elif a in ("-d", "-F", "-T", "--form", "--upload-file", "--json") or a.startswith(("--data", "--post-")):
                    method = method or "POST"
            urls = [a for a in args if re.match(r"^(https?://|[\w.-]+:\d+/|localhost)", a, re.I)]
            if method in ("POST", "PUT", "PATCH", "DELETE") and not (urls and all(LOCAL_HOST.match(u) for u in urls)):
                r = ("ask", f"{prog} {method} to {urls[0] if urls else 'a remote host'}")
        elif prog == "ssh":
            i = 0
            while i < len(args) and args[i].startswith("-"):
                i += 2 if len(args[i]) == 2 and args[i][1] in SSH_ARG_OPTS else 1
            remote = " ".join(args[i + 1:])
            if remote:
                if REMOTE_CONFIG.search(remote):
                    r = ("block", f"configuration change over ssh: {remote[:80]!r}")
                elif set(re.findall(r"[a-z_-]+", remote.lower())) & (WRITE - {"start", "stop", "test"}) - {"show"}:
                    r = ("block", f"remote command that changes something: {remote[:80]!r}")
                elif depth < 2:
                    r = shell_check(remote, depth + 1)
        elif prog == "scli":
            bad = [a for a in args if SCLI_CHANGE.match(a)]
            if bad:
                r = ("block", f"PowerFlex scli {bad[0]} changes the system")
        elif prog.startswith("sym") and prog != "symapi":
            if prog == "symconfigure":
                r = ("block", "symconfigure changes the PowerMax configuration")
            elif set(low) & SYM_CHANGE:
                r = ("block", f"{prog} {sorted(set(low) & SYM_CHANGE)[0]} changes the PowerMax")
        elif prog == "govc":
            toks = set(re.split(r"[._-]", sub)) if sub else set()
            if toks & (WRITE | {"destroy", "rm", "mv", "cp", "register", "unregister", "power", "migrate", "vmotion"}):
                r = ("block", f"govc {sub} changes vSphere")
        elif prog == "esxcli":
            if set(low) & {"set", "add", "remove", "unmount", "mount", "detach", "attach", "claim", "unclaim",
                             "rescan", "unmap", "load", "unload"}:
                r = ("block", "esxcli command that changes the host")
        elif prog.startswith("mkfs") or prog.startswith("fsck."):
            if any(a.startswith("/dev/") for a in args):
                r = ("block", f"{prog} on a device")
        elif prog in HOST_DISK:
            if prog != "vmkfstools" or not set(low) <= {"-p", "-ph", "-d", "-h"} | {a for a in low if not a.startswith("-")}:
                r = ("block", f"{prog} changes disks / filesystems")
        elif prog in ("parted", "fdisk", "sfdisk", "gdisk") and not set(low) & {"-l", "print", "--list", "-s"}:
            r = ("block", f"{prog} can change a partition table")
        elif prog == "dd" and any(a.startswith("of=/dev/") for a in args):
            r = ("block", "dd writing to a device")
        elif prog == "multipath" and set(low) & {"-f", "-F", "-r", "-w", "-W", "-a"}:
            r = ("block", "multipath flush / reload / wwids change")
        elif prog == "multipathd" and set(low) & MPATHD_CHANGE:
            r = ("block", "multipathd command that changes paths")
        elif prog == "iscsiadm" and (set(low) & {"--login", "--logout", "-l", "-u", "--rescan", "-r"} or
                                     any(low[i] in ("-o", "--op") and i + 1 < len(low) and low[i + 1] in
                                         ("new", "delete", "update", "nonpersistent") for i in range(len(low)))):
            r = ("block", "iscsiadm login / logout / node change")
        elif prog == "nvme" and sub in NVME_CHANGE:
            r = ("block", f"nvme {sub} changes NVMe connections / namespaces")
        elif prog in ("rescan-scsi-bus.sh", "rescan-scsi-bus"):
            r = ("block", "SCSI bus rescan / device removal")
        elif prog == "systemctl" and sub in ("start", "stop", "restart", "reload", "enable", "disable", "mask",
                                              "unmask", "kill", "isolate", "reboot", "poweroff", "halt"):
            r = ("ask", f"systemctl {sub}")
        elif prog in ("reboot", "shutdown", "poweroff", "halt"):
            r = ("ask", prog)
        elif prog == "terraform" and sub in ("apply", "destroy", "import", "taint", "state"):
            r = ("ask", f"terraform {sub}")
        elif prog == "ansible-playbook" and not set(low) & {"--check", "-c", "--syntax-check", "--list-tasks", "--list-hosts"}:
            r = ("ask", "ansible-playbook run (not --check)")
        if r[0] == "block":
            return r
        if r[0] == "ask" and not worst[0]:
            worst = r
    return worst


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
    # Bypass mode: the user has approved every change on this server, so the questions below are skipped; the blocks
    # (storage, switches, UCS, VMware) stay in every mode
    bypass = data.get("permission_mode") == "bypassPermissions"
    if name == "Bash":
        cmd = str((data.get("tool_input") or {}).get("command", ""))
        if allowed("Bash:" + cmd):
            return 0
        level, why = shell_check(cmd)
        if level == "block":
            print(f"BLOCKED by the read-only policy: {why}. Storage / fabric / virtualization infrastructure is "
                  f"read-only here; give the command for the user to run, labelled 'to be run by you'.",
                  file=sys.stderr)
            return 2
        if level == "ask" and not bypass:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                     "permissionDecisionReason": f"Read-only guard: changes something: {why}. Allow?"}}))
        return 0
    if not name.startswith("mcp__") or allowed(name):
        return 0
    # Chrome DevTools: drives the person's own Chrome (its own empty profile), not infrastructure; the plugin's connector
    # only lets it open this server's own pages
    if re.match(r"mcp__(plugin_[\w-]+_)?chrome-devtools__", name):
        return 0
    tool_input = data.get("tool_input") or {}
    if re.fullmatch(r"mcp__databases__(pg_execute|mongo_write)", name):
        # the user's own application databases (writable connections only, the server checks): confirm each write
        if bypass:
            return 0
        what = tool_input.get("sql") or " ".join(str(tool_input.get(k, "")) for k in ("op", "database", "collection"))
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                 "permissionDecisionReason": f"Read-only guard: database write on {tool_input.get('connection')}: "
                                                                             f"{str(what)[:300]}"}}))
        return 0
    r = reason_for(name, tool_input)
    if r and name.startswith("mcp__databases__"):
        r += " (pg_query / mongo_* are the reading tools: use pg_execute or mongo_write on a writable connection)"
    if r:
        print(f"BLOCKED by the read-only policy: {name}: {r}. This environment is read-only; give the user "
              f"the steps to run instead. (False positive? the user can add the tool name to "
              f"{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'allowed-tools.txt')})", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
