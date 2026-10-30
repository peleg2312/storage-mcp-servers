"""Tool texts shared by server.py (HTTP) and mcp_stdio.py (stdio). Standard library only."""

INSTRUCTIONS = """\
Read-only, OFFLINE search over the team's storage documentation: NetApp ONTAP / EMS / SAN hosts / Trident, Dell \
PowerMax / PowerFlex / PowerScale / CSM, Cisco, VMware, Kubernetes / OpenShift, HashiCorp, backend libraries, KB \
articles, CSI driver source, Dell CSM pull requests (the fixes), Trident / Harvest bug trackers, and library \
"local" (the team's runbooks). The urls are for the humans.
0. An EMS / alert / SIO / CONTAP / DSA / KB number: explain_code(code) first, one call.
1. search_docs with the exact technical terms (error text in "quotes", EMS names, commands). Old and new product \
names and acronyms match each other. Filter by vendor / product when known (list_sources(vendor); by_product shows \
where the hits are). read_top=2 returns the top sections inline. Partial or off-target: queries=[2-3 rephrasings \
in the vendor's words], replacing the `unmatched` words.
2. read_chunk the best 2-3 hits before answering; read_document for a whole page or PDF. also_in = the same page \
in other versions: open the installed one.
3. Cite title + url + version for every statement; never invent commands, settings or bug numbers. `matched` \
(n/m query words) appears only on partial hits: weak evidence.
Live state comes from the PowerMax / ONTAP / MDS MCP servers, not from here."""

SEARCH_DOC = ('Search the docs, KB, bug trackers, pull requests and source code. query: technical words; '
              '"quoted text" must match verbatim (error messages); synonyms apply (Isilon=PowerScale, VMAX=PowerMax...). '
              'vendor: netapp|dell|cisco|kubernetes|openshift|vmware|python|mcp|hashicorp|kb. product: substring '
              '(ontap-ems-9151, trident-2510, csm, csm-prs, powerflex-api...). Up to `limit` hits, max 2 per '
              'document; chunk_id feeds read_chunk. read_top (0-3): the full text of the best hits comes inline (field text), '
              'so one call answers. queries: several phrasings at once (wins over query); merged, with partial / '
              'unmatched reported per query in by_query.')

EXPLAIN_DOC = ('Exact lookup of an identifier the library documents: ONTAP EMS event name (wafl.vol.full), PowerMax '
               'SYMAPI_AEVENT2_* alert, PowerFlex SIO dial-home code, CONTAP-* bug, DSA-* advisory, Dell / NetApp KB '
               'number (000xxxxxx). Returns severity, description, corrective action, title, url, product, chunk_id; '
               'a KB / bug adds its Symptoms / Cause / Resolution sections. Not documented: documented=false.')
