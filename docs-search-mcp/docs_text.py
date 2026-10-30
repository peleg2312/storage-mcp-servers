"""Tool texts shared by server.py (HTTP) and mcp_stdio.py (stdio). Standard library only."""

INSTRUCTIONS = """\
Read-only, OFFLINE search over the team's storage documentation: NetApp ONTAP / EMS / SAN hosts / Trident, Dell \
PowerMax / PowerFlex / PowerScale / CSM, Cisco, VMware, Kubernetes / OpenShift, HashiCorp, the backend stack \
(FastAPI, httpx, MCP...), KB articles, CSI driver source, Dell CSM pull requests (the fixes), Trident / Harvest \
bug trackers, and library "local" (the team's own runbooks, when present). The urls are for the humans.
1. search_docs with the exact technical terms (error text in "quotes", EMS / event names, commands, KB / CONTAP / \
DSA numbers). Old and new product names and acronyms match each other. Filter by vendor / product when the platform \
is known (list_sources(vendor) gives the names; by_product shows where the hits are). No good hit: send 2-3 \
rephrasings in parallel in the vendor's words and replace the `unmatched` words.
2. read_chunk the best 2-3 hits before answering; read_document for a whole page or PDF. also_in = the same page \
in other versions: open the installed one.
3. Cite title + url + version for every statement; never invent commands, settings or bug numbers. `matched` \
(n/m query words) appears only on partial hits: weak evidence.
Live state comes from the PowerMax / ONTAP / MDS MCP servers, not from here."""

SEARCH_DOC = ('Search the docs, KB, bug trackers, pull requests and source code. query: technical words; '
              '"quoted text" must match verbatim (error messages); synonyms apply (Isilon=PowerScale, VMAX=PowerMax...). '
              'vendor: netapp|dell|cisco|kubernetes|openshift|vmware|python|mcp|hashicorp|kb. product: substring '
              '(ontap-ems-9151, trident-2510, csm, csm-prs, powerflex-api...). Up to `limit` hits, max 2 per '
              'document; chunk_id feeds read_chunk.')
