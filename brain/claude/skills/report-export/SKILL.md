---
name: report-export
description: Charts, graphs and Excel files from any storage data - throughput / IOPS / latency over time, capacity per array / aggregate / pool, top talkers, any table (unused LUNs, zoning audit, paths) as a formatted .xlsx. Draws a text chart in the answer and writes an HTML report (hover for values) and an Excel workbook with native charts. Triggers - "graph", "chart", "plot", "trend", "over the last N days", "excel", "xlsx", "export", "report I can send"
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
| Capacity now (per array, SRP, aggregate, datastore) | powermax `list_srps`, ontap aggregates, kuparashit `ds` sizes |
| Fabric port traffic / errors | mds `show_interface_counters_detailed_for` / `get_log_events` |

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
Answer first; then each text chart in a code block exactly as printed, min / avg / max (time of max) / last, what
it shows (peaks, daily pattern, trend toward a limit); the files as Markdown links to their full paths (web UI:
Download button); the final "to the PC" line of report.py in its own code block. Name source, object, step and
gaps. First run for a user: point to the setup comment at the top of `~/.claude/tools/get-reports.ps1`.
