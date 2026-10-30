#!/usr/bin/env python3
"""Retrieval benchmark: runs every tests/retrieval_*.json set (realistic queries + the document each must find)
through the same search the MCP tools use, and prints hit@1 / hit@5 / hit@10 / MRR and every miss.

    python3 eval_search.py [--db work/index/docs.db] [--cases tests/retrieval_*.json] [--min-hit5 0.8] [--dump out.json]

Run it after every library build or search change; --min-hit5 makes it fail (exit 1) when any set is below a floor.
A case matches when an expected substring appears in a result document's path (or an alias's path).
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import search_cli as lib  # noqa: E402  (in the library folder it is search.py)
except ImportError:
    import search as lib  # noqa: E402


def ranked_docs(c, q, k=10):
    """Documents in the order search_docs returns them (one entry per document, aliases included)."""
    rows = lib.search_docs(c, q, limit=k)["results"]
    out = []
    for r in rows:
        names = [r["path"]] + r.get("also_in", [])
        if not any(names == o for o in out):
            out.append(names)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    lib_db = os.path.join(here, "docs.db")                     # inside the installed library
    ap.add_argument("--db", default=lib_db if os.path.exists(lib_db) else os.path.join(here, "work", "index", "docs.db"))
    ap.add_argument("--cases", nargs="+", default=sorted(glob.glob(os.path.join(here, "tests", "retrieval_*.json"))))
    ap.add_argument("--min-hit5", type=float, default=0.0)
    ap.add_argument("--dump", help="write every reply (as the agent sees it) to this JSON file, to diff before / after")
    a = ap.parse_args()
    c = lib.connect(a.db)
    dump, worst = [], 1.0
    for path in a.cases:
        cases = json.load(open(path))
        h1 = h5 = h10 = mrr = 0.0
        for case in cases:
            docs = ranked_docs(c, case["q"])
            if a.dump:
                dump.append(lib.for_agent(lib.search_docs(c, case["q"], limit=10)))
            rank = next((i + 1 for i, names in enumerate(docs)
                         if any(e in n for e in case["expect"] for n in names)), None)
            if rank:
                h1 += rank == 1; h5 += rank <= 5; h10 += rank <= 10; mrr += 1 / rank
            if not rank or rank > 1:
                top = docs[0][0][:90] if docs else "-"
                print(f"{'MISS' if not rank else f'@{rank:<3}'} {case['q']!r}  top: {top}")
        n = len(cases)
        worst = min(worst, h5 / n)
        print(f"\n{os.path.basename(path)}: {n} cases  hit@1 {h1 / n:.2f}  hit@5 {h5 / n:.2f}  hit@10 {h10 / n:.2f}  MRR {mrr / n:.3f}")
    if a.dump:
        json.dump(dump, open(a.dump, "w"), ensure_ascii=False, indent=1)
    sys.exit(1 if worst < a.min_hit5 else 0)


if __name__ == "__main__":
    main()
