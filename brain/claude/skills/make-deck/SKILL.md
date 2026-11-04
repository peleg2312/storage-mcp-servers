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
| section | title, subtitle, icon | start of a part (its name becomes the small label above later titles) |
| hero | value, text, sub, icon | ONE big number or statement on a full-colour slide ("14 months" / "until full") |
| stats | stats [{value, label, delta, good, progress, icon}], note | 2-4 headline numbers (progress "78%" draws a bar) |
| chart | chart {kind, categories, series [{name, values}], unit, highlight, target, target_label, source, min, max}, takeaway, icon | trends, comparisons; kind: column, bar, stacked, stacked_bar, line, area, pie, doughnut |
| bullets | bullets [text or {text, sub: [..]}], takeaway, icon | reasons, findings |
| cards | cards [{title, text, icon, value}] (2-6) | options, checks, pillars (value: "90 TB" beside the icon) |
| iconlist | items [{icon, title, text}] (2-6) | checks, principles, features |
| compare | left / right {title, bullets}, verdict | A vs B, before / after |
| table | columns, rows, highlight (row index), heat [column names], total, zebra, note | ≤ 12 rows, ≤ 7 columns (more: the Excel export) |
| timeline | items [{date, title, text, done, icon}] (3-6) | plan, history (done: false greys future items) |
| process | steps [{title, text}] (3-5) | procedures, flows |
| quote | quote, by | one strong statement |
| image | image (path), caption | a screenshot or diagram file |
| closing | title, subtitle, bullets, contact | the ask, next steps |

Every slide takes `notes` (speaker notes). Deck fields: `title`, `footer`, `style`, `theme` / `accent`, `look`,
`template` (company .pptx / .potx), `colors` / `fonts` overrides.
- **Every deck looks different by itself**: its `look` (layouts of the title, section, agenda, cards and numbers
  slides, palette, fonts, bullets) comes from its title; the output's `look:` line gives the number. Do not copy a
  theme from an earlier deck. The user liked one: `"look": <that number>`; wants another: `"look": "random"`.
- **Choose the style for the audience** (always set it): management, kick-off, a proposal → `"bold"`; an ops review,
  a technical walkthrough, a handover → `"clean"`; an incident review → `"clean"` with `"theme": "graphite"`.
- Colours: leave them to the look, or `"accent": "#7A3EF0"` (the team's or the customer's colour: a whole palette is
  built from it), or a fixed `theme` (midnight, graphite, ocean, emerald, sunset, light). A `template` overrides all
  of this: company decks always look like the company.
- **Icons** (`deck.py --icons`): database, server, disk, network, switch, cloud, shield, lock, check, alert, error,
  clock, calendar, chart, trend-up, gauge, money, users, gear, search, archive, replication, rocket, idea... (aliases:
  storage, backup, dr, risk, cost, team...). Give one icon per card / stat / list item, matching its meaning.
- **Charts**: one measure per chart; `highlight` a category to make it the only strong bar; `target` draws a dashed
  limit line (capacity 80%, an SLA); a line chart names each series at its end (no legend); a doughnut shows its total
  in the middle; ≤ 5 series, a pie ≤ 6 slices; `unit` "%", "TB", "ms"...
- **Tables**: status words (OK, Healthy, Warning, Degraded, Failed, Down, In sync, Lagging...) are coloured by
  themselves; `heat` tints a numeric column by value (used %, latency); `total: true` styles the last row as a total.
- Rhythm: vary the slide types (a hero after the stats, a chart, then cards); never three bullet slides in a row.

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
