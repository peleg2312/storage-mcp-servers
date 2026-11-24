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
#   /opt/paas-kit/                 the kit, a Python 3.12 venv (Headroom), rtk, wheels, tiktoken
#                                  data
#   /etc/paas-kit/kit.json         its settings
#   /etc/claude-code/managed-settings.d/60-paas-kit.json   Claude settings for everyone, above anyone's own: rtk on
#                                  and, with Headroom on,
#                                  ANTHROPIC_BASE_URL=http://127.0.0.1:8787; never managed-settings.json
#   paas-headroom.service, paas-kit-watch.timer (systemd); /usr/local/bin/paas-kit, rtk, ast-grep
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
chmod -R a+rX "$D"

ln -sf "$D/bin/paas-kit" /usr/local/bin/paas-kit
ln -sf "$D/bin/rtk" /usr/local/bin/rtk
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
c["plugins"].setdefault("rtk", True)
if not c.get("market_plugins"):   # earlier kits forced code-graph and fastapi-api on for everyone: now each user's choice
    for p in ("code-graph", "fastapi-api"):
        c["plugins"].pop(p, None)
    c["market_plugins"] = True
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

# the kit's own plugins are on for everyone: no Market card for them (older kits added one, and a paas-kit-extras one).
! command -v paas-market >/dev/null 2>&1 || { paas-market source remove paas-kit; paas-market source remove paas-kit-extras; } >/dev/null 2>&1 || true
# the optional plugins (code-graph, fastapi-api, ponytail) go into the paas Market's own plugin catalogue (the brain's /opt/paas/plugins, marketplace brain-dev),
# when that brain version does not carry them yet; brain updates carry them from now on (brain/plugins/)
if [ -f /opt/paas/plugins/.claude-plugin/marketplace.json ]; then
  for p in "$D"/kit/brain-plugins/*/; do
    [ -d "$p" ] || continue          # a slim kit carries no plugins: the brain update brings them
    p=$(basename "$p")
    # a copy the kit put there is refreshed; one the brain carries (no .paas-kit mark) is the brain's - unless it is an
    # older one that still runs from the kit (/opt/paas-kit/..., paas-kit venv) or lacks the plugin's own launchers
    old=0; T=/opt/paas/plugins/$p
    if [ -d "$T" ] && [ ! -f "$T/.paas-kit" ]; then
      grep -rqsE '/opt/paas-kit|paas-kit venv' "$T/.mcp.json" "$T/hooks" "$T/commands" "$T/skills" && old=1
      for f in "$D/kit/brain-plugins/$p"/bin/* "$D/kit/brain-plugins/$p"/hooks/*.sh; do
        [ -e "$f" ] && [ ! -e "$T/${f#"$D/kit/brain-plugins/$p/"}" ] && old=1
      done
    fi
    if [ ! -d "$T" ] || [ -f "$T/.paas-kit" ] || [ $old = 1 ]; then
      rm -rf "/opt/paas/plugins/$p.new"; cp -R "$D/kit/brain-plugins/$p" "/opt/paas/plugins/$p.new"; touch "/opt/paas/plugins/$p.new/.paas-kit"
      rm -rf "/opt/paas/plugins/$p"; mv "/opt/paas/plugins/$p.new" "/opt/paas/plugins/$p"; chmod -R a+rX "/opt/paas/plugins/$p"
    fi
    python3 - "/opt/paas/plugins/.claude-plugin/marketplace.json" "$p" "$D/kit/brain-plugins/$p/.claude-plugin/plugin.json" <<'PY'
import json, sys
mf, name, pj = sys.argv[1:]
m = json.load(open(mf))
if not any(x.get("name") == name for x in m.get("plugins", [])):
    d = json.load(open(pj))
    m["plugins"].append({"name": name, "source": "./" + name, "category": "development",
                         "description": d.get("description", ""), "author": d.get("author", {})})
    json.dump(m, open(mf, "w"), indent=2)
    print(f"paas Market: added the optional plugin {name}")
PY
  done
  rm -rf "$D/venv/crg"                       # older kits ran code-graph from here; the plugin carries its own engine now
  for s in /opt/paas/plugins/*/bin/setup-shared; do   # a plugin's shared part, once for every user (code-graph's environment)
    [ -x "$s" ] && { PAAS_PLUGIN_VENVS=/opt/paas/plugin-venvs "$s" || echo "note: $s failed; each user builds their own on first use"; }
  done
else
  echo "note: no paas Market on this VM (/opt/paas/plugins); the optional plugins are not offered here"
fi
command -v node >/dev/null 2>&1 || echo "note: node is not on the PATH; the optional ponytail plugin needs it for its hooks"
echo
/usr/local/bin/paas-kit status
echo
echo "Done. New Claude sessions (every user) pick it up; running ones when they are started again."
echo "Help: paas-kit help     Off again: sudo paas-kit headroom off     Remove: sudo sh $D/kit/uninstall.sh"
