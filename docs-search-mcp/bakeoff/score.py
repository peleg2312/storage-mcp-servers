"""Bake-off scorer: python3 score.py <cases.json> <ranked.json> [db]
ranked.json = {question: [path, ...]}; a hit is an expected substring in a ranked path or in the path of an
identical copy the indexer folded into it (same rule for every engine)."""
import json
import sqlite3
import sys

cases, ranked = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
db = sqlite3.connect(sys.argv[3] if len(sys.argv) > 3 else "work/index/docs.db")
alias = {}
for path, canon in db.execute("SELECT a.path, d.path FROM docs a JOIN docs d ON d.id = a.dup_of"):
    alias.setdefault(canon, []).append(path)
h1 = h5 = h10 = mrr = 0.0
for c in cases:
    docs = [[p] + alias.get(p, []) for p in ranked.get(c["q"], [])]
    rank = next((i + 1 for i, names in enumerate(docs) if any(e in n for e in c["expect"] for n in names)), None)
    if rank:
        h1 += rank == 1; h5 += rank <= 5; h10 += rank <= 10; mrr += 1 / rank
n = len(cases)
print(f"hit@1 {h1 / n:.2f}  hit@5 {h5 / n:.2f}  hit@10 {h10 / n:.2f}  MRR {mrr / n:.3f}")
