"""
List the Broadcom (VMware) knowledge base articles about storage from the site's sitemap, for sync_web.py.

    python3 sync/broadcom_kb_list.py > work/vmware-kb-storage.txt
    python3 sync/sync_web.py --urls work/vmware-kb-storage.txt --dest work/docs --delay 2     # -> vmware/kb

The sitemap lists ~180,000 articles of every Broadcom product; the article slug is the only hint of the subject,
so this keeps the slugs that name a vSphere storage object (VMFS, NFS, datastore, LUN, naa, APD / PDL, multipath,
iSCSI, FC / HBA, vVols, VAAI, NVMe, SATP / PSA / NMP, esxcli, UNMAP, VMDK, RDM, WWN, zoning, VASA, vSAN) in
English, and drops the slugs of Broadcom's non-VMware products. Standard library only.
"""
import re
import sys
import urllib.request

SITE = "https://knowledge.broadcom.com"
UA = "docs-search-mcp/1.1 (internal documentation index)"
STORAGE = re.compile(r"\b(vmfs|nfs|nfsv?[34]|datastores?|luns?|naa|apd|pdl|multipath\w*|iscsi|fibre|fiber|hba|hbas|scsi|vvols?|vaai|"
                     r"nvme\w*|satp|psa|nmp|hpp|esxcli|unmap|vmdks?|rdm|rdms|wwn|wwpn|zoning|vasa|dead-paths?|all-paths-down|"
                     r"permanent-device-loss|vsan|vmkernel|storage-(array|device|path|paths|adapter|controller|policy|policies|io|dr|"
                     r"vmotion|provider|container|pod)|esxi-storage|san-storage|nas-storage)\b")
VMWARE = re.compile(r"\b(esxi?|vsphere|vcenter|vmware|vms?|vmotion|vmkernel|vsan|vmfs|datastore|vcsa)\b")
NARROW = re.compile(r"\b(storage|disks?|snapshots?|latency|paths?|controller|vmdk|array|thin|thick|nvme|raid|san|capacity|iops)\b")
DROP = re.compile(r"\b(backup|vami|hcx|vmc|aws|azure|gcp|horizon|nsx|tanzu|aria|workspace|vcf)\b")
# Broadcom's other products share the KB (CA UIM, Spectrum, mainframe, Symantec...): their slugs are left out
OTHER = re.compile(r"\b(snmp\w*|uim|spectrum|netops|nfa|ca|clarity|automic|autosys|xcom|librarian|mainframe|ims|cics|db2|datacom|"
                   r"idms|endevor|sysview|top-secret|acf2|siteminder|api-gateway|rally|agile|symantec|dlp|sep|edr|layer7|apm|dx|"
                   r"oneclick|tdm|arcot|pam|identity|ppm|ssl-visibility)\b")


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def main():
    urls = []
    for sub in re.findall(r"<loc>([^<]+)</loc>", get(SITE + "/sitemap.xml")):
        urls += re.findall(r"<loc>([^<]+)</loc>", get(sub))
    def wanted(slug):
        # a storage object in the slug, or a VMware word next to a storage word (disk, snapshot, latency, controller:
        # alone they would pull in Broadcom's other products); hosted and backup products are left out
        return (STORAGE.search(slug) or (VMWARE.search(slug) and NARROW.search(slug))) and not OTHER.search(slug) \
            and not DROP.search(slug)
    keep = [u for u in urls if u.isascii() and wanted(u.rsplit("/", 1)[-1])]
    print(f"{len(urls)} articles, {len(keep)} about storage", file=sys.stderr)
    print("\n".join(sorted(set(keep))))


if __name__ == "__main__":
    main()
