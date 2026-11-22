#!/bin/sh
# paas-kit: VM-wide add-ons, apart from the brain (works with any brain, or none). Run once as root; every user,
# and every user created later, has them on, with no question asked; users cannot turn them off - only root can
# (paas-kit headroom off, paas-kit plugin off <name>). Running it again updates the kit and keeps /etc/paas-kit/kit.json.
#
#   sudo sh install.sh                          everything; Headroom forwards to the model address the VM uses today
#   sudo sh install.sh --upstream <url>         the model address to forward to, when it is not found by itself
#   sudo sh install.sh --no-headroom            install Headroom but leave it off (paas-kit headroom on, later)
#
# What it touches (nothing of the brain, no team repository, no user's own settings):
#   /opt/paas-kit/                 the kit, two Python 3.12 venvs (Headroom, code-review-graph), rtk, wheels, tiktoken
#                                  data
#   /etc/paas-kit/kit.json         its settings
#   /etc/claude-code/managed-settings.d/60-paas-kit.json   Claude settings for everyone, above anyone's own: the kit's
#                                  plugins on (rtk, code-graph, fastapi-api) and, with Headroom on,
#                                  ANTHROPIC_BASE_URL=http://127.0.0.1:8787; never managed-settings.json
#   paas-headroom.service, paas-kit-watch.timer (systemd); /usr/local/bin/paas-kit, code-review-graph, ast-grep
set -eu
KIT=$(cd "$(dirname "$0")" && pwd)
[ "$(id -u)" = 0 ] || { echo "run it as root: sudo sh $0 $*"; exit 1; }
UP=""; HR=1
while [ $# -gt 0 ]; do
  case $1 in
    --upstream) UP=${2:?--upstream needs the model URL}; shift 2 ;;
    --no-headroom) HR=0; shift ;;
    -h|--help) sed -n 2,17p "$0"; exit 0 ;;
    *) echo "unknown option $1 (see: sh $0 --help)"; exit 1 ;;
  esac
done
PY=$(command -v python3.12 || true)
[ -n "$PY" ] || { echo "paas-kit needs python3.12:  dnf install -y python3.12   (RHEL 9 AppStream), then run this again"; exit 1; }
D=/opt/paas-kit
mkdir -p "$D/venv" /etc/paas-kit
echo "== kit files -> $D/kit"
rm -rf "$D/kit.new"; cp -R "$KIT" "$D/kit.new"
rm -rf "$D/kit.old"; [ ! -d "$D/kit" ] || mv "$D/kit" "$D/kit.old"; mv "$D/kit.new" "$D/kit"; rm -rf "$D/kit.old"
rm -rf "$D/bin"; cp -R "$D/kit/bin" "$D/bin"; cp "$D/kit/rtk/rtk" "$D/bin/rtk"; chmod 755 "$D/bin/"*
rm -rf "$D/tiktoken"; cp -R "$D/kit/tiktoken" "$D/tiktoken"
rm -rf "$D/hf"; [ ! -d "$D/kit/hf" ] || cp -R "$D/kit/hf" "$D/hf"   # Kompress model, only in a kit built with it

venv() {   # venv <name> <wheels> <packages...>: a fresh venv; the old one comes back if the install fails
  n=$1; w=$2; shift 2       # (a venv records its own path, so it is built under its final name)
  rm -rf "$D/venv/$n.old"; [ ! -d "$D/venv/$n" ] || mv "$D/venv/$n" "$D/venv/$n.old"
  "$PY" -m venv "$D/venv/$n"
  if "$D/venv/$n/bin/pip" install -q --no-index --find-links "$D/kit/wheels/$w" "$@"; then rm -rf "$D/venv/$n.old"
  else rm -rf "$D/venv/$n"; [ ! -d "$D/venv/$n.old" ] || mv "$D/venv/$n.old" "$D/venv/$n"; echo "install of $n failed"; exit 1; fi
}
echo "== Headroom (venv, offline wheels)"
venv headroom headroom "headroom-ai[proxy]"
echo "== code-review-graph (venv, offline wheels)"
venv crg crg code-review-graph
chmod -R a+rX "$D"

ln -sf "$D/bin/paas-kit" /usr/local/bin/paas-kit
ln -sf "$D/bin/rtk" /usr/local/bin/rtk
ln -sf "$D/venv/crg/bin/code-review-graph" /usr/local/bin/code-review-graph
ln -sf "$D/venv/headroom/bin/ast-grep" /usr/local/bin/ast-grep

echo "== settings"
python3 - "$UP" "$HR" <<'PY'
import json, os, subprocess, sys
up, hr = sys.argv[1], sys.argv[2] == "1"
conf = "/etc/paas-kit/kit.json"
try:
    c = json.load(open(conf))
except (OSError, ValueError):
    c = {}
fresh = not c
if up:
    c["upstream"] = up.rstrip("/")
elif not c.get("upstream"):
    c["upstream"] = subprocess.run(["python3", "/opt/paas-kit/bin/paas-kit", "detect-upstream"],
                                   capture_output=True, text=True).stdout.strip()
if fresh or not hr:
    c["headroom"] = hr and bool(c.get("upstream"))
c.setdefault("profile", "safe")
c.pop("rtk_rewrite", None)
if c.get("rtk_exclude") in (None, ["oc", "kubectl", "grep", "egrep", "rg"],                 # unset, or an earlier
                            ["oc logs", "kubectl logs", "oc describe", "kubectl describe"]):  # kit's default list
    c["rtk_exclude"] = ["oc logs", "kubectl logs", "oc describe", "kubectl describe", "aws", "ps", "ruff",
                        r"^ls\s+(.*\s)?-[a-zA-Z]*l", r"^ls\s+(.*\s)?--format=long"]
if not c.get("profile_chosen"):
    c["profile"] = "safe"           # JSON tables only: nothing left out (root: paas-kit headroom profile full)
c.setdefault("plugins", {})
for p in ("rtk", "code-graph", "fastapi-api"):
    c["plugins"].setdefault(p, True)
json.dump(c, open(conf, "w"), indent=2)
os.chmod(conf, 0o644)
print("model address:", c["upstream"] or "NOT FOUND (Headroom stays off: paas-kit headroom upstream <url>, then paas-kit headroom on)")
PY

echo "== services"
cp "$D/kit/systemd/"*.service "$D/kit/systemd/"*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now paas-kit-watch.timer >/dev/null 2>&1 || true
if python3 -c 'import json,sys; c=json.load(open("/etc/paas-kit/kit.json")); sys.exit(0 if c.get("headroom") and c.get("upstream") else 1)'; then
  systemctl enable paas-headroom >/dev/null 2>&1; systemctl restart paas-headroom
  i=0; until curl -s -o /dev/null http://127.0.0.1:8787/health || [ $i -ge 90 ]; do sleep 1; i=$((i+1)); done
else
  systemctl disable --now paas-headroom >/dev/null 2>&1 || true
fi
/usr/local/bin/paas-kit apply

# the kit's own plugins are on for everyone: no Market card for them (older kits added one). The optional extras
# (ponytail) are a Market source of their own, so each user adds them there or in /plugin.
if command -v paas-market >/dev/null 2>&1; then
  paas-market source remove paas-kit >/dev/null 2>&1 || true
  if paas-market source list 2>/dev/null | grep -q '^paas-kit-extras '; then
    paas-market source sync paas-kit-extras >/dev/null 2>&1 || true
  else
    paas-market source add "$D/kit/marketplace-extras" paas-kit-extras >/dev/null 2>&1 || true
  fi
fi
command -v node >/dev/null 2>&1 || echo "note: node is not on the PATH; the optional ponytail plugin needs it for its hooks"
echo
/usr/local/bin/paas-kit status
echo
echo "Done. New Claude sessions (every user) pick it up; running ones when they are started again."
echo "Help: paas-kit help     Off again: sudo paas-kit headroom off     Remove: sudo sh $D/kit/uninstall.sh"
