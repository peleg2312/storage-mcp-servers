#!/bin/sh
# Install the storage brain for Claude Code.
#   sh install.sh                      into ~/.claude (user scope: every folder on this VM)
#   sh install.sh --project <dir>      into <dir> only: <dir>/CLAUDE.md, <dir>/.claude/{skills,agents,hooks,brain,banner,
#                                      settings.json} and <dir>/.mcp.json - the brain exists only inside that folder
#   sh install.sh --no-library         skip the documentation library (when docs-search runs on the cluster)
# Re-run after every git pull; your environment.md, tool-map.md, notes.md, notes/ and allowed-tools.txt are kept.
# The documentation library is always shared in ~/.claude/brain/library (also in project mode).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$HERE/claude
USER_DST=${CLAUDE_HOME:-$HOME/.claude}
PROJECT=""
NO_LIBRARY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --no-library) NO_LIBRARY=1 ;;
    --project) [ $# -ge 2 ] || { echo "usage: install.sh [--project <dir>] [--no-library]"; exit 1; }
               shift; mkdir -p "$1"; PROJECT=$(cd "$1" && pwd) ;;
    --project=*) PROJECT=${1#--project=}; mkdir -p "$PROJECT"; PROJECT=$(cd "$PROJECT" && pwd) ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (usage: install.sh [--project <dir>] [--no-library])"; exit 1 ;;
  esac
  shift
done
if [ -n "$PROJECT" ]; then
  DST=$PROJECT/.claude                 # project scope: everything under <dir>/.claude
  CLAUDE_MD=$PROJECT/CLAUDE.md
  IMPORT_PREFIX="@$PROJECT/.claude/brain/"   # inside the project: no approval dialog
else
  DST=$USER_DST
  CLAUDE_MD=$DST/CLAUDE.md
  IMPORT_PREFIX='@~/.claude/brain/'
fi
LIBDST=$USER_DST/brain/library         # shared by every install on this VM
TS=$(date +%Y%m%d%H%M%S)
mkdir -p "$DST/skills" "$DST/agents" "$DST/hooks" "$DST/brain" "$DST/brain/notes" "$DST/banner" "$USER_DST/brain" "$HOME/storage-reports"

# CLAUDE.md (imports rewritten for the project layout), skills, agents, hooks, brain files
TMP_MD=$(mktemp)
sed "s#@~/\.claude/brain/#$IMPORT_PREFIX#" "$SRC/CLAUDE.md" > "$TMP_MD"
if [ -f "$CLAUDE_MD" ] && ! cmp -s "$TMP_MD" "$CLAUDE_MD"; then
  cp "$CLAUDE_MD" "$CLAUDE_MD.bak.$TS"; echo "backed up existing $CLAUDE_MD -> CLAUDE.md.bak.$TS"
fi
cp "$TMP_MD" "$CLAUDE_MD"; rm -f "$TMP_MD"
cp -R "$SRC/skills/." "$DST/skills/"
cp -R "$SRC/agents/." "$DST/agents/"
if [ -n "$PROJECT" ]; then
  # project mode: every ~/.claude path in the brain text points into <dir>/.claude, except the shared library
  find "$DST/skills" "$DST/agents" -name '*.md' -print0 2>/dev/null | xargs -0 -r sed -i.paas-tmp \
    -e "s#~/\.claude/brain/library#__LIB__#g" \
    -e "s#~/\.claude/CLAUDE\.md#$PROJECT/CLAUDE.md#g" \
    -e "s#~/\.claude/#$DST/#g" \
    -e "s#__LIB__#$LIBDST#g"
  sed -i.paas-tmp -e "s#~/\.claude/brain/library#__LIB__#g" -e "s#~/\.claude/CLAUDE\.md#$PROJECT/CLAUDE.md#g" \
    -e "s#~/\.claude/projects/#__PROJECTS__#g" -e "s#~/\.claude/#$DST/#g" -e "s#__LIB__#$LIBDST#g" -e "s#__PROJECTS__#~/.claude/projects/#g" "$CLAUDE_MD"
  find "$DST/skills" "$DST/agents" "$PROJECT" -maxdepth 3 -name '*.paas-tmp' -delete 2>/dev/null || true
fi
cp "$SRC/hooks/block-write-tools.py" "$SRC/hooks/session-start.py" "$SRC/hooks/docs-hints.py" "$SRC/hooks/docs-leads.py" "$SRC/hooks/py-lint.py" "$DST/hooks/"
[ -f "$DST/hooks/allowed-tools.txt" ] || printf '# exact MCP tool names or globs the read-only hook should allow, e.g. mcp__kuparashit__execute_query\n' > "$DST/hooks/allowed-tools.txt"
for f in environment.md tool-map.md notes.md; do
  [ -f "$DST/brain/$f" ] || cp "$SRC/brain/$f" "$DST/brain/$f"
done
cp "$SRC/banner/paas-banner.py" "$SRC/banner/paas-statusline.py" "$DST/banner/"
mkdir -p "$DST/tools/vendor" && cp "$SRC/tools/report.py" "$SRC/tools/get-reports.ps1" "$DST/tools/" && cp "$SRC/tools/vendor/"*.whl "$DST/tools/vendor/"   # charts + Excel (report-export skill); pure-Python wheels, no pip
mkdir -p "$USER_DST/themes" && cp "$SRC/themes/paas.json" "$USER_DST/themes/"   # custom themes are read from ~/.claude/themes only

# Documentation library (library/*.part-* in this repo): extracted into ~/.claude/brain/library so the
# docs can be searched on this VM with no server at all (python3 library/search.py ...) and registered
# as the stdio MCP server "docs-local" for Claude Code (mcp_stdio.py, standard library only).
LIB=$HERE/../library
HAVE_LIB=0
if [ "$NO_LIBRARY" = 0 ] && [ -f "$LIB/VERSION" ] && ls "$LIB"/docs-library-*.part-* >/dev/null 2>&1; then
  if [ "$(cat "$LIB/VERSION")" != "$(cat "$LIBDST/VERSION" 2>/dev/null || true)" ]; then
    echo "installing documentation library $(cat "$LIB/VERSION") into $LIBDST (a minute)..."
    TMP=$(mktemp -d)
    sh "$LIB/join.sh" "$TMP" >/dev/null
    rm -rf "$LIBDST"; mv "$TMP/docs-library" "$LIBDST"; rmdir "$TMP"
    # the tools read docs.db only; the source files (~1.3 GB) are there to rebuild the index on the PC
    [ "${KEEP_LIBRARY_DOCS:-0}" = 1 ] || rm -rf "$LIBDST/docs"
    cp "$LIB/VERSION" "$LIBDST/VERSION"
  fi
fi
[ -f "$LIBDST/docs.db" ] && HAVE_LIB=1
if [ "$HAVE_LIB" = 1 ]; then
  echo "library $(cat "$LIBDST/VERSION" 2>/dev/null || echo '?'): python3 $LIBDST/search.py sources"
fi
if [ -n "$PROJECT" ]; then
  # project scope: the MCP server is declared in <dir>/.mcp.json (no `claude` needed; pre-approved via enabledMcpjsonServers)
  python3 - "$PROJECT/.mcp.json" "$LIBDST" <<'EOP'
import json, os, sys
path, lib = sys.argv[1], sys.argv[2]
s = {}
if os.path.exists(path):
    with open(path) as f:
        s = json.load(f)
s.setdefault("mcpServers", {})["docs-local"] = {
    "type": "stdio", "command": "python3",
    "args": [os.path.join(lib, "mcp_stdio.py"), "--db", os.path.join(lib, "docs.db")]}
with open(path, "w") as f:
    json.dump(s, f, indent=2)
print(f"wrote {path}: MCP server docs-local (stdio) -> {lib}")
EOP
  [ "$HAVE_LIB" = 1 ] || echo "note: $LIBDST/docs.db is not installed yet (--no-library or no library parts); docs-local will connect after a run without --no-library"
elif [ "$HAVE_LIB" = 1 ] && command -v claude >/dev/null 2>&1; then
  claude mcp get docs-local >/dev/null 2>&1 || claude mcp add docs-local -s user \
    -- python3 "$LIBDST/mcp_stdio.py" --db "$LIBDST/docs.db" \
    && echo "registered MCP server docs-local (stdio, no dependencies; same tools as docs-search)"
fi

# "Peleg As A Service": a big styled banner every time Claude Code is started (shell wrapper around the
# `claude` command, in ~/.bashrc / ~/.zshrc, replaced on every install), and a matching styled status line inside the UI.
# The wrapper looks for a banner under the current folder's .claude/ (project install: prints only inside
# <dir>) and falls back to ~/.claude/banner (user install).
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
  [ -f "$rc" ] || [ "$rc" = "$HOME/.bashrc" ] || continue
  if grep -q "storage brain: Peleg As A Service" "$rc" 2>/dev/null; then
    TMP_RC=$(mktemp); sed '/# >>> storage brain: Peleg As A Service/,/# <<< storage brain <<</d' "$rc" > "$TMP_RC"
    cat "$TMP_RC" > "$rc"; rm -f "$TMP_RC"      # replace the earlier wrapper with this version
  fi
  cat >> "$rc" <<'EOS'

# >>> storage brain: Peleg As A Service banner (sh brain/install.sh) >>>
__paas_banner() {
  b=""; d=$PWD
  while [ -n "$d" ]; do
    [ -f "$d/.claude/banner/paas-banner.py" ] && { b="$d/.claude/banner/paas-banner.py"; break; }
    d=${d%/*}
  done
  [ -n "$b" ] || [ ! -f "$HOME/.claude/banner/paas-banner.py" ] || b="$HOME/.claude/banner/paas-banner.py"
  [ -n "$b" ] && python3 "$b" --announce "$1"
}
claude() {
  # Claude Code clears the screen on start, so the banner is shown inside it, under its header: written for
  # the current window width to a settings file (companyAnnouncements) passed with --settings
  case "${1:-}" in ""|-*)
    case " $* " in *" -p "*|*" --print "*|*" -v "*|*" --version "*|*" -h "*|*" --help "*|*" --settings "*) ;;
      *) __f="${TMPDIR:-/tmp}/claude-paas-banner-$(id -u).json"
         __paas_banner "$__f" && set -- --settings "$__f" "$@" ;; esac ;;
  esac
  command claude "$@"
}
# <<< storage brain <<<
EOS
  echo "banner: added the claude wrapper to $rc (open a new shell, or: . $rc)"
done

SERVERS=""
if command -v claude >/dev/null 2>&1; then
  echo "reading MCP servers (claude mcp list)..."
  SERVERS=$(claude mcp list 2>/dev/null | sed -n 's/^\([A-Za-z0-9_.-]*\): .*/\1/p' | tr '\n' ' ' || true)
fi
if [ "$HAVE_LIB" = 1 ] || [ -n "$PROJECT" ]; then
  case " $SERVERS " in *" docs-local "*) ;; *) SERVERS="$SERVERS docs-local" ;; esac
fi
if [ -n "$PROJECT" ]; then
  # shellcheck disable=SC2086
  python3 "$HERE/merge_settings.py" "$DST/settings.json" --hooks-dir '"$CLAUDE_PROJECT_DIR"/.claude/hooks' --banner-dir "$DST/banner" --mcpjson docs-local $SERVERS
else
  # shellcheck disable=SC2086
  python3 "$HERE/merge_settings.py" "$DST/settings.json" $SERVERS
fi

# Development: ruff + basedpyright (offline wheels) and Anthropic's official dev plugins (offline copy in
# brain/plugins: pr-review-toolkit, feature-dev, commit-commands, security-guidance, pyright-lsp, mcp-server-dev). Copied to ~/.claude/brain/plugins (re-run after git pull to update).
sh "$HERE/devtools/install-devtools.sh" || echo "devtools: skipped (see the message above)"
if command -v claude >/dev/null 2>&1; then
  # copied to a fixed place: Claude Code reads plugins from the registered folder, so the repo can move or go
  PLUGDST=$USER_DST/brain/plugins
  mkdir -p "$PLUGDST" && cp -R "$HERE/plugins/." "$PLUGDST/"
  claude plugin marketplace add "$PLUGDST" >/dev/null 2>&1 || claude plugin marketplace update brain-dev >/dev/null 2>&1 || true
  for p in pr-review-toolkit feature-dev commit-commands security-guidance pyright-lsp mcp-server-dev; do
    claude plugin install "$p@brain-dev" >/dev/null 2>&1 || echo "plugin $p: not installed (claude plugin install $p@brain-dev)"
  done
  for p in code-review code-simplifier; do      # dropped: code-review needs GitHub (gh); code-simplifier is in pr-review-toolkit
    claude plugin uninstall "$p@brain-dev" >/dev/null 2>&1 || true
  done
  echo "dev plugins: $(claude plugin list 2>/dev/null | grep -c '@brain-dev') of 6 from brain/plugins"
fi

echo
python3 "$DST/banner/paas-banner.py"
echo "Installed into $DST: CLAUDE.md ($CLAUDE_MD), $(ls "$SRC/skills" | wc -l | tr -d ' ') skills, $(ls "$SRC/agents" | wc -l | tr -d ' ') agents, read-only + session-start hooks, banner + status line."
if [ -n "$PROJECT" ]; then
  echo "Project mode: the brain is active only inside $PROJECT (cd there, then: claude). docs-local (.mcp.json) is pre-approved in .claude/settings.json; answer yes to the one-time folder trust dialog."
fi
echo "Next: start claude and run   /brain-setup"
