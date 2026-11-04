# presentations

Designed, editable PowerPoint decks on an offline VM. Claude writes the content as a short JSON outline; the brain's
renderer (`~/.claude/tools/deck.py`) does the design: 16 slide types, a clean or a bold style, a look of its own per deck
(layouts, palette, fonts), 41 line icons as editable shapes, native charts (target lines, labelled series, doughnut
totals) and tables (status colours, heat, totals), the company template when given, and checks that report what does not
fit.

- MCP server `deck`: `deck_guide`, `deck_build`, `deck_read`, `deck_icons`, `deck_deliver`
- skill `make-deck`: the workflow and the design rules
- agent `deck-designer`: builds a whole deck in its own context from the facts it is given
- command `/presentations:deck <topic or file>`

Needs the storage brain's tools (`brain/install.sh` or the multi-user installer) and python-pptx in the devtools venv.
Decks land in `~/storage-reports/<date>-<title>/`.
