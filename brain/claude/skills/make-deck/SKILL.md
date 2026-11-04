---
name: make-deck
description: Designed PowerPoint decks (.pptx, editable, native charts and tables) from any topic, investigation, report or data - you write a short JSON outline, ~/.claude/tools/deck.py does the design (themes or the company template). Triggers - "presentation", "PowerPoint", "pptx", "slides", "deck", "make it a presentation for management / the team"
---
# Designed decks (`~/.claude/tools/deck.py`)

You write the **content** as a JSON outline; the tool does the **design**: layout, fonts, colours, native charts
with their data, styled tables, text fitted to its box, page numbers. Never draw slides with python-pptx yourself.

## 1. Content first
- Facts only from tool results, reports or documents in this session (golden rule 2); numbers you chart come from
  saved data (python), never retyped. Missing data: say so on the slide, never invent it.
- Story: what the audience must decide or know → 8-15 slides: title, agenda (optional), a section per part,
  the evidence, the ask / next steps (closing).
- **One message per slide.** The title says the conclusion ("Prod-A grew fastest: 40 TB a month"), not the topic
  ("Growth"). `**bold**` the one number or phrase that matters.
- Short: 3-6 bullets of one line each; card / step / milestone texts are one sentence.

## 2. Write the outline
`python3 ~/.claude/tools/deck.py --example` prints a spec with every slide type: start from it. Save yours as
`~/storage-reports/<date>-<topic>/deck.json` (no spaces in the folder name).

| type | fields | use for |
|---|---|---|
| title | title, subtitle, meta | first slide |
| agenda | items (≤ 7) | the parts |
| section | title, subtitle | start of a part (its name becomes the small label above later titles) |
| stats | stats [{value, label, delta, good}], note | 2-4 headline numbers |
| chart | chart {kind, categories, series [{name, values}], unit, highlight, source, min, max}, takeaway | trends, comparisons; kind: column, bar, stacked, stacked_bar, line, area, pie, doughnut |
| bullets | bullets [text or {text, sub: [..]}], takeaway | reasons, findings |
| cards | cards [{title, text, icon}] (2-6) | options, checks, pillars (icon: a short value like "90 TB") |
| compare | left / right {title, bullets}, verdict | A vs B, before / after |
| table | columns, rows, highlight (row index), note | ≤ 12 rows, ≤ 7 columns (more: the Excel export) |
| timeline | items [{date, title, text, done}] (3-6) | plan, history (done: false greys future items) |
| process | steps [{title, text}] (3-5) | procedures, flows |
| quote | quote, by | one strong statement |
| image | image (path), caption | a screenshot or diagram file |
| closing | title, subtitle, bullets, contact | the ask, next steps |

Every slide takes `notes` (speaker notes). Deck fields: `title`, `theme` (midnight, graphite, ocean, emerald,
sunset, light), `footer`, `template` (company .pptx / .potx), `colors` / `fonts` overrides.
Charts: one measure per chart; `highlight` a category to make it the only strong bar; ≤ 5 series, a pie ≤ 6 slices.

## 3. Build, then fix every WARN
```bash
python3 ~/.claude/tools/deck.py ~/storage-reports/<dir>/deck.json --out ~/storage-reports/<dir>/ [--template <company.pptx>] [--preview]
```
- `WARN` lines (text that does not fit, too many bullets, long titles, crowded charts): shorten or split in the
  JSON and run again until `checks: ok`. Never deliver with WARN lines left.
- **Company look**: `--template` with the company deck or .potx (its master, logo, colours, fonts and layouts).
  Ask the user for the path once and keep it in `notes/tools.md`.
- `--preview` (when LibreOffice is installed) writes `preview/contact-sheet.png` and one PNG per slide: if you can
  view images, look at the sheet and fix what looks wrong; else rely on the WARN checks.

## 4. Deliver
`python3 ~/.claude/tools/report.py --send <file>.pptx` (to the PC / Reports tab), then answer with the file as a
Markdown link to its full path, the slide list (one line each) and what the user should check (numbers, names).
