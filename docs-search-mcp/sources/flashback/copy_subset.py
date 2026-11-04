"""Copy documents from the general library tarball (library/docs-library-<date>.tar.gz.part-*) into another library's docs
folder, by product and path (subset.txt). The tarball is read as a stream (nothing else is extracted); each product's
manifest.json (urls, titles) and .source_url come along, filtered to the copied files.

    python3 copy_subset.py --library ../library --subset subset.txt --dest work/flashback/docs
Standard library only."""
import argparse
import glob
import io
import json
import os
import re
import tarfile


class Parts(io.RawIOBase):
    """the 45 MB parts read in order as one file"""
    def __init__(self, files):
        self.files, self.f = list(files), None

    def readable(self):
        return True

    def readinto(self, b):
        while True:
            if self.f is None:
                if not self.files:
                    return 0
                self.f = open(self.files.pop(0), "rb")
            n = self.f.readinto(b)
            if n:
                return n
            self.f.close()
            self.f = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", required=True)
    ap.add_argument("--subset", required=True)
    ap.add_argument("--dest", required=True)
    a = ap.parse_args()
    rules = []
    for line in open(a.subset, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            prod, _, rx = line.partition(" ")
            rules.append((prod.strip("/") + "/", re.compile(rx.strip() or ".")))
    parts = sorted(glob.glob(os.path.join(a.library, "docs-library-*.tar.gz.part-*")))
    if not parts:
        raise SystemExit(f"no library parts in {a.library}")
    kept, manifests = {}, {}
    with tarfile.open(fileobj=io.BufferedReader(Parts(parts), 1 << 20), mode="r|gz") as tar:
        for m in tar:
            if not m.isfile() or not m.name.startswith("docs-library/docs/"):
                continue
            rel = m.name[len("docs-library/docs/"):]
            for prod, rx in rules:
                if not rel.startswith(prod):
                    continue
                inner = rel[len(prod):]
                if inner in ("manifest.json", ".source_url"):
                    data = tar.extractfile(m).read()
                    if inner == "manifest.json":
                        manifests[prod] = json.loads(data)
                    else:
                        os.makedirs(os.path.join(a.dest, prod), exist_ok=True)
                        open(os.path.join(a.dest, prod, inner), "wb").write(data)
                elif rx.search(inner):
                    out = os.path.join(a.dest, rel)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with open(out, "wb") as f:
                        f.write(tar.extractfile(m).read())
                    kept.setdefault(prod, []).append(inner)
                break
    for prod, files in sorted(kept.items()):
        if prod in manifests:
            mf = {k: v for k, v in manifests[prod].items() if k in set(files)}
            json.dump(mf, open(os.path.join(a.dest, prod, "manifest.json"), "w"), indent=0)
        print(f"{prod:32} {len(files)} files")


if __name__ == "__main__":
    main()
