#!/bin/sh
# Acceptance test of the multi-user sign-in gate (brain/multiuser/GATE-SPEC.md, section 6) on Rocky Linux 9 (= RHEL 9),
# x86_64, with systemd running in the container: the UI files in /opt/paas/ui, install-gate.sh, then root, peleg and dana
# (group paas-users) and eve (not in it) signing in through https://127.0.0.1:3001. Needs docker (colima on a Mac).
# Passwords are random and never printed.
#   sh brain/ui/test-gate.sh
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
C=paas-gate-test
docker rm -f $C >/dev/null 2>&1 || true
# rockylinux:9 has no systemd: add it once (docker commit, since the legacy builder ignores --platform)
# (dbus: without it pam_systemd stalls su for 25 s)
I=paas-gate-test:2
if [ "$(docker image inspect -f '{{.Architecture}}' $I 2>/dev/null)" != amd64 ]; then
  docker run --name $C --platform linux/amd64 rockylinux:9 sh -c \
    'dnf -q -y install systemd openssl hostname procps-ng dbus-broker util-linux shadow-utils python3 >/dev/null && dnf clean all >/dev/null'
  docker commit $C $I >/dev/null && docker rm $C >/dev/null
fi
docker run -d --name $C --platform linux/amd64 --privileged --cgroupns=host -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
  -v "$ROOT/brain:/repo/brain:ro" $I /usr/sbin/init >/dev/null
trap 'docker rm -f $C >/dev/null 2>&1' EXIT
docker exec -i $C bash -s <<'EOS'
set -u
for i in $(seq 30); do systemctl is-system-running 2>/dev/null | grep -Eq 'running|degraded' && break; sleep 1; done
# container only: logind under emulation leaves su hanging in its optional pam_systemd session step (a VM is fine)
sed -i '/pam_systemd/d' /etc/pam.d/system-auth /etc/pam.d/password-auth
UI_DIR=/opt/paas/ui UI_SHARED=1 sh /repo/brain/ui/install-ui.sh >/tmp/install-ui.log 2>&1 || { cat /tmp/install-ui.log; exit 1; }
sh /repo/brain/multiuser/install-gate.sh >/tmp/install-gate.log 2>&1 || { cat /tmp/install-gate.log; journalctl -u paas-gate -n 30; exit 1; }
pw() { openssl rand -hex 12; }
R=$(pw); echo "root:$R" | chpasswd
P=$(pw); useradd -m -G paas-users peleg; echo "peleg:$P" | chpasswd
D=$(pw); useradd -m -G paas-users dana;  echo "dana:$D"  | chpasswd
E=$(pw); useradd -m eve;                 echo "eve:$E"   | chpasswd
form() { printf 'username=%s&password=%s' "$1" "$2" > "/tmp/$3.form"; }
form peleg "$P" peleg; form dana "$D" dana; form eve "$E" eve; form root "$R" root; form peleg wrong-password bad
G=https://127.0.0.1:3001; FAIL=0
check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2', want '$3'"; FAIL=1; fi; }
# signin <form> <jar> -> status; the page lands in /tmp/<form>.out
signin() { curl -ks -c "/tmp/$2.jar" -o "/tmp/$1.out" -w %{http_code} -d @"/tmp/$1.form" $G/paas-gate/login; }
token() { sed -n "s/.*localStorage.setItem('auth-token', \"\([^\"]*\)\").*/\1/p" "/tmp/$1.out"; }
has_cookie() { grep -c paas_gate "/tmp/$1.jar" 2>/dev/null || true; }
api() { curl -ks -b "/tmp/$1.jar" -H "Authorization: Bearer $2" "$G$3"; }
apicode() { curl -ks -o /dev/null -w %{http_code} -b "/tmp/$1.jar" -H "Authorization: Bearer $2" "$G$3"; }
cat > /tmp/ws.js <<'EOF'
// node ws.js <url> <cookie header> <"open" | regex the replies must match> [message to send]
const WebSocket = require('/opt/paas/ui/app/node_modules/ws');
const [url, cookie, expect, msg] = process.argv.slice(2);
const ws = new WebSocket(url, { headers: { cookie }, rejectUnauthorized: false });
let got = '';
setTimeout(() => { console.log('timeout'); process.exit(1); }, 30000);
ws.on('open', () => { if (expect === 'open') { console.log('open'); process.exit(0); } if (msg) ws.send(msg); });
ws.on('message', (d) => { got += d; if (new RegExp(expect).test(got)) { console.log('match'); process.exit(0); } });
ws.on('unexpected-response', (_q, r) => { console.log(`http ${r.statusCode}`); process.exit(1); });
ws.on('error', (e) => { console.log(`error ${e.message}`); process.exit(1); });
EOF
ws() { /opt/paas/ui/node/bin/node /tmp/ws.js "$@"; }
cookie_of() { awk '$6 == "paas_gate" { print "paas_gate=" $7 }' "/tmp/$1.jar"; }

# 1
check "1  sign-in page without cookie"  "$(curl -ks -o /tmp/p.html -w %{http_code} $G/)$(grep -c "Sign in with this VM" /tmp/p.html)" 2001
# 2, 3: same answer, similar time
t0=$(date +%s%N); s2=$(signin bad b); t2=$(( ($(date +%s%N) - t0) / 1000000 ))
check "2  wrong password: 401, no cookie" "$s2 $(has_cookie b)" "401 0"
t0=$(date +%s%N); s3=$(signin eve e); t3=$(( ($(date +%s%N) - t0) / 1000000 ))
check "3  not in paas-users: same 401"   "$s3 $(has_cookie e) $([ "$(cat /tmp/bad.out)" = "$(cat /tmp/eve.out)" ] && echo same)" "401 0 same"
check "3  similar time (${t2} ms / ${t3} ms)" "$(( (t2 > t3 ? t2 - t3 : t3 - t2) < 1500 ))" 1
# 4
check "4  peleg signs in: 200, cookie"   "$(signin peleg pj) $(has_cookie pj)" "200 1"
TP=$(token peleg)
check "4  page stores a token"           "$([ -n "$TP" ] && grep -c "location.replace('/')" /tmp/peleg.out)" 1
# 5, 6
check "5  peleg's projects"              "$(api pj "$TP" /api/projects | grep -c /home/peleg)" 1
check "6  dana signs in"                 "$(signin dana dj) $(has_cookie dj)" "200 1"
TD=$(token dana)
api pj "$TP" /api/projects > /tmp/p.json & api dj "$TD" /api/projects > /tmp/d.json & wait
check "6  both at once: each only their own" \
  "$(grep -c /home/peleg /tmp/p.json) $(grep -c /home/dana /tmp/p.json) $(grep -c /home/dana /tmp/d.json) $(grep -c /home/peleg /tmp/d.json)" "1 0 1 0"
# 7, 8
check "7  peleg's cookie, dana's token"  "$(apicode pj "$TD" /api/projects)" 401
sed 's/\tpaas_gate\tpeleg\./\tpaas_gate\tdana./' /tmp/pj.jar > /tmp/forged.jar
check "8  edited cookie = signed out"    "$(apicode forged "$TD" /api/projects) $(api forged "$TD" /api/projects)" '401 {"error":"Sign in"}'
# 9, 10, 11
check "9  WebSocket /ws"                 "$(ws "wss://127.0.0.1:3001/ws?token=$TP" "$(cookie_of pj)" open)" open
check "9  WebSocket without cookie"      "$(ws "wss://127.0.0.1:3001/ws?token=$TP" "" open)" "http 401"
check "10 shell tab runs as peleg"       "$(ws "wss://127.0.0.1:3001/shell?token=$TP" "$(cookie_of pj)" 'peleg' \
  '{"type":"init","projectPath":"/home/peleg","isPlainShell":true,"initialCommand":"id -un","cols":80,"rows":24}')" match
PID=$(systemctl show -p MainPID --value paas-ui@peleg)
check "11 peleg's UI (and the Claude it starts) runs as peleg" "$(ps -o user= -p "$PID")" peleg
# 13
IP=$(hostname -I | awk '{print $1}')
for port in $(sed -n 's/^SERVER_PORT=//p' /etc/paas/users/*.env); do
  curl -s -m 5 -o /dev/null "http://$IP:$port/"; check "13 instance port $port from the network refused" "$?" 7
done
# 15
systemctl stop paas-ui@peleg
check "15 stopped instance restarted"    "$(apicode pj "$TP" /api/projects)" 200
# 16
PID_JSON=$(api pj "$TP" /api/projects)
PROJ=$(echo "$PID_JSON" | python3 -c 'import json,sys
for p in json.load(sys.stdin):
    if "/home/peleg" in json.dumps(p): print(p["projectId"]); break')
head -c 52428800 /dev/urandom > /tmp/big.bin
UP=$(curl -ks -o /tmp/up.out -w %{http_code} -b /tmp/pj.jar -H "Authorization: Bearer $TP" -F "files=@/tmp/big.bin" \
  "$G/api/file-tree/projects/$PROJ/files/upload")
check "16 50 MB upload"                  "$UP $(find /home/peleg -name big.bin -size 51200k | wc -l)" "200 1"
# root
check "   root signs in, own instance"   "$(signin root rj) $(sed -n 's/^SERVER_PORT=//p' /etc/paas/users/root.env)" "200 41000"
# 14
curl -ks -o /dev/null -c /tmp/pj.jar -b /tmp/pj.jar -H "Authorization: Bearer $TP" -X POST $G/api/auth/logout
check "14 sign-out clears the cookie"    "$(has_cookie pj) $(apicode pj "$TP" /api/projects)" "0 401"
# 12
for i in 1 2 3 4 5; do signin bad x >/dev/null; done
check "12 locked after 5 wrong"          "$(signin peleg x)" 429
# section 5
check "   key, .env and TLS key root 0600" "$(stat -c %a%U /etc/paas/gate.key /etc/paas/users/peleg.env /etc/paas/tls/paas-ui.key | sort -u)" 600root
check "   no passwords in the gate log"  "$(journalctl -u paas-gate | grep -c -e "$P" -e "$D" -e "$E" -e "$R" -e "$TP")" 0
check "   sign-ins logged"               "$(journalctl -u paas-gate | grep -c 'sign-in ok user=peleg ip=127.0.0.1')" 1
[ $FAIL = 0 ] && echo "RESULT: all passed" || { echo "RESULT: FAILED"; journalctl -u paas-gate -n 40 --no-pager; exit 1; }
EOS
