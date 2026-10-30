---
name: handover-note
description: Turns the current investigation into a handover / ticket text (ServiceNow, Jira, email to the vendor, shift handover) written to a file, never sent - summary, impact, evidence with sources, timeline, commands run, docs cited, next steps. Triggers - "write a handover", "ticket text", "incident note", "summary for the vendor / for ServiceNow / for Jira", "hand this over"
---
# Handover note

Write `~/storage-reports/<date>-<topic>/handover.md` (same folder as the reports of this investigation, if any)
and show its path. Plain Markdown, no headings deeper than `##`, short lines a ticket form keeps. **Only facts
from this session** (tool results, documents, what the user said): nothing invented, every number with its source.

## Sections, in this order (leave out an empty one)
1. **Summary** - 2-3 lines: what is wrong (or what was done), since when, who is affected.
2. **Impact** - hosts / VMs / applications / volumes / paths concerned, with their identifiers (NAA / EUI, WWPN, volume
   and LUN ids exactly as the tools returned them); what still works.
3. **Evidence** - one bullet per finding: the fact, then `(source: <MCP tool> <object>, <time>)` or
   `(source: <doc title>, <url>, <version>)`. Error texts and event names verbatim, in backticks.
4. **Timeline** - `YYYY-MM-DD HH:MM` lines, oldest first: first symptom, changes found (change-review), actions taken.
5. **Commands / checks run** - the read-only tool calls and commands, in order, as a list; any step the user ran
   himself labelled "run by <user>".
6. **Documents cited** - title, url, version; KB / bug numbers.
7. **Next steps** - what is proposed, each labelled "to be run by you" with its pre-check and rollback (rule 1), and
   who owns it; what the vendor should look at (support bundle, logs already collected).
8. **Open questions** - what could not be checked and why (unreachable system, missing source, denied action).

For the vendor: add the serial / cluster name, software version and a support-bundle status line at the top.
For Jira: keep the Summary as the first line (it becomes the title). Never include passwords, tokens or cookies.
