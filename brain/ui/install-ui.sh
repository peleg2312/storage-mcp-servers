#!/bin/sh
# "Peleg As A Service" web UI on the VM (CloudCLI, branded; offline bundle from build-bundle.sh). Safe to re-run.
#   sh brain/ui/install-ui.sh            install / update, start it as a service on port 3001 (UI_PORT to change)
# Open https://<vm>:3001 from your PC and sign in with the VM's root account (UI_LOGIN_USERS="root peleg" to allow
# others): the password is checked by the system (su), never stored, and there is no sign-up page. HTTPS uses a
# certificate made here once (~/.claude/paas-ui-tls; import paas-ui.crt on your PC to drop the browser warning).
# It runs the real `claude` of this user: same ~/.claude (skills, hooks, read-only guard, MCP servers, library),
# plus the Brain (docs library, skills, agents, MCP, memory), Reports (~/storage-reports), Schedule (timed prompts) and Status (health, usage) tabs from ./plugins.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
B=$HERE/bundle
DST=${UI_DIR:-$HOME/.claude/paas-ui}        # multi-user VM: UI_DIR=/opt/paas/ui UI_SHARED=1 (files only, see brain/multiuser)
PORT=${UI_PORT:-3001}
[ -f "$B/VERSION" ] && ls "$B"/paas-ui-*.part-* >/dev/null 2>&1 || { echo "ui: no bundle in $B (build-bundle.sh)"; exit 0; }
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) ;;
  *) echo "ui: the bundle is for Linux x86_64, skipped on $(uname -s)-$(uname -m)"; exit 0 ;;
esac
V=$(cat "$B/VERSION")
if [ "$V" != "$(cat "$DST/VERSION" 2>/dev/null || true)" ]; then
  echo "installing web UI $V into $DST..."
  TMP=$(mktemp -d)
  cat "$B"/paas-ui-"$V".tar.gz.part-* > "$TMP/ui.tar.gz"
  (cd "$TMP" && mv ui.tar.gz "paas-ui-$V.tar.gz" && sha256sum -c "$B/SHA256SUMS" >/dev/null) || { echo "ui: checksum mismatch"; rm -rf "$TMP"; exit 1; }
  tar -xzf "$TMP/paas-ui-$V.tar.gz" -C "$TMP"
  find "$TMP/paas-ui" -name '._*' -type f -delete
  rm -rf "$DST"; mkdir -p "$(dirname "$DST")"; mv "$TMP/paas-ui" "$DST"; rm -rf "$TMP"
fi
[ "${UI_SHARED:-0}" = 1 ] && { chmod -R a+rX "$DST"; echo "ui: files in $DST (per-user services: brain/multiuser)"; exit 0; }
# plugins (Brain, Reports, Schedule, Status): replaced on every run, other plugins you install are left alone
mkdir -p "$HOME/.claude-code-ui/plugins"
rm -rf "$HOME/.claude-code-ui/plugins/paas-usage"    # merged into Status
for p in "$HERE"/plugins/*/; do
  n=$(basename "$p")
  case "$n" in paas-users|paas-market) [ -d /opt/paas/marketplace ] || continue ;; esac   # multi-user VM only
  rm -rf "$HOME/.claude-code-ui/plugins/$n"; cp -R "$p" "$HOME/.claude-code-ui/plugins/$n"
done
# HTTPS: a self-signed certificate for this VM's names and addresses, made once
TLS=$HOME/.claude/paas-ui-tls
if [ ! -f "$TLS/paas-ui.crt" ] && command -v openssl >/dev/null 2>&1; then
  mkdir -p "$TLS" && chmod 700 "$TLS"
  FQ=$(hostname -f 2>/dev/null || hostname)
  SAN="DNS:$FQ,DNS:$(hostname -s 2>/dev/null || hostname),DNS:localhost,IP:127.0.0.1"
  for ip in $(hostname -I 2>/dev/null); do case "$ip" in *:*) ;; *) SAN="$SAN,IP:$ip" ;; esac; done
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=$FQ/O=Peleg As A Service" -addext "subjectAltName=$SAN" \
    -keyout "$TLS/paas-ui.key" -out "$TLS/paas-ui.crt" >/dev/null 2>&1 && chmod 600 "$TLS/paas-ui.key" \
    && echo "ui: HTTPS certificate for $SAN in $TLS"
fi
TLSENV=""; SCHEME=http
[ -f "$TLS/paas-ui.crt" ] && TLSENV="PAAS_TLS_CERT=$TLS/paas-ui.crt PAAS_TLS_KEY=$TLS/paas-ui.key" && SCHEME=https
CLAUDE=$(command -v claude || echo "$HOME/.local/bin/claude")
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/paas-ui" <<EOF
#!/bin/sh
# run the web UI in the foreground (the service runs this too)
export HOST=0.0.0.0 SERVER_PORT=$PORT CLAUDE_CLI_PATH=$CLAUDE PATH="$HOME/.local/bin:$DST/node/bin:\$PATH"
export PAAS_LOGIN_USERS="${UI_LOGIN_USERS:-root}" $TLSENV
cd "$DST/app" && exec "$DST/node/bin/node" dist-server/server/index.js
EOF
chmod +x "$HOME/.local/bin/paas-ui"

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  cat > "$HOME/.config/systemd/user/paas-ui.service" <<EOF
[Unit]
Description=Peleg As A Service web UI (port $PORT)
After=network-online.target

[Service]
ExecStart=$HOME/.local/bin/paas-ui
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable paas-ui >/dev/null 2>&1
  systemctl --user restart paas-ui
  sleep 3
  systemctl --user is-active --quiet paas-ui && echo "web UI running: $SCHEME://$(hostname -f 2>/dev/null || hostname):$PORT (sign in as ${UI_LOGIN_USERS:-root})" \
    || echo "ui: service did not start: journalctl --user -u paas-ui -n 50"
  # without linger the service stops when you log out and does not start at boot
  loginctl show-user "$(id -un)" -p Linger 2>/dev/null | grep -q yes \
    || loginctl enable-linger "$(id -un)" 2>/dev/null \
    || echo "ui: to keep it running after logout and start it at boot, run once:  sudo loginctl enable-linger $(id -un)"
else
  echo "ui: no systemd user session here; start it with:  paas-ui"
fi
if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  firewall-cmd --list-ports 2>/dev/null | grep -qw "$PORT/tcp" \
    || echo "ui: open the port once:  sudo firewall-cmd --permanent --add-port=$PORT/tcp && sudo firewall-cmd --reload"
fi
