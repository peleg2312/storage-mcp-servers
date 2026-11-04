#!/bin/sh
# Join this team's brain on a Linux or macOS machine with Claude Code, from a clone of the team repository:
#   git clone <team repository url> && sh brain-<team>/join.sh          [--no-sudo]
# 1. trusts the VM's certificate (the plugin's lib/paas-ui.crt): the system store with sudo, else NODE_EXTRA_CA_CERTS in your
#    shell profile; 2. checks the VM's docs service (TCP, certificate, token); 3. adds the team marketplace and installs (or
#    updates) the plugin; 4. checks that Claude Code connects docs-http. Safe to run again. Nothing here needs Python.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
NOSUDO=0; [ "${1:-}" = "--no-sudo" ] && NOSUDO=1
TEAM=$(sed -n 's/^ *"name": *"\([a-z0-9_-]*\)".*/\1/p' "$HERE/team.json" | head -1)
[ -n "$TEAM" ] || { echo "join: no team.json here: run this from a clone of the team repository"; exit 1; }
PLUG="paas-brain-$TEAM"
CRT="$HERE/$PLUG/lib/paas-ui.crt"
DOCS=$(grep -o 'https\{0,1\}://[^"]*?team=[^"]*' "$HERE/$PLUG/.mcp.json" 2>/dev/null | head -1 || true)
ok() { printf '  ok    %s\n' "$*"; }
bad() { printf '  FAIL  %s\n' "$*"; FAILED=1; }
FAILED=0
echo "team $TEAM"
command -v claude >/dev/null 2>&1 || { echo "join: Claude Code (claude) is not installed or not on PATH"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "join: git is missing (Claude Code installs the team marketplace with it)"; exit 1; }

# 1. the VM's certificate
EXTRA=""
if [ -z "$DOCS" ]; then
  bad "the plugin has no docs-http: the team was published without the VM's docs address (re-run the VM's installer)"
elif [ "${DOCS#http://}" != "$DOCS" ]; then                  # the VM serves plain HTTP (--plain-http): no certificate
  base=${DOCS%%/mcp*}
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$base/health" 2>/dev/null || true)
  case "$code" in
    200) ok "docs service answers: $base (plain HTTP, no certificate needed)" ;;
    000) bad "docs service not reachable at $base: the port must be open (TCP) from this machine to the VM, and the VM name in the url must resolve" ;;
    *) bad "docs service at $base answered $code" ;;
  esac
elif [ ! -f "$CRT" ]; then
  bad "no certificate in $PLUG/lib/paas-ui.crt (publish the team on the VM, where the certificate is)"
else
  installed=""
  if [ "$(uname -s)" = Darwin ]; then
    security add-trusted-cert -r trustRoot -k "$HOME/Library/Keychains/login.keychain-db" "$CRT" 2>/dev/null && installed="login keychain"
  elif [ "$NOSUDO" = 0 ] && command -v sudo >/dev/null 2>&1; then
    if [ -d /etc/pki/ca-trust/source/anchors ]; then
      sudo cp "$CRT" "/etc/pki/ca-trust/source/anchors/paas-$TEAM.crt" && sudo update-ca-trust && installed="system store (update-ca-trust)"
    elif [ -d /usr/local/share/ca-certificates ]; then
      sudo cp "$CRT" "/usr/local/share/ca-certificates/paas-$TEAM.crt" && sudo update-ca-certificates >/dev/null 2>&1 && installed="system store (update-ca-certificates)"
    fi
  fi
  if [ -n "$installed" ]; then ok "VM certificate trusted: $installed"
  else                                                     # no sudo: Claude Code reads NODE_EXTRA_CA_CERTS when it starts
    mkdir -p "$HOME/.claude"; cp "$CRT" "$HOME/.claude/paas-$TEAM.crt"; EXTRA="$HOME/.claude/paas-$TEAM.crt"
    for rc in "$HOME/.profile" "$HOME/.bashrc" "$HOME/.zshrc"; do
      [ -f "$rc" ] || [ "$rc" = "$HOME/.profile" ] || continue
      grep -q "NODE_EXTRA_CA_CERTS=$EXTRA" "$rc" 2>/dev/null || echo "export NODE_EXTRA_CA_CERTS=$EXTRA" >> "$rc"
    done
    ok "VM certificate: NODE_EXTRA_CA_CERTS=$EXTRA in your shell profile (open a new terminal before starting claude)"
  fi
  # 2. the docs service answers (TCP open, the certificate matches the name, the service is up)
  base=${DOCS%%/mcp*}
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 --cacert "$CRT" "$base/health" 2>/dev/null || true)
  case "$code" in
    200) ok "docs service answers: $base" ;;
    000) bad "docs service not reachable at $base: the port must be open (TCP) from this machine to the VM, and the VM name in the url must resolve" ;;
    *) bad "docs service at $base answered $code" ;;
  esac
fi

# 3. the plugin (the marketplace is this repository's own remote, or this folder when there is none)
SRC=$(git -C "$HERE" remote get-url origin 2>/dev/null || true); [ -n "$SRC" ] || SRC=$HERE
if claude plugin marketplace list 2>/dev/null | grep -q "$PLUG"; then claude plugin marketplace update "$PLUG" >/dev/null 2>&1 || true
else claude plugin marketplace add "$SRC" >/dev/null 2>&1 || bad "claude plugin marketplace add $SRC failed"; fi
if claude plugin list 2>/dev/null | grep -q "$PLUG@$PLUG"; then claude plugin update "$PLUG@$PLUG" >/dev/null 2>&1 || true
else claude plugin install "$PLUG@$PLUG" >/dev/null 2>&1 || bad "claude plugin install $PLUG@$PLUG failed"; fi
claude plugin list 2>/dev/null | grep -q "$PLUG@$PLUG" && ok "plugin $PLUG installed"

# 4. Claude Code connects docs-http
if [ -n "$DOCS" ]; then
  line=$(${EXTRA:+env NODE_EXTRA_CA_CERTS="$EXTRA"} claude mcp list 2>&1 | grep "$PLUG:docs-http" || true)
  case "$line" in
    *onnected*) ok "Claude Code connects docs-http" ;;
    *SELF_SIGNED*|*certificate*|*CERT*) bad "docs-http: certificate not trusted ($line)" ;;
    *) bad "docs-http: ${line:-not listed}" ;;
  esac
fi
if command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then ok "Python 3 found: the brain's hooks run"
else bad "Python 3 is missing: without it the read-only guard blocks MCP and shell calls (only docs-http works) and the team setup and notes sync do not run"; fi
[ "$FAILED" = 0 ] && echo "done: start claude; the first session sets the team up" || { echo "some checks failed (above)"; exit 1; }
