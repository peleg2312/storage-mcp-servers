#!/bin/sh
# The multi-user VM end to end, one command, as root. Safe to re-run; an update is `git pull` and the same command.
#
#   sh brain/multiuser/install-multiuser.sh \
#      --gitlab-host gitlab.example.com \
#      --team san=https://gitlab.example.com/storage/brain-san.git --team nas=https://gitlab.example.com/storage/brain-nas.git \
#      --groups "storage-san-team,storage-nas-team" [--people 8] [--api-key-file F] [--git-token-file F]
#
# What it does, in order: checks the packages; the brain for root (install-vm.sh); the shared base (install-shared.sh);
# the sign-in gate with its certificate (install-gate.sh); the API key (/etc/paas/api-key); who may sign in
# (/etc/paas/allowed-groups); the GitLab token for every account (paas-user git-token) and each team's repository url
# (recorded, then published there with the docs token); the shared base again, now with the certificate (marketplace,
# docs service, team repositories pushed); every account re-provisioned; then it checks the services, the gate, the docs
# service and each team repository and prints what is left for you.
# Flags are remembered in /etc/paas/multiuser.conf, so later runs need none. Secrets (API key, GitLab token) are asked
# once when missing and a terminal is present, or read from the --*-file flags; they are never printed.
#   --dry-run   print the plan and the remembered settings, change nothing (works as any user)
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
ETC=/etc/paas
CONF=$ETC/multiuser.conf
DRY=0; GITLAB_HOST=""; TEAM_URLS=""; GROUPS_CSV=""; PEOPLE=""; API_KEY_FILE=""; GIT_TOKEN_FILE=""
[ -f "$CONF" ] && . "$CONF"
while [ $# -gt 0 ]; do
  case "$1" in
    --gitlab-host) GITLAB_HOST=$(printf '%s' "$2" | tr 'A-Z' 'a-z'); shift 2 ;;
    --team) t=$2; case "$t" in *=*) ;; *) echo "install-multiuser: --team wants <name>=<git url>"; exit 1 ;; esac
            n=${t%%=*}; u=${t#*=}
            kept=""; for x in $TEAM_URLS; do case "$x" in "$n="*) ;; *) kept="${kept:+$kept }$x" ;; esac; done   # no case inside $(): bash 3.2 (macOS) misparses it
            TEAM_URLS="${kept:+$kept }$n=$u"; shift 2 ;;
    --groups) GROUPS_CSV=$(printf '%s' "$2" | tr 'A-Z' 'a-z' | tr -d ' '); shift 2 ;;
    --people) case "$2" in ''|*[!0-9]*) echo "install-multiuser: --people wants a number"; exit 1 ;; esac; PEOPLE=$2; shift 2 ;;
    --api-key-file) API_KEY_FILE=$2; shift 2 ;;
    --git-token-file) GIT_TOKEN_FILE=$2; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,/^set -eu/{/^set -eu/!p;}' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "install-multiuser: unknown option $1 (try --help)"; exit 1 ;;
  esac
done
if [ -z "$GITLAB_HOST" ] && [ -n "$TEAM_URLS" ]; then                     # the host of the first https team url
  for tu in $TEAM_URLS; do u=${tu#*=}; case "$u" in https://*|http://*) GITLAB_HOST=$(printf '%s' "$u" | sed -E 's#^[a-z]+://([^/@]*@)?([^/]+)/.*#\2#' | tr 'A-Z' 'a-z'); break ;; esac; done
fi
FQ=$(hostname -f 2>/dev/null || hostname)
say() { printf '\n== %s\n' "$*"; }
note() { printf '   %s\n' "$*"; }
TODO=""
todo() { TODO="$TODO
 - $*"; }

say "plan for $FQ"
note "1 packages  2 install-vm.sh (root's brain)  3 install-shared.sh  4 install-gate.sh  5 API key  6 who may sign in"
note "7 GitLab token + team repositories  8 install-shared.sh again (certificate, docs service, push to GitLab)  9 accounts  10 checks"
note "settings: gitlab host '${GITLAB_HOST:-none}', teams '${TEAM_URLS:-none}', groups '${GROUPS_CSV:-paas-users only}', people '${PEOPLE:-auto}'"
if [ "$DRY" = 1 ]; then echo; echo "dry run: nothing changed (settings file: $CONF)"; exit 0; fi
[ "$(id -u)" = 0 ] || { echo "install-multiuser: run as root"; exit 1; }

say "[1/10] packages"
MISSING=""
for c in git python3 openssl setfacl diff hostname; do command -v "$c" >/dev/null 2>&1 || MISSING="$MISSING $c"; done
[ -z "$MISSING" ] || { echo "missing:$MISSING  ->  dnf install git python3 openssl acl diffutils hostname"; exit 1; }
command -v claude >/dev/null 2>&1 && note "claude: $(command -v claude)" || { note "claude is not in root's PATH: install Claude Code first (the brain installs, plugins are skipped until then)"; todo "install Claude Code for root, then re-run this command"; }

# remember the settings before anything runs, so a run that stops half-way needs no flags again
mkdir -p "$ETC"; chmod 755 "$ETC"
{ echo "# written by install-multiuser.sh; re-run it without flags to reuse these"
  echo "GITLAB_HOST='$GITLAB_HOST'"; echo "TEAM_URLS='$TEAM_URLS'"; echo "GROUPS_CSV='$GROUPS_CSV'"; echo "PEOPLE='$PEOPLE'"; } > "$CONF"
chmod 644 "$CONF"
if [ -n "$PEOPLE" ]; then
  [ -f "$ETC/limits.env" ] && sed -i "s/^PAAS_PEOPLE=.*/PAAS_PEOPLE=$PEOPLE/" "$ETC/limits.env" || printf 'PAAS_PEOPLE=%s\n' "$PEOPLE" > "$ETC/limits.env"
fi

say "[2/10] the brain for root (install-vm.sh)"
(cd "$ROOT" && sh install-vm.sh)
say "[3/10] the shared base (install-shared.sh)"
sh "$HERE/install-shared.sh"
say "[4/10] the sign-in gate (install-gate.sh)"
sh "$HERE/install-gate.sh"

say "[5/10] the API key for everyone's Claude"
if [ -s "$ETC/api-key" ]; then note "already set ($ETC/api-key)"
elif [ -n "$API_KEY_FILE" ]; then head -n1 "$API_KEY_FILE" > "$ETC/api-key"; note "stored from $API_KEY_FILE"
elif [ -t 0 ]; then
  printf '   Anthropic API key (not shown; Enter to skip): '; stty -echo 2>/dev/null || true; IFS= read -r k; stty echo 2>/dev/null || true; echo
  k=$(printf '%s' "$k" | tr -d '[:space:]'); [ -z "$k" ] || printf '%s\n' "$k" > "$ETC/api-key"
  [ -n "$k" ] && note "stored" || todo "put the Anthropic API key into $ETC/api-key (one line) or pass --api-key-file"
else todo "put the Anthropic API key into $ETC/api-key (one line) or pass --api-key-file"; fi
chown root:paas-users "$ETC/api-key" 2>/dev/null || true; chmod 640 "$ETC/api-key"

say "[6/10] who may sign in"
if [ -n "$GROUPS_CSV" ]; then
  { echo "# groups whose members may sign in (one per line; local or AD groups); root always may"; echo paas-users
    printf '%s\n' "$GROUPS_CSV" | tr ',' '\n' | grep -v '^$' | grep -vx paas-users; } > "$ETC/allowed-groups"
fi
for g in $(grep -v '^#' "$ETC/allowed-groups" | grep -v '^$' | grep -vx paas-users); do
  if getent group "$g" >/dev/null 2>&1; then note "group $g: known"; else note "group $g: UNKNOWN here"; todo "join the VM to Active Directory (RUNBOOK, \"Active Directory accounts\") so that group $g resolves: getent group $g"; fi
done
[ -n "$GROUPS_CSV" ] || note "no AD groups given (--groups): only local accounts in paas-users may sign in (paas-user add <name>)"

say "[7/10] GitLab: the team token and each team's repository"
if [ -n "$GITLAB_HOST" ]; then
  if [ -s "$ETC/git/$GITLAB_HOST.token" ]; then note "token for $GITLAB_HOST: already stored"
  elif [ -n "$GIT_TOKEN_FILE" ]; then head -n1 "$GIT_TOKEN_FILE" | /opt/paas/bin/paas-user git-token "$GITLAB_HOST" >/dev/null && note "token for $GITLAB_HOST: stored from $GIT_TOKEN_FILE"
  elif [ -t 0 ]; then /opt/paas/bin/paas-user git-token "$GITLAB_HOST" >/dev/null && note "token for $GITLAB_HOST: stored" || todo "paas-user git-token $GITLAB_HOST  (a project or group access token: Developer, write_repository)"
  else todo "paas-user git-token $GITLAB_HOST  (a project or group access token: Developer, write_repository), or --git-token-file"; fi
else note "no --gitlab-host: the team repositories stay on this VM only (members' notes sync to /opt/paas/teams clones, not to GitLab)"; fi
for tu in $TEAM_URLS; do
  n=${tu%%=*}; u=${tu#*=}
  [ -d "$ROOT/brain/teams/$n" ] || { note "team $n: no such team in brain/teams"; todo "fix --team $n=... (teams: $(ls "$ROOT/brain/teams" | grep -v '\.' | tr '\n' ' '))"; continue; }
  python3 "$ROOT/brain/teams/publish.py" "$n" --to "/opt/paas/teams/$n" --remote "$u" >/dev/null && note "team $n: remote $u recorded"
done

say "[8/10] the shared base again (certificate, marketplace and docs service, team repositories pushed to GitLab)"
sh "$HERE/install-shared.sh"

say "[9/10] accounts"
/opt/paas/bin/paas-user provision --all >/dev/null && note "every existing account re-provisioned (helper, plugins, rules)"

say "[10/10] checks"
for s in paas-gate paas-docs paas-market-serve; do systemctl is-active --quiet "$s" && note "$s: running" || { note "$s: NOT running (journalctl -u $s -n 30)"; todo "systemctl status $s"; }; done
http() { python3 - "$1" <<'EOF'
import ssl, sys, urllib.request
try:
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(sys.argv[1], timeout=5, context=ctx) as r: print(r.status)
except Exception as e: print(getattr(e, "code", None) or type(e).__name__)
EOF
}
g=$(http https://127.0.0.1:3001/); [ "$g" = 200 ] && note "gate answers: https://$FQ:3001" || { note "gate on 3001 answered $g"; todo "check the gate: journalctl -u paas-gate -n 50"; }
DP=$(sed -n 's/^PAAS_DOCS_PORT=//p' "$ETC/docs.env" 2>/dev/null); DP=${DP:-8001}
d=$(http "https://127.0.0.1:$DP/health"); [ "$d" = 200 ] && note "docs service answers: https://$FQ:$DP/mcp (one token for everyone, in each team's mcp.json)" || { note "docs service answered $d"; todo "check the docs service: journalctl -u paas-docs -n 50"; }
for tu in $TEAM_URLS; do
  n=${tu%%=*}; u=${tu#*=}
  if GIT_TERMINAL_PROMPT=0 git -c credential.helper=/opt/paas/bin/paas-git-credential ls-remote --exit-code -q -- "$u" HEAD >/dev/null 2>&1; then note "team $n: $u reachable with the stored token"
  else note "team $n: $u NOT reachable with the stored token"; todo "team $n: create the project in GitLab (empty, branch main), store the token (paas-user git-token $GITLAB_HOST), re-run this command"; fi
done
echo
echo "done. Sign in: https://$FQ:3001 (AD or local account). Everyone starts without a team and picks one in the Brain tab."
echo "Laptops: claude plugin marketplace add <team url> && claude plugin install paas-brain-<team>@paas-brain-<team> && claude"
echo "Update later: git pull && sh brain/multiuser/install-multiuser.sh"
[ -z "$TODO" ] || { echo; echo "left for you:$TODO"; }
