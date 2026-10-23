"""python3 ours.py <cases.json> > ranked.json: this search (OURS_DB or work/index/docs.db), same shape as bench.mjs."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import search_cli as lib
c = lib.connect(os.environ.get("OURS_DB") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work", "index", "docs.db"))
out, t0 = {}, time.time()
cases = json.load(open(sys.argv[1]))
for case in cases:
    docs = []
    for r in lib.search_docs(c, case["q"], limit=10)["results"]:
        if r["path"] not in docs:
            docs.append(r["path"])
    out[case["q"]] = docs
print(f"ours: {(time.time() - t0) / len(cases):.2f} s/query", file=sys.stderr)
print(json.dumps(out))
