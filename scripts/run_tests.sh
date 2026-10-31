#!/bin/sh
# Run every test in the repo: sh scripts/run_tests.sh   (PY=python3 by default; MDS_PY for the mds tests)
# A suite that cannot import its deps (container-only, e.g. mds needs fastmcp 3.x + prefab-ui) prints SKIP.
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-python3}; MDS_PY=${MDS_PY:-$PY}
case $PY in */*) PY=$(cd "$(dirname "$PY")" && pwd)/$(basename "$PY") ;; esac   # absolute: run() cds
case $MDS_PY in */*) MDS_PY=$(cd "$(dirname "$MDS_PY")" && pwd)/$(basename "$MDS_PY") ;; esac
P=0; F=0; S=0
run() { # dir script interpreter
  out=$(cd "$1" && "$3" $2 2>&1); rc=$?
  if [ $rc = 0 ] && ! echo "$out" | grep -q "skipped"; then echo "PASS  $1/$2"; P=$((P+1))
  elif [ $rc = 77 ]; then echo "SKIP  $1/$2 ($(echo "$out" | tail -1 | cut -c1-90))"; S=$((S+1))
  elif [ $rc = 0 ] || echo "$out" | grep -q -E "ModuleNotFoundError|ImportError"; then
    echo "SKIP  $1/$2 ($(echo "$out" | tail -1 | cut -c1-90))"; S=$((S+1))
  else echo "FAIL  $1/$2"; echo "$out" | tail -15; F=$((F+1)); fi
}
for t in brain/test_*.py; do run brain "$(basename "$t")" "$PY"; done
for t in docs-search-mcp/test_*.py powermax-mcp/test_*.py powerflex-mcp/test_*.py ucsc-mcp/test_*.py; do
  run "$(dirname "$t")" "$(basename "$t")" "$PY"; done
for t in mds-mcp/test_*.py; do run mds-mcp "$(basename "$t")" "$MDS_PY"; done
if command -v node >/dev/null; then
  run brain/ui/plugins/paas-schedule "server.js --self-test" node
  run brain/multiuser "gate.js --self-test" node          # idle stop and allowed-groups logic
else echo "SKIP  node self-tests (no node)"; S=$((S+1)); fi
run brain/ui/plugins "sync-shared.py --check" "$PY"   # every tab carries the current shared block
# real-index search quality, only when the built index exists
DB=${DOCS_DB:-docs-search-mcp/work/index/docs.db}
if [ -f "$DB" ]; then
  # floors = the measured reference minus a little: hard_heldout is 0.84 since the NetApp NAS and VMware KB sets joined the
  # corpus (2026-10-31, relevant new articles crowd the top 5); eval_search.py prints the exact numbers
  for c in "eval 1.0" "heldout 1.0" "fresh_heldout 0.9" "bestpractice_heldout 0.9" "general_heldout 0.85" "hard 0.85" "hard_heldout 0.80" "vast_vmware 0.95" "powerscale 0.85"; do
    set -- $c
    if (cd docs-search-mcp && "$PY" eval_search.py --db "${DB#docs-search-mcp/}" --cases "tests/retrieval_$1.json" --min-hit5 "$2" >/dev/null 2>&1)
    then echo "PASS  eval $1 hit@5 >= $2"; P=$((P+1)); else echo "FAIL  eval $1 hit@5 >= $2"; F=$((F+1)); fi
  done
else echo "SKIP  retrieval evals (no $DB)"; S=$((S+1)); fi
echo "RESULT pass=$P fail=$F skip=$S"
[ $F = 0 ]
