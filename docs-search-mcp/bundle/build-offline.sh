#!/bin/sh
# Build the OFFLINE documentation image, then carry the image into the air-gapped environment like any
# other image (registry mirror, file transfer, oc-mirror...).
#
# A) From the prebuilt library committed in this repo (library/*.part-*): no internet needed at all.
#      sh bundle/build-offline.sh --from-library            (needs: sh, python3, docker or podman)
# B) Fresh from the vendor sites, on a machine WITH internet (and then, optionally, pack-library.sh to
#    commit the result):
#      GITHUB_TOKEN=<read-only token> sh bundle/build-offline.sh
#      URLS=my-kb-urls.txt GITHUB_TOKEN=... sh bundle/build-offline.sh   (+ a plain list of KB URLs)
#    Needs: sh, git, python3 (3.10+, with pypdf installed for the Dell PDFs: pip install pypdf),
#    docker or podman. Re-runs are incremental (only new/changed documents are fetched/indexed).
# C) Both: start from the prebuilt library and add what is new on the internet side:
#      sh bundle/build-offline.sh --from-library --sync
#
# Output: work/docs-search-offline-<label>.tar.gz (+ .sha256), image docs-search-offline:<label>
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
WORK=${WORK:-$HERE/work}
LIB=${LIB:-$HERE/../library}
ENGINE=${ENGINE:-$(command -v podman || command -v docker)}
BASE_IMAGE=${BASE_IMAGE:-docs-search-mcp:1.1}
FROM_LIB=0; SYNC=1
for arg in "$@"; do
  case "$arg" in
    --from-library) FROM_LIB=1; SYNC=0 ;;
    --sync) SYNC=1 ;;
    *) echo "unknown option $arg"; exit 2 ;;
  esac
done
DOCS=$WORK/docs
mkdir -p "$DOCS" "$WORK/index"

if [ "$FROM_LIB" = 1 ]; then
  LABEL=${LABEL:-$(cat "$LIB/VERSION")}
  echo "== 0/5 Prebuilt library $LABEL from $LIB"
  sh "$LIB/join.sh" "$WORK"
  rm -rf "$DOCS"; mv "$WORK/docs-library/docs" "$DOCS"
  mv "$WORK/docs-library/docs.db" "$WORK/index/docs.db"
  rm -rf "$WORK/docs-library"
else
  LABEL=${LABEL:-$(date +%Y.%m.%d)}
fi

if [ "$SYNC" = 1 ]; then
  echo "== 1/5 Git documentation (NetApp ONTAP + Trident, Dell CSM / CSI / automation, PyU4V)"
  sh "$HERE/sync/sync-git.sh" ${NETAPP_ALL:+--netapp-all} "$DOCS"
  echo "== 2/5 Dell PowerMax / PowerFlex documents + KB articles (dell.com)"
  python3 "$HERE/sync/sync_dell.py" --dest "$DOCS/dell" || echo "WARNING: Dell sync had errors (continuing)"
  echo "== 3/5 Public bug trackers (Trident, Harvest, CSM)"
  python3 "$HERE/sync/sync_github_issues.py" --dest "$DOCS" || echo "WARNING: issue export had errors (continuing)"
  echo "== 3b/5 Your chosen web pages (NetApp / Dell / VMware KB articles in sources/web-pages.txt)"
  python3 "$HERE/sync/sync_web.py" --dest "$DOCS" ${URLS:+--urls "$URLS"} || echo "WARNING: some web pages failed (continuing)"
fi
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
[ "$SYNC" = 1 ] && echo "To commit this library into the repo: sh bundle/pack-library.sh"
echo "Optional for humans: tar czf dell-pdfs-$LABEL.tgz -C $DOCS dell   # the original PDFs"
