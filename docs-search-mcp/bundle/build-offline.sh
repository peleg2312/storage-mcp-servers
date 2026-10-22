#!/bin/sh
# Build the OFFLINE documentation image on a machine WITH internet access, then carry the image into
# the air-gapped environment like any other image (registry mirror, file transfer, oc-mirror...).
#
#   GITHUB_TOKEN=<read-only token> sh bundle/build-offline.sh
#   URLS=my-kb-urls.txt GITHUB_TOKEN=... sh bundle/build-offline.sh   (+ a plain list of KB URLs to include)
#
# Needs: sh, git, python3 (3.10+, with pypdf installed for the Dell PDFs: pip install pypdf),
#        docker or podman. Re-runs are incremental (only new/changed documents are fetched/indexed).
# Output: work/docs-search-offline-<label>.tar.gz (+ .sha256), image docs-search-offline:<label>
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
WORK=${WORK:-$HERE/work}
LABEL=${LABEL:-$(date +%Y.%m.%d)}
BASE_IMAGE=${BASE_IMAGE:-docs-search-mcp:1.1}
ENGINE=${ENGINE:-$(command -v podman || command -v docker)}
DOCS=$WORK/docs
mkdir -p "$DOCS" "$WORK/index"

echo "== 1/5 Git documentation (NetApp, Trident, Harvest, Dell CSM, PyU4V)"
sh "$HERE/sync/sync-git.sh" ${NETAPP_ALL:+--netapp-all} "$DOCS"
echo "== 2/5 Dell PowerMax / PowerFlex documents"
python3 "$HERE/sync/sync_dell.py" --dest "$DOCS/dell" || echo "WARNING: Dell sync had errors (continuing)"
echo "== 3/5 Public bug trackers (Trident, Harvest, CSM)"
python3 "$HERE/sync/sync_github_issues.py" --dest "$DOCS" || echo "WARNING: issue export had errors (continuing)"
echo "== 3b/5 Your chosen web pages (NetApp / Dell / VMware KB articles in sources/web-pages.txt)"
python3 "$HERE/sync/sync_web.py" --dest "$DOCS" ${URLS:+--urls "$URLS"} || echo "WARNING: some web pages failed (continuing)"
echo "== 4/5 KB pointers, extra files, index"
mkdir -p "$DOCS/kb" && cp "$HERE"/sources/kb/*.md "$DOCS/kb/"
[ -d "$HERE/extra" ] && cp -r "$HERE/extra/." "$DOCS/"      # optional: extra/<vendor>/<product>/files
BUNDLE_LABEL=$LABEL python3 "$HERE/docs_index.py" --docs "$DOCS" --db "$WORK/index/docs.db"
echo "== 5/5 Image"
"$ENGINE" image inspect "$BASE_IMAGE" >/dev/null 2>&1 || "$ENGINE" build -t "$BASE_IMAGE" "$HERE"
"$ENGINE" build -f "$HERE/bundle/Dockerfile.offline" --build-arg BASE="$BASE_IMAGE" -t "docs-search-offline:$LABEL" "$WORK"
"$ENGINE" save "docs-search-offline:$LABEL" | gzip > "$WORK/docs-search-offline-$LABEL.tar.gz"
(cd "$WORK" && sha256sum "docs-search-offline-$LABEL.tar.gz" > "docs-search-offline-$LABEL.tar.gz.sha256")
echo "Done: $WORK/docs-search-offline-$LABEL.tar.gz  (image docs-search-offline:$LABEL)"
echo "Optional for humans: tar czf dell-pdfs-$LABEL.tgz -C $DOCS dell   # the original PDFs"
