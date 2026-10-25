---
name: report-export
description: Charts, graphs and Excel files from any storage data - throughput / IOPS / latency over time, capacity per array / aggregate / pool, top talkers, any table (unused LUNs, zoning audit, paths) as a formatted .xlsx. Draws a text chart in the answer and writes an HTML report (hover for values) and an Excel workbook with native charts.
when_to_use: Trigger phrases - "graph", "chart", "plot", "trend", "over the last N days", "excel", "xlsx", "spreadsheet", "export", "report I can send", "show me visually"; also offer it after any answer with a time series or a table of more than ~15 rows
---
# Charts and Excel (`~/.claude/tools/report.py`)

One run turns CSV / JSON tables into: **text charts on stdout** (paste them in the answer, in a code block),
**report.html** (every chart, hover for values, data tables) and **report.xlsx** (one sheet per table with a
native Excel chart, plus a Summary sheet), in `~/storage-reports/<date>-<title>/`. No pip install needed.

## 1. Get the data (live MCPs, read-only)
| Wanted | Source |
|---|---|
| ONTAP throughput / IOPS / latency over days (volume, LUN, aggregate, node, FC port) | **harvest**: range query of the metric (`volume_read_data`, `volume_write_data`, `volume_avg_latency`, `lun_*`, `node_cpu_busy`, `fcp_*`; exact names: docs `harvest` "ontap metrics"), step 5m-1h |
| PowerMax (array, storage group, port, director) | **powermax**: `list_performance_metrics` for the names, then `get_performance` with start / end and the keys |
| VM / datastore / ESXi latency, IOPS, capacity, forecasts | **VMware Aria Operations** stats for the resource and time range |
| Capacity now (per array, SRP, aggregate, datastore) | powermax `capacity_report` / `list_srps`, ontap aggregates, kuparashit `ds` sizes |
| Fabric port traffic / errors | mds counters / `port_history` |

Match the step to the range so a series stays under ~3,000 points (10 days → 5-15 min; 90 days → 1 h-1 d).
Never invent or fill missing points: a gap stays empty (blank cell).

## 2. Write the table (CSV, wide)
- First column = x: time (ISO `2026-10-23T14:05:00`, `2026-10-23 14:05`, or epoch s / ms), or a name (aggregate,
  array, host). Every other column = one series of plain numbers (no units inside cells).
- **The file name is the chart title**: `~/storage-reports/<date>-<topic>/aggr1 throughput.csv`.
- One measure per file: MB/s and ms never share a chart (two files → two charts; one axis per chart).
  Up to 8 series per file; more → split (e.g. one file per node) or keep the top 8.
- Read and write as two columns of one file; per-object comparisons as one column per object.
- Convert units first (bytes/s → MB/s, µs → ms) and say which in `--unit`.
Write the CSV with python from the saved MCP output (rule 3: never copy numbers by hand).

## 3. Run
```bash
python3 ~/.claude/tools/report.py "<dir>/aggr1 throughput.csv" "<dir>/aggr1 latency.csv" \
  --title "aggr1 last 10 days" --unit "MB/s,ms" --out "<dir>"
python3 ~/.claude/tools/report.py "<dir>/unused luns.csv" --kind table --title "Unused LUNs" --out "<dir>"
```
`--kind auto` (line for time, horizontal bars for names) | `line` | `area` | `bar` | `table` (Excel + HTML table
only). `--unit` one for all or one per file, comma separated. `--width 100` text chart width.

## Custom Excel (any layout asked for)
Several sheets, formulas, conditional colours, a sheet per array: write a short python script with the bundled
openpyxl (no pip; the wheels import straight from the zip):
```python
import glob, os, sys
sys.path[:0] = glob.glob(os.path.expanduser("~/.claude/tools/vendor/*.whl"))
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill
```
Data from saved MCP output only (rule 3); numbers as numbers (not text), dates as datetimes; bold header,
`ws.freeze_panes = "A2"`, `ws.auto_filter.ref = ws.dimensions`, column widths; totals as formulas
(`=SUM(C2:C40)`); status colours (red / amber) by `CellIsRule`, with the value in the cell too. Save under
`~/storage-reports/<date>-<topic>/` (no spaces in the folder name), then deliver it:
`python3 ~/.claude/tools/report.py --send <file>`.

## 4. Answer
Answer first, then each text chart **in a code block exactly as printed**, then its min / avg / max (with the
time of max) / last line, then what the chart shows (peaks, daily pattern, step changes, a trend toward a
limit) and the files, each as a Markdown link to its full path, e.g.
`[report.xlsx](~/storage-reports/2026-10-25-volumes/report.xlsx)`: in the web UI that link gets a Download button.
The user works from a Windows PC over SSH or in the web UI. Every run (and `--send`) queues the folder for `get-reports.ps1`: if it runs on the PC, the report opens
there by itself (Downloads\storage-reports). **End with the "to the PC" line exactly as printed**, in its own
code block: pasted into PowerShell it copies the folder into Downloads and opens the report. First time: say
`get-reports.ps1` can do this automatically and give its one-time setup (the comment at the top of
`~/.claude/tools/get-reports.ps1`, with the user and VM address filled in).
Name the source and the time range of the data (MCP + object + step), and anything missing (gaps, an
array that did not answer).
