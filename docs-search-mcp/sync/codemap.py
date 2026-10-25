#!/usr/bin/env python3
"""Write CODEMAP.md into every source-code repository under the docs tree: the external commands the code runs
(and which function runs them), the host paths it uses, and every file with its functions / types. Indexed like
any page, it gives Claude the architecture of a CSI driver or array client before it reads one function.

    python3 sync/codemap.py work/docs          (sync-git.sh runs it after every sync)
"""
import os
import re
import subprocess
import sys
import time

FUNC = {".go": re.compile(r"^func\s+(?:\((\w+)\s+\*?(\w+)[^)]*\)\s+)?(\w+)\s*\("),
        ".py": re.compile(r"^(?:\s{0,4})(?:async\s+)?def\s+(\w+)\s*\(|^class\s+(\w+)")}
TYPE_GO = re.compile(r"^type\s+(\w+)\s+(struct|interface)")
EXEC = re.compile(r'exec\.Command(?:Context)?\((?:ctx,\s*)?([^,)]+)|subprocess\.\w+\(\s*\[?\s*([^,\]]+)')
HOSTPATH = re.compile(r'"((?:/opt|/usr|/sbin|/bin|/etc|/dev|/sys|/proc|/var/lib/kubelet|/noderoot)/[A-Za-z0-9_.\-/]+)"')
TOOLS = re.compile(r'"(mount|umount|mkfs(?:\.\w+)?|blkid|lsblk|findmnt|xfs_growfs|xfs_repair|resize2fs|fsck(?:\.\w+)?|e2fsck|nvme|'
                   r'iscsiadm|multipath|multipathd|chroot|nsenter|partprobe|dd|lsmod|modprobe|drv_cfg|scli|sg_inq|udevadm|'
                   r'blockdev|dmsetup|systemctl|lsscsi|rescan-scsi-bus\.sh|wipefs|sgdisk|parted)"')
SKIP = re.compile(r"(_test\.go|/vendor/|/mocks?/|/testdata/|/tests?/|_mock\.go|\.pb\.go$)")


def codemap(repo, rel):
    files, cmds, paths, tools = {}, {}, {}, {}
    for d, dirs, fs in os.walk(repo):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        for f in sorted(fs):
            ext = os.path.splitext(f)[1]
            p = os.path.join(d, f)
            r = os.path.relpath(p, repo)
            if ext not in FUNC or SKIP.search("/" + r):
                continue
            funcs, types, cur = [], [], "(top level)"
            try:
                lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            for line in lines:
                m = FUNC[ext].match(line)
                if m:
                    if ext == ".go":
                        cur = (m.group(2) + "." if m.group(2) else "") + m.group(3)
                    else:
                        cur = m.group(1) or m.group(2)
                    funcs.append(cur)
                t = TYPE_GO.match(line) if ext == ".go" else None
                if t:
                    types.append(t.group(1))
                for e in EXEC.finditer(line):
                    c = (e.group(1) or e.group(2) or "").strip().strip('"\'')
                    if c:
                        cmds.setdefault(c, set()).add(f"{r} :: {cur}")
                for t in TOOLS.findall(line):
                    tools.setdefault(t, set()).add(f"{r} :: {cur}")
                for h in HOSTPATH.findall(line):
                    paths.setdefault(h, set()).add(r)
            if funcs or types:
                files[r] = (types, funcs)
    if not files:
        return None
    try:
        sha = subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        sha = ""
    out = [f"# Code map of {rel}", "",
           f"Generated {time.strftime('%Y-%m-%d')} from the source{f' (commit {sha})' if sha else ''}: which external commands "
           "and host tools the code runs and from which function, the host paths it uses, and every file with its types and functions. "
           "Search a function name to read its code.", ""]
    if cmds:
        out += ["## External commands run (exec)", "", "| Command (or variable holding it) | Where (file :: function) |", "|---|---|"]
        for c in sorted(cmds):
            out.append(f"| `{c}` | {'; '.join(sorted(cmds[c])[:6])} |")
        out.append("")
    if tools:
        out += ["## Host tools named in the code (what it runs on the node)", "", "| Tool | Where (file :: function) |", "|---|---|"]
        for t in sorted(tools):
            out.append(f"| `{t}` | {'; '.join(sorted(tools[t])[:6])} |")
        out.append("")
    if paths:
        out += ["## Host paths used", ""] + [f"- `{h}`: {', '.join(sorted(paths[h])[:4])}" for h in sorted(paths)] + [""]
    out += ["## Files, types and functions", ""]
    for r in sorted(files):
        types, funcs = files[r]
        line = f"- `{r}`"
        if types:
            line += f" - types: {', '.join(types[:20])}"
        if funcs:
            line += f" - functions: {', '.join(dict.fromkeys(funcs))}"
        out.append(line)
    return "\n".join(out) + "\n"


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "work/docs"
    n = 0
    for vendor in sorted(os.listdir(root)):
        vd = os.path.join(root, vendor)
        if not os.path.isdir(vd):
            continue
        for product in sorted(os.listdir(vd)):
            repo = os.path.join(vd, product)
            if not os.path.isdir(os.path.join(repo, ".git")):
                continue
            text = codemap(repo, f"{vendor}/{product}")
            if text:
                open(os.path.join(repo, "CODEMAP.md"), "w", encoding="utf-8").write(text)
                n += 1
    print(f"code maps: {n} repositories")


if __name__ == "__main__":
    main()
