#!/bin/sh
# Installs the block-alerts skill for Claude Code.
#   sh install.sh               you: ~/.claude/skills/block-alerts
#   sudo sh install.sh --all    every user on this machine (existing users + users created later)
#   sh install.sh --check       test the script on the bundled example, install nothing
# Replaces only the block-alerts folder; other skills and settings are not touched. Mail settings
# (~/.config/block-alerts/) are kept.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); SRC=$HERE/block-alerts
[ -f "$SRC/SKILL.md" ] && [ -f "$SRC/block_alerts_mail.py" ] || { echo "run it from the unzipped folder (block-alerts/ missing)"; exit 1; }
PY=$(command -v python3 || true)
[ -n "$PY" ] && "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 9))' || { echo "needs python3 3.9 or newer"; exit 1; }
check() {
  T=$(mktemp -d)
  "$PY" "$SRC/block_alerts_mail.py" "$SRC/examples/report.json" --html "$T/e.html" --eml "$T/e.eml" >/dev/null
  grep -q "SRDF to DR is down" "$T/e.html" && echo "ok: the script builds the example email ($PY)"
  rm -rf "$T"
}
put() {   # put <home> <owner>
  d=$1/.claude/skills
  mkdir -p "$d"
  rm -rf "$d/block-alerts.new"; cp -R "$SRC" "$d/block-alerts.new"
  rm -rf "$d/block-alerts"; mv "$d/block-alerts.new" "$d/block-alerts"
  [ -z "$2" ] || chown -R "$2" "$1/.claude"
  echo "installed: $d/block-alerts"
}
case ${1:-} in
  --check) check ;;
  --all)
    [ "$(id -u)" = 0 ] || { echo "--all needs root: sudo sh $0 --all"; exit 1; }
    check
    getent passwd | awk -F: '$3 >= 1000 && $3 < 60000 && $6 != "" {print $1":"$4":"$6}' | while IFS=: read -r u g h; do
      [ -d "$h" ] && put "$h" "$u:$g"
    done
    put /root ""
    put /etc/skel ""                       # users created from now on get it in their new home
    echo "Done. Each user starts a new Claude session (or new chat in the web UI) to load it." ;;
  "")
    check; put "$HOME" ""
    echo "Done. Start a new Claude session (or a new chat in the web UI) to load it." ;;
  *) sed -n 2,8p "$0"; exit 1 ;;
esac
