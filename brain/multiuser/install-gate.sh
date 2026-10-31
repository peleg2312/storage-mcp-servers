#!/bin/sh
# Multi-user web UI: the sign-in gate on https://<vm>:3001 (GATE-SPEC.md). Run as root; safe to re-run.
#   sh brain/multiuser/install-gate.sh
# Needs the UI app in /opt/paas/ui (install-shared.sh puts it there). Makes /etc/paas/{users,tls}, the gate key, the group paas-users,
# a self-signed certificate (once), installs paas-gate.service and paas-ui@.service, and opens port 3001.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
[ "$(id -u)" = 0 ] || { echo "gate: run as root"; exit 1; }
[ -x /opt/paas/ui/node/bin/node ] && [ -d /opt/paas/ui/app/node_modules/node-pty ] || { echo "gate: no UI app in /opt/paas/ui"; exit 1; }
umask 077
mkdir -p /etc/paas/users /etc/paas/tls /opt/paas/gate
chmod 755 /etc/paas; chmod 700 /etc/paas/users /etc/paas/tls
[ -s /etc/paas/gate.key ] || head -c 32 /dev/urandom > /etc/paas/gate.key
chmod 600 /etc/paas/gate.key
getent group paas-users >/dev/null || groupadd paas-users
[ -f /etc/paas/allowed-groups ] || printf '# groups whose members may sign in (one per line; local or AD groups); root always may\npaas-users\n' > /etc/paas/allowed-groups
[ -f /etc/paas/team-groups ] || printf '# <team> <group>: a person without a team gets the team of the first group they are in, at first sign-in\n# sales sales-staff\n' > /etc/paas/team-groups
chmod 644 /etc/paas/allowed-groups /etc/paas/team-groups
echo "gate: who may sign in: /etc/paas/allowed-groups; AD group to team: /etc/paas/team-groups"
if [ ! -f /etc/paas/tls/paas-ui.crt ]; then
  FQ=$(hostname -f 2>/dev/null || hostname)
  SAN="DNS:$FQ,DNS:$(hostname -s 2>/dev/null || hostname),DNS:localhost,IP:127.0.0.1"
  for ip in $(hostname -I 2>/dev/null); do case "$ip" in *:*) ;; *) SAN="$SAN,IP:$ip" ;; esac; done
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=$FQ/O=Peleg As A Service" -addext "subjectAltName=$SAN" \
    -keyout /etc/paas/tls/paas-ui.key -out /etc/paas/tls/paas-ui.crt >/dev/null 2>&1
  echo "gate: HTTPS certificate for $SAN in /etc/paas/tls (import paas-ui.crt on the PCs to drop the browser warning)"
fi
chmod 600 /etc/paas/tls/paas-ui.key; chmod 644 /etc/paas/tls/paas-ui.crt
umask 022
install -m 644 "$HERE/gate.js" /opt/paas/gate/gate.js
install -m 644 "$HERE/paas-gate.service" "$HERE/paas-ui@.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable paas-gate >/dev/null 2>&1
systemctl restart paas-gate
if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  firewall-cmd -q --permanent --add-port=3001/tcp && firewall-cmd -q --reload
fi
sleep 1
systemctl is-active --quiet paas-gate && echo "gate running: https://$(hostname -f 2>/dev/null || hostname):3001" \
  || { echo "gate: did not start: journalctl -u paas-gate -n 50"; exit 1; }
