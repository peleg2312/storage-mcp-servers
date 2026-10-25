#!/bin/sh
# Build the offline "Peleg As A Service" web UI bundle (CloudCLI, siteboon/claudecodeui, AGPL-3.0, branded by
# brand/brand.py) for the RHEL 9 x86_64 VM: Node.js + the built app + its Linux node_modules, split into
# brain/ui/bundle/paas-ui-<version>.tar.gz.part-* (45 MB each, like the library). Needs internet, git, node/npm and
# docker (colima on a Mac). The client and server are built here (plain JS); the native modules (better-sqlite3,
# node-pty, bcrypt) are installed in a Rocky Linux 9 x86_64 container so they match the VM.
#   sh brain/ui/build-bundle.sh
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
COMMIT=80fbeac                           # siteboon/claudecodeui, 1.37.5 (2026-10-24): bump deliberately, re-check brand.py
NODE=v22.20.0
W=${WORK:-$HERE/../../work-ui}
mkdir -p "$W"
[ -d "$W/claudecodeui" ] || git clone -q https://github.com/siteboon/claudecodeui "$W/claudecodeui"
git -C "$W/claudecodeui" fetch -q --depth 50 origin 2>/dev/null || true
# a fresh copy per build (branding edits the sources), removed at the end
SRCDIR=$(mktemp -d "$W/build.XXXXXX")
trap 'rm -rf "$SRCDIR"' EXIT
git clone -q --shared "$W/claudecodeui" "$SRCDIR" && cd "$SRCDIR" && git checkout -q "$COMMIT"
VERSION=$(node -p "require('./package.json').version")-paas
python3 "$HERE/brand/brand.py" .
find server -name "*.test.ts" -delete -o -name "*.test.js" -delete    # upstream tests break the server tsc build
# dev dependencies for the build: reuse the checkout's when the lock file is the same (saves a minute)
if [ -d "$W/claudecodeui/node_modules" ] && cmp -s package-lock.json "$W/claudecodeui/package-lock.json"; then
  ln -s "$W/claudecodeui/node_modules" node_modules
else
  npm ci --no-audit --no-fund >/dev/null
fi
npm run build >/dev/null

echo "== Linux x86_64 runtime (Node.js + native modules)"
# cached by package-lock + Node version: the emulated x86 container (10-25 min on a Mac) only runs when they change
KEY=$({ cat package-lock.json; echo "$NODE"; } | { command -v sha256sum >/dev/null 2>&1 && sha256sum || shasum -a 256; } | cut -c1-16)
CACHE=$W/cache/runtime-$KEY.tar
STAGE=$W/stage && rm -rf "$STAGE" && mkdir -p "$STAGE/paas-ui/app"
cp -R dist dist-server server shared scripts package.json package-lock.json README.md LICENSE NOTICE "$STAGE/paas-ui/app/"
(cd "$STAGE/paas-ui/app" && npm pkg delete scripts.prepare scripts.preserver >/dev/null)   # no husky / dev hooks at run time
cp "$HERE/brand/logo.svg" "$STAGE/paas-ui/"
echo "$VERSION" > "$STAGE/paas-ui/VERSION"
if [ -f "$CACHE" ]; then
  echo "runtime from cache ($CACHE)"
else
  mkdir -p "$W/cache" "$STAGE/in" && cp package.json package-lock.json "$STAGE/in/"
  (cd "$STAGE/in" && npm pkg delete scripts.prepare scripts.preserver >/dev/null)
  # built on the container's own disk (a bind-mounted Mac folder refuses symlinks), only the archive comes out
  docker run --rm --platform linux/amd64 -v "$STAGE:/b" rockylinux:9 bash -ec "
    dnf -q -y install xz tar gzip python3 make gcc-c++ >/dev/null
    mkdir -p /w/paas-ui/app && cp /b/in/package.json /b/in/package-lock.json /w/paas-ui/app/
    curl -fsSL https://nodejs.org/dist/$NODE/node-$NODE-linux-x64.tar.xz | tar -xJ -C /w/paas-ui
    mv /w/paas-ui/node-$NODE-linux-x64 /w/paas-ui/node
    export PATH=/w/paas-ui/node/bin:\$PATH
    cd /w/paas-ui/app && npm ci --omit=dev --no-audit --no-fund >/dev/null 2>&1
    # not used here (~830 MB): the Codex agent, and the SDK's own Claude Code builds - the UI runs the VM's claude
    rm -rf node_modules/@openai/codex-linux-x64* node_modules/@anthropic-ai/claude-agent-sdk-linux-x64*
    find node_modules -name '*.map' -type f -delete
    node -e \"require('better-sqlite3'); require('node-pty'); require('bcrypt'); console.log('native modules OK')\"
    tar -C /w -cf /b/runtime.tar paas-ui/node paas-ui/app/node_modules && chown $(id -u):$(id -g) /b/runtime.tar"
  mv "$STAGE/runtime.tar" "$CACHE"
fi
tar -xf "$CACHE" -C "$STAGE"

echo "== packing"
OUT=$HERE/bundle && rm -f "$OUT"/paas-ui-*.part-* && mkdir -p "$OUT"
if tar --version 2>/dev/null | grep -q bsdtar; then MACOPT="--no-mac-metadata --no-xattrs"; else MACOPT=""; fi
# shellcheck disable=SC2086
COPYFILE_DISABLE=1 tar $MACOPT -C "$STAGE" -cf - paas-ui | gzip -6 > "$W/paas-ui-$VERSION.tar.gz"
(cd "$OUT" && split -b 45m -a 2 "$W/paas-ui-$VERSION.tar.gz" "paas-ui-$VERSION.tar.gz.part-")
(cd "$W" && { command -v sha256sum >/dev/null 2>&1 && sha256sum "paas-ui-$VERSION.tar.gz" || shasum -a 256 "paas-ui-$VERSION.tar.gz"; } > "$OUT/SHA256SUMS")
echo "$VERSION" > "$OUT/VERSION"
echo "ui $VERSION: $(du -h "$W/paas-ui-$VERSION.tar.gz" | cut -f1) in $(ls "$OUT"/paas-ui-*.part-* | wc -l) parts -> $OUT"
