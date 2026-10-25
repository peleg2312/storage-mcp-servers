#!/bin/sh
# Offline Python dev tools for Claude Code on the VM (run by install.sh; safe to re-run):
#   ruff                 lint (the brain's post-edit hook) and formatter
#   basedpyright         type checker; its language server runs as pyright-langserver for the pyright-lsp plugin
#   pypdf                reads PDFs for add-docs (your own documents into the library)
#   psycopg, pymongo     drivers of the read-only "databases" MCP server (brain/claude/tools/db_mcp.py)
# Wheels in ./wheels (Linux x86_64; drivers for Python 3.9 and 3.12; node.js comes as a wheel too). Uses python3.12
# when installed (RHEL 9: dnf install python3.12), else python3. Into ~/.claude/devtools-venv,
# commands linked into ~/.local/bin.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
VENV=$HOME/.claude/devtools-venv
BIN=$HOME/.local/bin
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) ;;
  *) echo "devtools: wheels are for Linux x86_64, skipped on $(uname -s)-$(uname -m)"; exit 0 ;;
esac
PY=$(command -v python3.12 || command -v python3)
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV" || { echo "devtools: $PY -m venv failed, skipped"; exit 0; }
"$VENV/bin/python" -m pip install -q --no-index --find-links "$HERE/wheels" --upgrade ruff basedpyright
"$VENV/bin/python" -m pip install -q --no-index --find-links "$HERE/wheels" --upgrade pypdf   # add-docs: PDFs
"$VENV/bin/python" -m pip install -q --no-index --find-links "$HERE/wheels" --upgrade "psycopg[binary]" pymongo \
  || echo "devtools: database drivers not installed for $("$VENV/bin/python" --version) (wheels: Python 3.9 / 3.12)"
mkdir -p "$BIN"
ln -sf "$VENV/bin/ruff" "$BIN/ruff"
ln -sf "$VENV/bin/basedpyright" "$BIN/basedpyright"
ln -sf "$VENV/bin/basedpyright-langserver" "$BIN/pyright-langserver"   # the name the pyright-lsp plugin starts
echo "devtools: $("$BIN/ruff" --version), $("$BIN/basedpyright" --version 2>/dev/null | head -1) in $VENV (linked in $BIN)"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "devtools: add $BIN to PATH (e.g. in ~/.bashrc) so Claude Code finds them" ;; esac
