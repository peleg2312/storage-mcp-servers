#!/bin/sh
# Starts paas-chrome.mjs with a Node.js new enough for chrome-devtools-mcp (20.19+ / 22.12+): the web UI's own Node
# (/opt/paas/ui on the shared server, ~/.claude/paas-ui for one user), else the system's node.
HERE=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
for n in /opt/paas/ui/node/bin/node "$HOME/.claude/paas-ui/node/bin/node" "$(command -v node 2>/dev/null)"; do
  [ -x "$n" ] || continue
  "$n" -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>22||(a===22&&b>=12)||(a===20&&b>=19)?0:1)' 2>/dev/null \
    && exec "$n" "$HERE/paas-chrome.mjs" "$@"
done
echo "paas-chrome: needs Node.js 20.19+ or 22.12+ (the web UI's Node is in /opt/paas/ui/node)" >&2
exit 1
