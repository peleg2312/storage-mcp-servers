#!/bin/sh
# Offline Python dev tools for Claude Code on the VM (run by install.sh; safe to re-run):
#   ruff                 lint (the brain's post-edit hook) and formatter
#   basedpyright         type checker; its language server runs as pyright-langserver for the pyright-lsp plugin
# Wheels in ./wheels (Linux x86_64, any Python >= 3.8; node.js comes as a wheel too). Into ~/.claude/devtools-venv,
# commands linked into ~/.local/bin.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
VENV=$HOME/.claude/devtools-venv
BIN=$HOME/.local/bin
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) ;;
  *) echo "devtools: wheels are for Linux x86_64, skipped on $(uname -s)-$(uname -m)"; exit 0 ;;
esac
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV" || { echo "devtools: python3 -m venv failed (install python3-venv), skipped"; exit 0; }
"$VENV/bin/python" -m pip install -q --no-index --find-links "$HERE/wheels" --upgrade ruff basedpyright
mkdir -p "$BIN"
ln -sf "$VENV/bin/ruff" "$BIN/ruff"
ln -sf "$VENV/bin/basedpyright" "$BIN/basedpyright"
ln -sf "$VENV/bin/basedpyright-langserver" "$BIN/pyright-langserver"   # the name the pyright-lsp plugin starts
echo "devtools: $("$BIN/ruff" --version), $("$BIN/basedpyright" --version 2>/dev/null | head -1) in $VENV (linked in $BIN)"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "devtools: add $BIN to PATH (e.g. in ~/.bashrc) so Claude Code finds them" ;; esac
