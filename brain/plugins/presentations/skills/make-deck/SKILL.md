---
name: make-deck
description: Designed PowerPoint decks (.pptx, editable, native charts and tables, Hebrew right-to-left by itself) from any topic, investigation, report, document or data - you write a short JSON outline, the deck MCP tools do all the design and check it. Triggers - "presentation", "PowerPoint", "pptx", "slides", "deck", "מצגת", "make it a presentation for management / the team", "restyle this deck"
---
# Make a deck (the `deck` MCP server of this plugin)

You write only the CONTENT, as a JSON outline. The tools do ALL the design: layout, colours, fonts, icons, charts,
fitting the text, right-to-left for Hebrew. Never draw slides with python-pptx yourself, never set positions, sizes,
colours or fonts. Follow the steps in order; do not skip one.

Tools: `deck_guide`, `deck_build`, `deck_read` (any .pptx back as text), `deck_icons`, `deck_deliver`.
No MCP tools in this session: the same with `python3 ~/.claude/tools/deck.py --example he > outline.json` (or `en`),
then `python3 ~/.claude/tools/deck.py outline.json --json --check` (`--story <name>` prints a story plan).

## Step 1. Facts
Collect the facts first, from tool results, reports or documents in this session (golden rule 2). Write them down as a
short list: numbers with their source, names, dates. A fact you do not have: write "(to confirm)" on that slide and
tell the user. Never invent a number.

## Step 2. Plan 8-12 slides
A recurring deck has a ready story: call `deck_guide` with `"story"` and follow its plan slide by slide:
`monthly-review`, `incident-review`, `dr-drill`, `proposal`, `status-update`.
Otherwise use this order and change it only when the content needs it:
1. `title` - the subject, the team, the date
2. `summary` - the answer first: the conclusion, 2-4 key points, the ask (always for managers)
3. `agenda` - 3-6 parts (skip it for 8 slides or fewer)
4. for each part: a `section` slide, then 1-3 evidence slides (see the table below)
5. `closing` - the ask or the next steps (3-5 bullets)

Pick the slide type by what you show; never two `bullets` slides in a row:
| You show | Type |
|---|---|
| 2-4 key numbers | `stats` |
| ONE number that matters most | `hero` |
| a comparison or a trend over time | `chart` |
| reasons or findings (3-5) | `bullets` |
| options or things that work (3-4) | `cards` |
| checks, principles, features (3-5) | `iconlist` |
| a list of systems with values | `table` |
| a plan with dates | `timeline` |
| a procedure in steps | `process` |
| A against B | `compare` |
| the health of several systems (OK / Warning / Failed) | `status` |
| how systems connect (backup flow, replication, topology) | `diagram` |
| options on two axes (effort / effect) | `matrix` |
| one number that changed (before / after) | `beforeafter` |
| the answer, for managers | `summary` |

## Step 3. Write the outline
1. Call `deck_guide` once, with `lang: "he"` for a Hebrew deck. It returns the rules and an `example` outline.
2. COPY the example. Keep its JSON shape and field names exactly; replace its content with your facts; delete the slides
   you do not need, repeat the types you need.
3. Each slide title says the conclusion in one line (max 60 characters): "env2 has most failures: 23 of 41", not
   "Failures". Put the one key number in `**bold**`.
4. Keep texts short: bullet max 90 characters, card or step text max 80, item title max 30, stat value max 12
   ("97.8%", "312 TB"), stat label max 30.
5. Counts: bullets 3-5, cards 3-4, stats 2-4, items 3-5, steps 3-5, table rows max 10 and columns max 6.
6. Give every card, stat, iconlist item and timeline item an `icon` from the icon list (closest meaning).
7. Chart values are plain numbers from your facts: `"values": [9, 23, 5]`. One point worth a word: `"callouts":
   [{"at": "env2", "text": "MA-SITEB-03 lost DNS"}]`. A stat with history: `"trend": [95.1, 96.0, 97.8]`.
   A diagram: `nodes` with an `id` each, `links` with `from` / `to` naming those ids.
8. `"style"`: `"bold"` for managers and proposals, `"clean"` for technical reviews. No colours. A theme only when the user
   asks for a premium look: `"theme": "executive"` (navy and gold), `"ivory"` (warm paper), `"noir"` (dark).

**Hebrew deck**: write every text in Hebrew; keep product names, IDs and commands in English exactly as they are
(Commvault, MA-SITEB-03, `oc get backups`). Do not set direction, alignment or fonts: the deck turns right-to-left by
itself (`"direction": "rtl"` in the reply confirms it).

**Never put in the outline**: emoji, bullet signs ("•", "-", "1.") at the start of a text, HTML, Markdown other than
`**bold**`, empty items, positions, sizes, colours, font names.

## Step 4. Build and fix
Call `deck_build` with `{"spec": <the outline>, "style": "bold" or "clean"}`. Read the reply:
- `fixed` and `repaired`: things the tool already repaired for you (in the outline, in the rendered deck). Nothing to do.
- The tool draws the deck with LibreOffice and checks every text where it really lands; `pdf` is a PDF copy beside it.
- `warnings`: each line names a slide and what is wrong (a text cut to fit, a title too long, a title that only names a
  topic, two bullets slides in a row, no closing). Change exactly that in the
  outline (shorten the text, or split the slide in two) and call `deck_build` again with the whole outline.
- Stop after 3 rounds: deliver, and tell the user which warnings are left.
- `look`: the design number. The user liked it: keep `"look": <number>` next time; wants another: `"look": "random"`.
- To restyle a deck the user gave you: `deck_read` it, write its content as an outline, build.
- Company look: `"template": "<path of the company .pptx or .potx>"` in the outline; ask the user for the path once and
  keep it in `notes/tools.md`.

## Step 5. Deliver
Call `deck_deliver` with the path (and with the `pdf` path). Answer the user with: the file paths as Markdown links, the
look number, one line per slide (number, type, title), and what to check (numbers, names, the `to_confirm` slides).
Speaker notes are written from each slide's own text; give a slide `"notes"` to say more.
Company template: when the user gives the company .pptx / .potx, put `"template": "<path>"` in the outline (its master,
colours, fonts and layouts are used).
