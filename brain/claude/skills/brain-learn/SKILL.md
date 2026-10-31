---
name: brain-learn
description: Capture durable knowledge into the brain's notes or captures, curate captures into notes, write a storage incident postmortem. Use for "remember this", "write it down", "curate the captures", "postmortem", "incident report", "what did we learn".
when_to_use: A problem was solved, the user asks to keep something, to curate captures, or to write up an incident.
---
# Brain learn

Facts come from tool results and the user only (rule 2). Never passwords, tokens or credentials: write `<REDACTED>`.
Management IPs only in `environment.md`.

## a) Capture
1. Worth it? Only if a teammate in three months saves real time. Not generic vendor facts the library already has.
2. `grep -ri <keyword> ~/.claude/brain/notes/ ~/.claude/brain/captures/` first: update an existing line instead of adding.
3. Destination: confident and topic clear -> a dated line in `notes/<topic>.md` (`date · fact · confidence · source`).
   Otherwise a capture `~/.claude/brain/captures/<date>-<slug>.md`, no frontmatter:
   ```
   # <title>
   ## Symptom        exact error text, so grep finds it
   ## Cause
   ## Fix / workaround   commands in a code block, placeholders not real names
   ## Scope          arrays, versions, hosts where it applies; where it is known not to
   ## How we know    what was observed, when, confidence: verified | observed | hypothesis
   ## History        <date>: created
   ```
   A fact that does not fit a dated line is a knowledge page `notes/<topic>-<slug>.md` (line 1 `# <title>`, then the
   sections of a capture); session-start lists it with the topic files.
4. Tell the user the file path and a two-line summary.

## b) Curate ("curate the captures")
List `~/.claude/brain/captures/*.md`. For each choose: **promote** (into `notes/<topic>.md` as dated lines, or as a page
`notes/<topic>-<slug>.md` when it fits no line), **merge** (fold into an existing note, bump its date), **keep**, **discard**. Show the table
(file | decision | reason) and wait for the user's go-ahead before writing anything. Never raise confidence while
curating. Stale facts: `python3 ~/.claude/hooks/notes-check.py --stale 180`; ask the user to re-verify, never delete them.

## c) Incident report
Blameless postmortem of a storage incident, saved to `~/.claude/brain/incidents/<yyyy>/<date>-<slug>.md` (create the folder).
First search the library and `notes/` for related history. Sections, in order:
- **Header**: title, date, severity (sev1-sev4), status, systems (arrays / fabrics / hosts / datastores affected),
  started, detected, mitigated, resolved (each with timezone).
- **Impact**
- **Timeline**: one line per event, with time.
- **Root cause** (with confidence word)
- **Contributing factors**
- **What fixed it**
- **What was tried and did not work**
- **Evidence**: redacted log lines, alert names, EMS events, KB and bug numbers cited from the library.
- **Action items**: owner, due.

Then add one dated line in `notes/<topic>.md` pointing to the report. Only when the user wants it delivered: copy it
to `~/storage-reports/<date>-incident-<slug>/incident.md` and run `python3 ~/.claude/tools/report.py --send <file>`.

## d) After writing
After a promote, a new page or an incident, run `add-docs --brain`: the docs search then finds them next to the
vendor documents (notes.md, captures and environment.md are never indexed). Nothing to commit by hand: the
notes-check hook commits each saved file to the brain's git history (Brain tab shows it).
When the brain has a shared remote (install.sh --brain-remote), notes, captures and incidents reach the team at the next session start; notes.md and environment.md stay personal.
