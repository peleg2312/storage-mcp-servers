#!/bin/sh
# The brain on a laptop that runs Claude Code (macOS or Linux, connected or not): a Claude Code plugin built from
# the brain's own files (skills, agents, hooks, docs-local) + the rules + the documentation library.
# No web UI, no dev tools, no multi-user parts (that is install-vm.sh).
#   git clone <this repo> && cd <it> && sh install-laptop.sh        update: git pull && sh install-laptop.sh
#   sh install-laptop.sh --no-library           skip the documentation library
#   sh install-laptop.sh --brain-remote <url>   share the brain's git history with a team remote (or BRAIN_REMOTE=<url>)
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$HERE/brain/claude
DST=${CLAUDE_HOME:-$HOME/.claude}
B=$DST/brain
LIB=$HERE/library
NO_LIBRARY=0
REMOTE=${BRAIN_REMOTE:-}
while [ $# -gt 0 ]; do
  case "$1" in
    --no-library) NO_LIBRARY=1 ;;
    --brain-remote) [ $# -ge 2 ] || { echo "usage: --brain-remote <url>"; exit 1; }; shift; REMOTE=$1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
  shift
done
command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }
command -v claude >/dev/null 2>&1 || { echo "claude (Claude Code) is required: install it first, then run this again"; exit 1; }
mkdir -p "$DST/hooks" "$DST/tools/vendor" "$B/notes" "$B/inbox" "$HOME/storage-reports"

echo "== rules and personal files (kept when they exist)"
cp "$SRC/brain/storage.md" "$SRC/brain/coding.md" "$B/"
for f in environment.md tool-map.md notes.md; do [ -f "$B/$f" ] || cp "$SRC/brain/$f" "$B/$f"; done
# main.md = CLAUDE.md; brain/install.sh rewrites @~/.claude/brain/ imports only for a project install, so here it is a copy.
# Your own ~/.claude/CLAUDE.md is never replaced: it only gets one import line.
cp "$SRC/CLAUDE.md" "$B/main.md"
touch "$DST/CLAUDE.md"
grep -qxF '@~/.claude/brain/main.md' "$DST/CLAUDE.md" || printf '\n@~/.claude/brain/main.md\n' >> "$DST/CLAUDE.md"
# the read-only guard reads ~/.claude/hooks/allowed-tools.txt too, so your list survives plugin updates
[ -f "$DST/hooks/allowed-tools.txt" ] || printf '# exact MCP tool names or globs the read-only hook should allow, e.g. mcp__kuparashit__execute_query\n' > "$DST/hooks/allowed-tools.txt"

echo "== tools (as brain/install.sh: the skills call ~/.claude/tools/...)"
cp "$SRC/tools/report.py" "$SRC/tools/get-reports.ps1" "$SRC/tools/db_mcp.py" "$SRC/tools/add-docs" "$SRC/tools/paas-open" "$HERE/docs-search-mcp/docs_index.py" "$DST/tools/"
cp "$SRC/tools/vendor/"*.whl "$DST/tools/vendor/"
[ -f "$B/databases.json" ] || cp "$SRC/tools/databases.example.json" "$B/databases.example.json"

echo "== git history of the brain (as brain/install.sh)"
IGN='library/ inbox/ plugins/ plugin-market/ .nudged/ .brain-index/ *.bak *.db .DS_Store notes.md environment.md main.md storage.md coding.md databases.example.json'   # personal and installer-owned files
for l in $IGN; do grep -qxF -- "$l" "$B/.gitignore" 2>/dev/null || echo "$l" >> "$B/.gitignore"; done   # before the first commit
if command -v git >/dev/null 2>&1 && [ ! -d "$B/.git" ]; then
  ( cd "$B" && git init -q && git add -A >/dev/null 2>&1 \
    && git -c user.name=brain -c user.email=brain@localhost commit -q -m 'brain: initial' >/dev/null 2>&1 ) \
    || echo "note: could not start a git history in $B (skipped)"
fi

# Documentation library: same steps as brain/install.sh (library/join.sh checks SHA256SUMS and unpacks the parts)
if [ "$NO_LIBRARY" = 0 ] && [ -f "$LIB/VERSION" ] && ls "$LIB"/docs-library-*.part-* >/dev/null 2>&1; then
  if [ "$(cat "$LIB/VERSION")" != "$(cat "$B/library/VERSION" 2>/dev/null || true)" ]; then
    echo "== documentation library $(cat "$LIB/VERSION") into $B/library (a minute)"
    TMP=$(mktemp -d)
    sh "$LIB/join.sh" "$TMP" >/dev/null
    rm -rf "$B/library"; mv "$TMP/docs-library" "$B/library"; rm -rf "$TMP"
    find "$B/library" -name '._*' -type f -delete 2>/dev/null || true
    [ "${KEEP_LIBRARY_DOCS:-0}" = 1 ] || rm -rf "$B/library/docs"     # the tools read docs.db only
    cp "$LIB/VERSION" "$B/library/VERSION"
  fi
fi
if [ -d "$B/library" ]; then      # this repo's server code over the library, as brain/install.sh
  cp "$HERE/docs-search-mcp/search_cli.py" "$B/library/search.py"
  cp "$HERE/docs-search-mcp/mcp_stdio.py" "$HERE/docs-search-mcp/docs_text.py" "$B/library/"
fi

echo "== plugin paas-brain"
python3 "$HERE/brain/plugin/build.py" "$B/plugin-market"
claude plugin marketplace add "$B/plugin-market" >/dev/null 2>&1 || claude plugin marketplace update paas-brain >/dev/null 2>&1 || true
if claude plugin list 2>/dev/null | grep -q 'paas-brain@paas-brain'; then
  claude plugin update paas-brain@paas-brain >/dev/null 2>&1 || true
else
  claude plugin install paas-brain@paas-brain --scope user || claude plugin install paas-brain@paas-brain \
    || echo "plugin: not installed; run: claude plugin marketplace add $B/plugin-market && claude plugin install paas-brain@paas-brain"
fi

if [ -n "$REMOTE" ]; then
  python3 "$B/plugin-market/paas-brain/hooks/notes-check.py" --remote "$REMOTE" \
    || echo "note: this notes-check.py has no --remote yet; add the remote by hand: git -C $B remote add origin $REMOTE"
fi

echo
echo "Done. Brain: $B   rules: @~/.claude/brain/main.md in $DST/CLAUDE.md   plugin: $B/plugin-market"
[ -f "$B/library/docs.db" ] && echo "library $(cat "$B/library/VERSION" 2>/dev/null): python3 $B/library/search.py sources" || echo "no library (--no-library, or library/*.part-* missing)"
echo "Check: claude plugin list   (paas-brain enabled), then in claude: /mcp (docs-local), /brain-setup"
