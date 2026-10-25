# Dell documents that need a browser download (login-only)

Dell returns its 'Statement against modern slavery' PDF instead of these documents unless the browser is signed in to
dell.com/support. Easiest: `python3 sync/dell_browser.py login` once, then `python3 sync/dell_browser.py needed`
(downloads them through the signed-in browser into `extra/dell/<product>/`). By hand: open each link signed in and save
the PDF under `extra/dell/<product>/` with the file name shown. Then `python3 sync/import_extra.py --dest work/docs`
and `git add -f docs-search-mcp/extra/dell && git commit && git push`.

## powerflex  ->  save into extra/dell/powerflex/

| File name | Link |
|---|---|
| `manual55425296-dell-powerflex-5-1-x-4-5-x-and-powerflex-manager-5-1-x-release-notes.pdf` | https://dl.dell.com/content/manual55425296-dell-powerflex-5-1-x-4-5-x-and-powerflex-manager-5-1-x-release-notes.pdf |
| `manual41313829-dell-powerflex-5-1-x-and-powerflex-manager-5-1-x-support-matrix.pdf` | https://dl.dell.com/content/manual41313829-dell-powerflex-5-1-x-and-powerflex-manager-5-1-x-support-matrix.pdf |
| `manual69966030-dell-powerflex-family-5-x-security-configuration-guide.pdf` | https://dl.dell.com/content/manual69966030-dell-powerflex-family-5-x-security-configuration-guide.pdf |
| `manual21472110-dell-powerflex-5-1-x-and-powerflex-manager-5-1-x-alerts-and-events-reference-guide.pdf` | https://dl.dell.com/content/manual21472110-dell-powerflex-5-1-x-and-powerflex-manager-5-1-x-alerts-and-events-reference-guide.pdf |
| `manual16632609-dell-powerflex-5-0-x-and-powerflex-manager-5-0-x-example-csv-files.pdf` | https://dl.dell.com/content/manual16632609-dell-powerflex-5-0-x-and-powerflex-manager-5-0-x-example-csv-files.pdf |
| `manual71189798-dell-powerflex-family-4-x-security-configuration-guide.pdf` | https://dl.dell.com/content/manual71189798-dell-powerflex-family-4-x-security-configuration-guide.pdf |
| `manual21579043-dell-powerflex-4-5-x-and-powerflex-manager-5-1-x-alerts-and-events-reference-guide.pdf` | https://dl.dell.com/content/manual21579043-dell-powerflex-4-5-x-and-powerflex-manager-5-1-x-alerts-and-events-reference-guide.pdf |
| `manual36345513-dell-powerflex-4-x-example-csv-files.pdf` | https://dl.dell.com/content/manual36345513-dell-powerflex-4-x-example-csv-files.pdf |
| `powerflex-5-0-specification-sheet.pdf` | https://www.delltechnologies.com/asset/en-us/products/storage/technical-support/powerflex-5-0-specification-sheet.pdf |
| `powerflex-solution-brief.pdf` | https://www.delltechnologies.com/asset/en-us/products/storage/briefs-summaries/powerflex-solution-brief.pdf |
| `h18390-dell-emc-powerflex-networking-best-practices-wp.pdf` | https://www.delltechnologies.com/asset/en-us/products/storage/industry-market/h18390-dell-emc-powerflex-networking-best-practices-wp.pdf |
| `manual51257183-dell-powerflex-appliance-with-powerflex-5-x-architecture-overview.pdf` | https://dl.dell.com/content/manual51257183-dell-powerflex-appliance-with-powerflex-5-x-architecture-overview.pdf |
| `manual49095098-dell-powerflex-appliance-with-powerflex-5-x-administration-guide.pdf` | https://dl.dell.com/content/manual49095098-dell-powerflex-appliance-with-powerflex-5-x-administration-guide.pdf |
| `manual48592454-dell-powerflex-appliance-with-powerflex-5-x-intelligent-catalog-release-notes-3-9.pdf` | https://dl.dell.com/content/manual48592454-dell-powerflex-appliance-with-powerflex-5-x-intelligent-catalog-release-notes-3-9.pdf |
| `manual43265058-dell-powerflex-appliance-with-powerflex-5-x-network-planning-guide.pdf` | https://dl.dell.com/content/manual43265058-dell-powerflex-appliance-with-powerflex-5-x-network-planning-guide.pdf |
| `manual29291371-dell-powerflex-appliance-and-powerflex-rack-with-powerflex-5-x-powerflex-manager-compatibility-matrix.pdf` | https://dl.dell.com/content/manual29291371-dell-powerflex-appliance-and-powerflex-rack-with-powerflex-5-x-powerflex-manager-compatibility-matrix.pdf |
| `manual66926257-dell-powerflex-appliance-with-powerflex-5-x-management-cluster-replacement-procedures.pdf` | https://dl.dell.com/content/manual66926257-dell-powerflex-appliance-with-powerflex-5-x-management-cluster-replacement-procedures.pdf |
| `manual49882844-dell-powerflex-appliance-and-powerflex-rack-with-powerflex-5-x-hardening-procedures.pdf` | https://dl.dell.com/content/manual49882844-dell-powerflex-appliance-and-powerflex-rack-with-powerflex-5-x-hardening-procedures.pdf |
| `manual64639733-dell-powerflex-appliance-upgrading-to-powerflex-manager-5-x-and-powerflex-5-x-4-5-x.pdf` | https://dl.dell.com/content/manual64639733-dell-powerflex-appliance-upgrading-to-powerflex-manager-5-x-and-powerflex-5-x-4-5-x.pdf |
| `manual40172030-dell-powerflex-family-licensing-guide.pdf` | https://dl.dell.com/content/manual40172030-dell-powerflex-family-licensing-guide.pdf |
| `manual25305810-dell-cloudlink-8-3-x-release-notes.pdf` | https://dl.dell.com/content/manual25305810-dell-cloudlink-8-3-x-release-notes.pdf |
| `manual28911486-dell-cloudlink-security-configuration-guide.pdf` | https://dl.dell.com/content/manual28911486-dell-cloudlink-security-configuration-guide.pdf |
| `manual37428579-dell-powerflex-5-0-x-and-powerflex-manager-5-0-x-support-matrix.pdf` | https://dl.dell.com/content/manual37428579-dell-powerflex-5-0-x-and-powerflex-manager-5-0-x-support-matrix.pdf |
| `manual59926943-dell-powerflex-5-0-x-and-powerflex-manager-5-0-x-cli-reference-guide.pdf` | https://dl.dell.com/content/manual59926943-dell-powerflex-5-0-x-and-powerflex-manager-5-0-x-cli-reference-guide.pdf |
| `manual55355780-dell-powerflex-5-0-x-and-powerflex-manager-5-0-x-alerts-and-events-reference-guide.pdf` | https://dl.dell.com/content/manual55355780-dell-powerflex-5-0-x-and-powerflex-manager-5-0-x-alerts-and-events-reference-guide.pdf? |
| `manual72830551-dell-powerflex-4-5-x-and-powerflex-manager-4-8-x-release-notes.pdf` | https://dl.dell.com/content/manual72830551-dell-powerflex-4-5-x-and-powerflex-manager-4-8-x-release-notes.pdf |
| `manual36877518-dell-powerflex-4-5-x-and-powerflex-manager-4-8-x-support-matrix.pdf` | https://dl.dell.com/content/manual36877518-dell-powerflex-4-5-x-and-powerflex-manager-4-8-x-support-matrix.pdf |
| `manual2550056-dell-powerflex-4-5-x-and-powerflex-manager-4-8-x-alerts-and-events-reference-guide.pdf` | https://dl.dell.com/content/manual2550056-dell-powerflex-4-5-x-and-powerflex-manager-4-8-x-alerts-and-events-reference-guide.pdf |
| `manual39480792-dell-powerflex-4-6-x-release-notes.pdf` | https://dl.dell.com/content/manual39480792-dell-powerflex-4-6-x-release-notes.pdf |
| `manual37556768-dell-powerflex-4-6-x-alerts-and-events-reference-guide.pdf` | https://dl.dell.com/content/manual37556768-dell-powerflex-4-6-x-alerts-and-events-reference-guide.pdf |
| `manual68830250-dell-powerflex-4-5-x-release-notes.pdf` | https://dl.dell.com/content/manual68830250-dell-powerflex-4-5-x-release-notes.pdf |
| `manual36963827-dell-powerflex-support-matrix-v4-5-x.pdf` | https://dl.dell.com/content/manual36963827-dell-powerflex-support-matrix-v4-5-x.pdf |
| `manual21813579-dell-powerflex-4-5-x-security-configuration-guide.pdf` | https://dl.dell.com/content/manual21813579-dell-powerflex-4-5-x-security-configuration-guide.pdf |
| `manual28550240-dell-powerflex-4-5-x-alerts-and-events-reference-guide.pdf` | https://dl.dell.com/content/manual28550240-dell-powerflex-4-5-x-alerts-and-events-reference-guide.pdf |
| `manual18767752-dell-powerflex-4-0-x-support-matrix.pdf` | https://dl.dell.com/content/manual18767752-dell-powerflex-4-0-x-support-matrix.pdf |
| `manual30688224-monitor-dell-emc-powerflex.pdf` | https://dl.dell.com/content/manual30688224-monitor-dell-emc-powerflex.pdf |
| `manual32534988-troubleshoot-and-maintain-dell-emc-powerflex.pdf` | https://dl.dell.com/content/manual32534988-troubleshoot-and-maintain-dell-emc-powerflex.pdf |
| `manual11097151-dell-powerflex-support-matrix-v3-6-0-x.pdf` | https://dl.dell.com/content/manual11097151-dell-powerflex-support-matrix-v3-6-0-x.pdf |

## powermax  ->  save into extra/dell/powermax/

| File name | Link |
|---|---|

## Retired links (not downloaded: Dell now redirects them to its home page; the papers moved to Info Hub,
which `dell_browser.py infohub` collects)

| Was | Link |
|---|---|
| `h17072-data-reduction-with-dell-emc-powermax.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/h17072-data-reduction-with-dell-emc-powermax.pdf |
| `h17108-dell-emc-service-levels-for-powermaxos.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/h17108-dell-emc-service-levels-for-powermaxos.pdf |
| `h17133-non-disruptive-migration-best-practices-and-operational-guide.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/h17133-non-disruptive-migration-best-practices-and-operational-guide.pdf |
| `h16856-dell-emc-embedded-management-on-powermax-and-vmax-all-flash.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/h16856-dell-emc-embedded-management-on-powermax-and-vmax-all-flash.pdf |
| `docu88905.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/docu88905.pdf |
| `docu71867.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage-5/docu71867.pdf |
| `docu68889.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage-5/docu68889.pdf |
| `docu90731.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/docu90731.pdf |
| `docu88876.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/docu88876.pdf |
| `docu88872.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/docu88872.pdf |
| `docu68803.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/networking-3/docu68803.pdf |
| `docu68804.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/networking-3/docu68804.pdf |
| `docu68805.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/networking-3/docu68805.pdf |
| `h15201-data-protector-for-z-systems-zdp-essentials.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/solutions/h15201-data-protector-for-z-systems-zdp-essentials.pdf |
| `h17064-dell-emc-powermax-reliability-availability-and-serviceability-technical-white-paper.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/h17064-dell-emc-powermax-reliability-availability-and-serviceability-technical-white-paper.pdf |
| `h17132-role-based-access-controls-rbac-technical-overview-and-enhancements.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/h17132-role-based-access-controls-rbac-technical-overview-and-enhancements.pdf |
| `h14531-vmax3-iscsi-implementation-tech-note.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage-1/h14531-vmax3-iscsi-implementation-tech-note.pdf |
| `h13697-emc-vmax3-local-replication.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage-1/h13697-emc-vmax3-local-replication.pdf |
| `h14556-vmax3-srdf-metro-overview-and-best-practices-tech-note.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage-1/h14556-vmax3-srdf-metro-overview-and-best-practices-tech-note.pdf |
| `h13904-vmax3-embedded-nas-technical-note.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage-1/h13904-vmax3-embedded-nas-technical-note.pdf |
| `h15188-emc-vmax3-vmax-all-flash-enas-best-practices.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-2/h15188-emc-vmax3-vmax-all-flash-enas-best-practices.pdf |
| `h14920-intro-to-vmax-af-storage.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage/h14920-intro-to-vmax-af-storage.pdf |
| `h13807-emc-vmax3-reliability-availability-and-serviceability-tech-note.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage-1/h13807-emc-vmax3-reliability-availability-and-serviceability-tech-note.pdf |
| `h14040-understanding-storage-resource-pools-emc-vmax3-storage-arrays.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-1/h14040-understanding-storage-resource-pools-emc-vmax3-storage-arrays.pdf |
| `h14944-emc-vmax-unisphere-360-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-1/h14944-emc-vmax-unisphere-360-wp.pdf |
| `h15498-dell-emc-vmax3-and-vmax-all-flash-quality-of-service-controls-for-multi-tenant-environments.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-2/h15498-dell-emc-vmax3-and-vmax-all-flash-quality-of-service-controls-for-multi-tenant-environments.pdf |
| `h14247-fast-x-emc-cloudarray-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-1/h14247-fast-x-emc-cloudarray-wp.pdf |
| `h11108-compatible-mc-features-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-1/h11108-compatible-mc-features-wp.pdf |
| `h15260-unisphere-vmax-mainframe-dashboard.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-2/h15260-unisphere-vmax-mainframe-dashboard.pdf |
| `h17390-deployment-bp-for-oracle-with-powermax-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage/h17390-deployment-bp-for-oracle-with-powermax-wp.pdf |
| `h14557-vmax3-all-flash-storage-for-oracle-database-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-1/h14557-vmax3-all-flash-storage-for-oracle-database-wp.pdf |
| `h14232-oracle-database-backup-recovery-vmax3.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage/h14232-oracle-database-backup-recovery-vmax3.pdf |
| `h15132-vmax-all-flash-vmax3-iscsi-deploy-guide-oracle-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-1/h15132-vmax-all-flash-vmax3-iscsi-deploy-guide-oracle-wp.pdf |
| `h14577-srdf-metro-oracle-ebus-rac.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-1/h14577-srdf-metro-oracle-ebus-rac.pdf |
| `h17234-powermax-sql-server-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage/h17234-powermax-sql-server-wp.pdf |
| `h16434-vmax-all-flash-storage-for-microsoft-hyper-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-2/h16434-vmax-all-flash-storage-for-microsoft-hyper-wp.pdf |
| `h15529-vmax-all-flash-sql-srdf-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-2/h15529-vmax-all-flash-sql-srdf-wp.pdf |
| `h15143-emc-vmax-all-flash-vmax3-iscsi-deploy-win-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-2/h15143-emc-vmax-all-flash-vmax3-iscsi-deploy-win-wp.pdf |
| `h2529-vmware-esx-svr-w-symmetrix-wp-ldv.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage-2/h2529-vmware-esx-svr-w-symmetrix-wp-ldv.pdf |
| `h8115-vmware-vstorage-vmax-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage/h8115-vmware-vstorage-vmax-wp.pdf |
| `h12138-emc-vmax-content-pack-vmware-loginsight-wp.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage-1/h12138-emc-vmax-content-pack-vmware-loginsight-wp.pdf |
| `h10553-sra-vmware-tb.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage-1/h10553-sra-vmware-tb.pdf |
| `h17000-srdf-sra-srm-tb.pdf` (powermax) | https://www.dell.com/en-sg/collaterals/unauth/technical-guides-support-information/products/storage/h17000-srdf-sra-srm-tb.pdf |
