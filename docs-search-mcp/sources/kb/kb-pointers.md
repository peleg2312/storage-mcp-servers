# SAN knowledge-base pointers

Curated, verified public KB articles and reference pages. Each entry: what it answers, the ID, and the
link. Content is NOT copied here - open the link (or ask Claude to fetch it) for the current version.
Add entries as you find useful KBs; this file is indexed by docs-search.

## Identifiers: NAA / EUI -> array volume

- **PowerMax / VMAX: which device is behind an naa ID** - Dell KB 000204833. NAA format
  `60000970` + 12-digit array serial + `53` + ASCII-hex device ID. Host LUN ID (HLU) can NOT be derived
  from the NAA. https://www.dell.com/support/kbdoc/en-us/000204833/how-to-know-what-storage-lun-is-presented-at-a-particular-naa-id
- **PowerMax / VMAX: symdev command examples** (list -wwn, -noport unmapped devices, show) - Dell KB 000228219.
  https://www.dell.com/support/kbdoc/en-us/000228219/list-of-symdev-commands-with-examples-a-simplified-guide-to-symdev-related-operations
- **PowerMax / VMAX: view and modify host LUN ID (HLU)** - Dell KB 000204697.
  https://www.dell.com/support/kbdoc/en-us/000204697/how-to-view-and-modify-powermax-vmax-host-lun-id-hlu
- **PowerFlex: locate the device identifier (EUI) of a volume (3.6.x)** - Dell KB 000264404. ESXi shows
  SDC volumes as `eui.<id>`; match the trailing digits to the Volume ID from `scli --query_all_volumes`.
  Verify the rule on 4.x/5.x. https://www.dell.com/support/kbdoc/en-us/000264404/how-to-locate-the-device-identifier-eui-in-a-volume-powerflex-3-6-x
- **NetApp ONTAP: match a LUN's NAA number to its serial number** - NetApp KB. NAA `600a0980` (clustered
  ONTAP) or `60a98000` (7-mode) + hex of the ASCII LUN serial; `lun show -serial-hex <hex>`.
  https://kb.netapp.com/hybrid/FlexPod/How_to_match__LUNs_NAA_number_to_its_serial_number
- **VMware: correlate vml ID with naa ID** - Broadcom KB 320217 (vml is a legacy alias of the naa/eui ID).
  https://knowledge.broadcom.com/external/article/320217/correlating-vml-id-with-naa-id-in-esxi-5.html

## Removing LUNs / datastores safely

- **VMware: how to detach a LUN device from ESXi hosts** - Broadcom KB 323128. Order: unmount datastore ->
  detach device on EVERY host -> unmap on array -> rescan -> `esxcli storage core device detached remove`.
  Skipping the detach causes APD. https://knowledge.broadcom.com/external/article/323128/how-to-detach-a-lun-device-from-esxi-hos.html
- **vSphere: detach a device and remove a LUN (esxcli)** - Broadcom TechDocs, ESXCLI Concepts and Examples 8.0.
  https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere-sdks-tools/8-0/esxcli-concepts-and-examples-8-0/managing-storage/detach-a-device-and-remove-a-lun.html
- **vSphere: unmount datastores** - Broadcom TechDocs, vSphere Storage 7.0.
  https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere/7-0/vsphere-storage/working-with-datastores-in-vsphere-storage-environment/basic-administrative-operations-for-vsphere-datastores/unmount-datastores.html

## APD / PDL / connectivity

- **vSphere: identifying ESXi storage connectivity problems (APD, PDL, Misc.APDTimeout 140 s)** - Broadcom TechDocs 8.0.
  https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere/8-0/vsphere-storage-8-0/managing-esxi-storage-devices/identifying-esxi-storage-connectivity-problems.html
- **vSphere: ESXi storage device names and identifiers (naa, eui, t10, vml)** - Broadcom TechDocs 7.0.
  https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere/7-0/vsphere-storage/managing-esxi-storage-devices/esxi-storage-device-names-and-identifiers.html
- **PowerFlex: ESXi SDC stops responding in vCenter (APD)** - Dell KB 000437810.
  https://www.dell.com/support/kbdoc/en-sg/000437810/powerflex-esxi-sdc-stop-responding-in-vcenter-apd

## Documentation hubs (where to look first)

- **PowerMax / VMAX documentation hub** (product, Unisphere, Solutions Enabler, REST, SRDF, SnapVX, VMware papers):
  https://www.dell.com/en-sg/dt/documentation/vmax-all-flash-family.htm
- **PowerFlex software documentation hub** (3.6, 4.x, 5.x guides, release notes, REST API):
  https://www.dell.com/support/kbdoc/en-us/000314729/powerflex-software-documentation
- **Unisphere for PowerMax REST API reference (OpenAPI)**: https://developer.dell.com/apis/4458/versions/10.1.0
- **NetApp ONTAP documentation**: https://docs.netapp.com/us-en/ontap/ (source: https://github.com/NetAppDocs)
- **NetApp docs MCP server** (official; needs a subscription key from ng-docs-mcp@netapp.com):
  https://docs.netapp.com/us-en/about/mcp-server-get-started.html
- **NetApp Knowledge Base** (some articles need a NetApp Support login): https://kb.netapp.com/
- **NetApp Bugs Online** (login): https://kb.netapp.com/nss/Support_Site/How_to_use_NetApp_Bugs_Online_Tool
- **Broadcom / VMware KB**: https://knowledge.broadcom.com/ (VMware KB IDs were remapped; legacy IDs redirect)
