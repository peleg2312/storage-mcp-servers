#!/bin/sh
# ONE command on the offline VM that runs Claude Code. Needs only: this git clone, python3, claude.
#
#   git clone <this repo>  (or copy the folder in)        then:
#   sh install-vm.sh
#
# It installs, into ~/.claude:
#   - the storage brain: CLAUDE.md, 17 skills, 6 agents, the read-only safety hook (brain/install.sh)
#   - the documentation library from library/*.part-* (NetApp ONTAP + Trident docs and KB, Dell
#     PowerMax / PowerFlex / CSM docs, VMware KB pages, bug trackers when present): ~/.claude/brain/library
#   - the MCP server "docs-local" (stdio, standard library only, no pip, no containers) so Claude Code
#     can search_docs / read_chunk / read_document / list_sources offline
# and runs a smoke test. Re-run it after every git pull (your environment.md / tool-map.md are kept).
#
# Cluster instead of VM? Build the image with  sh docs-search-mcp/bundle/build-offline.sh --from-library
# on any machine with podman/docker (no internet needed) and deploy docs-search-mcp/openshift-offline.yaml.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DST=${CLAUDE_HOME:-$HOME/.claude}
command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }
python3 -c "import sqlite3; sqlite3.connect(':memory:').execute(\"CREATE VIRTUAL TABLE t USING fts5(x)\")" 2>/dev/null \
  || { echo "this python3's sqlite3 has no FTS5 (very old build); install python3 >= 3.8 from the OS repos"; exit 1; }
command -v claude >/dev/null 2>&1 || echo "note: 'claude' not found in PATH - the brain and library are installed anyway; the MCP server is registered when you run this again with claude installed"

echo "== brain + library + MCP server"
sh "$HERE/brain/install.sh" "$@"

LIB=$DST/brain/library
if [ -f "$LIB/docs.db" ]; then
  echo
  echo "== smoke test"
  python3 "$LIB/search.py" sources | head -2
  python3 "$LIB/search.py" search "lun mapping show" --limit 1 | sed -n '1,4p'
  echo
  echo "Library: $LIB  (MANIFEST.md lists every source)"
  echo "Search from the shell:   python3 $LIB/search.py search \"your error text\""
  echo "Claude Code:             claude   ->  /brain-setup   (docs-local appears in 'claude mcp list')"
else
  echo "no library installed (library/*.part-* missing in this clone)"
fi
