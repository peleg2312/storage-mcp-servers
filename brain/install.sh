#!/bin/sh
# Install the storage brain for Claude Code.
#   sh install.sh                      into ~/.claude (user scope: every folder on this VM)
#   sh install.sh --project <dir>      into <dir> only: <dir>/CLAUDE.md, <dir>/.claude/{skills,agents,hooks,brain,banner,
#                                      settings.json} and <dir>/.mcp.json - the brain exists only inside that folder
#   sh install.sh --no-library         skip the documentation library (when docs-search runs on the cluster)
#   sh install.sh --brain-remote <url>  share the team knowledge (notes/, captures/, incidents/, tool-map.md) through a git
#                                      remote, e.g. an internal GitLab project (or env BRAIN_REMOTE); notes.md and
#                                      environment.md stay personal. Idempotent.
#   sh install.sh --team <name>        a team profile (brain/teams/<name>: san, nas, ...; or env BRAIN_TEAM): its rules,
#                                      skills, agents and knowledge folder, switchable later with `paas-team use <other>`
#   sh install.sh --team-source <url|dir>  take the team from a published team repository (GitLab) instead of this clone
# Re-run after every git pull; your environment.md, tool-map.md, notes.md, notes/ and allowed-tools.txt are kept.
# The documentation library is always shared in ~/.claude/brain/library (also in project mode).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$HERE/claude
USER_DST=${CLAUDE_HOME:-$HOME/.claude}
PROJECT=""
NO_LIBRARY=0
BRAIN_REMOTE=${BRAIN_REMOTE:-}
TEAM=${BRAIN_TEAM:-}
TEAM_SOURCE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-library) NO_LIBRARY=1 ;;
    --team) [ $# -ge 2 ] || { echo "usage: install.sh --team <name>"; exit 1; }; shift; TEAM=$1 ;;
    --team=*) TEAM=${1#--team=} ;;
    --team-source) [ $# -ge 2 ] || { echo "usage: install.sh --team-source <url|dir>"; exit 1; }; shift; TEAM_SOURCE=$1 ;;
    --team-source=*) TEAM_SOURCE=${1#--team-source=} ;;
    --brain-remote) [ $# -ge 2 ] || { echo "usage: install.sh --brain-remote <url>"; exit 1; }
                    shift; BRAIN_REMOTE=$1 ;;
    --brain-remote=*) BRAIN_REMOTE=${1#--brain-remote=} ;;
    --project) [ $# -ge 2 ] || { echo "usage: install.sh [--project <dir>] [--no-library]"; exit 1; }
               shift; mkdir -p "$1"; PROJECT=$(cd "$1" && pwd) ;;
    --project=*) PROJECT=${1#--project=}; mkdir -p "$PROJECT"; PROJECT=$(cd "$PROJECT" && pwd) ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (usage: install.sh [--project <dir>] [--no-library] [--team <name>])"; exit 1 ;;
  esac
  shift
done
[ -z "$TEAM" ] || [ -z "$PROJECT" ] || { echo "install.sh: --team works with the user install only (not --project)"; exit 1; }
[ -z "$TEAM" ] || [ -n "$TEAM_SOURCE" ] || [ -f "$HERE/teams/$TEAM/team.json" ] || { echo "install.sh: no team '$TEAM' in brain/teams"; exit 1; }
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
[ ! -L "$LIBDST" ] || LIBDST=$(readlink -f "$LIBDST")   # multi-user VM: root's library is a link to /opt/paas/library
esc() { printf '%s' "$1" | sed 's/[&#\\]/\\&/g'; }   # a path as a sed replacement ('#' is our delimiter)
TS=$(date +%Y%m%d%H%M%S)
mkdir -p "$DST/skills" "$DST/agents" "$DST/hooks" "$DST/brain" "$DST/brain/notes" "$DST/banner" "$USER_DST/brain" "$HOME/storage-reports"

# CLAUDE.md (imports rewritten for the project layout), skills, agents, hooks, brain files
# Project mode never replaces a CLAUDE.md that is not ours (no first-line marker): the brain text goes to
# .claude/brain/main.md and CLAUDE.md only gets an import line.
BRAIN_MD=$CLAUDE_MD
MARK=$(head -n1 "$SRC/CLAUDE.md")
if [ -n "$PROJECT" ] && [ -f "$CLAUDE_MD" ] && [ "$(head -n1 "$CLAUDE_MD")" != "$MARK" ]; then
  BRAIN_MD=$DST/brain/main.md
  grep -qF "${IMPORT_PREFIX}main.md" "$CLAUDE_MD" || printf '\n## Storage brain\n%smain.md\n' "$IMPORT_PREFIX" >> "$CLAUDE_MD"
  echo "note: $CLAUDE_MD is your own; left as is, the brain rules are imported from $BRAIN_MD"
fi
TMP_MD=$(mktemp)
sed "s#@~/\.claude/brain/#$(esc "$IMPORT_PREFIX")#" "$SRC/CLAUDE.md" > "$TMP_MD"
if [ -z "$PROJECT" ] && [ -f "$CLAUDE_MD" ] && ! cmp -s "$TMP_MD" "$CLAUDE_MD"; then
  cp "$CLAUDE_MD" "$CLAUDE_MD.bak.$TS"; echo "backed up existing $CLAUDE_MD -> CLAUDE.md.bak.$TS"
fi
cp "$TMP_MD" "$BRAIN_MD"; rm -f "$TMP_MD"
# the storage rules: loaded in plain chats (~/chats, see below) and in a project install; code projects read them on demand.
# The persona ("who you work for") is the team profile's (brain/teams/<team>/persona.md; san without --team).
# With --team, paas-team (below) puts the team's persona, rules, skills and agents in place instead of these copies.
if [ -z "$TEAM" ]; then
  sed "s#@~/\.claude/brain/#$(esc "$IMPORT_PREFIX")#" "$SRC/brain/storage.md" > "$DST/brain/storage.md"
  [ ! -L "$DST/brain/persona.md" ] || rm -f "$DST/brain/persona.md"
  cp "$HERE/teams/san/persona.md" "$DST/brain/persona.md"
  cp -R "$SRC/skills/." "$DST/skills/"
  cp -R "$SRC/agents/." "$DST/agents/"
fi
cp "$SRC/brain/coding.md" "$DST/brain/coding.md"      # coding rules, read on demand by code work only
[ -z "$PROJECT" ] || grep -q "^@.*storage\.md" "$BRAIN_MD" || printf '\n## Storage rules\n%sstorage.md\n' "$IMPORT_PREFIX" >> "$BRAIN_MD"
if [ -n "$PROJECT" ]; then
  # project mode: every ~/.claude path in the brain text points into <dir>/.claude, except the shared library
  P_E=$(esc "$PROJECT"); D_E=$(esc "$DST"); L_E=$(esc "$LIBDST")
  find "$DST/skills" "$DST/agents" -name '*.md' -print0 2>/dev/null | xargs -0 -r sed -i.paas-tmp \
    -e "s#~/\.claude/brain/library#__LIB__#g" \
    -e "s#~/\.claude/CLAUDE\.md#$P_E/CLAUDE.md#g" \
    -e "s#~/\.claude/#$D_E/#g" \
    -e "s#__LIB__#$L_E#g"
  sed -i.paas-tmp -e "s#~/\.claude/brain/library#__LIB__#g" -e "s#~/\.claude/CLAUDE\.md#$P_E/CLAUDE.md#g" \
    -e "s#~/\.claude/projects/#__PROJECTS__#g" -e "s#~/\.claude/#$D_E/#g" -e "s#__LIB__#$L_E#g" -e "s#__PROJECTS__#~/.claude/projects/#g" "$BRAIN_MD" "$DST/brain/storage.md"
  find "$DST/skills" "$DST/agents" "$PROJECT" -maxdepth 3 -name '*.paas-tmp' -delete 2>/dev/null || true
fi
cp "$SRC/hooks/block-write-tools.py" "$SRC/hooks/session-start.py" "$SRC/hooks/docs-hints.py" "$SRC/hooks/docs-leads.py" "$SRC/hooks/py-lint.py" "$SRC/hooks/notes-check.py" "$SRC/hooks/capture-nudge.py" "$DST/hooks/"
[ -f "$DST/hooks/allowed-tools.txt" ] || printf '# exact MCP tool names or globs the read-only hook should allow, e.g. mcp__kuparashit__execute_query\n' > "$DST/hooks/allowed-tools.txt"
[ -n "$TEAM" ] || for f in environment.md tool-map.md notes.md; do
  [ -f "$DST/brain/$f" ] || cp "$SRC/brain/$f" "$DST/brain/$f"
done
cp "$SRC/banner/paas-banner.py" "$SRC/banner/paas-statusline.py" "$DST/banner/"
mkdir -p "$DST/tools/vendor" && cp "$SRC/tools/report.py" "$SRC/tools/get-reports.ps1" "$SRC/tools/db_mcp.py" "$SRC/tools/add-docs" "$SRC/tools/paas-open" "$SRC/tools/paas-team" "$DST/tools/"
cp "$HERE/../docs-search-mcp/docs_index.py" "$DST/tools/"     # add-docs: your own documents into the library
[ -f "$USER_DST/brain/databases.json" ] || cp "$SRC/tools/databases.example.json" "$USER_DST/brain/databases.example.json"
cp "$SRC/tools/vendor/"*.whl "$DST/tools/vendor/"   # charts + Excel (report-export skill); pure-Python wheels, no pip
mkdir -p "$USER_DST/themes" && cp "$SRC/themes/paas.json" "$USER_DST/themes/"   # custom themes are read from ~/.claude/themes only

# Documentation library (library/*.part-* in this repo): extracted into ~/.claude/brain/library so the
# docs can be searched on this VM with no server at all (python3 library/search.py ...) and registered
# as the stdio MCP server "docs-local" for Claude Code (mcp_stdio.py, standard library only).
LIB=$HERE/../library
HAVE_LIB=0
NEW_LIB=0
mkdir -p "$USER_DST/brain/inbox"                   # your own documents (add-docs); kept across library updates
# the brain as a git history (notes-check.py commits each saved note); big or private things stay out of it
if command -v git >/dev/null 2>&1 && [ ! -d "$USER_DST/brain/.git" ]; then
  ( cd "$USER_DST/brain" && git init -q \
    && printf 'library/\ninbox/\nplugins/\nteams/\nteam-sources/\nteam\nteam-mode\npersona.md\n.nudged/\n.brain-index/\n*.bak\n*.db\n.DS_Store\nnotes.md\nenvironment.md\nmain.md\nstorage.md\ncoding.md\ndatabases.example.json\n' > .gitignore \
    && git add -A >/dev/null 2>&1 \
    && git -c user.name=brain -c user.email=brain@localhost commit -q -m 'brain: initial' >/dev/null 2>&1 ) \
    || echo "note: could not start a git history in $USER_DST/brain (skipped)"
fi
if [ -d "$USER_DST/brain/.git" ]; then                 # an older history learns new ignore lines
  for l in library/ inbox/ plugins/ teams/ team-sources/ team team-mode persona.md .nudged/ .brain-index/ '*.bak' '*.db' .DS_Store notes.md environment.md main.md storage.md coding.md databases.example.json; do
    grep -qxF -- "$l" "$USER_DST/brain/.gitignore" 2>/dev/null || echo "$l" >> "$USER_DST/brain/.gitignore"
  done
  # notes.md and environment.md are personal (management IPs, owners); main.md, storage.md, coding.md are the
  # installer's (they differ between brain versions): out of the shared history, files kept
  if ( cd "$USER_DST/brain" && git ls-files notes.md environment.md main.md storage.md coding.md databases.example.json | grep -q . ); then
    ( cd "$USER_DST/brain" && git rm --cached -q notes.md environment.md main.md storage.md coding.md databases.example.json 2>/dev/null; git add .gitignore >/dev/null 2>&1
      git -c user.name=brain -c user.email=brain@localhost commit -q -m 'brain: personal files leave the history' >/dev/null 2>&1 ) || true
  fi
fi
# Team profile: the team repository (plugin + knowledge) built from this clone, or taken from --team-source, is cloned
# into ~/.claude/brain/teams/<team> and switched on; `paas-team use <other>` changes team later, `paas-team` shows the state.
if [ -n "$TEAM" ]; then
  mkdir -p "$HOME/.local/bin" && ln -sf "$DST/tools/paas-team" "$HOME/.local/bin/paas-team"
  # the team is the Claude Code plugin wherever claude is installed (the same install as every laptop); without claude the
  # skills are copied into ~/.claude and the hooks come from settings.json
  if command -v claude >/dev/null 2>&1; then echo plugin > "$USER_DST/brain/team-mode"; else echo files > "$USER_DST/brain/team-mode"; fi
  # every team of this clone as a local source (~480 KB each), so `paas-team use <other>` works offline later
  python3 "$HERE/teams/publish.py" --all --to "$USER_DST/brain/team-sources" >/dev/null
  if [ -n "$TEAM_SOURCE" ]; then
    python3 "$DST/tools/paas-team" add "$TEAM" "$TEAM_SOURCE"
  elif [ -d "$USER_DST/brain/teams/$TEAM" ] && case "$(git -C "$USER_DST/brain/teams/$TEAM" remote get-url origin 2>/dev/null)" in ""|"$USER_DST/brain/team-sources/"*) true ;; *) false ;; esac; then
    # added earlier from this clone (no remote, or this clone's team-sources): this clone's plugin replaces the old one.
    # A team taken from a published repository (--team-source, GitLab) is left to `paas-team sync`.
    rm -rf "$USER_DST/brain/teams/$TEAM/paas-brain-$TEAM"; cp -R "$USER_DST/brain/team-sources/$TEAM/paas-brain-$TEAM" "$USER_DST/brain/teams/$TEAM/"
    cp "$USER_DST/brain/team-sources/$TEAM/.claude-plugin/marketplace.json" "$USER_DST/brain/teams/$TEAM/.claude-plugin/"
    ( cd "$USER_DST/brain/teams/$TEAM" \&\& git add -A >/dev/null 2>\&1 \&\& git -c user.name=brain -c user.email=brain@localhost commit -q -m "team $TEAM: plugin updated by install.sh" >/dev/null 2>\&1 ) || true
  else
    python3 "$DST/tools/paas-team" add "$TEAM"
  fi
  python3 "$DST/tools/paas-team" use "$TEAM"
  [ -z "$BRAIN_REMOTE" ] || { python3 "$DST/tools/paas-team" remote "$TEAM" "$BRAIN_REMOTE" \
    && python3 "$DST/hooks/notes-check.py" --remote "$BRAIN_REMOTE" || echo "note: the shared team remote is not set up yet (see the line above)"; }
elif [ -n "$BRAIN_REMOTE" ] && [ -d "$USER_DST/brain/.git" ]; then   # shared team knowledge (hooks are copied above)
  python3 "$DST/hooks/notes-check.py" --remote "$BRAIN_REMOTE" || echo "note: the shared brain is not set up yet (see the line above)"
fi
if [ "$NO_LIBRARY" = 0 ] && [ -f "$LIB/VERSION" ] && ls "$LIB"/docs-library-*.part-* >/dev/null 2>&1; then
  if [ "$(cat "$LIB/VERSION")" != "$(cat "$LIBDST/VERSION" 2>/dev/null || true)" ]; then
    echo "installing documentation library $(cat "$LIB/VERSION") into $LIBDST (a minute)..."
    TMP=$(mktemp -d)
    sh "$LIB/join.sh" "$TMP" >/dev/null
    rm -rf "$LIBDST"; mv "$TMP/docs-library" "$LIBDST"; rm -rf "$TMP"
    find "$LIBDST" -name '._*' -type f -delete 2>/dev/null || true     # macOS metadata in archives packed on a Mac
    # the tools read docs.db only; the source files (~1.3 GB) are there to rebuild the index on the PC
    [ "${KEEP_LIBRARY_DOCS:-0}" = 1 ] || rm -rf "$LIBDST/docs"
    cp "$LIB/VERSION" "$LIBDST/VERSION"
    NEW_LIB=1
  fi
fi
[ -f "$LIBDST/docs.db" ] && HAVE_LIB=1
# run this repo's server code over the library without repacking its parts
if [ -d "$LIBDST" ]; then
  cp "$HERE/../docs-search-mcp/search_cli.py" "$LIBDST/search.py"
  cp "$HERE/../docs-search-mcp/mcp_stdio.py" "$HERE/../docs-search-mcp/docs_text.py" "$LIBDST/"
fi
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
fi
# dev tools first (ruff, basedpyright, database drivers): the databases MCP below needs their Python
sh "$HERE/devtools/install-devtools.sh" || echo "devtools: skipped (see the message above)"
[ -n "$PROJECT" ] || { mkdir -p "$HOME/.local/bin" && ln -sf "$DST/tools/add-docs" "$HOME/.local/bin/add-docs"; ln -sf "$DST/tools/paas-open" "$HOME/.local/bin/paas-open"; ln -sf "$USER_DST/brain/plugins/chrome-devtools/bin/run.sh" "$HOME/.local/bin/paas-chrome"; }
# a new library replaced docs.db: put the documents from your inbox back in (add-docs needs pypdf from the devtools)
if [ "$NEW_LIB" = 1 ] && [ -n "$(find "$USER_DST/brain/inbox" -type f ! -name '._*' 2>/dev/null | head -1)" ]; then
  echo "re-adding your documents from $USER_DST/brain/inbox..."
  DOCS_DB="$LIBDST/docs.db" sh "$DST/tools/add-docs" | tail -1 || echo "add-docs failed: run add-docs to retry"
fi
# PostgreSQL / MongoDB MCP for development (connections: ~/.claude/brain/databases.json), only when its drivers work:
# a registered server that cannot start shows "Failed to connect" in every session
DBPY=$USER_DST/devtools-venv/bin/python
if ! "$DBPY" -c "import psycopg, pymongo" >/dev/null 2>&1; then
  echo "databases MCP: not registered (no drivers in $USER_DST/devtools-venv; Linux x86_64 with Python 3.9 or 3.12 needed)"
  command -v claude >/dev/null 2>&1 && claude mcp remove databases -s user >/dev/null 2>&1 || true
elif [ -z "$PROJECT" ] && command -v claude >/dev/null 2>&1; then
  claude mcp get databases >/dev/null 2>&1 || { claude mcp add databases -s user \
    -- "$DBPY" "$DST/tools/db_mcp.py" >/dev/null 2>&1 \
    && echo "registered MCP server databases (read-only PostgreSQL / MongoDB; add connections in ~/.claude/brain/databases.json)"; }
fi
if [ -n "$PROJECT" ]; then :
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
  NOHOOKS=""; [ -n "$TEAM" ] && [ "$(cat "$USER_DST/brain/team-mode" 2>/dev/null)" = plugin ] && NOHOOKS="--no-hooks"   # the plugin runs them
  # shellcheck disable=SC2086
  python3 "$HERE/merge_settings.py" "$DST/settings.json" $NOHOOKS $SERVERS
  sh "$HERE/multiuser/setup-chats.sh" "$DST/hooks/session-start.py"
fi

# Development: ruff + basedpyright (offline wheels) and Anthropic's official dev plugins (offline copy in
# brain/plugins, copied to ~/.claude/brain/plugins: Claude Code reads plugins from the registered folder, so the repo can move).
# Installed by default: pyright-lsp, security-guidance, dev-discipline, commit-commands (~300 tokens per session).
# The rest (pr-review-toolkit, feature-dev, mcp-server-dev) are opt-in: claude plugin install <name>@brain-dev
# Dev tools and the banner wrapper are per user in both modes; plugins are user-scope only, so a project install skips them.
PLUGDST=$USER_DST/brain/plugins
mkdir -p "$PLUGDST" && cp -R "$HERE/plugins/." "$PLUGDST/"
if [ -n "$PROJECT" ]; then
  echo "plugins: skipped in project mode (claude plugin install has no project scope)"
elif command -v claude >/dev/null 2>&1; then
  claude plugin marketplace add "$PLUGDST" >/dev/null 2>&1 || claude plugin marketplace update brain-dev >/dev/null 2>&1 || true
  HAVE=$(claude plugin list 2>/dev/null || true)
  for p in pyright-lsp security-guidance dev-discipline commit-commands; do
    case "$HAVE" in *"$p@brain-dev"*) ;; *) claude plugin install "$p@brain-dev" >/dev/null 2>&1 || echo "plugin $p: not installed (claude plugin install $p@brain-dev)" ;; esac
  done
  echo "dev plugins: $(claude plugin list 2>/dev/null | grep -c '@brain-dev') from brain/plugins (4 by default; earlier installs keep any others until: claude plugin uninstall <name>@brain-dev)"
fi

echo
python3 "$DST/banner/paas-banner.py"
echo "Installed into $DST: CLAUDE.md ($CLAUDE_MD), $(ls "$DST/skills" | wc -l | tr -d ' ') skills, $(ls "$DST/agents"/*.md | wc -l | tr -d ' ') agents, read-only + session-start hooks, banner + status line.${TEAM:+ Team $TEAM active (paas-team use <team> switches).}"
if [ -n "$PROJECT" ]; then
  echo "Project mode: the brain is active only inside $PROJECT (cd there, then: claude). docs-local (.mcp.json) is pre-approved in .claude/settings.json; answer yes to the one-time folder trust dialog."
fi
[ ! -f /etc/paas/gate.key ] || echo "multi-user VM: now run  sh $HERE/multiuser/install-shared.sh  (refreshes /opt/paas and strips the duplicate hooks)"
echo "Next: start claude and run   /brain-setup"
