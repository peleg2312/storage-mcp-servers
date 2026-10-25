#!/bin/bash
# root part: a RHEL 9-like machine (git, python3), a normal user; Claude Code only when WITH_CLAUDE=1
set -e
dnf -y -q install git which procps-ng tar gzip findutils >/dev/null 2>&1
useradd -m peleg
if [ "${WITH_CLAUDE:-0}" = 1 ]; then
  su - peleg -c 'curl -fsSL https://claude.ai/install.sh | bash' > /tmp/claude-install.log 2>&1 || { tail -5 /tmp/claude-install.log; exit 1; }
  su - peleg -c 'export PATH=$HOME/.local/bin:$PATH; claude --version'
fi
su - peleg -c 'bash /e2e/e2e.sh'
