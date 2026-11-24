"""Tests for paas-kit/bin/rtk-hook: model-typed rtk calls are refused, text that only mentions rtk is not.
    python3 paas-kit/test_rtk_hook.py"""
import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "rtk-hook")

DENY = [
    "rtk oc delete pod x",
    "/opt/paas-kit/bin/rtk kubectl delete ns y",
    "ls; rtk oc get pods",
    "echo a && rtk git push",
    "(rtk oc delete pod x)",
    "x=$(rtk oc get pods)",
    "sudo rtk oc delete pod x",
    "sh -c 'rtk oc delete pod x'",
    'bash -c "rtk kubectl delete ns y"',
    "su -c 'rtk oc delete pod x' root",
    "eval \"rtk oc delete pod x\"",
    "timeout 30 rtk oc get pods",
    "cat <<'EOF' > f.txt\nhello\nEOF\nrtk oc delete pod x",
]
ALLOW = [
    "rtk gain",
    "rtk recall 3f2a",
    "rtk --version",
    "git status",
    "cat <<'EOF' > INSTALL.txt\n2. PAAS-KIT  (rtk + Headroom for every user)\nrtk oc get pods is rewritten for you\nEOF",
    "cat > a.txt <<EOF\n(rtk + Headroom)\nEOF\necho done",
    'git commit -m "paas-kit: fix (rtk + Headroom) guard"',
    "echo '(rtk + Headroom) are on'",
    "grep -n 'rtk ' README.txt",
    "python3 - <<'PY'\nprint('rtk oc get pods')\nPY",
]


def decide(cmd):
    out = subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_input": {"command": cmd}}),
                         capture_output=True, text=True).stdout.strip()
    return "deny" if out else "allow"


bad = [("deny", c) for c in DENY if decide(c) != "deny"] + [("allow", c) for c in ALLOW if decide(c) != "allow"]
for want, c in bad:
    print(f"FAIL want {want}: {c!r}")
print(f"{len(DENY) + len(ALLOW) - len(bad)}/{len(DENY) + len(ALLOW)} ok")
sys.exit(1 if bad else 0)
