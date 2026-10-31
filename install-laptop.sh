#!/bin/sh
# The brain on a laptop that runs Claude Code (macOS or Linux, connected or not): a Claude Code plugin built from
# the brain's own files (skills, agents, hooks, docs-local) + the rules + the documentation library.
# No web UI, no dev tools, no multi-user parts (that is install-vm.sh).
#   git clone <this repo> && cd <it> && sh install-laptop.sh        update: git pull && sh install-laptop.sh
#   sh install-laptop.sh --no-library           skip the documentation library
#   sh install-laptop.sh --brain-remote <url>   share the team's knowledge through its git remote (or BRAIN_REMOTE=<url>)
#   sh install-laptop.sh --team <name>          the team profile (brain/teams: san, nas; default san, or BRAIN_TEAM=<name>)
#   sh install-laptop.sh --team-source <url|dir>  take the team from a published team repository (GitLab) instead of this clone
# The team's brain is the Claude Code plugin paas-brain-<team>; `paas-team use <other>` switches team later.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$HERE/brain/claude
DST=${CLAUDE_HOME:-$HOME/.claude}
B=$DST/brain
LIB=$HERE/library
NO_LIBRARY=0
REMOTE=${BRAIN_REMOTE:-}
TEAM=${BRAIN_TEAM:-san}
TEAM_SOURCE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-library) NO_LIBRARY=1 ;;
    --brain-remote) [ $# -ge 2 ] || { echo "usage: --brain-remote <url>"; exit 1; }; shift; REMOTE=$1 ;;
    --team) [ $# -ge 2 ] || { echo "usage: --team <name>"; exit 1; }; shift; TEAM=$1 ;;
    --team-source) [ $# -ge 2 ] || { echo "usage: --team-source <url|dir>"; exit 1; }; shift; TEAM_SOURCE=$1 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
  shift
done
command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }
command -v claude >/dev/null 2>&1 || { echo "claude (Claude Code) is required: install it first, then run this again"; exit 1; }
[ -n "$TEAM_SOURCE" ] || [ -f "$HERE/brain/teams/$TEAM/team.json" ] || { echo "no team '$TEAM' in brain/teams (or give --team-source <url>)"; exit 1; }
mkdir -p "$DST/hooks" "$DST/tools/vendor" "$B/inbox" "$HOME/storage-reports"

echo "== rules (the team's persona, storage rules, skills and agents come with the team below)"
cp "$SRC/brain/coding.md" "$B/"
# main.md = CLAUDE.md; brain/install.sh rewrites @~/.claude/brain/ imports only for a project install, so here it is a copy.
# Your own ~/.claude/CLAUDE.md is never replaced: it only gets one import line.
cp "$SRC/CLAUDE.md" "$B/main.md"
touch "$DST/CLAUDE.md"
grep -qxF '@~/.claude/brain/main.md' "$DST/CLAUDE.md" || printf '\n@~/.claude/brain/main.md\n' >> "$DST/CLAUDE.md"
# the read-only guard reads ~/.claude/hooks/allowed-tools.txt too, so your list survives plugin updates
[ -f "$DST/hooks/allowed-tools.txt" ] || printf '# exact MCP tool names or globs the read-only hook should allow, e.g. mcp__kuparashit__execute_query\n' > "$DST/hooks/allowed-tools.txt"

echo "== tools (as brain/install.sh: the skills call ~/.claude/tools/...)"
cp "$SRC/tools/report.py" "$SRC/tools/get-reports.ps1" "$SRC/tools/db_mcp.py" "$SRC/tools/add-docs" "$SRC/tools/paas-open" "$SRC/tools/paas-team" "$HERE/docs-search-mcp/docs_index.py" "$DST/tools/"
mkdir -p "$HOME/.local/bin" && ln -sf "$DST/tools/paas-team" "$HOME/.local/bin/paas-team"
cp "$SRC/tools/vendor/"*.whl "$DST/tools/vendor/"
[ -f "$B/databases.json" ] || cp "$SRC/tools/databases.example.json" "$B/databases.example.json"

# an older laptop install kept the whole brain as one git history; the team clone holds it now (teams/ never tracked there)
if [ -d "$B/.git" ]; then
  for l in teams/ team-sources/ team team-mode persona.md; do grep -qxF -- "$l" "$B/.gitignore" 2>/dev/null || echo "$l" >> "$B/.gitignore"; done
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

echo "== team $TEAM: the plugin paas-brain-$TEAM and the team's knowledge folder"
echo plugin > "$B/team-mode"                          # skills and hooks come from the plugin (no managed settings on a laptop)
python3 "$HERE/brain/teams/publish.py" --all --to "$B/team-sources" >/dev/null   # every team of this clone, for `paas-team use <other>` offline
if [ -n "$TEAM_SOURCE" ]; then
  python3 "$DST/tools/paas-team" add "$TEAM" "$TEAM_SOURCE"
elif [ -d "$B/teams/$TEAM" ]; then                    # added earlier from this clone: this clone's plugin replaces the old one
  rm -rf "$B/teams/$TEAM/paas-brain-$TEAM"; cp -R "$B/team-sources/$TEAM/paas-brain-$TEAM" "$B/teams/$TEAM/"
  cp "$B/team-sources/$TEAM/.claude-plugin/marketplace.json" "$B/teams/$TEAM/.claude-plugin/"
  ( cd "$B/teams/$TEAM" && git add -A >/dev/null 2>&1 && git -c user.name=brain -c user.email=brain@localhost commit -q -m "team $TEAM: plugin updated by install-laptop.sh" >/dev/null 2>&1 ) || true
else
  python3 "$DST/tools/paas-team" add "$TEAM"
fi
python3 "$DST/tools/paas-team" use "$TEAM"
rm -rf "$B/plugin-market"                            # the pre-team marketplace (paas-brain@paas-brain is uninstalled by paas-team)
[ -z "$REMOTE" ] || { python3 "$DST/tools/paas-team" remote "$TEAM" "$REMOTE" \
  && python3 "$B/teams/$TEAM/paas-brain-$TEAM/hooks/notes-check.py" --remote "$REMOTE" || echo "note: the team remote is not set up yet (see the line above)"; }

echo
echo "Done. Brain: $B   rules: @~/.claude/brain/main.md in $DST/CLAUDE.md   team: $TEAM ($B/teams/$TEAM)"
[ -f "$B/library/docs.db" ] && echo "library $(cat "$B/library/VERSION" 2>/dev/null): python3 $B/library/search.py sources" || echo "no library (--no-library, or library/*.part-* missing)"
echo "Check: claude plugin list   (paas-brain-$TEAM enabled), then in claude: /mcp (docs-local), /brain-setup.   Other team: paas-team use <team>"
