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
allowed-tools.txt next to this hook or in ~/.claude/hooks/ (both are read); for a shell command a line
"Bash:<glob of the command>". This is a safety net against mistakes, not a sandbox: a determined command can get past it.
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
         "ack", "cancel", "sync", "flush"}
CLI_KEYS = {"command", "cmd", "cli", "cli_command", "commands"}
CLI_READ = {"show", "get", "list", "display", "dir", "ls", "cat", "describe", "terminal"}
METHOD_KEYS = {"method", "http_method", "verb", "request_method", "http_verb", "action"}
SQL_KEYS = {"sql", "query", "statement"}
# anywhere in the text, not only at the start: "SELECT 1; DELETE FROM x" and "WITH t AS (...) DELETE ..." are writes too
SQL_WRITE = re.compile(r"\b(insert\s+(or\s+\w+\s+)?into|replace\s+into|update\s+\S+\s+set|delete\s+from|"
                       r"drop\s+(table|database|view|index|trigger)|alter\s+table|truncate\s+table?|"
                       r"create\s+(temp\w*\s+)?(table|index|database|view|trigger)|grant\s|revoke\s|merge\s+into|"
                       r"attach\s+database|vacuum\b|pragma\s+\w+\s*=|copy\s+[^;]*\bprogram\b|copy\s+[\w.\"]+\s*(\([^)]*\))?\s*from\b)", re.I)


def tokens(name):
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [t for t in re.split(r"[_\-.\s]+", name.lower()) if t]


def allowed(tool):
    pats = []     # next to this hook (~/.claude or <project>/.claude) and the user's ~/.claude/hooks: the union of both
    for f in {os.path.join(os.path.dirname(os.path.abspath(__file__)), "allowed-tools.txt"),
              os.path.expanduser("~/.claude/hooks/allowed-tools.txt")}:
        if os.path.exists(f):
            pats += [line.strip() for line in open(f) if line.strip() and not line.startswith("#")]
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
                           r"install\s+all(?!\s+(status|impact))|copy\s+\S+\s+start\S*|snapmirror\s+(break|resync|initialize|release|delete)|zoneset\s+activate|system\s+node\s+(reboot|halt|takeover|giveback))\b", re.I)
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
LOCAL_HOST = re.compile(r"^(https?://)?(localhost|127\.\d+\.\d+\.\d+|\[?::1\]?|0\.0\.0\.0|[\w.-]+\.localhost)(:\d+)?([/?#]|$)", re.I)
ESXCLI_CHANGE = {"set", "add", "remove", "unmount", "mount", "detach", "attach", "claim", "unclaim", "rescan", "unmap",
                 "load", "unload"}
GOVC_CHANGE = WRITE | {"destroy", "rm", "mv", "cp", "register", "unregister", "power", "migrate", "vmotion", "change",
                       "enter", "exit", "disconnect", "reconnect", "markastemplate", "upload", "mkdir"}
K8S_VAL = {"-n", "--namespace", "--context", "--cluster", "--user", "--kubeconfig", "-s", "--server", "--token", "--as",
           "--as-group", "--request-timeout", "--certificate-authority", "--client-certificate", "--client-key"}
PART_WRITE = {"mklabel", "mktable", "mkpart", "mkpartfs", "rm", "resizepart", "resize", "set", "name", "toggle", "move",
              "rescue", "disk_set", "disk_toggle"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
# ssh remote commands: every statement must be a read. Switch / UCS / Brocade reads, the Linux programs whose
# arguments the shell rules below then check, ONTAP "<directory> ... show|list", session settings
REMOTE_READ = {"show", "dir", "display", "terminal", "version", "ls", "cat", "df", "ping", "tail", "head", "grep", "egrep",
               "zgrep", "less", "more", "uptime", "uname", "hostname", "date", "whoami", "id", "ps", "free", "du", "stat",
               "wc", "sort", "uniq", "cut", "include", "exclude", "begin", "section", "count", "last", "no-more", "json",
               "xml", "journalctl", "dmesg", "lsblk", "lsscsi", "lspci", "ip", "ss", "netstat", "multipath", "multipathd",
               "iscsiadm", "nvme", "systemctl", "esxcli", "sanlun", "rescan-scsi-bus.sh", "scope", "top", "exit"}
ONTAP_DIRS = {"aggr", "aggregate", "application", "cifs", "cluster", "dashboard", "disk", "event", "export-policy", "fcp",
              "fpolicy", "igroup", "iscsi", "job", "license", "lun", "metrocluster", "name-mapping", "network", "nfs",
              "node", "nvme", "protocol", "qos", "qtree", "quota", "security", "sis", "snaplock", "snapmirror", "snapshot",
              "statistics", "storage", "system", "ucadmin", "vol", "volume", "vscan", "vserver"}


def _words(seg):
    try:
        return shlex.split(seg)
    except ValueError:
        return seg.split()


# wrapper options that take a value ("sudo -u root symsg ..."): the value is not the program
WRAP_VAL = {"sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-U", "--user", "--group", "--host"},
            "xargs": {"-a", "-I", "-d", "-L", "-l", "-n", "-P", "-E", "-s"}, "timeout": {"-s", "-k"},
            "env": {"-u", "-C", "-S"}, "nice": {"-n"}, "ionice": {"-c", "-n", "-p"}, "stdbuf": {"-i", "-o", "-e"},
            "watch": {"-n", "-d"}}
SHELL_C = re.compile(r"""(?<![\w.-])(?:(?:bash|sh|zsh|dash|ksh)\s+(?:-\w+\s+)*?-\w*c\w*|eval)\s+("[^"]*"|'[^']*'|\S+)""")


def _program(w):
    """(program, its arguments): the first word that is not VAR=x, a wrapper (sudo, timeout...) or its option / value."""
    wrap = ""
    for i, t in enumerate(w):
        if wrap and i and w[i - 1] in WRAP_VAL.get(wrap, ()):
            continue
        if re.match(r"^\w+=", t) or t.startswith("-") or re.fullmatch(r"[\d.]+[smhd]?", t):
            continue
        base = os.path.basename(t)
        if base in WRAPPERS:
            wrap = base
            continue
        return base, w[i + 1:]
    return "", []


def _first(args):
    return next((a for a in args if not a.startswith("-")), "")


def _k8s_verb(args):
    """oc / kubectl verb: the first word that is not a global flag or its value ("-n x delete pod p" -> delete)."""
    skip = False
    for a in args:
        if skip:
            skip = False
        elif a in K8S_VAL:
            skip = True
        elif not a.startswith("-"):
            return a
    return ""


def _split(cmd):
    """[(separator before, segment)]: split on ; | & || && newline $( ` ) outside quotes ("a|b" stays one word)."""
    out, cur, sep, q, i = [], "", "", "", 0
    while i < len(cmd):
        c = cmd[i]
        if c == "\\" and q != "'":
            cur, i = cur + cmd[i:i + 2], i + 2
            continue
        if q or c in "'\"":
            q = "" if c == q else (q or c)
        else:
            m = re.match(r"\|\||&&|[;|&\n)`]|\$\(", cmd[i:])
            if m:
                out.append((sep, cur))
                cur, sep, i = "", m.group(), i + len(m.group())
                continue
        cur, i = cur + c, i + 1
    out.append((sep, cur))
    return out


def _remote_check(remote, depth):
    """ssh remote command: every statement must be a read (see REMOTE_READ); anything else is blocked."""
    for _, st in _split(remote):
        w = _words(st)
        if not w:
            continue
        prog = _program(w)[0].lower()
        head = [x.lower() for x in w[:next((i for i, x in enumerate(w) if x.startswith("-")), len(w))]]
        if prog in REMOTE_READ:
            r = shell_check(st, depth + 1)
            if r[0]:
                return r
        elif not ((prog.endswith("show") and len(prog) > 4) or                      # Brocade switchshow, zoneshow ...
                  (head and head[0] in ONTAP_DIRS and (head[-1] in ("show", "list") or head[-1].startswith("show-"))) or
                  (w[0].lower() == "set" and len(w) > 1 and
                   w[1].lower() in ("-privilege", "-priv", "-units", "-rows", "-confirmations"))):
            return "block", f"remote command that is not a read: {st.strip()[:80]!r}"
    return None, ""


def shell_check(cmd, depth=0):
    """("block" | "ask" | None, reason) for one shell command line."""
    worst = (None, "")
    if re.search(r"(>{1,2}|\btee\s+(-a\s+)?)\s*/(sys|proc/sys)/", cmd):
        return "block", "writes to /sys or /proc/sys (SCSI rescan / delete, kernel settings)"
    if re.search(r"(>{1,2}|\btee\s+(-a\s+)?)\s*/dev/(?!(null|zero|stdout|stderr|tty\w*|fd/|pts/|shm/))", cmd):
        return "block", "writes to a device under /dev"
    if re.search(r"/etc/paas/|paas-api-key", cmd):
        return "block", "the shared service files under /etc/paas (API key) are not for reading"
    if re.search(r"\b(pwsh|powershell|Connect-VIServer)\b", cmd, re.I) and POWERCLI_CHANGE.search(cmd):
        return "block", "PowerCLI / PowerShell command that changes something"
    if depth < 2:     # bash -c "..." / eval "...": check the quoted command (the splitter below would cut inside the quotes)
        for m in SHELL_C.finditer(cmd):
            r = shell_check((_words(m.group(1)) or [""])[0] if m.group(1)[0] in "\"'" else m.group(1), depth + 1)
            if r[0] == "block":
                return r
            worst = worst if worst[0] else r
        for m in re.finditer(r"\$\(([^()]*)\)|`([^`]*)`", cmd):     # command substitution, also inside "..."
            r = shell_check(m.group(1) or m.group(2) or "", depth + 1)
            if r[0] == "block":
                return r
            worst = worst if worst[0] else r
    prev = []
    for sep, seg in _split(cmd):
        w = _words(seg)
        prog, args = _program(w)
        low = [a.lower() for a in args]
        sub = _first(low)
        r = (None, "")
        if prog in SHELLS and (sep == "|" or "<<<" in args):        # text piped / here-string into a shell
            pprog, pargs = _program(prev)
            body = args[args.index("<<<") + 1:] if "<<<" in args else pargs if pprog in ("echo", "printf") else None
            r = shell_check(" ".join(body), depth + 1) if body is not None and depth < 2 else (None, "")
            if r[0] != "block" and body is None:
                r = ("ask", f"pipes {pprog or 'text'} into {prog}")
        elif re.fullmatch(r"(python[\d.]*|perl|ruby)", prog) and set(args) & {"-c", "-e"}:
            code = " ".join(args)
            if re.search(r"\b(system|subprocess|popen|exec\w*|spawn\w*)\b|`", code):
                strs = [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", code)]
                r = shell_check(" ".join(strs), depth + 1) if depth < 2 else (None, "")
                r = r if r[0] == "block" else ("ask", f"{prog} runs a shell command")
        elif prog in ("oc", "kubectl"):
            sub = _k8s_verb(low)
            if sub in K8S_CHANGE:
                r = ("ask", f"{prog} {sub} changes the cluster")
            elif sub == "rollout" and any(a in ("restart", "undo", "pause", "resume") for a in low):
                r = ("ask", f"{prog} rollout restart / undo changes the cluster")
            elif sub == "adm" and _first(low[low.index("adm") + 1:]) not in K8S_ADM_READ:
                r = ("ask", f"{prog} adm changes the cluster")
            elif sub == "certificate" or (sub == "auth" and "reconcile" in low) or (sub == "config" and any(
                    a in ("set-context", "use-context", "set", "set-cluster", "set-credentials", "unset", "rename-context")
                    or a.startswith("delete-") for a in low)):
                r = ("ask", f"{prog} {sub} changes the cluster / kubeconfig")
            elif sub in ("exec", "rsh", "debug") and "--" in args and depth < 2:
                payload = args[args.index("--") + 1:]
                r = shell_check(" ".join(shlex.quote(a) for a in payload), depth + 1)
                if not r[0] and _program(payload)[0] in ("rm", "mv", "truncate", "shred"):
                    r = ("ask", f"{prog} {sub} runs {_program(payload)[0]} in the pod")
        elif prog == "eval" and depth < 2:
            r = shell_check(" ".join(args), depth + 1)
        elif prog == "chroot" and depth < 2:
            r = shell_check(" ".join(shlex.quote(a) for a in args[next((i for i, a in enumerate(args) if not a.startswith("-")), -1) + 1:]),
                            depth + 1)
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
                else:
                    r = _remote_check(remote, depth)
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
            if sub == "host.esxcli":
                if set(low[low.index(sub) + 1:]) & ESXCLI_CHANGE:
                    r = ("block", "govc host.esxcli command that changes the host")
            elif toks & GOVC_CHANGE:
                r = ("block", f"govc {sub} changes vSphere")
        elif prog == "esxcli":
            if set(low) & ESXCLI_CHANGE:
                r = ("block", "esxcli command that changes the host")
        elif prog.startswith("mkfs") or prog.startswith("fsck."):
            if any(a.startswith("/dev/") for a in args) and not (prog.startswith("fsck.") and set(low) & {"-n", "--dry-run"}):
                r = ("block", f"{prog} on a device")
        elif prog in HOST_DISK:
            if prog in ("e2fsck", "xfs_repair") and set(args) & {"-n", "-N", "--dry-run"}:
                pass                                    # check only, changes nothing
            elif prog != "vmkfstools" or not set(low) <= {"-p", "-ph", "-d", "-h"} | {a for a in low if not a.startswith("-")}:
                r = ("block", f"{prog} changes disks / filesystems")
        elif prog in ("parted", "fdisk", "sfdisk", "gdisk") and (not set(low) & {"-l", "print", "--list"} or set(low) & PART_WRITE):
            r = ("block", f"{prog} can change a partition table")
        elif prog == "dd" and any(a.startswith("of=/dev/") for a in args):
            r = ("block", "dd writing to a device")
        elif prog == "multipath" and set(low) & {"-f", "-F", "-r", "-w", "-W", "-a"}:
            r = ("block", "multipath flush / reload / wwids change")
        elif prog == "multipathd" and set(" ".join(a[2:] if a.startswith("-k") else a for a in low).split()) & MPATHD_CHANGE:
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
        elif prog == "terraform" and sub in ("apply", "destroy", "import", "taint", "state", "force-unlock"):
            r = ("ask", f"terraform {sub}")
        elif prog == "ansible-playbook" and not set(low) & {"--check", "-c", "--syntax-check", "--list-tasks", "--list-hosts"}:
            r = ("ask", "ansible-playbook run (not --check)")
        elif prog == "ansible":                          # ad-hoc: -m <module> -a <args>; the shell modules' text is checked
            mod = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-m", "--module-name")), "command").split(".")[-1]
            arg = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-a", "--args")), "")
            if mod in ("shell", "command", "raw") and depth < 2:
                r = shell_check(arg, depth + 1)
            if r[0] != "block" and mod not in ("ping", "setup", "stat", "debug", "gather_facts") and not set(args) & {"-C", "--check"}:
                r = ("ask", f"ansible -m {mod} runs on the hosts")
        if r[0] == "block":
            return r
        if r[0] == "ask" and not worst[0]:
            worst = r
        prev = w
    return worst


def reason_for(tool_name, tool_input):
    tool = tool_name.split("__", 2)[-1]
    toks = tokens(tool)
    bad = [t for t in toks if t in WRITE]
    if toks and toks[0] in READ_FIRST:   # get_snapshot_restores reads; get_and_delete, getOrCreate..., show_set do not
        bad = [t for i, t in enumerate(toks) if t in WRITE and i and (i == len(toks) - 1 or toks[i - 1] in ("and", "then", "or"))]
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


def audit(data, decision, why=""):
    """Append-only record of every MCP / shell call this guard saw: who, when, which tool, what the guard decided.
    ~/.claude/brain/audit/tool-calls.jsonl (one file per VM account, mode 600; rotated at 20 MB to a dated name).
    Arguments are never written, only their names and a hash, and the reason only as its rule (no url / remote text)."""
    try:
        import getpass
        import hashlib
        import time
        d = os.path.join(os.path.expanduser("~"), ".claude", "brain", "audit")
        os.makedirs(d, mode=0o700, exist_ok=True)
        f = os.path.join(d, "tool-calls.jsonl")
        if os.path.exists(f) and os.path.getsize(f) > 20 * 1024 * 1024:
            os.replace(f, f + "." + time.strftime("%Y%m%d%H%M%S"))
        args = data.get("tool_input") or {}
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "user": getpass.getuser(), "session": str(data.get("session_id", ""))[:8],
               "tool": data.get("tool_name", ""), "decision": decision, "args": sorted(args)[:8],
               "hash": hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[:12]}
        if why:
            row["why"] = why.split(":")[0].split(" to ")[0][:60]     # the rule only: the detail can hold a url or a password
        fd = os.open(f, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, (json.dumps(row) + "\n").encode())      # one write on an O_APPEND fd: no interleaved lines
        finally:
            os.close(fd)
    except Exception as e:                              # the log never blocks a call
        print(f"read-only guard: audit log not written ({e.__class__.__name__})", file=sys.stderr)


def managed_twin():
    """Run from a team plugin on a VM whose managed settings (/etc/claude-code/managed-settings.json) run this very hook
    for every account: that copy is the enforced one, this run would only repeat its answer. One small file read."""
    if not os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.realpath(__file__).startswith("/opt/paas/hooks/"):
        return False                                   # the enforced copy never steps aside, whatever the environment says
    try:
        with open(os.environ.get("PAAS_MANAGED_SETTINGS") or "/etc/claude-code/managed-settings.json", encoding="utf-8") as f:
            return "block-write-tools.py" in f.read()
    except OSError:
        return False


def main():
    if managed_twin():
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(data, dict):
        return 0
    try:
        rc = decide(data)
    except Exception:                                   # unexpected payload shape: fail closed for the guarded tools
        name = str(data.get("tool_name") or "")
        rc = 2 if name == "Bash" or name.startswith("mcp__") else 0
        if rc:
            decide.why = "unreadable tool input"
            print("BLOCKED by the read-only policy: the guard could not read this call's input.", file=sys.stderr)
    audit(data, {0: "allow", 2: "block"}.get(rc, str(rc)) if not decide.asked else "ask", decide.why)
    return rc


def decide(data):
    decide.asked, decide.why = False, ""
    name = str(data.get("tool_name") or "")
    # Bypass mode: the user has approved every change on this server, so the questions below are skipped; the blocks
    # (storage, switches, UCS, VMware) stay in every mode
    bypass = data.get("permission_mode") == "bypassPermissions"
    if name == "Bash":
        cmd = str((data.get("tool_input") or {}).get("command", ""))
        if allowed("Bash:" + cmd):
            return 0
        level, why = shell_check(cmd)
        if level == "block":
            decide.why = why
            print(f"BLOCKED by the read-only policy: {why}. Storage / fabric / virtualization infrastructure is "
                  f"read-only here; give the command for the user to run, labelled 'to be run by you'.",
                  file=sys.stderr)
            return 2
        if level == "ask" and not bypass:
            decide.asked, decide.why = True, why
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                     "permissionDecisionReason": f"Read-only guard: changes something: {why}. Allow?"}}))
        return 0
    if not name.startswith("mcp__") or allowed(name):
        return 0
    # Chrome DevTools: drives the person's own Chrome (its own empty profile), not infrastructure; the plugin's connector
    # only lets it open this server's own pages
    if re.match(r"mcp__(plugin_[\w-]+_)?chrome-devtools__", name):
        return 0
    if re.match(r"mcp__docs-(local|search)__", name):    # read-only documentation search: the query text may say "create view" / "grant"
        return 0
    tool_input = data.get("tool_input") or {}
    if re.fullmatch(r"mcp__databases__(pg_execute|mongo_write)", name):
        # the user's own application databases (writable connections only, the server checks): confirm each write
        if bypass:
            return 0
        what = tool_input.get("sql") or " ".join(str(tool_input.get(k, "")) for k in ("op", "database", "collection"))
        s = str(what)     # show what will run, so nothing past the cut is approved unseen
        shown = s[:1500] + (f" ...[+{len(s) - 1500} more chars not shown]" if len(s) > 1500 else "")
        warn = "LONG/DESTRUCTIVE: " if len(s) > 1500 or re.search(r"(?i)\b(drop|truncate|delete\s+from|alter)\b", s) else ""
        decide.asked, decide.why = True, "database write"
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                 "permissionDecisionReason": f"Read-only guard: database write on "
                                                                             f"{tool_input.get('connection')}: {warn}{shown}"}}))
        return 0
    r = reason_for(name, tool_input)
    if r and name.startswith("mcp__databases__"):
        r += " (pg_query / mongo_* are the reading tools: use pg_execute or mongo_write on a writable connection)"
    if r:
        decide.why = r
        print(f"BLOCKED by the read-only policy: {name}: {r}. This environment is read-only; give the user "
              f"the steps to run instead. (False positive? the user can add the tool name to "
              f"{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'allowed-tools.txt')})", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
