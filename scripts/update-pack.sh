#!/bin/sh
# An update pack for a machine without git access (the air-gapped VM holds an unpacked copy of this repository):
# every file that changed since <base> (a commit, tag or branch), a list of the files removed since then, and an
# apply script. Built where git is (the PC); carried over like the ZIP; applied with one command.
#
#   sh scripts/update-pack.sh <base> [<out dir>]          e.g. sh scripts/update-pack.sh c014fbf ~/Downloads
#   sh scripts/update-pack.sh <base> --no-ui-bundle       leave the web UI bundle out (180 MB; take it only when it changed)
#
# On the VM:   tar -xzf storage-mcp-servers-update-<base>-<head>.tar.gz && sh update-<base>-<head>/apply-update.sh /path/to/storage-mcp-servers
# then the usual command: sh brain/multiuser/install-multiuser.sh  (multi-user VM) or sh install-vm.sh (single VM)
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
BASE=${1:-}; [ -n "$BASE" ] || { sed -n '2,/^set -eu/{/^set -eu/!p;}' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
shift
OUT=$PWD; UI=1
for a in "$@"; do case "$a" in --no-ui-bundle) UI=0 ;; *) OUT=$a ;; esac; done
cd "$ROOT"
git rev-parse -q --verify "$BASE^{commit}" >/dev/null || { echo "update-pack: no such commit $BASE"; exit 1; }
B=$(git rev-parse --short "$BASE"); H=$(git rev-parse --short HEAD)
[ "$B" != "$H" ] || { echo "update-pack: HEAD is $BASE already"; exit 1; }
NAME=update-$B-$H
W=$(mktemp -d); mkdir -p "$W/$NAME"
# changed and added files (renames as their new name); the library and image parts are left out unless they changed
EXCL=':!docs-search-mcp/work'
# also every file a commit since <base> touched that exists now, when it ends up as it was at <base>: a VM that applied an
# earlier pack from the same base carries the in-between version, which this pack must put back
{ git diff --name-only --diff-filter=AMRC "$BASE" HEAD -- . $EXCL
  git log --no-renames --format= --name-only "$BASE..HEAD" -- . $EXCL | while IFS= read -r f; do
    [ -n "$f" ] && git cat-file -e "HEAD:$f" 2>/dev/null && echo "$f"; done; } | sort -u > "$W/changed"
if [ "$UI" = 0 ] && grep -q '^brain/ui/bundle/' "$W/changed"; then
  rm -rf "$W"; echo "update-pack: the web UI bundle changed since $B: leaving it out would keep the old UI on the VM; build without --no-ui-bundle"; exit 1
fi
# removed: gone since <base>, and also files added after <base> and removed again (a VM may carry them from an earlier
# pack made from the same base); rm -f of a file that is not there is harmless
{ git diff --no-renames --name-only --diff-filter=D "$BASE" HEAD -- . $EXCL
  git log --no-renames --format= --name-only --diff-filter=D "$BASE..HEAD" -- . $EXCL | while IFS= read -r f; do
    [ -n "$f" ] && ! git cat-file -e "HEAD:$f" 2>/dev/null && echo "$f"; done; } | sort -u > "$W/$NAME/REMOVED.txt"
while IFS= read -r f; do
  [ -e "$f" ] || continue
  mkdir -p "$W/$NAME/files/$(dirname "$f")"; cp -p "$f" "$W/$NAME/files/$f"
done < "$W/changed"
(cd "$W/$NAME/files" && find . -type f | sed 's#^\./##' | sort | xargs sha256sum > "../SHA256SUMS")
{ echo "storage-mcp-servers update pack: $B -> $H ($(date -u +%Y-%m-%d))"; echo "files: $(wc -l < "$W/$NAME/SHA256SUMS") changed or added, $(wc -l < "$W/$NAME/REMOVED.txt") removed";
  echo; git log --format='%h %ad %s' --date=short "$BASE..HEAD" | cut -c1-140; } > "$W/$NAME/CHANGES.txt"
cat > "$W/$NAME/apply-update.sh" <<'EOF'
#!/bin/sh
# Apply this update pack to an unpacked copy of storage-mcp-servers:  sh apply-update.sh /path/to/storage-mcp-servers
# Copies every file of files/ over the copy (after checking the checksums), removes the files listed in REMOVED.txt,
# and records the version in UPDATE-LEVEL. Re-running it is harmless.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DST=${1:-}; [ -d "$DST" ] && [ -f "$DST/install-vm.sh" ] || { echo "apply-update: give the folder that holds install-vm.sh"; exit 1; }
(cd "$HERE/files" && sha256sum -c --quiet "$HERE/SHA256SUMS") || { echo "apply-update: a file is damaged (checksum); copy the pack again"; exit 1; }
(cd "$HERE/files" && find . -type f | sed 's#^\./##') | while IFS= read -r f; do
  mkdir -p "$DST/$(dirname "$f")"; cp -p "$HERE/files/$f" "$DST/$f"
done
while IFS= read -r f; do [ -z "$f" ] || rm -f "$DST/$f"; done < "$HERE/REMOVED.txt"
find "$DST" -depth -type d -empty -not -path "$DST" -not -path '*/.git*' -delete 2>/dev/null || true
head -n1 "$HERE/CHANGES.txt" > "$DST/UPDATE-LEVEL"
echo "applied: $(head -n1 "$HERE/CHANGES.txt")"
echo "next (as root): cd $DST && sh brain/multiuser/install-multiuser.sh      # single VM: sh install-vm.sh"
EOF
chmod +x "$W/$NAME/apply-update.sh"
mkdir -p "$OUT"
SUMMARY=$(sed -n 2p "$W/$NAME/CHANGES.txt")
tar -C "$W" -czf "$OUT/storage-mcp-servers-$NAME.tar.gz" "$NAME"
rm -rf "$W"
echo "$OUT/storage-mcp-servers-$NAME.tar.gz ($(du -h "$OUT/storage-mcp-servers-$NAME.tar.gz" | cut -f1)): $SUMMARY"
