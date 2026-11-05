# presentations

Designed, editable PowerPoint decks on an offline VM. Claude writes the content as a short JSON outline; the brain's
renderer (`~/.claude/tools/deck.py`) does the design: 21 slide types (among them an executive summary, a status board,
a boxes-and-arrows diagram, a 2x2 matrix and before / after), a clean or a bold style, a look of its own per deck
(layouts, palette, fonts) or a premium theme (executive, ivory, noir), line icons as editable shapes, native charts (target
lines, labelled series, callouts on a point, doughnut totals), sparklines under numbers, tables (status colours, heat,
totals), fade transitions, speaker notes from each slide's text, Hebrew right to left, the company template when given,
story plans for recurring decks (monthly review, incident review, DR drill, proposal, status update) and checks of the
story and of the layout.

**Real fit check and PDF**: with LibreOffice and poppler-utils on the VM (`dnf install libreoffice-impress poppler-utils`
from the RHEL repository), every deck is drawn once more as it really renders, any text that lands outside its box is
made smaller until it fits, and a PDF copy is kept beside the .pptx. Without them the decks are built the same, the
reply says the check was skipped.

- MCP server `deck`: `deck_guide`, `deck_build`, `deck_read`, `deck_icons`, `deck_deliver`
- skill `make-deck`: the workflow and the design rules
- agent `deck-designer`: builds a whole deck in its own context from the facts it is given
- command `/presentations:deck <topic or file>`

Needs the storage brain's tools (`brain/install.sh` or the multi-user installer) and python-pptx in the devtools venv.
Decks land in `~/storage-reports/<date>-<title>/`.
