#!/bin/sh
# A plugin of the brain's marketplace (brain/plugins) for a VM that does not have the brain: one folder, one command there.
#   sh scripts/make-plugin-kit.sh presentations [out-dir]      -> <out-dir>/plugin-kit-presentations.zip
# The kit carries the plugin as a small Claude Code marketplace of its own (brain-kit) and what the plugin needs to run
# that the brain would otherwise bring: for presentations the deck tools (deck.py, deck_mcp.py, deck_icons.py) and the
# offline wheels of python-pptx (Python 3.9 and 3.12). On the other VM:
#   unzip plugin-kit-presentations.zip && sh plugin-kit-presentations/install.sh               (this person, no root)
#   unzip ... && sudo sh plugin-kit-presentations/install.sh --all-users                       (root: shared once,
#        then each person: sh /opt/paas-kit/presentations/install.sh --use)
set -eu
NAME=${1:-}; OUT=${2:-.}
HERE=$(cd "$(dirname "$0")/.." && pwd)
SRC="$HERE/brain/plugins/$NAME"
[ -n "$NAME" ] && [ -f "$SRC/.claude-plugin/plugin.json" ] || { echo "usage: make-plugin-kit.sh <plugin of brain/plugins> [out-dir]"; ls "$HERE/brain/plugins"; exit 1; }
K=$(mktemp -d)/plugin-kit-$NAME
mkdir -p "$K/marketplace/.claude-plugin"
cp -R "$SRC" "$K/marketplace/$NAME"
find "$K" -name __pycache__ -prune -exec rm -rf {} +
python3 - "$HERE/brain/plugins/.claude-plugin/marketplace.json" "$NAME" "$K/marketplace/.claude-plugin/marketplace.json" <<'PY'
import json, sys
src, name, dst = sys.argv[1:]
m = json.load(open(src))
p = next(x for x in m["plugins"] if x["name"] == name)
json.dump({"name": "brain-kit", "owner": {"name": "storage brain"}, "description": "plugins of the storage brain for VMs without it",
           "plugins": [dict(p, source="./" + name)]}, open(dst, "w"), indent=2)
PY
if [ "$NAME" = presentations ]; then
  mkdir -p "$K/tools" "$K/wheels"
  cp "$HERE/brain/claude/tools/deck.py" "$HERE/brain/claude/tools/deck_mcp.py" "$HERE/brain/claude/tools/deck_icons.py" "$K/tools/"
  for w in python_pptx lxml pillow xlsxwriter typing_extensions; do cp "$HERE/brain/devtools/wheels/$w"-*.whl "$K/wheels/"; done
fi
cat > "$K/install.sh" <<'EOF'
#!/bin/sh
# Installs this plugin on a VM without the storage brain.
#   sh install.sh               for you: ~/.claude (tools, a Python venv for python-pptx), then the plugin in your Claude
#   sh install.sh --all-users   root: the shared parts once (/opt/paas-kit, /opt/paas/tools, /opt/paas/devtools-venv);
#                               then each person runs:  sh /opt/paas-kit/<plugin>/install.sh --use
#   sh install.sh --use         the plugin in your Claude only (the shared parts are there)
set -eu
KIT=$(cd "$(dirname "$0")" && pwd)
NAME=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["plugins"][0]["name"])' "$KIT/marketplace/.claude-plugin/marketplace.json")
MODE=${1:-}
if [ "$MODE" = --all-users ]; then
  [ "$(id -u)" = 0 ] || { echo "--all-users: run it as root"; exit 1; }
  MP=/opt/paas-kit/$NAME; TOOLS=/opt/paas/tools; VENV=/opt/paas/devtools-venv
  rm -rf "$MP.new"; mkdir -p /opt/paas-kit; cp -R "$KIT" "$MP.new"; rm -rf "$MP"; mv "$MP.new" "$MP"; chmod -R a+rX /opt/paas-kit
elif [ "$MODE" = --use ]; then
  MP=$KIT; TOOLS=""; VENV=""
else
  C=${CLAUDE_HOME:-$HOME/.claude}
  MP=$C/plugin-kits/$NAME; TOOLS=$C/tools; VENV=$C/devtools-venv
  rm -rf "$MP"; mkdir -p "$(dirname "$MP")"; cp -R "$KIT" "$MP"
fi
if [ -n "$TOOLS" ] && [ -d "$KIT/tools" ]; then
  mkdir -p "$TOOLS"; cp "$KIT"/tools/*.py "$TOOLS/"; chmod a+rx "$TOOLS"/*.py
fi
if [ -n "$VENV" ] && [ -d "$KIT/wheels" ]; then
  PY=$(command -v python3.12 || command -v python3)
  [ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
  if "$VENV/bin/python" -m pip install -q --no-index --find-links "$KIT/wheels" --upgrade python-pptx; then
    echo "python-pptx installed in $VENV"
  else
    echo "python-pptx not installed: the kit has wheels for Python 3.9 and 3.12 only ($("$VENV/bin/python" --version)); install python3.12 or python3.9 and run this again"; exit 1
  fi
  [ "$MODE" != --all-users ] || chmod -R a+rX "$VENV"
fi
if [ "$MODE" = --all-users ]; then
  echo "shared parts of $NAME installed. Each person now runs:  sh $MP/install.sh --use"
  command -v soffice >/dev/null 2>&1 || [ "$NAME" != presentations ] || echo "optional: dnf install libreoffice-impress poppler-utils (the real layout check and a PDF copy of every deck)"
  exit 0
fi
command -v claude >/dev/null 2>&1 || { echo "claude is not in PATH: install Claude Code first, then run this again"; exit 1; }
claude plugin marketplace add "$MP/marketplace" >/dev/null 2>&1 || claude plugin marketplace update brain-kit >/dev/null 2>&1 || true
if claude plugin list 2>/dev/null | grep -q "$NAME@brain-kit"; then
  claude plugin update "$NAME@brain-kit" >/dev/null 2>&1 || true
  claude plugin enable "$NAME@brain-kit" >/dev/null 2>&1 || true
else
  claude plugin install "$NAME@brain-kit" --scope user
fi
echo "$NAME is installed in your Claude ($NAME@brain-kit). Start a new Claude session to use it."
[ "$NAME" != presentations ] || echo "try:  /presentations:deck a short status update in English   (decks land in ~/storage-reports/)"
command -v soffice >/dev/null 2>&1 || [ "$NAME" != presentations ] || echo "optional (root): dnf install libreoffice-impress poppler-utils (the real layout check and a PDF copy of every deck)"
EOF
chmod +x "$K/install.sh"
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
(cd "$(dirname "$K")" && rm -f "$OUT/plugin-kit-$NAME.zip" && zip -qr "$OUT/plugin-kit-$NAME.zip" "plugin-kit-$NAME")
rm -rf "$(dirname "$K")"
echo "$OUT/plugin-kit-$NAME.zip ($(du -h "$OUT/plugin-kit-$NAME.zip" | cut -f1)): unzip on the other VM, then sh plugin-kit-$NAME/install.sh"
