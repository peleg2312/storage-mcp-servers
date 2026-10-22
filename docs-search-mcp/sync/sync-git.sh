#!/bin/sh
# Pull text-only documentation from the Git sources in sources/git-repos.txt.
#   sync-git.sh [DOCS_DIR]                 sources/git-repos.txt -> DOCS_DIR/<vendor>/<product>
#   sync-git.sh --netapp-all [DOCS_DIR]    additionally every public NetAppDocs repo (~2000; GitHub API)
# Needs: sh, git (curl or wget only for --netapp-all). Re-running updates existing clones.
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
ALL=0
[ "${1:-}" = "--netapp-all" ] && { ALL=1; shift; }
DOCS=${1:-${DOCS_DIR:-/data/docs}}
LIST=$(mktemp)
sed 's/#.*//' "$HERE/sources/git-repos.txt" | awk 'NF>=3' > "$LIST"
if [ "$ALL" = 1 ]; then
  get() {
    if command -v curl >/dev/null 2>&1; then curl -fsSL ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} "$1"
    else wget -qO- ${GITHUB_TOKEN:+--header "Authorization: Bearer $GITHUB_TOKEN"} "$1"; fi
  }
  page=1
  while :; do
    names=$(get "https://api.github.com/orgs/NetAppDocs/repos?per_page=100&page=$page&type=public" |
      grep -o '"full_name": *"NetAppDocs/[^"]*"' | sed 's|.*NetAppDocs/||; s|"$||')
    [ -z "$names" ] && break
    for n in $names; do grep -q " https://github.com/NetAppDocs/$n\$" "$LIST" || echo "netapp $n https://github.com/NetAppDocs/$n" >> "$LIST"; done
    page=$((page+1))
  done
fi
ok=0; fail=0
while read -r vendor product url subdirs; do
  d="$DOCS/$vendor/$product"
  if [ -d "$d/.git" ]; then
    if git -C "$d" fetch -q --depth 1 origin && git -C "$d" reset -q --hard FETCH_HEAD; then
      ok=$((ok+1)); echo "${url%.git}" > "$d/.source_url"; echo "updated $vendor/$product"
    else fail=$((fail+1)); echo "update failed: $url"; fi
    continue
  fi
  rm -rf "$d"; mkdir -p "$(dirname "$d")"
  if ! git clone -q --depth 1 --filter=blob:none --no-checkout "$url" "$d"; then
    fail=$((fail+1)); echo "clone failed: $url"; continue
  fi
  pats=""
  if [ -n "$subdirs" ]; then
    for s in $subdirs; do
      case "$s" in
        *.md|*.adoc|*.rst|*.txt) pats="$pats /$s" ;;      # a single file (e.g. CHANGELOG.md)
        *) pats="$pats /$s/**/*.adoc /$s/**/*.md /$s/**/*.rst /$s/*.md /$s/*.rst /$s/*.adoc" ;;
      esac
    done
  else
    pats="/*.adoc /**/*.adoc /*.md /**/*.md /*.rst /**/*.rst"
  fi
  # shellcheck disable=SC2086
  git -C "$d" sparse-checkout set --no-cone $pats >/dev/null
  git -C "$d" checkout -q
  echo "${url%.git}" > "$d/.source_url"
  ok=$((ok+1)); echo "cloned $vendor/$product"
done < "$LIST"
rm -f "$LIST"
echo "git sources: $ok synced, $fail failed -> $DOCS"
