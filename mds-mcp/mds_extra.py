"""
Extra read-only tools for the MDS MCP server (registered on the upstream `main.mcp`):

  run_show            any single `show` command; JSON when the switch supports it, otherwise text
                      (NX-API `cli_ascii`), with grep / tail filtering and a size cap
  show_logging_onboard  OBFL (onboard failure logging): error-stats, txwait, rxwait, credit-loss,
                      datarate, ... per switch and optionally per module
  get_log_events      syslog parsed into structured events (time, severity, facility, mnemonic,
                      interface) with filters and a summary, across one or all switches
  slow_drain_check    one-call congestion bundle: OBFL txwait/rxwait/credit-loss/error-stats,
                      port-monitor policy, and a parsed error/warning log summary

All commands go through the same strict validator as the upstream tools (a single `show`
command, no ; | > ` or newlines). NX-API errors are translated into plain explanations.
"""

import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import main

TIMEOUT = 60
MAX_CHARS_DEFAULT = 60000

# Commands that are slow or huge on a production switch; refuse with an explanation.
_HEAVY = re.compile(r"^show\s+(tech-?support|techsupport)\b", re.I)


class NxapiError(Exception):
    pass


def _explain(err: dict, cmd: str, switch: str) -> str:
    msg = " ".join(str(x) for x in (err.get("message"), (err.get("data") or {}).get("msg")) if x).strip()
    low = msg.lower()
    if "permission" in low or "not authorized" in low or "authorization" in low:
        return (f"{switch}: the switch account's role is not allowed to run '{cmd}'. Add it to the "
                f"read-only role (e.g. `rule N permit show ...`) or use network-operator. Detail: {msg}")
    if "invalid command" in low or "incomplete command" in low or "ambiguous" in low:
        return (f"{switch}: '{cmd}' is not valid on this switch's NX-OS version/model. Check the syntax "
                f"(e.g. section names) and try a related command. Detail: {msg}")
    if "structured output" in low or "unsupported" in low:
        return f"{switch}: '{cmd}' has no JSON output on this switch; use output='text'. Detail: {msg}"
    return f"{switch}: NX-API error for '{cmd}': {msg or err}"


def _post(name: str, cfg: dict, cmd: str, method: str):
    payload = [{"jsonrpc": "2.0", "method": method, "params": {"cmd": cmd, "version": 1.2}, "id": 1}]
    try:
        r = main.requests.post(cfg["url"], json=payload, headers={"content-type": "application/json-rpc"},
                               auth=(cfg["username"], cfg["password"]), timeout=TIMEOUT,
                               verify=cfg["verify_ssl"])
    except Exception as e:
        raise NxapiError(f"{name}: cannot reach NX-API at {cfg['url']} ({e.__class__.__name__}: {e}). "
                         "Check network path/firewall and that `feature nxapi` is enabled.") from None
    if r.status_code == 401:
        raise NxapiError(f"{name}: login refused (HTTP 401) - wrong username/password for the MCP account.")
    try:
        data = r.json()
    except Exception:
        raise NxapiError(f"{name}: unexpected HTTP {r.status_code} from NX-API: {r.text[:300]}") from None
    if isinstance(data, list):
        data = data[0] if data else {}
    if "error" in data:
        raise NxapiError(_explain(data["error"], cmd, name))
    if r.status_code >= 400:
        raise NxapiError(f"{name}: HTTP {r.status_code} from NX-API: {r.text[:300]}")
    return data.get("result") or {}


def nxapi(switch, cmd: str, output: str = "auto"):
    """Run one validated show command. Returns (switch_name, kind, payload) where kind is
    'json' (dict) or 'text' (str)."""
    name, cfg = main._resolve_switch(switch or None)
    cmd = main._validate_command(cmd)
    if _HEAVY.match(cmd):
        raise ValueError("show tech-support is too heavy to run through MCP (minutes of CPU and MBs of "
                         "output). Use specific show commands, or collect it from the CLI.")
    if output == "text":
        res = _post(name, cfg, cmd, "cli_ascii")
        return name, "text", res.get("msg", "") if isinstance(res, dict) else str(res)
    try:
        res = _post(name, cfg, cmd, "cli")
    except NxapiError as e:
        if output == "auto" and ("no JSON output" in str(e) or "structured" in str(e).lower()):
            res = _post(name, cfg, cmd, "cli_ascii")
            return name, "text", res.get("msg", "") if isinstance(res, dict) else str(res)
        raise
    if isinstance(res, dict) and res.get("body") not in (None, "", {}):
        body = res["body"]
        if isinstance(body, str):
            return name, "text", body
        return name, "json", body
    if isinstance(res, dict) and "msg" in res:
        return name, "text", res["msg"]
    if output == "auto":  # empty JSON body: some commands only have text output
        res = _post(name, cfg, cmd, "cli_ascii")
        return name, "text", res.get("msg", "") if isinstance(res, dict) else str(res)
    return name, "json", res


def _filter_text(text: str, grep: str, tail_lines: int, max_chars: int):
    lines = text.splitlines()
    total = len(lines)
    if grep:
        try:
            rx = re.compile(grep, re.I)
        except re.error as e:
            raise ValueError(f"Invalid grep regex: {e}") from None
        lines = [ln for ln in lines if rx.search(ln)]
    if tail_lines and tail_lines > 0:
        lines = lines[-int(tail_lines):]
    out = "\n".join(lines)
    truncated = False
    max_chars = max(1000, min(int(max_chars), 500000))
    if len(out) > max_chars:
        out, truncated = out[-max_chars:], True
    return out, {"total_lines": total, "returned_lines": len(lines), "truncated_to_last_chars": truncated}


def _switches(switch: str):
    return [switch] if switch else sorted(main.SWITCHES)


def _fan_out(switch, fn):
    names = _switches(switch)
    results, errors = {}, {}
    with ThreadPoolExecutor(max_workers=min(8, len(names))) as ex:
        futs = {n: ex.submit(fn, n) for n in names}
    for n, f in futs.items():
        try:
            results[n] = f.result()
        except Exception as e:
            errors[n] = str(e)
    return results, errors


# ---------------------------------------------------------------------------
# Syslog parsing
# ---------------------------------------------------------------------------

_SEV_NAMES = {0: "emergency", 1: "alert", 2: "critical", 3: "error", 4: "warning",
              5: "notification", 6: "informational", 7: "debugging"}
_LOG_RE = re.compile(
    r"^(?P<ts>\d{4}\s+[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
    r"(?P<host>\S+)\s+(?:(?P<proc>[^%]*?)\s+)?"
    r"%(?P<fac>[A-Z0-9_]+)(?:-(?P<slot>(?:SLOT|MOD|LC)\d+))?-(?P<sev>[0-7])-(?P<mnem>[A-Z0-9_\-]+):\s*(?P<msg>.*)$")
_IFACE_RE = re.compile(r"\b(fc\d+/\d+(?:/\d+)?|port-channel\s?\d+|san-port-channel\s?\d+|mgmt0|vfc\d+)\b", re.I)
_VSAN_RE = re.compile(r"\bVSAN\s*[:%$]*\s*(\d{1,4})\b", re.I)


def _parse_ts(s: str):
    s = re.sub(r"\s+", " ", s.strip())
    for fmt in ("%Y %b %d %H:%M:%S.%f", "%Y %b %d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def parse_log(text: str):
    events, unparsed = [], 0
    for line in text.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        m = _LOG_RE.match(line)
        if not m:
            if events and line.startswith((" ", "\t")):  # continuation line
                events[-1]["message"] += " " + line.strip()
            else:
                unparsed += 1
            continue
        msg = m.group("msg").replace("%$", "").strip()
        sev = int(m.group("sev"))
        events.append({
            "time": m.group("ts"), "_dt": _parse_ts(m.group("ts")),
            "severity": sev, "severity_name": _SEV_NAMES[sev],
            "facility": m.group("fac"), "mnemonic": m.group("mnem"),
            "slot": m.group("slot"),
            "event": f"{m.group('fac')}-{sev}-{m.group('mnem')}",
            "interfaces": sorted({i.lower().replace(" ", "") for i in _IFACE_RE.findall(msg)}),
            "vsan": (_VSAN_RE.search(msg) or [None, None])[1],
            "message": msg,
        })
    return events, unparsed


def _switch_now(switch: str):
    """Switch clock (so 'last N hours' is relative to the switch's own time zone)."""
    try:
        _, _, txt = nxapi(switch, "show clock", output="text")
    except Exception:
        return None
    m = re.search(r"(\d{2}:\d{2}:\d{2})(?:\.\d+)?\s+\S+\s+\w{3}\s+(\w{3})\s+(\d{1,2})\s+(\d{4})", txt or "")
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(4)} {m.group(2)} {m.group(3)} {m.group(1)}", "%Y %b %d %H:%M:%S")
    except ValueError:
        return None


def register(mcp, RO):
    @mcp.tool(annotations=RO)
    def run_show(command: str, switch: str = "", output: str = "auto", grep: str = "",
                 tail_lines: int = 0, max_chars: int = MAX_CHARS_DEFAULT) -> dict:
        """Run ANY single read-only `show` command on a switch, for anything the dedicated tools
        don't cover (e.g. "show logging onboard error-stats", "show port-monitor",
        "show interface fc1/5 counters detailed", "show rdp fcid 0x010203 vsan 100",
        "show system internal ...", "show fcs ie", "show topology").

        output: "auto" (JSON if the switch supports it, else text), "json" or "text".
        grep: case-insensitive regex; keep only matching text lines (instead of `| include`).
        tail_lines: keep only the last N lines. max_chars caps the size (keeps the end).
        Pipes, `;`, redirection and `show tech-support` are refused. Read-only by construction.
        """
        if output not in ("auto", "json", "text"):
            raise ValueError("output must be auto, json or text")
        name, kind, payload = nxapi(switch, command, output)
        if kind == "json":
            return {"switch": name, "command": command, "format": "json", "body": payload}
        text, stats = _filter_text(payload, grep, tail_lines, max_chars)
        return {"switch": name, "command": command, "format": "text", **stats, "text": text}

    @mcp.tool(annotations=RO)
    def show_logging_onboard(section: str, switch: str = "", module: int = 0, grep: str = "",
                             tail_lines: int = 300, max_chars: int = MAX_CHARS_DEFAULT) -> dict:
        """Onboard Failure Logging (OBFL): persistent per-module history that survives reboots and log
        rotation. Common sections: error-stats (port/ASIC error counters over time), txwait and rxwait
        (time ports waited on B2B credits - slow drain / congestion), credit-loss, datarate
        (high-utilisation periods), interrupt-stats, environmental-history, exception-log,
        obfl-logs, status. Section names vary by model/NX-OS; an invalid one returns a clear error.
        module: line-card/slot number (0 = all / switch default).
        Output is text (OBFL has no JSON). grep/tail_lines filter it; most recent entries are usually
        at the top or bottom depending on the section, so check timestamps.
        """
        sec = re.sub(r"\s+", " ", (section or "").strip().lower())
        if not re.fullmatch(r"[a-z][a-z0-9\-]*( [a-z][a-z0-9\-]*){0,2}", sec):
            raise ValueError("section must be OBFL section words such as 'error-stats', 'txwait', "
                             "'credit-loss', 'flow-control request-timeout'")
        mod = int(module or 0)
        if mod < 0 or mod > 64:
            raise ValueError("module must be 0-64")
        cmd = f"show logging onboard module {mod} {sec}" if mod else f"show logging onboard {sec}"
        name, _, text = nxapi(switch, cmd, output="text")
        text, stats = _filter_text(text or "", grep, tail_lines, max_chars)
        out = {"switch": name, "command": cmd, **stats, "text": text}
        if not text.strip():
            out["note"] = "No OBFL entries for this section (nothing recorded, or OBFL disabled for it)."
        return out

    @mcp.tool(annotations=RO)
    def get_log_events(switch: str = "", last: int = 2000, max_severity: int = 7, since_hours: float = 0,
                       facility: str = "", text: str = "", interface: str = "", limit: int = 200) -> dict:
        """Syslog parsed into structured events, newest first, with a summary - across all switches or one.

        Each event: time (switch clock), severity (0 emergency .. 7 debug) and name, facility, mnemonic,
        event code (e.g. PORT-5-IF_DOWN_LINK_FAILURE), interfaces and VSAN mentioned, message.
        Filters: max_severity (4 = warnings and worse, 3 = errors and worse), since_hours (relative to
        the switch's own clock), facility (e.g. PORT, ZONE, FCNS, PLATFORM), text (regex on message),
        interface (e.g. fc1/5). last = how many log lines to read per switch (max 9999).
        The summary groups by event code and interface so flapping ports and repeated errors stand out.
        """
        n = max(10, min(int(last), 9999))
        sev_max = max(0, min(int(max_severity), 7))
        rx = re.compile(text, re.I) if text else None
        want_if = interface.lower().replace(" ", "") if interface else ""

        def one(sw):
            _, _, txt = nxapi(sw, f"show logging last {n}", output="text")
            events, unparsed = parse_log(txt or "")
            cutoff = None
            if since_hours and since_hours > 0:
                now = _switch_now(sw) or max((e["_dt"] for e in events if e["_dt"]), default=None)
                cutoff = now - timedelta(hours=float(since_hours)) if now else None
            keep = []
            for e in events:
                if e["severity"] > sev_max:
                    continue
                if facility and e["facility"].upper() != facility.upper():
                    continue
                if rx and not rx.search(e["message"]):
                    continue
                if want_if and want_if not in e["interfaces"]:
                    continue
                if cutoff and e["_dt"] and e["_dt"] < cutoff:
                    continue
                keep.append(dict(e, switch=sw))
            return keep, unparsed, len(events)

        res, errors = _fan_out(switch, one)
        events = [e for keep, _, _ in res.values() for e in keep]
        events.sort(key=lambda e: e["_dt"] or datetime.min, reverse=True)
        summary = {
            "by_severity": dict(Counter(e["severity_name"] for e in events)),
            "top_events": [{"event": k, "count": c} for k, c in Counter(e["event"] for e in events).most_common(15)],
            "top_interfaces": [{"interface": f"{s}:{i}", "count": c} for (s, i), c in
                               Counter((e["switch"], i) for e in events for i in e["interfaces"]).most_common(15)],
            "per_switch": {s: {"matched": len(k), "parsed_lines": tot, "unparsed_lines": u}
                           for s, (k, u, tot) in res.items()},
        }
        if events:
            summary["newest"] = events[0]["time"]
            summary["oldest"] = events[-1]["time"]
        lim = max(1, min(int(limit), 2000))
        for e in events:
            e.pop("_dt", None)
        out = {"filters": {"max_severity": sev_max, "since_hours": since_hours, "facility": facility,
                           "text": text, "interface": interface, "lines_read_per_switch": n},
               "total_matching": len(events), "returned": min(lim, len(events)),
               "summary": summary, "events": events[:lim]}
        if errors:
            out["errors"] = errors
        return out

    @mcp.tool(annotations=RO)
    def slow_drain_check(switch: str = "", module: int = 0, tail_lines: int = 80) -> dict:
        """One-call congestion / slow-drain evidence for one or all switches: OBFL txwait, rxwait,
        credit-loss and error-stats (most relevant lines), the port-monitor policy, and a summary of
        warning-or-worse syslog events by interface. Follow up on the interfaces it names with
        show_interface_counters_detailed_for, show_interface_bbcredit_for and the FLOGI database.
        """
        sections = ["txwait", "rxwait", "credit-loss", "error-stats"]

        def one(sw):
            out = {}
            for sec in sections:
                cmd = (f"show logging onboard module {int(module)} {sec}" if module
                       else f"show logging onboard {sec}")
                try:
                    _, _, txt = nxapi(sw, cmd, output="text")
                    t, st = _filter_text(txt or "", "", tail_lines, 20000)
                    out[sec] = {"command": cmd, **st, "text": t or "(no entries)"}
                except Exception as e:
                    out[sec] = {"command": cmd, "error": str(e)}
            try:
                _, _, txt = nxapi(sw, "show port-monitor", output="text")
                out["port_monitor"] = _filter_text(txt or "", "", 200, 20000)[0]
            except Exception as e:
                out["port_monitor"] = {"error": str(e)}
            try:
                _, _, txt = nxapi(sw, "show logging last 3000", output="text")
                ev, _ = parse_log(txt or "")
                bad = [e for e in ev if e["severity"] <= 4]
                out["log_warnings_by_interface"] = [
                    {"interface": i, "count": c} for i, c in
                    Counter(i for e in bad for i in e["interfaces"]).most_common(15)]
                out["log_top_events"] = [{"event": k, "count": c} for k, c in
                                         Counter(e["event"] for e in bad).most_common(10)]
            except Exception as e:
                out["log_summary"] = {"error": str(e)}
            return out

        res, errors = _fan_out(switch, one)
        out = {"switches": res}
        if errors:
            out["errors"] = errors
        return out
