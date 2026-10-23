#!/bin/sh
# Pack the synced documentation library (work/docs) + its index (work/index/docs.db) into
# library/docs-library-<label>.tar.gz, split into 45 MB parts so it can be committed to GitHub and
# carried into the air-gapped site with a plain `git clone`.
#
#   sh bundle/pack-library.sh                 label = today (YYYY.MM.DD)
#   LABEL=2026.10.22 sh bundle/pack-library.sh
#
# Run it after the syncs (sync-git.sh, sync_dell.py, sync_github_issues.py, sync_web.py) and the index
# build - i.e. after `bundle/build-offline.sh` or the "Run locally" steps in the README. Replaces the
# previous library parts (one library per repo; the old one stays in git history).
# Inside: docs/<vendor>/<product>/... (the documents, text + PDFs + manifests) and docs.db (FTS5 index
# with all the text), plus MANIFEST.md (what is inside, per source).
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
WORK=${WORK:-$HERE/work}
LIB=${LIB:-$HERE/../library}
LABEL=${LABEL:-$(date +%Y.%m.%d)}
DOCS=$WORK/docs
DB=$WORK/index/docs.db
[ -d "$DOCS" ] || { echo "no $DOCS: run the syncs first"; exit 1; }
[ -f "$DB" ] || { echo "no $DB: run  python3 docs_index.py --docs $DOCS --db $DB  first"; exit 1; }
mkdir -p "$LIB"

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
echo "== staging (text + PDF + HTML documents, no .git folders)"
mkdir -p "$STAGE/docs-library"
# documents: everything except git metadata; keep .source_url (gives the docs.netapp.com / github links)
(cd "$DOCS" && find . -type d -name .git -prune -o -type f -print | grep -v '/\.git/' | grep -v '\.part$' |
  tar -cf - -T -) | tar -xf - -C "$STAGE/docs-library"
mkdir -p "$STAGE/docs-library/docs"
# move <vendor>/... under docs/
for v in "$STAGE/docs-library"/*; do
  [ "$(basename "$v")" = docs ] && continue
  mv "$v" "$STAGE/docs-library/docs/"
done
cp "$DB" "$STAGE/docs-library/docs.db"
cp "$HERE/search_cli.py" "$STAGE/docs-library/search.py"
cp "$HERE/mcp_stdio.py" "$STAGE/docs-library/"                     # stdio MCP server, no dependencies
mkdir -p "$STAGE/docs-library/tests"                                # search-quality check: python3 eval_search.py
cp "$HERE/eval_search.py" "$STAGE/docs-library/"
cp "$HERE/tests/retrieval_eval.json" "$HERE/tests/retrieval_heldout.json" "$STAGE/docs-library/tests/"
cp "$HERE/server.py" "$HERE/mcp_auth.py" "$STAGE/docs-library/"     # HTTP server (needs fastmcp)
python3 "$HERE/bundle/manifest.py" --db "$DB" --docs "$DOCS" --label "$LABEL" > "$STAGE/docs-library/MANIFEST.md"
cp "$STAGE/docs-library/MANIFEST.md" "$LIB/MANIFEST.md"

echo "== packing"
rm -f "$LIB"/docs-library-*.tar.gz.part-* "$LIB"/docs-library-*.tar.gz
TAR="$WORK/docs-library-$LABEL.tar.gz"
tar -C "$STAGE" -cf - docs-library | gzip -9 > "$TAR"
(cd "$LIB" && split -b 45m -a 2 "$TAR" "docs-library-$LABEL.tar.gz.part-")   # part-aa, part-ab ... (GNU and BSD split)
(cd "$WORK" && { command -v sha256sum >/dev/null 2>&1 && sha256sum "docs-library-$LABEL.tar.gz" || shasum -a 256 "docs-library-$LABEL.tar.gz"; } > "$LIB/SHA256SUMS")
echo "$LABEL" > "$LIB/VERSION"
ls -l "$LIB"
echo "library $LABEL: $(du -h "$TAR" | cut -f1) in $(ls "$LIB"/docs-library-*.part-* | wc -l) parts -> $LIB"
echo "commit library/ and push; on the offline side: sh library/join.sh"
