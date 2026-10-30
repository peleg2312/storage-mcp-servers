#!/bin/sh
# Rebuild the image tarballs from their 45 MB parts and verify checksums.
set -e
cd "$(dirname "$0")"
for img in $(awk '{print $2}' SHA256SUMS | sed 's/\.tar\.gz$//'); do
  cat "$img.tar.gz.part-"* > "$img.tar.gz"
done
sha256sum -c SHA256SUMS
