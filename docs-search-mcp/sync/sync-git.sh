#!/bin/sh
# Pull text-only documentation (and, for lines marked "code", source code) from sources/git-repos.txt.
#   sync-git.sh [DOCS_DIR]                 sources/git-repos.txt -> DOCS_DIR/<vendor>/<product>
#   sync-git.sh --netapp-all [DOCS_DIR]    additionally every public NetAppDocs repo (~2000; GitHub API)
# Needs: sh, git (curl or wget only for --netapp-all). Re-running updates existing clones.
set -euf          # -f: the sparse-checkout patterns below must reach git unexpanded
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
# sparse-checkout patterns for one source line: the listed subdirs / files (or every doc), and with the
# word "code" also the source code (Go, Python, proto, YAML, shell) minus vendored, test, mock and
# generated files - error strings and their context become searchable.
patterns() {
  docs=""; code=0
  for s in "$@"; do
    case "$s" in
      code) code=1 ;;
      *.md|*.adoc|*.rst|*.txt|*.proto) docs="$docs /$s" ;;     # a single file (e.g. CHANGELOG.md)
      *) docs="$docs /$s/**/*.adoc /$s/**/*.md /$s/**/*.rst /$s/*.md /$s/*.rst /$s/*.adoc" ;;
    esac
  done
  [ -z "$docs" ] && docs="/*.adoc /**/*.adoc /*.md /**/*.md /*.rst /**/*.rst"
  [ "$code" = 1 ] && docs="$docs /**/*.go /**/*.py /**/*.proto /**/*.yaml /**/*.yml /**/*.sh
    !**/vendor/** !**/third_party/** !*_test.go !**/mocks/** !**/mock/** !**/testdata/** !**/test/** !**/tests/**
    !**/zz_generated* !*.pb.go !*_mock.go !**/mockhelper/** !**/inttests/** !**/release-tools/** !**/hack/**
    !**/crds/** !**/config/crd/** !**/.github/**"
  echo "$docs"
}
ok=0; fail=0
while read -r vendor product url subdirs; do
  d="$DOCS/$vendor/$product"
  # shellcheck disable=SC2086
  pats=$(patterns $subdirs)
  if [ -d "$d/.git" ]; then
    # shellcheck disable=SC2086
    if git -C "$d" sparse-checkout set --no-cone $pats >/dev/null && git -C "$d" fetch -q --depth 1 origin && git -C "$d" reset -q --hard FETCH_HEAD; then
      ok=$((ok+1)); echo "${url%.git}" > "$d/.source_url"; echo "updated $vendor/$product"
    else fail=$((fail+1)); echo "update failed: $url"; fi
    continue
  fi
  rm -rf "$d"; mkdir -p "$(dirname "$d")"
  if ! git clone -q --depth 1 --filter=blob:none --no-checkout "$url" "$d"; then
    fail=$((fail+1)); echo "clone failed: $url"; continue
  fi
  # shellcheck disable=SC2086
  git -C "$d" sparse-checkout set --no-cone $pats >/dev/null
  git -C "$d" checkout -q
  echo "${url%.git}" > "$d/.source_url"
  ok=$((ok+1)); echo "cloned $vendor/$product"
done < "$LIST"
rm -f "$LIST"
echo "git sources: $ok synced, $fail failed -> $DOCS"
