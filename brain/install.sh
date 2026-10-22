#!/bin/sh
# Install the storage brain into ~/.claude on the VM that runs Claude Code.
#   sh install.sh                 (re-run after every git pull; your environment.md, tool-map.md and notes.md are kept)
#   sh install.sh --no-library    skip the documentation library (when docs-search runs on the cluster)
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$HERE/claude
DST=${CLAUDE_HOME:-$HOME/.claude}
TS=$(date +%Y%m%d%H%M%S)
mkdir -p "$DST/skills" "$DST/agents" "$DST/hooks" "$DST/brain" "$HOME/storage-reports"

if [ -f "$DST/CLAUDE.md" ] && ! cmp -s "$SRC/CLAUDE.md" "$DST/CLAUDE.md"; then
  cp "$DST/CLAUDE.md" "$DST/CLAUDE.md.bak.$TS"; echo "backed up existing CLAUDE.md -> CLAUDE.md.bak.$TS"
fi
cp "$SRC/CLAUDE.md" "$DST/CLAUDE.md"
cp -R "$SRC/skills/." "$DST/skills/"
cp -R "$SRC/agents/." "$DST/agents/"
cp "$SRC/hooks/block-write-tools.py" "$SRC/hooks/session-start.py" "$DST/hooks/"
[ -f "$DST/hooks/allowed-tools.txt" ] || printf '# exact MCP tool names or globs the read-only hook should allow, e.g. mcp__kuparashit__execute_query\n' > "$DST/hooks/allowed-tools.txt"
for f in environment.md tool-map.md notes.md; do
  [ -f "$DST/brain/$f" ] || cp "$SRC/brain/$f" "$DST/brain/$f"
done

# Documentation library (library/*.part-* in this repo): extracted into ~/.claude/brain/library so the
# docs can be searched on this VM with no server at all (python3 library/search.py ...) and registered
# as the stdio MCP server "docs-local" for Claude Code (mcp_stdio.py, standard library only).
LIB=$HERE/../library
if [ "${1:-}" != "--no-library" ] && [ -f "$LIB/VERSION" ] && ls "$LIB"/docs-library-*.part-* >/dev/null 2>&1; then
  if [ "$(cat "$LIB/VERSION")" != "$(cat "$DST/brain/library/VERSION" 2>/dev/null || true)" ]; then
    echo "installing documentation library $(cat "$LIB/VERSION") into $DST/brain/library (a minute)..."
    TMP=$(mktemp -d)
    sh "$LIB/join.sh" "$TMP" >/dev/null
    rm -rf "$DST/brain/library"; mv "$TMP/docs-library" "$DST/brain/library"; rmdir "$TMP"
    cp "$LIB/VERSION" "$DST/brain/library/VERSION"
  fi
  echo "library $(cat "$DST/brain/library/VERSION"): python3 $DST/brain/library/search.py sources"
  if command -v claude >/dev/null 2>&1; then
    claude mcp get docs-local >/dev/null 2>&1 || claude mcp add docs-local -s user \
      -- python3 "$DST/brain/library/mcp_stdio.py" --db "$DST/brain/library/docs.db" \
      && echo "registered MCP server docs-local (stdio, no dependencies; same tools as docs-search)"
  fi
fi

# "Peleg As A Service": a big styled banner every time Claude Code is started (shell wrapper around the
# `claude` command, added to ~/.bashrc / ~/.zshrc once), and a matching styled status line inside the UI.
mkdir -p "$DST/banner"
cp "$SRC/banner/paas-banner.py" "$SRC/banner/paas-statusline.py" "$DST/banner/"
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
  [ -f "$rc" ] || [ "$rc" = "$HOME/.bashrc" ] || continue
  grep -q "storage brain: Peleg As A Service" "$rc" 2>/dev/null && continue
  cat >> "$rc" <<'EOS'

# >>> storage brain: Peleg As A Service banner (sh brain/install.sh) >>>
claude() {
  case "${1:-}" in ""|-*)
    case " $* " in *" -p "*|*" --print "*|*" -v "*|*" --version "*|*" -h "*|*" --help "*) ;;
      *) python3 "$HOME/.claude/banner/paas-banner.py" ;; esac ;;
  esac
  command claude "$@"
}
# <<< storage brain <<<
EOS
  echo "banner: added the claude wrapper to $rc (open a new shell, or: . $rc)"
done

SERVERS=""
if command -v claude >/dev/null 2>&1; then
  echo "reading MCP servers (claude mcp list)..."
  SERVERS=$(claude mcp list 2>/dev/null | sed -n 's/^\([A-Za-z0-9_.-]*\): .*/\1/p' | tr '\n' ' ' || true)
fi
# shellcheck disable=SC2086
python3 "$HERE/merge_settings.py" "$DST/settings.json" $SERVERS

echo
python3 "$DST/banner/paas-banner.py"
echo "Installed into $DST: CLAUDE.md, $(ls "$SRC/skills" | wc -l | tr -d ' ') skills, $(ls "$SRC/agents" | wc -l | tr -d ' ') agents, read-only + session-start hooks, banner + status line."
echo "Next: start claude and run   /brain-setup"
