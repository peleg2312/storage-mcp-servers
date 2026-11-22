#!/bin/sh
# paas: run one of ponytail's hook scripts with a Node.js that is there: the web UI's own (/opt/paas/ui on the shared
# VM, ~/.claude/paas-ui for one user), else the system's. Without any Node the hook does nothing (ponytail's skills
# and commands still work); it never blocks a session.
HERE=$(cd "$(dirname "$0")" && pwd)
case $1 in /*) JS=$1 ;; *) JS=$HERE/$1 ;; esac
for n in /opt/paas/ui/node/bin/node "$HOME/.claude/paas-ui/node/bin/node" "$(command -v node 2>/dev/null)"; do
  [ -n "$n" ] && [ -x "$n" ] && exec "$n" "$JS"
done
exit 0
