"""
List the Broadcom (VMware) knowledge base articles about storage from the site's sitemap, for sync_web.py.

    python3 sync/broadcom_kb_list.py > work/vmware-kb-storage.txt
    python3 sync/sync_web.py --urls work/vmware-kb-storage.txt --dest work/docs --delay 2     # -> vmware/kb

The sitemap lists ~180,000 articles of every Broadcom product; the article slug is the only hint of the subject,
so this keeps the slugs that name a vSphere storage object (VMFS, NFS, datastore, LUN, naa, APD / PDL, multipath,
iSCSI, FC / HBA, vVols, VAAI, NVMe, SATP / PSA / NMP, esxcli, UNMAP, VMDK, RDM, WWN, zoning, VASA, vSAN) in
English. Standard library only.
"""
import re
import sys
import urllib.request

SITE = "https://knowledge.broadcom.com"
UA = "docs-search-mcp/1.1 (internal documentation index)"
STORAGE = re.compile(r"(vmfs|nfs|datastore|lun\b|luns|naa|apd|pdl|multipath|iscsi|fibre|fiber|hba|scsi|vvol|vaai|nvme|"
                     r"satp|psa\b|nmp|esxcli|unmap|vmdk|rdm\b|wwn|zoning|vasa|dead-?path|all-?paths|lost-?access|vsan|"
                     r"storage-?(array|device|path|adapter|controller|policy|io|dr|vmotion))", re.I)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def main():
    urls = []
    for sub in re.findall(r"<loc>([^<]+)</loc>", get(SITE + "/sitemap.xml")):
        urls += re.findall(r"<loc>([^<]+)</loc>", get(sub))
    keep = [u for u in urls if u.isascii() and STORAGE.search(u.rsplit("/", 1)[-1])]
    print(f"{len(urls)} articles, {len(keep)} about storage", file=sys.stderr)
    print("\n".join(sorted(set(keep))))


if __name__ == "__main__":
    main()
