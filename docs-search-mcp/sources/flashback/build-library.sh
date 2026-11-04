#!/bin/sh
# The Flashback (backup and restore) team library, built on a machine WITH internet, then carried in as one tarball:
#   sh sources/flashback/build-library.sh [WORK]          (default WORK=work/flashback; incremental, re-run to refresh)
# -> WORK/docs/<vendor>/<product>/...  WORK/docs.db  and  WORK/flashback-library-<date>.tar.gz (+ .sha256)
# On the VM, as root:  paas-library import flashback flashback-library-<date>.tar.gz   (RUNBOOK, "Flashback library")
#
# What goes in (sources/flashback/*.txt and the regular expressions next to this file):
#   commvault/<version>       documentation.commvault.com Command Center docs, 2024e (= 11.36), 11.40, 11.42, 11.44: the
#                             databases (PostgreSQL, SQL Server incl. Always On AG, Oracle, Oracle RAC / Data Guard),
#                             Exchange, VMware, Kubernetes (etcd), S3 object storage, storage (cloud / disk libraries,
#                             MediaAgents, deduplication), IntelliSnap (NetApp, PowerMax, PowerFlex), CommServe DR /
#                             LiveSync, plans, monitoring, reports, REST API, PowerShell, upgrades (commvault-include.re).
#                             11.38 is left out: the site's robots.txt disallows it (its topics match 11.36 / 11.40).
#   veeam/<guide>             helpcenter.veeam.com v13: Backup & Replication user guide (VMware vSphere, agents, PostgreSQL,
#                             NFS / NetApp repositories, other hypervisors left out), PowerShell reference, event IDs,
#                             what's new, permissions, Veeam ONE, Veeam Agent for Linux.
#   redhat/oadp-1.4|1.5|1.6   the OpenShift "Backup and restore" guide of OCP 4.18 / 4.20 / 4.22 (OADP 1.4.x / 1.5.x / 1.6.x
#   redhat/hosted-control-planes-<ocp>  and the hosted control planes guide (backup / restore / DR of hosted clusters with OADP)
#   openshift/*, velero/*     GitHub: oadp-operator docs per release branch, hypershift-oadp-plugin (README, examples
#                             YAML), HyperShift disaster-recovery docs, Velero docs v1.14 to v1.17 (git-repos.txt)
#   netapp/*, dell/*          copied from the general library (library/ in this repository): ONTAP data protection
#                             (snapshots, policies, SnapMirror, SVM DR, FlexClone, restore), KB data protection, Trident,
#                             PowerMax (SnapVX, SRDF), PowerFlex (snapshots, replication), CSM / CSI PowerFlex snapshots
#                             and replication (subset.txt)
# Standard library Python 3 and git; the library's own docs_index.py builds the index.
set -eu
HERE=$(cd "$(dirname "$0")/../.." && pwd)                 # docs-search-mcp
SRC="$HERE/sources/flashback"
WORK=${1:-$HERE/work/flashback}
DOCS="$WORK/docs"
mkdir -p "$DOCS"
SYNC="python3 $HERE/sync/sync_site.py"
INC=$(cat "$SRC/commvault-include.re"); EXC=$(cat "$SRC/commvault-exclude.re")

# 1. Commvault: 11.40 first (every topic read once, the filter keeps ~3,900); the other versions skip what 11.40 dropped
$SYNC commvault --version 11.40 --dest "$DOCS" --include "$INC" --exclude "$EXC" --prune --workers 6
for v in 2024e 11.42 11.44; do
  $SYNC commvault --version "$v" --dest "$DOCS" --include "$INC" --exclude "$EXC" --like "$DOCS/commvault/11.40" --prune --workers 6
done

# 2. Veeam v13 guides (veeam-guides.txt: <guide> [exclude=RE])
VEX=$(cat "$SRC/veeam-exclude.re")
grep -v '^#' "$SRC/veeam-guides.txt" | while read -r guide filt; do
  [ -n "$guide" ] || continue
  if [ "$filt" = "filter" ]; then $SYNC veeam --guide "$guide" --dest "$DOCS" --exclude "$VEX" --prune --workers 6
  else $SYNC veeam --guide "$guide" --dest "$DOCS" --workers 6; fi
done

# 3. Red Hat guides: one html-single page per guide, split per section (redhat-guides.txt: <ocp> <guide> <product>)
mkdir -p "$WORK/redhat-pages"
grep -v '^#' "$SRC/redhat-guides.txt" | while read -r ocp guide product; do
  [ -n "$ocp" ] || continue
  page="$WORK/redhat-pages/$guide-$ocp.html"
  curl -fsSL --compressed --max-time 300 -o "$page" \
    "https://docs.redhat.com/en/documentation/openshift_container_platform/$ocp/html-single/$guide/index"
  $SYNC redhat --guide "openshift_container_platform/$ocp/$guide" --product "$product" --dest "$DOCS" --file "$page"
done

# 4. GitHub docs (git-repos.txt, same format as sources/git-repos.txt plus #branch on the url)
SOURCES="$SRC/git-repos.txt" sh "$HERE/sync/sync-git.sh" "$DOCS"

# 5. NetApp / Dell data-protection documents from the general library (library/ parts in this repository)
python3 "$SRC/copy_subset.py" --library "$HERE/../library" --subset "$SRC/subset.txt" --dest "$DOCS"

# 6. Team pointers written by hand (kb-pointers.md: verified one-line answers), then the index and the tarball
mkdir -p "$DOCS/flashback/pointers"
cp "$SRC/pointers/"*.md "$DOCS/flashback/pointers/"
python3 "$HERE/docs_index.py" --docs "$DOCS" --db "$WORK/docs.db"
python3 "$SRC/manifest.py" "$WORK" > "$WORK/MANIFEST.md"
D=$(date +%Y.%m.%d)
tar -C "$WORK" -czf "$WORK/flashback-library-$D.tar.gz" --exclude='*/.git' --exclude='.crawl.json' docs docs.db MANIFEST.md
( cd "$WORK" && sha256sum "flashback-library-$D.tar.gz" > "flashback-library-$D.tar.gz.sha256" )
echo "flashback library: $WORK/flashback-library-$D.tar.gz"
