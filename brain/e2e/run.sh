#!/bin/sh
# End-to-end test of install-vm.sh on Rocky Linux 9 (= RHEL 9) containers: x86_64 without Claude Code (installer,
# library, dev tools, drivers, hooks on Python 3.9, MCP servers, re-install) and arm64 with Claude Code (MCP
# registration, plugins, settings permissions). Needs docker (colima on a Mac: colima start). ~10 minutes.
#   sh brain/e2e/run.sh
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
W=$(mktemp -d)
cp "$ROOT/brain/e2e/e2e.sh" "$ROOT/brain/e2e/setup.sh" "$W/"
git -C "$ROOT" archive --format=tar HEAD -- . ':!docs-search-mcp/work' ':!images' ':!docs-search-mcp/bakeoff' | gzip > "$W/repo.tar.gz"
for a in amd64 arm64; do
  c=0; [ "$a" = arm64 ] && c=1
  echo "######## linux/$a (Claude Code: $c)"
  docker run --rm --platform "linux/$a" -e WITH_CLAUDE=$c -v "$W:/e2e" rockylinux:9 bash /e2e/setup.sh 2>&1 | tee "$W/result-$a.txt" | grep -E "FAIL|RESULT"
done
echo "full logs: $W/result-*.txt"
