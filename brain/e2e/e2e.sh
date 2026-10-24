#!/bin/bash
# End-to-end test of install-vm.sh on Rocky Linux 9 (= RHEL 9), x86_64, Python 3.9, as a normal user.
# Runs inside the container as user "peleg"; prints PASS / FAIL lines; never stops at the first failure.
set -u
cd ~
P=0; F=0
ok()   { echo "PASS  $1"; P=$((P+1)); }
bad()  { echo "FAIL  $1"; F=$((F+1)); }
chk()  { if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }
export PATH="$HOME/.local/bin:$PATH"

echo "== 1. fresh install"
mkdir -p storage-mcp-servers && tar -xzf /e2e/repo.tar.gz -C storage-mcp-servers
cd storage-mcp-servers
time sh install-vm.sh > /tmp/install1.log 2>&1; rc=$?
[ $rc = 0 ] && ok "install-vm.sh exit 0" || { bad "install-vm.sh exit $rc"; tail -30 /tmp/install1.log; }
grep -i -E "error|traceback|failed|skipped|not installed|warning" /tmp/install1.log | head -20 | sed 's/^/  log: /'
cd ~

echo "== 2. files"
C=~/.claude
chk "CLAUDE.md"                        "test -s $C/CLAUDE.md"
chk "26 skills"                        "[ \$(ls $C/skills | wc -l) -ge 26 ]"
chk "8 agents"                         "[ \$(ls $C/agents/*.md | wc -l) -eq 8 ]"
chk "5 hooks"                          "ls $C/hooks/block-write-tools.py $C/hooks/docs-hints.py $C/hooks/docs-leads.py $C/hooks/session-start.py $C/hooks/py-lint.py"
chk "environment / notes / tool-map"   "ls $C/brain/environment.md $C/brain/notes.md $C/brain/tool-map.md"
chk "library docs.db"                  "[ \$(stat -c %s $C/brain/library/docs.db) -gt 300000000 ]"
chk "library source files removed"     "[ ! -d $C/brain/library/docs ]"
chk "library VERSION"                  "test -s $C/brain/library/VERSION"
chk "tools: report, db_mcp, ps1"       "ls $C/tools/report.py $C/tools/db_mcp.py $C/tools/get-reports.ps1"
chk "databases example"                "test -s $C/brain/databases.example.json"
chk "plugins copied"                   "[ \$(ls $C/brain/plugins | wc -l) -ge 7 ]"
chk "theme"                            "test -s $C/themes/paas.json"
chk "banner wrapper in .bashrc"        "grep -q 'storage brain: Peleg As A Service' ~/.bashrc"

echo "== 3. settings.json"
python3 - <<'EOF' && ok "settings: hooks, matchers, env, look and feel" || bad "settings: see above"
import json, os, sys
s = json.load(open(os.path.expanduser("~/.claude/settings.json")))
h = s.get("hooks", {})
cmds = lambda ev: [(e.get("matcher"), x["command"].split("/")[-1]) for e in h.get(ev, []) for x in e.get("hooks", [])]
problems = []
if ("mcp__.*|Bash", "block-write-tools.py") not in cmds("PreToolUse"): problems.append(f"PreToolUse {cmds('PreToolUse')}")
for need in [("mcp__.*", "docs-hints.py"), ("Edit|Write|MultiEdit", "py-lint.py")]:
    if need not in cmds("PostToolUse"): problems.append(f"PostToolUse missing {need}")
if not any(c == "docs-leads.py" for _, c in cmds("UserPromptSubmit")): problems.append("UserPromptSubmit")
if not any(c == "session-start.py" for _, c in cmds("SessionStart")): problems.append("SessionStart")
if s.get("env", {}).get("ENABLE_CODE_SECURITY_REVIEW") != "0": problems.append("env")
if s.get("theme") != "custom:paas" or "statusLine" not in s: problems.append("look and feel")
allow = s.get("permissions", {}).get("allow", [])
import shutil
import subprocess
dbs = subprocess.run([os.path.expanduser("~/.claude/devtools-venv/bin/python"), "-c", "import psycopg, pymongo"],
                     capture_output=True).returncode == 0 if os.path.exists(os.path.expanduser("~/.claude/devtools-venv/bin/python")) else False
for srv in ((("mcp__docs-local",) + (("mcp__databases",) if dbs else ())) if shutil.which("claude") else ()):
    if srv not in allow: problems.append(f"allow {srv}: {allow}")
print("\n".join("  " + p for p in problems)); sys.exit(1 if problems else 0)
EOF

HAVE_CLAUDE=0; command -v claude >/dev/null 2>&1 && HAVE_CLAUDE=1
echo "== 4. claude: MCP servers and plugins (claude present: $HAVE_CLAUDE)"
if [ $HAVE_CLAUDE = 1 ]; then
claude mcp list > /tmp/mcp.txt 2>&1; sed 's/^/  /' /tmp/mcp.txt | head
chk "docs-local registered"            "grep -q '^docs-local' /tmp/mcp.txt"
if $C/devtools-venv/bin/python -c "import psycopg, pymongo" 2>/dev/null; then
chk "databases registered"             "grep -q '^databases' /tmp/mcp.txt"
chk "databases connected"              "grep '^databases' /tmp/mcp.txt | grep -q -i connected"
else
chk "databases NOT registered without drivers" "! grep -q '^databases' /tmp/mcp.txt && grep -q 'databases MCP: not registered' /tmp/install1.log"
fi
chk "docs-local connected"             "grep '^docs-local' /tmp/mcp.txt | grep -q -i connected"
claude plugin list > /tmp/plugins.txt 2>&1
chk "7 brain-dev plugins"              "[ \$(grep -c '@brain-dev' /tmp/plugins.txt) -eq 7 ]"
chk "plugins read from ~/.claude"      "grep 'Read from' /tmp/plugins.txt | grep -q '.claude/brain/plugins'"
else
chk "install without claude: registrations skipped, files in place" "test -s ~/.claude/settings.json"
fi

echo "== 5. dev tools (arch $(uname -m))"
if [ "$(uname -m)" = x86_64 ]; then
chk "ruff runs"                        "ruff --version"
chk "basedpyright runs"                "basedpyright --version"
chk "pyright-langserver on PATH"       "command -v pyright-langserver"
chk "db drivers in devtools venv"      "$C/devtools-venv/bin/python -c 'import psycopg, pymongo'"
printf 'import os\n\ndef f():\n    return nope\n' > /tmp/bad.py
echo '{"tool_input":{"file_path":"/tmp/bad.py"}}' | python3 $C/hooks/py-lint.py > /tmp/lint.out
chk "py-lint hook reports F821"        "grep -q F821 /tmp/lint.out"
basedpyright /tmp/bad.py > /tmp/bp.out 2>&1; chk "basedpyright finds the undefined name" "grep -q nope /tmp/bp.out"
else
chk "devtools skipped cleanly off x86_64" "grep -q 'devtools: wheels are for Linux x86_64' /tmp/install1.log"
fi

echo "== 6. hooks on Python $(python3 -V)"
echo '{"tool_name":"Bash","tool_input":{"command":"scli --add_volume"}}' | python3 $C/hooks/block-write-tools.py >/dev/null 2>&1; [ $? = 2 ] && ok "guard blocks scli write" || bad "guard scli"
echo '{"tool_name":"Bash","tool_input":{"command":"oc apply -f x.yaml"}}' | python3 $C/hooks/block-write-tools.py | grep -q '"ask"' && ok "guard asks for oc apply" || bad "guard oc apply"
echo '{"tool_name":"mcp__databases__pg_execute","tool_input":{"connection":"d","sql":"DELETE FROM t"}}' | python3 $C/hooks/block-write-tools.py | grep -q '"ask"' && ok "guard asks for db write" || bad "guard db write"
echo '{"session_id":"e2e1","tool_name":"mcp__ontap__ems","tool_response":"node1: wafl.vol.full on vol1"}' | python3 $C/hooks/docs-hints.py > /tmp/hint.out
chk "docs-hints explains an EMS (library)"  "grep -q 'wafl.vol.full' /tmp/hint.out"
echo '{"session_id":"e2e2","prompt":"trident pvc stuck in pending with ontap-san"}' | python3 $C/hooks/docs-leads.py > /tmp/lead.out
chk "docs-leads gives Trident leads"        "grep -q -i trident /tmp/lead.out"
echo '{"session_id":"e2e3","prompt":"write me a fastapi endpoint that returns the users list"}' | python3 $C/hooks/docs-leads.py > /tmp/lead2.out
chk "docs-leads: FastAPI prompt gets no ONTAP pages" "! grep -q ontap-restapi /tmp/lead2.out"
echo '{"session_id":"e2e4"}' | python3 $C/hooks/session-start.py > /tmp/ss.out
chk "session-start: library installed + guard configured" "grep -q -i 'library' /tmp/ss.out && ! grep -q 'NOT configured' /tmp/ss.out"
sed 's/^/  /' /tmp/ss.out | head -6

echo "== 7. MCP servers over stdio (as Claude Code calls them)"
rpc() { printf '%s\n' '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' '{"jsonrpc":"2.0","method":"notifications/initialized"}' "$1"; }
rpc '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_docs","arguments":{"query":"powerflex 5.1 rest api map volume to sdc","limit":3}}}' \
  | python3 $C/brain/library/mcp_stdio.py --db $C/brain/library/docs.db > /tmp/docs.out
chk "docs-local search_docs answers"   "grep -q 'Map a volume' /tmp/docs.out"
chk "docs-local answer is lean"        "! grep -q '\\\\\"score\\\\\"' /tmp/docs.out"
if [ -x $C/devtools-venv/bin/python ]; then
rpc '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"db_list","arguments":{}}}' | $C/devtools-venv/bin/python $C/tools/db_mcp.py > /tmp/db.out
chk "databases db_list answers (no config yet)" "grep -q 'databases.json' /tmp/db.out"
fi

echo "== 8. report tool"
printf 'time,read\n2026-10-20T00:00:00,10\n2026-10-21T00:00:00,30\n' > /tmp/r.csv
SSH_CONNECTION="10.0.0.9 5 10.0.0.5 22" python3 $C/tools/report.py /tmp/r.csv --unit MB/s --out /tmp/rep > /tmp/rep.out 2>&1
chk "report.py: html + xlsx + copy line" "test -s /tmp/rep/report.html && test -s /tmp/rep/report.xlsx && grep -q 'scp -r' /tmp/rep.out"

echo "== 9. banner"
python3 $C/banner/paas-banner.py --announce /tmp/ann.json < /dev/null
chk "banner announcement written"       "grep -q companyAnnouncements /tmp/ann.json"
bash -ic 'type claude' 2>/dev/null | grep -q function && ok "claude wrapper is a shell function" || bad "claude wrapper"

echo "== 10. second install: idempotent, user data kept"
echo "- 2026-10-24 · SG prefix SG_PROD_ · test" >> $C/brain/notes.md
mkdir -p $C/brain/notes && echo "# fabric: test" > $C/brain/notes/fabric.md
echo "- arrays: 000197900123" >> $C/brain/environment.md
cp $C/settings.json /tmp/settings-before.json
cd ~/storage-mcp-servers && sh install-vm.sh > /tmp/install2.log 2>&1; rc=$?; cd ~
[ $rc = 0 ] && ok "second install exit 0" || bad "second install exit $rc"
chk "notes.md kept"                     "grep -q SG_PROD_ $C/brain/notes.md"
chk "notes/fabric.md kept"              "test -s $C/brain/notes/fabric.md"
chk "environment.md kept"               "grep -q 000197900123 $C/brain/environment.md"
chk "banner block once in .bashrc"      "[ \$(grep -c 'storage brain: Peleg As A Service' ~/.bashrc) -eq 1 ]"
python3 - <<'EOF' && ok "settings: no duplicated hooks" || bad "settings: duplicated hooks"
import json, os, sys
s = json.load(open(os.path.expanduser("~/.claude/settings.json")))
cmds = [x["command"] for ev in s["hooks"].values() for e in ev for x in e["hooks"]]
dup = [c for c in set(cmds) if cmds.count(c) > 1]
print("  " + str(dup) if dup else "", end=""); sys.exit(1 if dup else 0)
EOF
if [ $HAVE_CLAUDE = 1 ]; then
claude mcp list > /tmp/mcp2.txt 2>&1
chk "MCP servers not duplicated"        "[ \$(grep -c '^docs-local' /tmp/mcp2.txt) -eq 1 ] && [ \$(grep -c '^databases' /tmp/mcp2.txt) -le 1 ]"
claude plugin list > /tmp/plugins2.txt 2>&1
chk "plugins still 7 after re-install"  "[ \$(grep -c '@brain-dev' /tmp/plugins2.txt) -eq 7 ]"
fi
chk "library not re-extracted"          "! grep -q 'installing documentation library' /tmp/install2.log"

echo
echo "RESULT: $P passed, $F failed"
