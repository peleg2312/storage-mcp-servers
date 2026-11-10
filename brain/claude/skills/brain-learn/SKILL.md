---
name: brain-learn
description: Capture durable knowledge into the brain's notes or captures, curate captures into notes, save a tested procedure as a runbook, write a storage incident postmortem. Use for "remember this", "write it down", "curate the captures", "save this as a runbook", "postmortem", "incident report", "what did we learn".
when_to_use: A problem was solved, a change procedure the user ran worked, the user asks to keep something, to curate captures, or to write up an incident.
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
`notes/<topic>-<slug>.md` when it fits no line, or as a runbook (d) when it is a procedure the user has since run and
confirmed), **merge** (fold into an existing note, bump its date), **keep**, **discard**. Show the table
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

## d) Runbook
A procedure the **user ran and that worked** (a change: add a host to a masking view, expand a LUN, replace an SFP)
becomes `~/.claude/brain/runbooks/<topic>-<task>.md` (topic as in notes: powermax, ontap, fabric, ...). Not yet run, or
it needed fixes on the way that nobody re-checked: a capture instead. Search first (`ls ~/.claude/brain/runbooks/`,
grep): a runbook that exists is updated (steps fixed, Scope widened, a History line), never duplicated. Every command
is for the user to run; placeholders (`<sid>`, `<sg-name>`, `<wwpn>`) instead of real names, plus the read-only command
that shows each value; never passwords or tokens. Sections, in order (`check.py` requires the four marked *):
```
# <Verb phrase: Add an ESXi host to a PowerMax masking view>
When to use: <situation / request>   Impact while running: <what users see, how long>   Prerequisites: <access, window>
## Pre-checks *      read-only commands and what each must show before going on
## Procedure *       numbered steps, one command block each, with why
## Verification *    commands that prove it worked
## Rollback *        how to undo each step, or "not reversible after step N"
## Scope             arrays / models / versions it was run on; where it is known not to apply
## History           <date>: created, run on <array model / version> by <who> · verified
```
Show it to the user and wait for the go-ahead before saving. When asked for change steps later, a matching runbook
is the answer: follow it, say which one, and add a History line when the user reports it worked again (or fix it).

## e) After writing
After a promote, a new page, a runbook or an incident, run `add-docs --brain`: the docs search then finds them next to the
vendor documents (each dated fact line is its own hit; captures are found too, titled "Unverified capture";
notes.md and environment.md are never indexed: they are in every session anyway). Nothing to commit by hand: the
notes-check hook commits each saved file to the brain's git history (Brain tab shows it).
On a team, every saved note, capture, runbook and incident is committed and pushed to the team repository at once and pulled by every member at their next session start; the whole memory is the team's.
