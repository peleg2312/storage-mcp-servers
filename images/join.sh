#!/bin/sh
# Rebuild the image tarballs from their 45 MB parts and verify checksums.
set -e
cd "$(dirname "$0")"
for img in powermax-mcp-2.0 ucsc-mcp-2.2 mds-mcp-2.2 docs-search-mcp-1.0; do
  cat "$img.tar.gz.part-"* > "$img.tar.gz"
done
sha256sum -c SHA256SUMS
