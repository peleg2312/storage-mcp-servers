#!/usr/bin/env python3
"""Paste shared.js into every plugins/*/index.js between the paas shared markers.
  python3 sync-shared.py          update all
  python3 sync-shared.py --check  exit 1 if any plugin is out of date (scripts/run_tests.sh)
Lines in a plugin that repeat a one-line helper from shared.js (esc, fmtSize, fmtTime) are dropped: the block defines them."""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BEGIN = "// >>> paas shared"
END = "// <<< paas shared"
block = open(os.path.join(HERE, "shared.js"), encoding="utf-8").read().rstrip("\n") + "\n"
dups = {l for l in block.splitlines() if re.match(r"const (esc|fmtSize|fmtTime) = ", l)}

def sync(src):
    if BEGIN in src and END in src:
        i = src.index(BEGIN)
        j = src.index(END, i) + len(END)
        rest = src[:i] + src[j:].lstrip("\n")
        rest = rest.lstrip("\n")
    else:
        rest = src
    rest = "".join(l for l in rest.splitlines(True) if l.rstrip("\n") not in dups)
    return block + "\n" + rest

stale = []
for f in sorted(glob.glob(os.path.join(HERE, "*", "index.js"))):
    old = open(f, encoding="utf-8").read()
    new = sync(old)
    if new != old:
        stale.append(os.path.relpath(f, HERE))
        if "--check" not in sys.argv:
            open(f, "w", encoding="utf-8").write(new)
if "--check" in sys.argv and stale:
    print("out of date (run python3 brain/ui/plugins/sync-shared.py):", *stale)
    sys.exit(1)
print(("updated: " if "--check" not in sys.argv else "ok ") + " ".join(stale))
