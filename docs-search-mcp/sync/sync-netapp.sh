#!/bin/sh
# Pull NetApp documentation (text only: .adoc/.md/.yml) from github.com/NetAppDocs.
#   sync-netapp.sh [DEST]          curated SAN/VMware list (sources/netapp-repos.txt)
#   sync-netapp.sh --all [DEST]    every public NetAppDocs repo (needs GitHub API; ~2000 repos)
# Re-running updates existing clones. Images and PDFs are never downloaded.
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
ALL=0
[ "${1:-}" = "--all" ] && { ALL=1; shift; }
DEST=${1:-${DOCS_DIR:-/data/docs}/netapp}
mkdir -p "$DEST"
if [ "$ALL" = 1 ]; then
  page=1; : > "$DEST/.repos"
  get() {  # curl or busybox wget; optional GITHUB_TOKEN raises the API rate limit
    if command -v curl >/dev/null 2>&1; then
      curl -fsSL ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} "$1"
    else
      wget -qO- ${GITHUB_TOKEN:+--header "Authorization: Bearer $GITHUB_TOKEN"} "$1"
    fi
  }
  while :; do
    names=$(get "https://api.github.com/orgs/NetAppDocs/repos?per_page=100&page=$page&type=public" |
      grep -o '"full_name": *"NetAppDocs/[^"]*"' | sed 's|.*NetAppDocs/||; s|"$||')
    [ -z "$names" ] && break
    echo "$names" >> "$DEST/.repos"; page=$((page+1))
  done
  LIST="$DEST/.repos"
else
  LIST="$HERE/sources/netapp-repos.txt"
fi
n=0; fail=0
for repo in $(sed 's/#.*//' "$LIST" | awk 'NF{print $1}'); do
  d="$DEST/$repo"
  if [ -d "$d/.git" ]; then
    git -C "$d" fetch -q --depth 1 origin && git -C "$d" reset -q --hard FETCH_HEAD || { echo "update failed: $repo"; fail=$((fail+1)); continue; }
  else
    rm -rf "$d"
    if ! git clone -q --depth 1 --filter=blob:none --no-checkout "https://github.com/NetAppDocs/$repo" "$d"; then
      echo "clone failed: $repo"; fail=$((fail+1)); continue
    fi
    git -C "$d" sparse-checkout set --no-cone '/*.adoc' '/**/*.adoc' '/*.md' '/**/*.md' '/_index.yml' '/sidebar.yml' >/dev/null
    git -C "$d" checkout -q
  fi
  n=$((n+1)); echo "ok $repo"
done
echo "NetApp: $n repos synced into $DEST ($fail failed)"
