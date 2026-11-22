#!/bin/sh
# Builds block-alerts-<git short sha>.zip: the block-alerts skill on its own, ready to install.
#   sh scripts/make-block-alerts.sh [out dir]
# block-alerts/SKILL.md                the skill (the script is also inside it, at the end)
# block-alerts/block_alerts_mail.py    the script, taken out of SKILL.md: the email's complete HTML
# block-alerts/examples/               report.json (+ Hebrew) and the email.html / .eml / plain text the script makes
# install.sh, INSTALL.txt              install for one user or every user on the VM
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd); OUT=${1:-.}
SK=$HERE/brain/claude/skills/block-alerts
V=$(git -C "$HERE" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d)
T=$(mktemp -d); B=$T/block-alerts-$V; S=$B/block-alerts
mkdir -p "$S/examples"
cp "$SK/SKILL.md" "$S/SKILL.md"
TAG=$(grep -m1 '^# >>> block_alerts_mail.py v' "$SK/SKILL.md")
sed -n "/^$TAG\$/,/^# <<< block_alerts_mail.py\$/p" "$SK/SKILL.md" > "$S/block_alerts_mail.py"
python3 -m py_compile "$S/block_alerts_mail.py"; rm -rf "$S/__pycache__"
cp "$SK/examples/"*.json "$S/examples/"
(cd "$S/examples" && python3 ../block_alerts_mail.py report.json --html email.html --eml email.eml >/dev/null \
  && python3 ../block_alerts_mail.py report-he.json --html email-he.html >/dev/null \
  && python3 -c "import email,email.policy;m=email.message_from_bytes(open('email.eml','rb').read(),policy=email.policy.default);open('email.txt','w').write(m.get_body(('plain',)).get_content())")
cp "$HERE/scripts/block-alerts-install/install.sh" "$HERE/scripts/block-alerts-install/INSTALL.txt" "$B/"
chmod +x "$B/install.sh" "$S/block_alerts_mail.py"
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
(cd "$T" && rm -f "$OUT/block-alerts-$V.zip" && zip -qr "$OUT/block-alerts-$V.zip" "block-alerts-$V")
rm -rf "$T"
echo "$OUT/block-alerts-$V.zip ($(du -h "$OUT/block-alerts-$V.zip" | cut -f1))"
