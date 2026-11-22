#!/bin/sh
# Removes paas-kit: the services, the Claude settings drop-in, the Market source, /opt/paas-kit and /etc/paas-kit.
# Claude sessions go straight to the model again. Graphs people built (.code-review-graph/ in their repositories)
# and their project venvs stay; people who installed the plugins keep a copy until they remove it in /plugin.
set -u
[ "$(id -u)" = 0 ] || { echo "run it as root: sudo sh $0"; exit 1; }
rm -f /etc/claude-code/managed-settings.d/60-paas-kit.json
systemctl disable --now paas-headroom paas-kit-watch.timer >/dev/null 2>&1
rm -f /etc/systemd/system/paas-headroom.service /etc/systemd/system/paas-kit-watch.service /etc/systemd/system/paas-kit-watch.timer
systemctl daemon-reload
command -v paas-market >/dev/null 2>&1 && { paas-market source remove paas-kit; paas-market source remove paas-kit-extras; } >/dev/null 2>&1
for f in paas-kit code-review-graph ast-grep rtk; do
  case $(readlink /usr/local/bin/$f 2>/dev/null) in /opt/paas-kit/*) rm -f /usr/local/bin/$f ;; esac
done
rm -rf /opt/paas-kit /etc/paas-kit
echo "paas-kit removed. New Claude sessions go straight to the model."
