#!/bin/sh
# ONE command on the offline VM that runs Claude Code. Needs only: this git clone, python3, claude.
#
#   git clone <this repo>  (or copy the folder in)        then:
#   sh install-vm.sh                      brain for every folder on this VM (~/.claude)
#   sh install-vm.sh --project <dir>      brain only inside <dir>: <dir>/CLAUDE.md, <dir>/.claude/{skills,agents,
#                                         hooks,brain,banner,settings.json}, <dir>/.mcp.json (docs-local)
#   sh install-vm.sh --no-library         skip the documentation library (docs-search runs on the cluster)
#   sh install-vm.sh --login-banner       also the "Peleg As A Service" banner at every login on this VM, for every
#                                         user (SSH, console, terminal windows); asks for sudo (brain/login-banner.sh)
#
# It installs:
#   - the storage brain: CLAUDE.md, 24 skills, 8 agents, the read-only safety hook, the banner (brain/install.sh)
#   - the documentation library from library/*.part-* (NetApp ONTAP + Trident docs and KB, Dell
#     PowerMax / PowerFlex / CSM docs, VMware KB pages, bug trackers when present): always ~/.claude/brain/library
#   - the MCP server "docs-local" (stdio, standard library only, no pip, no containers) so Claude Code
#     can search_docs / read_chunk / read_document / list_sources offline (user scope: `claude mcp add`;
#     project scope: <dir>/.mcp.json)
# and runs a smoke test. Re-run it after every git pull (your environment.md / tool-map.md are kept).
# `claude` may be missing while you install: everything is copied anyway; only `claude mcp add` / `claude mcp list`
# are skipped (re-run once claude is in PATH, or use --project, which needs no claude at all).
#
# Cluster instead of VM? Build the image with  sh docs-search-mcp/bundle/build-offline.sh --from-library
# on any machine with podman/docker (no internet needed) and deploy docs-search-mcp/openshift-offline.yaml.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DST=${CLAUDE_HOME:-$HOME/.claude}
PROJECT=""
LOGIN_BANNER=0
for a in "$@"; do                       # take --login-banner out; the rest goes to brain/install.sh
  shift
  case "$a" in --login-banner) LOGIN_BANNER=1 ;; *) set -- "$@" "$a" ;; esac
done
prev=""
for a in "$@"; do
  [ "$prev" = "--project" ] && PROJECT=$a
  case "$a" in --project=*) PROJECT=${a#--project=} ;; esac
  prev=$a
done
command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }
python3 -c "import sqlite3; sqlite3.connect(':memory:').execute(\"CREATE VIRTUAL TABLE t USING fts5(x)\")" 2>/dev/null \
  || { echo "this python3's sqlite3 has no FTS5 (very old build); install python3 >= 3.8 from the OS repos"; exit 1; }
command -v claude >/dev/null 2>&1 || echo "note: 'claude' not found in PATH - the brain and library are installed anyway; the MCP server is registered when you run this again with claude installed (project mode: .mcp.json needs no claude)"

echo "== brain + library + MCP server"
sh "$HERE/brain/install.sh" "$@"

LIB=$DST/brain/library
if [ -f "$LIB/docs.db" ]; then
  echo
  echo "== smoke test"
  python3 "$LIB/search.py" sources | head -2
  python3 "$LIB/search.py" search "lun mapping show" --limit 1 | sed -n '1,4p'
  [ -f "$LIB/eval_search.py" ] && python3 "$LIB/eval_search.py" | tail -1    # search quality on this VM
  echo
  echo "Library: $LIB  (MANIFEST.md lists every source)"
  echo "Search from the shell:   python3 $LIB/search.py search \"your error text\""
  if [ -n "$PROJECT" ]; then
    echo "Claude Code:             cd $PROJECT && claude   ->  approve docs-local (.mcp.json), then /brain-setup"
  else
    echo "Claude Code:             claude   ->  /brain-setup   (docs-local appears in 'claude mcp list')"
  fi
else
  echo "no library installed (library/*.part-* missing in this clone, or --no-library)"
fi

if [ "$LOGIN_BANNER" = 1 ]; then
  echo
  echo "== login banner (every user, every login on this VM)"
  if [ "$(id -u)" = 0 ]; then sh "$HERE/brain/login-banner.sh"; else sudo sh "$HERE/brain/login-banner.sh"; fi
fi
