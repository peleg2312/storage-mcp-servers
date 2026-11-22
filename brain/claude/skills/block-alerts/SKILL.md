---
name: block-alerts
description: Take storage alerts from any vendor (PowerMax, PowerFlex, ONTAP, PowerScale, VAST, MDS, UCS, ESXi, CSM, Trident...) from the source the user names, explain each from the docs and read-only MCP checks, rate how urgent it is, say what to do, and send a clear HTML summary email to Outlook. Triggers - "block alerts", "summarize these alerts", "alerts report", "send me the alerts by mail", a pasted list of alerts
---
# Block alerts: alerts in, a clear Outlook report out

The user tells you **where the alerts are and how to read them**. You turn them into a short, accurate report and
email it. The email is rendered by the script at the end of this file (Outlook-safe HTML + plain text). **Do not write
the HTML yourself**: fill the JSON (step 5) and run the script.

Never change anything on a system: no acknowledge / clear / delete of alerts, no config change. MCP calls are
read-only (list / get / show). Commands in the report are for the user to run.

## 1. Where the alerts come from (ask only what the user did not say)
| The user says | You do |
|---|---|
| pastes alerts in the chat | use the text as is |
| a file or folder (log, CSV, JSON, syslog, exported .eml / .txt) | read it; a folder: the files they name, or the newest |
| "from the array / switch / MCP" | the MCP of that system, read-only: **powermax** (alerts), **powerflex** (alerts, `get_health` first), **ontap** (EMS events), **mds** (logs), **ucs-central** (faults), Aria Operations (alerts); exact tool names: the tool map |
| a command (e.g. `oc get events`, `journalctl`) | run it only if it is read-only |
Also ask, if not said: **time window** (default: last 24 h) and **which systems** (default: all the source has).
When the user says "always like this", save it in `~/.config/block-alerts/sources.json`
(`{"default": {"source": "...", "how": "...", "window": "24h"}}`) and use it next time without asking.

## 2. Normalize and group
For each alert take: vendor, product, system (array serial / cluster / switch name), object (volume, port, drive,
RDF group, node...), alert ID / event name / code, vendor severity, time, message text.
Group: same system + same code + same object = **one** entry with `count`, `first_seen`, `last_seen`. Same code on
many objects = one entry, objects listed ("4 drives: 0A:12, 0A:13, ..."). Drop exact duplicates.
More than 20 groups: full research for the 20 most urgent; the rest get a one-line explanation (`explain_code` only).

## 3. Research each group (docs first, then the live state)
Follow the **docs-lookup** and **explain-error** skills:
1. Docs MCP `explain_code(<event name / code / KB>)` first (severity, corrective action, KB in one call).
2. Not documented: `search_docs` with the exact message part **in quotes** (drop names, IDs, times), vendor +
   product filter (names: `~/.claude/brain/library/MANIFEST.md`); read the best hit with `read_chunk`. Never
   answer from snippets. Check known bugs / fixed-in version for the installed version.
3. Live state (only for the systems in the report, read-only): is the alert still active or cleared? state of the
   object now (path / port / drive / link / pool %). One or two calls per group, not a full investigation.
4. Write down **sources you actually read** (title + url + version). Nothing found: say "not in the library",
   and label general knowledge as such. Never invent KB numbers, URLs, thresholds or commands.

## 4. How urgent (your priority; the vendor severity is only a starting point)
| Priority | Act by | When |
|---|---|---|
| **P1** Critical | Now | data unavailable or at risk now: pool / SRP / aggregate full or >=95%, array / node / pool offline, host or datastore lost all paths, redundancy fully lost, drive failed with no spare or rebuild failing, DR replication stopped beyond its RPO |
| **P2** High | Today | redundancy lost but service up: one of two directors / nodes / FIs / fabrics / paths / PSUs down, single path left, drive rebuilding, one SRDF / SnapMirror link down, replication lag growing, capacity 85-95%, latency hurting applications, certificate expires in <7 days |
| **P3** Medium | This week | degraded with redundancy intact, capacity 75-85%, repeating non-critical errors, certificate <30 days, config drift |
| **P4** Low | Plan | advisories, firmware notices, cleanup |
| **INFO** | No action | already cleared (checked live), tests, logins / audit events, transient and self-healed |
Raise one level for production impact or many repeats; lower one level when it is cleared (say how you know).
Give a one-line reason (`why`) for each priority.

## 5. Fill the report JSON
Folder: `~/block-alerts/<YYYYmmdd-HHMM>/`; file `report.json`. The mail must fit about one screen: **short**.
- `headline` (the big title and the start of the subject): what matters most + when to act, max ~8
  words, e.g. "SRDF to DR is down — act now", "All clear — 3 informational alerts". Not a generic
  "alerts report" title.
- `summary` 1-2 sentences; `actions` at most 3, one line each.
- Per alert: `what` 1 sentence (+ `impact` 1 sentence), `cause` and `live` one short line each, `why` one line,
  `steps` at most 3 short steps, `commands` at most 2, `sources` at most 2. P3 / P4: `what` + `steps` only.
- INFO alerts are shown as one line at the bottom (title + count): no other fields needed.
- More than 8 non-INFO alerts: the 8 most urgent in full, the rest grouped as one alert per kind
  (e.g. "5 more ports with CRC errors") - the details stay in the chat answer, not the mail. Email language: the language the user writes in (`"lang": "he"` for Hebrew, else `"en"`).
```json
{
  "headline": "SRDF to DR is down — act now",
  "generated": "22 Nov 2026, 18:40", "window": "last 24 h",
  "source": "powermax MCP alerts + MDS syslog",
  "lang": "en",
  "summary": "2-3 sentences: what is going on overall, what is urgent, what is noise.",
  "actions": ["The 1-5 most important things to do first, most urgent first, each one line"],
  "alerts": [{
    "priority": "P1",
    "title": "SRDF group 10 - all links down",
    "vendor": "Dell", "product": "PowerMax", "system": "000197900123", "object": "RDF group 10 (DC2)",
    "code": "SRDF link down (event 1220)", "vendor_severity": "Critical",
    "count": 3, "first_seen": "2026-11-22 09:14", "last_seen": "2026-11-22 09:20", "act_by": "Now",
    "why": "Replication to DR is stopped; RPO is breached while it stays down.",
    "what": "What the alert means, in plain words.",
    "impact": "What is affected now and what happens if nobody acts.",
    "cause": "Most likely causes, most likely first.",
    "steps": ["Step 1 ...", "Step 2 ..."],
    "commands": ["symrdf -sid 123 -rdfg 10 list", "show interface fc1/5"],
    "live": "Checked 18:35: links 10/1 and 10/2 still offline; RDF pairs Partitioned.",
    "known_bug": "",
    "sources": [{"title": "PowerMax Events and Alerts guide - event 1220", "url": "https://..."}]
  }]
}
```
`priority`: P1 / P2 / P3 / P4 / INFO. Empty strings / lists for what you do not have (they are left out of the mail).
`commands`: read-only check commands, or the fix commands the docs give (with `<placeholders>`), never invented.

## 6. Render, check, send
Get the script out of this file once (it is the block between the `# >>>` and `# <<<` lines below):
```bash
S=$(find ~/.claude /opt/paas -path '*block-alerts/SKILL.md' 2>/dev/null | head -1)
mkdir -p ~/.config/block-alerts
sed -n '/^# >>> block_alerts_mail.py v4$/,/^# <<< block_alerts_mail.py$/p' "$S" > ~/.config/block-alerts/block_alerts_mail.py
```
(If `~/.config/block-alerts/block_alerts_mail.py` already starts with `# >>> block_alerts_mail.py v4`, skip this.)
Then, with `M=~/.config/block-alerts/block_alerts_mail.py` and `R=~/block-alerts/<folder>`:
1. `python3 $M $R/report.json --html $R/email.html` - fix any error it prints (it validates the JSON).
2. Show the user in the chat: the subject line, the count per priority, the "do first" list, and the path of
   `email.html` (they can open it to see the mail).
3. Send: `python3 $M $R/report.json --send` (to / cc from `mail.json`; `--to a@x.com,b@x.com` overrides).
   The user said "draft" / "don't send", or there is no mail relay: `--eml $R/alerts.eml` instead - an Outlook
   draft: they open it in Outlook (double-click), check, press Send.
4. Report what happened: sent to whom, or the error. Never claim it was sent unless the script printed `sent`.

### Mail setup (first time only, or when `--send` says mail.json is missing)
Ask the user for: the SMTP relay of the mail server (Exchange / Outlook; e.g. `smtp.corp.local`), port (25, or 587
with STARTTLS), whether it needs a login, the From address, default To and Cc. Write
`~/.config/block-alerts/mail.json`:
```json
{"smtp_host": "smtp.corp.local", "smtp_port": 25, "starttls": false, "ssl": false,
 "user": "", "password_file": "~/.config/block-alerts/smtp.pass", "ca_file": "",
 "from": "storage-alerts@corp.local", "to": ["me@corp.local"], "cc": []}
```
A login is needed: the **user** puts the password in the file themselves - never in the chat, never in mail.json:
`install -m 600 /dev/null ~/.config/block-alerts/smtp.pass && vi ~/.config/block-alerts/smtp.pass`.
An internal CA: its PEM path in `ca_file`. Then `python3 $M --check` (connects and logs in, sends nothing),
and send the first report to the user only (`--to <their address>`) so they see it before others do.

## The script (do not edit; extract it as in step 6)
```python
# >>> block_alerts_mail.py v4
"""block-alerts mail: the alert report JSON -> an Outlook-safe HTML email (+ plain text), standard library only.
  python3 block_alerts_mail.py report.json --html out.html     preview in a browser
  python3 block_alerts_mail.py report.json --eml out.eml       Outlook draft (open it, press Send)
  python3 block_alerts_mail.py report.json --send [--to a,b]   send through the relay in mail.json
  python3 block_alerts_mail.py --check                         test mail.json and the relay, sends nothing"""
import argparse, html, json, os, smtplib, ssl, stat, sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

CONF = os.path.expanduser("~/.config/block-alerts/mail.json")
PRI = {  # priority: (english, hebrew, text colour, background, border, act by)
    "P1": ("Critical", "קריטי", "#B42318", "#FEF3F2", "#FDA29B", "Now"),
    "P2": ("High", "גבוה", "#C4320A", "#FFF4ED", "#F9DBAF", "Today"),
    "P3": ("Medium", "בינוני", "#B54708", "#FFFAEB", "#FEDF89", "This week"),
    "P4": ("Low", "נמוך", "#175CD3", "#EFF8FF", "#B2DDFF", "Plan"),
    "INFO": ("Info", "מידע", "#475467", "#F2F4F7", "#D0D5DD", "No action"),
}
ORDER = list(PRI)
WORDS = {"critical": "P1", "fatal": "P1", "emergency": "P1", "alert": "P1", "high": "P2", "major": "P2",
         "error": "P2", "medium": "P3", "warning": "P3", "minor": "P3", "low": "P4", "notice": "P4"}
T = {
    "en": dict(report="Storage alerts", overview="All alerts", act="Do first", what="What it is",
               impact="Impact", cause="Likely cause", steps="What to do", cmds="Commands", live="Current state",
               bug="Known bug / fixed in", src="Sources", why="Why this priority", system="System", obj="Object",
               code="Alert", vsev="Vendor severity", seen="Seen", count="Count", actby="Act by",
               summary="Summary", now="Now", fix="Fix", also="No action needed", alerts="alerts", alert="alert", more="more", source="Source",
               footer="Prepared by Claude from the alerts, the offline docs and read-only checks. Review each step before you run it."),
    "he": dict(report="התראות אחסון", overview="כל ההתראות", act="לטפל קודם", what="מה זה", impact="השפעה",
               cause="סיבה אפשרית", steps="מה לעשות", cmds="פקודות", live="מצב נוכחי", bug="באג ידוע / תוקן בגרסה",
               src="מקורות", why="למה העדיפות הזו", system="מערכת", obj="רכיב", code="התראה", vsev="חומרת יצרן",
               seen="נראה", count="כמות", actby="לטפל עד", summary="סיכום", now="עכשיו", fix="תיקון", also="לא נדרשת פעולה", alerts="התראות", alert="התראה", more="נוספות",
               source="מקור",
               footer="הוכן על ידי Claude ממקור ההתראות, ספריית התיעוד הלא מקוונת ובדיקות לקריאה בלבד. "
                      "הפקודות מיועדות להרצה על ידך: בדוק כל צעד לפני שינוי."),
}
ACT_HE = {"Now": "מיד", "Today": "היום", "This week": "השבוע", "Plan": "לתכנן", "No action": "ללא פעולה"}
F = "font-family:'Segoe UI',Calibri,Arial,Helvetica,sans-serif;"
MONO = "font-family:Consolas,'Courier New',monospace;"
TBL = 'role="presentation" cellpadding="0" cellspacing="0" border="0"'


def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def br(s):
    return e(s).replace("\n", "<br>")


def prio(a):
    p = str(a.get("priority") or "").strip().upper()
    if p in PRI:
        return p
    return WORDS.get(p.lower(), "INFO") if p else WORDS.get(str(a.get("vendor_severity", "")).lower(), "INFO")


def load(path):
    try:
        r = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as x:
        sys.exit(f"report JSON: {x}")
    al = r.get("alerts")
    if not isinstance(al, list) or not al:
        sys.exit("report JSON: 'alerts' must be a non-empty list")
    for i, a in enumerate(al):
        if not isinstance(a, dict) or not a.get("title"):
            sys.exit(f"report JSON: alert {i + 1} needs a 'title'")
        a["priority"] = prio(a)
        for k in ("steps", "commands", "sources"):
            v = a.get(k) or []
            a[k] = [v] if isinstance(v, (str, dict)) else list(v)
    al.sort(key=lambda a: ORDER.index(a["priority"]))
    r["lang"] = "he" if str(r.get("lang", "")).lower().startswith("he") else "en"
    r["actions"] = [x for x in (r.get("actions") or []) if x]
    return r


def label(p, lang):
    return PRI[p][1] if lang == "he" else PRI[p][0]


def actby(a, lang):
    v = a.get("act_by") or PRI[a["priority"]][5]
    return ACT_HE.get(v, v) if lang == "he" else v


def pill(p, lang, text_=None):
    _, _, fg, bg, bd, _ = PRI[p]
    txt = e(text_) if text_ else (e(label(p, lang)) if p == "INFO" else f"{p} {e(label(p, lang))}")
    return (f'<table {TBL}><tr><td bgcolor="{bg}" style="{F}font-size:13px;line-height:18px;'
            f'mso-line-height-rule:exactly;font-weight:700;color:{fg};padding:3px 10px;border:1px solid {bd};'
            f'border-radius:10px;white-space:nowrap">{txt}</td></tr></table>')


def nlist(items, colour, al, size=15):
    """numbered list with a hanging indent: wrapped lines stay under the text, not under the number"""
    num = "padding:0 0 0 8px" if al == "right" else "padding:0 8px 0 0"
    return f'<table {TBL} width="100%">' + "".join(
        f'<tr><td width="18" valign="top" align="{al}" style="{F}font-size:{size}px;line-height:22px;'
        f'mso-line-height-rule:exactly;font-weight:700;color:{colour};{num}">{i}.</td>'
        f'<td valign="top" align="{al}" style="{F}font-size:{size}px;line-height:22px;mso-line-height-rule:exactly;'
        f'color:#101828;padding:0 0 4px 0">{br(x)}</td></tr>' for i, x in enumerate(items, 1)) + "</table>"


def row(label_, body, al):
    """a label column and a value column: the eye scans the labels, reads the values"""
    lp = "padding:9px 0 0 12px" if al == "right" else "padding:9px 12px 0 0"
    return (f'<tr><td width="96" valign="top" align="{al}" class="lbl" style="{F}font-size:13px;line-height:22px;'
            f'mso-line-height-rule:exactly;font-weight:600;color:#667085;{lp}">{e(label_)}</td>'
            f'<td valign="top" align="{al}" class="val" style="{F}font-size:15px;line-height:22px;'
            f'mso-line-height-rule:exactly;color:#101828;padding:9px 0 0 0">{body}</td></tr>')


def card(a, t, lang, al, op):
    p = a["priority"]
    fg, bg = PRI[p][2], PRI[p][3]
    n = str(a.get("count") or "")
    parts = [e(" ".join(filter(None, [a.get("product"), a.get("system")]))), e(a.get("object")),
             f"&times;{e(n)}" if n not in ("", "0", "1") else "", e(a.get("last_seen") or a.get("first_seen"))]
    sub = " &middot; ".join(f'<span style="white-space:nowrap">{x}</span>' for x in parts if x)
    rows = ""
    what = " ".join(x for x in (a.get("what"), a.get("impact")) if x)
    if what:
        rows += row(t["what"], br(what), al)
    if a.get("cause"):
        rows += row(t["cause"], br(a["cause"]), al)
    if a.get("live"):
        rows += row(t["now"], br(a["live"]), al)
    if a["steps"]:
        rows += row(t["fix"], nlist(a["steps"], fg, al), al)
    if a.get("known_bug"):
        rows += row(t["bug"], br(a["known_bug"]), al)
    extra = ""
    if a["commands"]:
        cmd = "<br>".join(e(c).replace("\n", "<br>") for c in a["commands"])
        extra += (f'<tr><td style="padding:10px 0 0 0"><table {TBL} width="100%"><tr><td bgcolor="#F4F5F7" dir="ltr" '
                  f'align="left" style="{MONO}font-size:13px;line-height:20px;mso-line-height-rule:exactly;'
                  f'color:#1D2939;padding:10px 12px;border:1px solid #E4E7EC;border-radius:6px">{cmd}</td></tr></table>'
                  f'</td></tr>')
    if a["sources"]:
        items = []
        for s in a["sources"]:
            s = s if isinstance(s, dict) else {"title": s}
            u, name = str(s.get("url") or ""), e(s.get("title") or s.get("url") or "")
            items.append(f'<a href="{e(u)}" style="color:#175CD3;text-decoration:underline">{name}</a>'
                         if u.startswith(("http://", "https://")) else name)
        extra += (f'<tr><td align="{al}" style="{F}font-size:13px;line-height:19px;color:#667085;padding:10px 0 0 0">'
                  f'{e(t["src"])}: ' + " &middot; ".join(items) + "</td></tr>")
    why = (f'<tr><td style="padding:10px 0 2px 0"><table {TBL} width="100%"><tr><td bgcolor="{bg}" align="{al}" '
           f'style="{F}font-size:14px;line-height:21px;mso-line-height-rule:exactly;color:{fg};font-weight:600;'
           f'padding:8px 12px;border-radius:6px">{br(a["why"])}</td></tr></table></td></tr>') if a.get("why") else ""
    tag = (label(p, lang) if p == "INFO" else f"{p} {label(p, lang)}").upper()
    side = "border-right" if al == "right" else "border-left"
    return (f'<table {TBL} width="100%" bgcolor="#FFFFFF"><tr><td valign="top" class="cp" bgcolor="#FFFFFF" '
            f'style="padding:16px 18px 18px 18px;border:1px solid #E4E7EC;{side}:5px solid {fg};border-radius:8px">'
            f'<table {TBL} width="100%">'
            f'<tr><td align="{al}" style="{F}font-size:12px;line-height:16px;mso-line-height-rule:exactly;'
            f'font-weight:700;letter-spacing:0.6px;color:{fg}">{e(tag)} &nbsp;&middot;&nbsp; {e(actby(a, lang)).upper()}</td></tr>'
            f'<tr><td align="{al}" style="{F}font-size:18px;line-height:24px;mso-line-height-rule:exactly;'
            f'font-weight:700;color:#101828;padding:5px 0 0 0">{e(a["title"])}</td></tr>'
            f'<tr><td align="{al}" style="{F}font-size:13px;line-height:19px;color:#667085;padding:3px 0 0 0">{sub}</td></tr>'
            f'{why}<tr><td><table {TBL} width="100%">{rows}</table></td></tr>{extra}</table></td></tr></table>')


def counts(r):
    c = {p: 0 for p in ORDER}
    for a in r["alerts"]:
        c[a["priority"]] += 1
    return c


def headline(r):
    a = r["alerts"][0]
    return r.get("headline") or (a["title"] + ("" if a["priority"] == "INFO" else f" \u2014 {actby(a, r['lang'])}"))


def systems(r):
    seen = []
    for a in r["alerts"]:
        x = " ".join(filter(None, [a.get("product"), a.get("system")]))
        if x and x not in seen:
            seen.append(x)
    return seen


def subject(r):
    al, lang = r["alerts"], r["lang"]
    top, c = al[0]["priority"], counts(r)
    tag = top if top != "INFO" else label(top, lang)
    real = ", ".join(f"{c[p]} {label(p, lang)}" for p in ORDER[:-1] if c[p])
    return f"{tag} \u00b7 {headline(r)} \u00b7 {len(al)} {T[lang]['alerts'] if len(al) != 1 else T[lang]['alert']}" + (f" ({real})" if real else "")


def render(r):
    lang = r["lang"]
    t, rtl = T[lang], lang == "he"
    al, op, d = ("right", "left", "rtl") if rtl else ("left", "right", "ltr")
    c, top = counts(r), r["alerts"][0]["priority"]
    status = " &middot; ".join(f"{c[p]} {e(label(p, lang))}" for p in ORDER if c[p])
    act = [a for a in r["alerts"] if a["priority"] != "INFO"]
    info = [a for a in r["alerts"] if a["priority"] == "INFO"]
    blocks = []
    if r.get("summary"):
        blocks.append(f'<tr><td class="px" align="{al}" style="padding:18px 24px 0 24px;{F}font-size:16px;'
                      f'line-height:25px;mso-line-height-rule:exactly;color:#101828">{br(r["summary"])}</td></tr>')
    if r["actions"]:
        fg, bg, bd = PRI[top][2], PRI[top][3], PRI[top][4]
        blocks.append(f'<tr><td class="px" style="padding:18px 24px 0 24px"><table {TBL} width="100%"><tr>'
                      f'<td bgcolor="{bg}" class="cp" style="padding:14px 18px 12px 18px;border:1px solid {bd};border-radius:8px">'
                      f'<p style="margin:0 0 8px 0;{F}font-size:12px;line-height:16px;font-weight:700;letter-spacing:0.6px;'
                      f'color:{fg}">{e(t["act"]).upper()}</p>{nlist(r["actions"], fg, al, 16)}</td></tr></table></td></tr>')
    for a in act:
        blocks.append(f'<tr><td class="px" style="padding:16px 24px 0 24px">{card(a, t, lang, al, op)}</td></tr>')
    if info:
        names = " &middot; ".join(e(a["title"]) + (f" (&times;{e(a['count'])})" if a.get("count") else "")
                                  for a in info)
        blocks.append(f'<tr><td class="px" align="{al}" style="padding:18px 24px 0 24px;{F}font-size:14px;'
                      f'line-height:21px;color:#475467"><b style="color:#344054">{e(t["also"])}:</b> {names}</td></tr>')
    pre = e(f'{len(r["alerts"])} {t["alerts"]}: ' + " · ".join(f"{c[p]} {label(p, lang)}" for p in ORDER if c[p])
            + " - " + " | ".join(r["actions"][:2] or [r["alerts"][0]["title"]]))
    kicker = " &middot; ".join(f'<span dir="auto" style="unicode-bidi:isolate">{e(x)}</span>'
                               for x in (t["report"].upper(), r.get("generated"), r.get("window")) if x)
    chips = "".join(f'<td style="padding:{"0 0 6px 6px" if rtl else "0 6px 6px 0"}">{pill(p, lang, f"{c[p]} {label(p, lang)}")}</td>'
                    for p in ORDER if c[p])
    sysline = " &middot; ".join(f'<span style="white-space:nowrap">{e(x)}</span>' for x in systems(r)[:6])
    return f'''<!DOCTYPE html>
<html lang="{lang}" dir="{d}" xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting"><meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark">
<title>{e(subject(r))}</title>
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
<style>@media only screen and (max-width:520px){{.px{{padding-left:12px!important;padding-right:12px!important}}.cp{{padding-left:14px!important;padding-right:14px!important}}.h1{{font-size:22px!important;line-height:28px!important}}.lbl,.val{{display:block!important;width:100%!important}}.lbl{{padding:10px 0 0 0!important;line-height:18px!important}}.val{{padding:1px 0 0 0!important}}}}</style>
</head>
<body dir="{d}" style="margin:0;padding:0;background-color:#F2F4F7;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;font-size:1px;line-height:1px;color:#F2F4F7">{pre}&#8203;&nbsp;&#8203;&nbsp;&#8203;&nbsp;&#8203;&nbsp;</div>
<table {TBL} width="100%" bgcolor="#F2F4F7" dir="{d}"><tr><td align="center" class="px" style="padding:16px 8px">
<!--[if mso]><table {TBL} width="640" align="center"><tr><td><![endif]-->
<table {TBL} width="100%" dir="{d}" style="max-width:640px" bgcolor="#FFFFFF">
<tr><td bgcolor="{PRI[top][2]}" height="5" style="font-size:0;line-height:0;mso-line-height-rule:exactly;height:5px">&nbsp;</td></tr>
<tr><td class="px" align="{al}" style="padding:22px 24px 0 24px">
<p style="margin:0;{F}font-size:12px;line-height:16px;mso-line-height-rule:exactly;font-weight:600;letter-spacing:0.5px;color:#667085">{kicker}</p>
<p class="h1" style="margin:8px 0 12px 0;{F}font-size:26px;line-height:32px;mso-line-height-rule:exactly;font-weight:700;color:#101828">{e(headline(r))}</p>
<table {TBL} align="{al}"><tr>{chips}</tr></table>
<p style="clear:both;margin:4px 0 0 0;{F}font-size:13px;line-height:19px;color:#667085">{sysline}</p></td></tr>
{"".join(blocks)}
<tr><td class="px" align="{al}" style="padding:22px 24px 22px 24px;{F}font-size:12px;line-height:18px;color:#98A2B3">{(e(t["source"]) + ": " + e(r["source"]) + "<br>") if r.get("source") else ""}{e(t["footer"])}</td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table></body></html>'''


def text(r):
    t, lang = T[r["lang"]], r["lang"]
    c = counts(r)
    out = [headline(r), "=" * 60, " | ".join(x for x in (t["report"], r.get("generated"), r.get("window")) if x),
           " · ".join(systems(r)),
           " · ".join(f"{c[p]} {label(p, lang)}" for p in ORDER if c[p]), ""]
    if r.get("summary"):
        out += [t["summary"].upper(), r["summary"], ""]
    if r["actions"]:
        out += [t["act"].upper()] + [f"  {i}. {x}" for i, x in enumerate(r["actions"], 1)] + [""]
    for a in r["alerts"]:
        out += ["-" * 60, f"[{a['priority']} {label(a['priority'], lang)}] {a['title']}",
                " · ".join(str(x) for x in (a.get("vendor"), a.get("product"), a.get("system"), a.get("object")) if x),
                f"{t['actby']}: {actby(a, lang)}" + (f"   {t['count']}: {a['count']}" if a.get("count") else "")]
        for k in ("why", "what", "impact", "cause", "live", "known_bug"):
            if a.get(k):
                out.append(f"{t[{'known_bug': 'bug'}.get(k, k)]}: {a[k]}")
        if a["steps"]:
            out += [t["steps"] + ":"] + [f"  {i}. {x}" for i, x in enumerate(a["steps"], 1)]
        if a["commands"]:
            out += [t["cmds"] + ":"] + [f"    {x}" for x in a["commands"]]
        for s in a["sources"]:
            s = s if isinstance(s, dict) else {"title": s}
            out.append(f"  - {s.get('title', '')} {s.get('url', '')}".rstrip())
        out.append("")
    return "\n".join(out + [t["footer"]])


def conf():
    try:
        c = json.load(open(CONF, encoding="utf-8"))
    except (OSError, ValueError) as x:
        sys.exit(f"{CONF}: {x} - set up the mail first (see the block-alerts skill, 'Mail setup')")
    for k in ("smtp_host", "from"):
        if not c.get(k):
            sys.exit(f"{CONF}: '{k}' is missing")
    return c


def connect(c):
    host, port = c["smtp_host"], int(c.get("smtp_port") or 25)
    ctx = ssl.create_default_context()
    if c.get("ca_file"):
        ctx.load_verify_locations(os.path.expanduser(c["ca_file"]))
    s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) if c.get("ssl") else smtplib.SMTP(host, port, timeout=30)
    s.ehlo()
    if c.get("starttls") and not c.get("ssl"):
        s.starttls(context=ctx)
        s.ehlo()
    if c.get("user"):
        pf = os.path.expanduser(c.get("password_file") or "~/.config/block-alerts/smtp.pass")
        if os.stat(pf).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            sys.exit(f"{pf} must be readable by you only: chmod 600 {pf}")
        s.login(c["user"], open(pf, encoding="utf-8").read().strip())
    return s


def message(r, c, to, cc):
    m = EmailMessage()
    m["Subject"] = subject(r)
    m["From"] = c.get("from", "")
    if to:
        m["To"] = ", ".join(to)
    if cc:
        m["Cc"] = ", ".join(cc)
    m["Date"] = formatdate(localtime=True)
    m["Message-ID"] = make_msgid(domain=(c.get("from", "x@block-alerts").split("@")[-1].strip("> ") or "block-alerts"))
    if r["alerts"][0]["priority"] == "P1":
        m["X-Priority"], m["Importance"] = "1", "High"
    m.set_content(text(r))
    m.add_alternative(render(r), subtype="html")
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", nargs="?")
    ap.add_argument("--html")
    ap.add_argument("--eml")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--to")
    ap.add_argument("--cc")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        c = conf()
        s = connect(c)
        s.noop()
        s.quit()
        print(f"ok: {c['smtp_host']}:{c.get('smtp_port') or 25} accepts the connection"
              + (" and the login" if c.get("user") else "") + "; nothing was sent")
        return
    if not a.report or not (a.html or a.eml or a.send):
        ap.error("give report.json and at least one of --html / --eml / --send")
    r = load(a.report)
    print("subject:", subject(r))
    if a.html:
        open(a.html, "w", encoding="utf-8").write(render(r))
        print("html:", os.path.abspath(a.html))
    if a.eml or a.send:
        c = conf() if (a.send or os.path.exists(CONF)) else {}
        split = lambda v: [x.strip() for x in v.split(",") if x.strip()]
        to = split(a.to) if a.to else list(c.get("to") or [])
        cc = split(a.cc) if a.cc else ([] if a.to else list(c.get("cc") or []))
        if a.eml:
            m = message(r, c, to, cc)
            m["X-Unsent"] = "1"  # Outlook opens it as a draft, ready to send
            open(a.eml, "wb").write(bytes(m))
            print("eml:", os.path.abspath(a.eml), "(open it in Outlook, check, press Send)")
        if a.send:
            if not to:
                sys.exit("no recipient: 'to' in mail.json or --to")
            s = connect(c)
            refused = s.send_message(message(r, c, to, cc))
            s.quit()
            ok = [x for x in to + cc if x not in refused]
            print("sent to:", ", ".join(ok) if ok else "nobody")
            if refused:
                sys.exit(f"refused by the server: {refused}")


if __name__ == "__main__":
    try:
        main()
    except (smtplib.SMTPException, OSError) as x:
        sys.exit(f"mail error: {type(x).__name__}: {x}")
# <<< block_alerts_mail.py
```
