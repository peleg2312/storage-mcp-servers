#!/bin/bash
# Multi-user acceptance checks (GATE-SPEC.md section 6), run as root on the VM or test container after
# install-shared.sh + install-gate.sh and `paas-user add` of two people.
#   PW_PELEG=... PW_DANA=... PW_EVE=... bash brain/multiuser/test-multiuser.sh
# eve = a Linux account NOT in paas-users. Passwords come from the environment, never printed.
set -u
G=https://127.0.0.1:3001
FAIL=0
check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2', want '$3'"; FAIL=1; fi; }
code() { curl -ks -o /dev/null -w '%{http_code}' "$@"; }
J='Content-Type: application/json'
cred() { python3 -c 'import json,sys;print(json.dumps({"username":sys.argv[1],"password":sys.argv[2]}))' "$1" "$2"; }
signin() {   # signin <user> <password> -> "<cookie value> <token>"
  local h; h=$(mktemp)
  local body; body=$(curl -ks -D "$h" -H "$J" -d "$(cred "$1" "$2")" $G/api/auth/login)
  local c; c=$(sed -n 's/^set-cookie: paas_gate=\([^;]*\).*/\1/ip' "$h" | tr -d '\r'); rm -f "$h"
  local t; t=$(echo "$body" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("token",""))' 2>/dev/null)
  echo "$c $t"
}
api() { curl -ks -H "Cookie: paas_gate=$1" -H "Authorization: Bearer $2" "$G$3"; }

check "sign-in page"                 "$(curl -ks $G/ | grep -c "Sign in with this VM")" 1
check "wrong password"               "$(code -H "$J" -d "$(cred peleg wrong-password)" $G/api/auth/login)" 401
check "account not in paas-users"    "$(code -H "$J" -d "$(cred eve "$PW_EVE")" $G/api/auth/login)" 401
read -r PC PT <<<"$(signin peleg "$PW_PELEG")"
check "peleg signs in (cookie+token)" "$([ -n "$PC" ] && [ -n "$PT" ] && echo yes)" yes
read -r DC DT <<<"$(signin dana "$PW_DANA")"
check "dana signs in at the same time" "$([ -n "$DC" ] && [ -n "$DT" ] && echo yes)" yes
check "peleg sees /home/peleg"       "$(api "$PC" "$PT" /api/projects | grep -c /home/peleg)" 1
check "peleg does not see dana"      "$(api "$PC" "$PT" /api/projects | grep -c /home/dana)" 0
check "dana sees /home/dana"         "$(api "$DC" "$DT" /api/projects | grep -c /home/dana)" 1
check "peleg cookie + dana token"    "$(code -H "Cookie: paas_gate=$PC" -H "Authorization: Bearer $DT" $G/api/projects)" 401
TAMPER="dana.${PC#peleg.}"
check "edited cookie (user changed)" "$(code -H "Cookie: paas_gate=$TAMPER" -H "Authorization: Bearer $DT" $G/api/projects)" 401
check "no cookie"                    "$(code -H "Authorization: Bearer $PT" $G/api/projects)" 401
plugins() { api "$1" "$2" /api/plugins | grep -o '"name":"paas-[a-z]*"' | sort -u | tr -d '"' | sed 's/name://' | tr '\n' ' '; }
check "peleg's tabs"                 "$(plugins "$PC" "$PT")" "paas-brain paas-market paas-reports paas-schedule paas-status "
check "peleg has no Users tab"       "$(plugins "$PC" "$PT" | grep -c paas-users)" 0
rpc() { curl -ks -H "Cookie: paas_gate=$1" -H "Authorization: Bearer $2" -H "$J" "${@:4}" "$G/api/plugins/$3"; }
check "marketplace lists items"      "$(rpc "$PC" "$PT" paas-market/rpc/list | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["items"])>40)')" True
rpc "$PC" "$PT" paas-market/rpc/add -d '{"ids":["skill/zoning-audit"]}' >/dev/null
check "peleg added zoning-audit"     "$([ -f /home/peleg/.claude/skills/zoning-audit/SKILL.md ] && echo yes)" yes
check "dana did not get it"          "$([ -e /home/dana/.claude/skills/zoning-audit ] && echo yes || echo no)" no
check "peleg's UI runs as peleg"     "$(ps -o user= -p "$(systemctl show -p MainPID --value paas-ui@peleg)" | tr -d ' ')" peleg
check "UIs only on 127.0.0.1"        "$(ss -ltnH | awk '{print $4}' | grep -E ':4100[0-9]$' | grep -vc '^127.0.0.1:')" 0
check "peleg cannot read dana's home" "$(runuser -u peleg -- ls /home/dana >/dev/null 2>&1 && echo yes || echo no)" no
systemctl stop paas-ui@peleg
check "stopped UI restarts on use"   "$(code -H "Cookie: paas_gate=$PC" -H "Authorization: Bearer $PT" --max-time 90 $G/api/projects)" 200
check "sign-out"                     "$(code -X POST -H "Cookie: paas_gate=$PC" -H "Authorization: Bearer $PT" $G/api/auth/logout)" 200
paas-user lock dana >/dev/null
check "locked user cannot sign in"   "$(code -H "$J" -d "$(cred dana "$PW_DANA")" $G/api/auth/login)" 401
paas-user unlock dana >/dev/null
for i in 1 2 3 4 5; do code -H "$J" -d "$(cred peleg "bad$i-password")" $G/api/auth/login >/dev/null; done
check "locked out after 5 wrong"     "$(code -H "$J" -d "$(cred peleg "$PW_PELEG")" $G/api/auth/login)" 429
[ $FAIL = 0 ] && echo "RESULT: all passed" || { echo "RESULT: FAILED"; exit 1; }
