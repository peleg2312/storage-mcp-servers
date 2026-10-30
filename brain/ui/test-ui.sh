#!/bin/sh
# End-to-end test of the web UI bundle on Rocky Linux 9 (= RHEL 9), x86_64 container: install-ui.sh, HTTPS, the VM-account
# sign-in (allowed account, not-allowed account, wrong password, lock-out, sign-up refused), plugins, file downloads, and the same
# sign-in with the UI running as root. Needs docker (colima on a Mac). The root password is random, never printed.
#   sh brain/ui/test-ui.sh
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
C=paas-ui-test
docker rm -f $C >/dev/null 2>&1 || true
docker run -d --name $C --platform linux/amd64 -v "$ROOT/brain/ui:/repo/brain/ui:ro" rockylinux:9 sleep infinity >/dev/null
trap 'docker rm -f $C >/dev/null 2>&1' EXIT
docker exec $C bash -c '
set -u
dnf -q -y install openssl hostname >/dev/null 2>&1
PW=$(openssl rand -hex 12); echo "root:$PW" | chpasswd
P2=$(openssl rand -hex 12); useradd -m peleg; echo "peleg:$P2" | chpasswd
python3 -c "import json,sys;print(json.dumps({\"username\":\"root\",\"password\":sys.argv[1]}))" "$PW" > /tmp/root.json
python3 -c "import json,sys;print(json.dumps({\"username\":\"peleg\",\"password\":sys.argv[1]}))" "$P2" > /tmp/peleg.json
J="Content-Type: application/json"; U=https://127.0.0.1:3001/api/auth; FAIL=0
check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got $2, want $3"; FAIL=1; fi; }
code() { curl -ks -o /dev/null -w %{http_code} -H "$J" -d "$2" "$U/$1"; }
up() { for i in $(seq 60); do curl -ks https://127.0.0.1:3001/ >/dev/null && return 0; sleep 2; done; echo "FAIL server did not start"; cat /tmp/ui.log; exit 1; }
stop() { for p in /proc/[0-9]*; do [ "$(cat $p/comm 2>/dev/null)" = node ] && kill ${p#/proc/}; done; sleep 2; }

su - peleg -c "cp -r /repo ~/repo && sh ~/repo/brain/ui/install-ui.sh >/tmp/install.log 2>&1; (nohup paas-ui >/tmp/ui.log 2>&1 &)"; up
check "https page"               "$(curl -ks https://127.0.0.1:3001/ | grep -c "Peleg As A Service")" 1
check "no setup screen"          "$(curl -ks $U/status | grep -c "\"needsSetup\":false")" 1
check "sign-up refused"          "$(code register "{\"username\":\"evil\",\"password\":\"whatever123\"}")" 403
check "wrong password"           "$(code login "{\"username\":\"root\",\"password\":\"nope-nope\"}")" 401
check "root signs in"            "$(code login @/tmp/root.json)" 200
check "valid but not allowed"    "$(code login @/tmp/peleg.json)" 401
T=$(curl -ks -H "$J" -d @/tmp/root.json $U/login | python3 -c "import json,sys;print(json.load(sys.stdin)[\"token\"])")
check "plugins Brain, Browser, Help, Reports, Schedule, Status" "$(curl -ks -H "Authorization: Bearer $T" https://127.0.0.1:3001/api/plugins | grep -o "paas-[a-z]*" | sort -u | tr "\n" " ")" "paas-brain paas-browser paas-help paas-reports paas-schedule paas-status "
check "api needs sign-in"        "$(curl -ks -o /dev/null -w %{http_code} https://127.0.0.1:3001/api/plugins)" 401
check "Chats space for plain chats" "$(curl -ks -H "Authorization: Bearer $T" https://127.0.0.1:3001/api/projects | grep -c "\"Chats\"")" 1
check "no git setup screen"      "$(curl -ks -H "Authorization: Bearer $T" https://127.0.0.1:3001/api/user/onboarding-status | grep -c "\"hasCompletedOnboarding\":true")" 1
T2=$(curl -ks -H "$J" -d @/tmp/root.json $U/login | python3 -c "import json,sys;print(json.load(sys.stdin)[\"token\"])")
check "two people signed in at once" "$(curl -ks -o /dev/null -w %{http_code} -H "Authorization: Bearer $T" https://127.0.0.1:3001/api/plugins)$(curl -ks -o /dev/null -w %{http_code} -H "Authorization: Bearer $T2" https://127.0.0.1:3001/api/plugins)" 200200
su - peleg -c "mkdir -p ~/storage-reports && echo a,b > ~/storage-reports/t.csv"
D="https://127.0.0.1:3001/api/paas/download?path="
check "download a report"        "$(curl -ks -H "Authorization: Bearer $T" "${D}~/storage-reports/t.csv")" "a,b"
check "download needs sign-in"   "$(curl -ks -o /dev/null -w %{http_code} "${D}~/storage-reports/t.csv")" 401
check "download outside home"    "$(curl -ks -o /dev/null -w %{http_code} -H "Authorization: Bearer $T" "${D}/etc/passwd")" 403
for i in 1 2 3 4 5; do code login "{\"username\":\"root\",\"password\":\"bad$i\"}" >/dev/null; done
check "locked after 5 wrong"     "$(code login @/tmp/root.json)" 429
stop
cp -r /repo /root/repo && HOME=/root sh /root/repo/brain/ui/install-ui.sh >/tmp/install-root.log 2>&1
(HOME=/root nohup /root/.local/bin/paas-ui >/tmp/ui.log 2>&1 &); up
check "UI as root: root signs in" "$(code login @/tmp/root.json)" 200
check "UI as root: wrong password" "$(code login "{\"username\":\"root\",\"password\":\"x-wrong\"}")" 401
[ $FAIL = 0 ] && echo "RESULT: all passed" || { echo "RESULT: FAILED"; exit 1; }
'
