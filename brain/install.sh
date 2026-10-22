#!/bin/sh
# Install the storage brain into ~/.claude on the VM that runs Claude Code.
#   sh install.sh            (re-run after every git pull; your environment.md and tool-map.md are kept)
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
cp "$SRC/hooks/block-write-tools.py" "$DST/hooks/"
[ -f "$DST/hooks/allowed-tools.txt" ] || printf '# exact MCP tool names or globs the read-only hook should allow, e.g. mcp__kuparashit__execute_query\n' > "$DST/hooks/allowed-tools.txt"
for f in environment.md tool-map.md; do
  [ -f "$DST/brain/$f" ] || cp "$SRC/brain/$f" "$DST/brain/$f"
done

SERVERS=""
if command -v claude >/dev/null 2>&1; then
  echo "reading MCP servers (claude mcp list)..."
  SERVERS=$(claude mcp list 2>/dev/null | sed -n 's/^\([A-Za-z0-9_.-]*\): .*/\1/p' | tr '\n' ' ' || true)
fi
# shellcheck disable=SC2086
python3 "$HERE/merge_settings.py" "$DST/settings.json" $SERVERS

echo
echo "Installed into $DST: CLAUDE.md, $(ls "$SRC/skills" | wc -l | tr -d ' ') skills, $(ls "$SRC/agents" | wc -l | tr -d ' ') agents, read-only hook."
echo "Next: start claude and run   /brain-setup"
