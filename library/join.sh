#!/bin/sh
# Rebuild the documentation library tarball from its 45 MB parts, verify the checksum and extract it.
#   sh library/join.sh                 -> ./docs-library/ in the current directory (docs/, docs.db, search.py, MANIFEST.md)
#   sh library/join.sh /some/dir       -> /some/dir/docs-library/     (Linux and macOS)
set -e
DEST=${1:-$(pwd)}
case "$DEST" in /*) ;; *) DEST=$(pwd)/$DEST ;; esac     # relative to where you run it, not to library/
cd "$(dirname "$0")"
LABEL=$(cat VERSION)
TAR="docs-library-$LABEL.tar.gz"
cat "$TAR.part-"* > "$TAR"
if command -v sha256sum >/dev/null 2>&1; then sha256sum -c SHA256SUMS; else shasum -a 256 -c SHA256SUMS; fi
mkdir -p "$DEST"
tar -xzf "$TAR" -C "$DEST" 2>/dev/null || tar -xzf "$TAR" -C "$DEST"
find "$DEST" -maxdepth 1 -name '._docs-library' -delete 2>/dev/null || true; find "$DEST/docs-library" -name '._*' -type f -delete 2>/dev/null || true
rm -f "$TAR"
echo "library $LABEL extracted to $DEST/docs-library"
echo "  search:  python3 $DEST/docs-library/search.py search \"lun mapping show\""
echo "  what's inside: $DEST/docs-library/MANIFEST.md"
