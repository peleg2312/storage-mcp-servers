#!/bin/sh
# Rebuild the documentation library tarball from its 45 MB parts, verify the checksum and extract it.
#   sh library/join.sh                 -> library/docs-library/   (docs/, docs.db, search.py, MANIFEST.md)
#   sh library/join.sh /some/dir       -> /some/dir/docs-library/
set -e
DEST=${1:-$(pwd)}
case "$DEST" in /*) ;; *) DEST=$(pwd)/$DEST ;; esac     # relative to where you run it, not to library/
cd "$(dirname "$0")"
LABEL=$(cat VERSION)
TAR="docs-library-$LABEL.tar.gz"
cat "$TAR.part-"* > "$TAR"
sha256sum -c SHA256SUMS
mkdir -p "$DEST"
tar -xzf "$TAR" -C "$DEST"
rm -f "$TAR"
echo "library $LABEL extracted to $DEST/docs-library"
echo "  search:  python3 $DEST/docs-library/search.py search \"lun mapping show\""
echo "  what's inside: $DEST/docs-library/MANIFEST.md"
