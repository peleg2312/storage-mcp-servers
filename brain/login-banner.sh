#!/bin/sh
# "Peleg As A Service" banner at every interactive login on this VM - SSH, console and terminal windows,
# every user - with a system card (host, OS, uptime, load, memory, disk). Needs root:
#   sudo sh brain/login-banner.sh            install / update        (install-vm.sh --login-banner runs this)
#   sudo sh brain/login-banner.sh --remove   remove everything it added
# Shown once per session and only in an interactive terminal: scp, rsync, ssh <cmd> and scripts see nothing.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SHARE=/usr/local/share/paas
PROFILE=/etc/profile.d/zz-paas-banner.sh
MARK="# paas-login-banner"
[ "$(id -u)" = 0 ] || { echo "needs root: sudo sh $0 $*"; exit 1; }

# shells that do not read /etc/profile.d for non-login terminals (desktop terminal windows)
RCS="/etc/bash.bashrc /etc/zsh/zshrc /etc/zshrc"

if [ "${1:-}" = "--remove" ]; then
  rm -f "$PROFILE"
  rm -rf "$SHARE"
  for f in $RCS; do [ -f "$f" ] && sed -i "/$MARK/d" "$f"; done
  echo "login banner removed"
  exit 0
fi

mkdir -p "$SHARE"
cp "$HERE/claude/banner/paas-banner.py" "$SHARE/paas-banner.py"
chmod 755 "$SHARE"
chmod 644 "$SHARE/paas-banner.py"
cat > "$PROFILE" <<'EOF'
# Peleg As A Service login banner (storage-mcp-servers brain/login-banner.sh; remove: sudo sh brain/login-banner.sh --remove)
case "$-" in
  *i*)
    if [ -z "${PAAS_BANNER_SHOWN:-}" ] && [ -t 1 ] && command -v python3 >/dev/null 2>&1; then
      PAAS_BANNER_SHOWN=1
      export PAAS_BANNER_SHOWN
      python3 /usr/local/share/paas/paas-banner.py --login 2>/dev/null || true
    fi
    ;;
esac
EOF
chmod 644 "$PROFILE"
for f in $RCS; do
  [ -f "$f" ] || continue
  grep -q "$MARK" "$f" || printf '[ -r %s ] && . %s  %s\n' "$PROFILE" "$PROFILE" "$MARK" >> "$f"
done
echo "login banner installed: $PROFILE (+ $SHARE/paas-banner.py); open a new SSH session or terminal to see it"
