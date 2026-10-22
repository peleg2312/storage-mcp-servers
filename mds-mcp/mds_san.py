"""
SAN troubleshooting composites for the MDS MCP server.

They read the stable NX-OS text output of flogi / fcns / device-alias / zoneset / port-channel /
interface commands (via mds_extra.nxapi, text mode) and turn it into structured answers:

  trace_wwpn          one WWPN across all switches: FLOGI, FCNS, aliases, active zones with the
                      other members and their login state, the login port's health, warnings
  zone_check          are two WWPNs/aliases zoned together in an active zoneset, per fabric/VSAN
  port_channel_health members, state, speed, trunk VSANs, B2B credits and error counters per member
  scan_port_errors    every interface with non-zero error/discard/credit counters, ranked
  flogi_summary       logins per interface and VSAN (shows which port-channels carry the UCS FIs)

Every command is a single `show` that goes through the same validator as all other tools.
Parsed results always include the raw matching lines, so the model can double-check the parsing.
"""

import re
from collections import Counter, defaultdict

from mds_extra import nxapi, _fan_out

WWN_RE = re.compile(r"\b([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){7})\b")
IFACE = r"(?:fc\d+/\d+(?:/\d+)?|port-channel\s?\d+|san-port-channel\s?\d+|vfc\d+|fcip\d+)"


def norm_wwn(w: str) -> str:
    h = re.sub(r"[^0-9a-fA-F]", "", w or "").lower()
    if len(h) != 16:
        raise ValueError(f"Not a WWN: {w!r} (need 16 hex digits)")
    return ":".join(h[i:i + 2] for i in range(0, 16, 2))


def _txt(switch, cmd):
    return nxapi(switch, cmd, output="text")[2] or ""


# ---------------------------------------------------------------------------
# Parsers for stable NX-OS text output
# ---------------------------------------------------------------------------

def parse_flogi(text):
    rows, last = [], None
    rx = re.compile(rf"^\s*({IFACE})\s+(\d+)\s+(0x[0-9a-fA-F]+)\s+([0-9a-fA-F:]{{23}})\s+([0-9a-fA-F:]{{23}})")
    for line in text.splitlines():
        m = rx.match(line)
        if m:
            last = {"interface": m.group(1).replace(" ", ""), "vsan": int(m.group(2)), "fcid": m.group(3).lower(),
                    "pwwn": m.group(4).lower(), "nwwn": m.group(5).lower(), "alias": None}
            rows.append(last)
            continue
        a = re.match(r"^\s+\[([^\]]+)\]\s*$", line)
        if a and last and last["alias"] is None:
            last["alias"] = a.group(1)
    return rows


def parse_fcns(text):
    rows, vsan, last = [], None, None
    rx = re.compile(r"^\s*(0x[0-9a-fA-F]+)\s+(\S+)\s+([0-9a-fA-F:]{23})\s*(\([^)]*\))?\s*(.*)$")
    for line in text.splitlines():
        v = re.match(r"^\s*VSAN\s+(\d+):", line)
        if v:
            vsan = int(v.group(1))
            continue
        m = rx.match(line)
        if m:
            last = {"vsan": vsan, "fcid": m.group(1).lower(), "type": m.group(2), "pwwn": m.group(3).lower(),
                    "vendor": (m.group(4) or "").strip("() ") or None, "fc4": m.group(5).strip() or None,
                    "alias": None}
            rows.append(last)
            continue
        a = re.match(r"^\s+\[([^\]]+)\]\s*$", line)
        if a and last and last["alias"] is None:
            last["alias"] = a.group(1)
    return rows


def parse_device_alias(text):
    out = {}
    for m in re.finditer(r"device-alias name (\S+) pwwn ([0-9a-fA-F:]{23})", text):
        out[m.group(1)] = m.group(2).lower()
    return out


def parse_zonesets(text):
    """Active zoneset text -> list of zones {zoneset, vsan, zone, members:[{pwwns, aliases, fcid,
    logged_in, raw}]}."""
    zones, zs, cur = [], None, None
    for line in text.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^\s*zoneset name (\S+) vsan (\d+)", line)
        if m:
            zs, cur = (m.group(1), int(m.group(2))), None
            continue
        m = re.match(r"^\s*zone name (\S+) vsan (\d+)", line)
        if m:
            cur = {"zoneset": zs[0] if zs else None, "vsan": int(m.group(2)), "zone": m.group(1), "members": []}
            zones.append(cur)
            continue
        if cur is None:
            continue
        s = line.strip()
        pw = [w.lower() for w in WWN_RE.findall(s)]
        aliases = re.findall(r"device-alias\s+([^\s\]]+)", s)
        aliases += [b.strip() for b in re.findall(r"\[([^\]]+)\]", s)
                    if not b.lower().startswith(("pwwn", "fcid", "device-alias", "interface"))]
        aliases = list(dict.fromkeys(aliases))
        fcid = re.search(r"fcid\s+(0x[0-9a-fA-F]+)", s)
        cur["members"].append({"pwwns": pw, "aliases": aliases, "fcid": fcid.group(1).lower() if fcid else None,
                               "logged_in": s.startswith("*"), "raw": s})
    return zones


def parse_port_channels(text):
    pcs, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^\s*(?:san-)?port-channel\s?(\d+)\s*$", line)
        if m:
            cur = pcs.setdefault(int(m.group(1)), {"members": [], "info": []})
            continue
        if cur is None:
            continue
        for mm in re.finditer(r"(fc\d+/\d+(?:/\d+)?)\s+\[([^\]]+)\]\s*(\*)?", line):
            cur["members"].append({"interface": mm.group(1), "state": mm.group(2), "first_operational": bool(mm.group(3))})
        s = line.strip()
        if s and not s.startswith("Ports:") and not re.match(r"^fc\d", s):
            cur["info"].append(s)
    return pcs


_COUNTER_KEYS = re.compile(r"error|discard|crc|fail|loss|timeout|credit|too long|too short|unknown|"
                           r"wait|drop|offline|ols|nos|lrr|bad", re.I)


def parse_interfaces(text):
    """`show interface [x]` text -> {iface: {state, mode, speed, b2b, trunk_vsans, counters{}}}."""
    out, cur = {}, None
    head = re.compile(rf"^({IFACE}) is (.+)$")
    for line in text.splitlines():
        m = head.match(line.strip()) if not line.startswith((" ", "\t")) else None
        if m:
            name = m.group(1).replace(" ", "")
            cur = out.setdefault(name, {"state": m.group(2).strip(), "counters": {}, "info": {}})
            continue
        if cur is None:
            continue
        s = line.strip()
        for key, rx in (("mode", r"Port mode is (\S+)"), ("speed", r"(?:Operating |Admin )?Speed is ([\w .]+)"),
                        ("tx_b2b", r"Transmit B2B Credit is (\d+)"), ("rx_b2b", r"Receive B2B Credit is (\d+)"),
                        ("trunk_vsans_up", r"Trunk vsans \(up\)\s+\(([^)]*)\)"),
                        ("trunk_vsans_allowed", r"Trunk vsans \(admin allowed and active\)\s+\(([^)]*)\)"),
                        ("port_vsan", r"Port vsan is (\d+)"), ("peer", r"Peer port WWN is ([0-9a-fA-F:]{23})"),
                        ("description", r"Port description is (.+)$")):
            mm = re.search(rx, s)
            if mm and key not in cur["info"]:
                cur["info"][key] = mm.group(1).strip()
        if re.match(r"^Member\[\d+\]\s*:", s):
            cur["info"].setdefault("members", []).append(s.split(":", 1)[1].strip())
        for mm in re.finditer(r"(\d+)\s+([A-Za-z][A-Za-z0-9 /_\-]*?)(?=,|$)", s):
            name = mm.group(2).strip().lower()
            if _COUNTER_KEYS.search(name) and "rate" not in name and "bytes" not in name:
                cur["counters"][name] = cur["counters"].get(name, 0) + int(mm.group(1))
    return out


def _nonzero(counters):
    return {k: v for k, v in counters.items() if v}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def register(mcp, RO):

    @mcp.tool(annotations=RO)
    def trace_wwpn(pwwn: str, switch: str = "") -> dict:
        """Everything about one WWPN across all MDS switches (both fabrics) in one call:
        FLOGI (switch, interface, VSAN, FCID), FCNS registration (type, vendor, FC4 features), device
        aliases, every zone in the ACTIVE zoneset that contains it (by pwwn or alias) with the other
        members and whether they are logged in, the health of the port it logs in on (state, speed,
        non-zero error/credit counters; port-channel members if it is an F-port-channel from a UCS FI),
        and warnings such as 'not logged in', 'logged in but not zoned', 'zone partner not logged in'.
        Accepts any WWN format."""
        w = norm_wwn(pwwn)

        def one(sw):
            aliases_all = parse_device_alias(_txt(sw, "show device-alias database"))
            aliases = sorted(a for a, p in aliases_all.items() if p == w)
            flogi_txt = _txt(sw, "show flogi database")
            flogi = [r for r in parse_flogi(flogi_txt) if r["pwwn"] == w]
            fcns = [r for r in parse_fcns(_txt(sw, "show fcns database")) if r["pwwn"] == w]
            zones = []
            for z in parse_zonesets(_txt(sw, "show zoneset active")):
                hit = [m for m in z["members"] if w in m["pwwns"] or set(m["aliases"]) & set(aliases)]
                if not hit:
                    continue
                others = []
                for m in z["members"]:
                    if m in hit:
                        continue
                    pws = m["pwwns"] or [aliases_all.get(a) for a in m["aliases"] if aliases_all.get(a)]
                    others.append({"pwwns": pws, "aliases": m["aliases"], "logged_in": m["logged_in"], "raw": m["raw"]})
                zones.append({"zoneset": z["zoneset"], "vsan": z["vsan"], "zone": z["zone"],
                              "this_member_logged_in": any(m["logged_in"] for m in hit), "other_members": others})
            ports = {}
            for f in flogi:
                ifc = f["interface"]
                info = parse_interfaces(_txt(sw, f"show interface {ifc}")).get(ifc, {})
                port = {"state": info.get("state"), **info.get("info", {}),
                        "nonzero_counters": _nonzero(info.get("counters", {}))}
                pcm = re.match(r"(?:san-)?port-channel(\d+)", ifc)
                if pcm:
                    pcs = parse_port_channels(_txt(sw, f"show port-channel database interface {ifc}"))
                    port["port_channel_members"] = (pcs.get(int(pcm.group(1))) or {}).get("members", [])
                    port["note"] = ("Logged in through a port-channel: typical for a UCS Fabric Interconnect in NPV "
                                    "mode (F-port-channel). Use port_channel_health for per-member errors.")
                ports[ifc] = port
            warnings = []
            if not flogi:
                warnings.append("not logged in (no FLOGI) on this switch")
            if flogi and not zones:
                warnings.append("logged in but not in any zone of the active zoneset")
            for z in zones:
                for o in z["other_members"]:
                    if not o["logged_in"]:
                        warnings.append(f"zone {z['zone']} (VSAN {z['vsan']}): member {o['raw']} is not logged in")
                if flogi and z["vsan"] not in {f["vsan"] for f in flogi}:
                    warnings.append(f"zone {z['zone']} is in VSAN {z['vsan']} but the WWPN logs in on VSAN "
                                    f"{sorted({f['vsan'] for f in flogi})}")
            for ifc, p in ports.items():
                if p.get("nonzero_counters"):
                    warnings.append(f"login port {ifc} has non-zero error/credit counters (cumulative): "
                                    f"{p['nonzero_counters']}")
            return {"device_aliases": aliases, "flogi": flogi, "fcns": fcns, "zones": zones,
                    "login_ports": ports, "warnings": warnings}

        res, errors = _fan_out(switch, one)
        seen_on = [s for s, r in res.items() if r["flogi"]]
        out = {"pwwn": w, "logged_in_on": seen_on, "switches": res,
               "summary": (f"logged in on {len(seen_on)} switch(es): {seen_on}" if seen_on
                           else "not logged in on any configured switch")}
        if errors:
            out["errors"] = errors
        return out

    @mcp.tool(annotations=RO)
    def zone_check(member_a: str, member_b: str, switch: str = "") -> dict:
        """Are two devices zoned together? member_a / member_b: WWPN (any format) or device-alias name.
        Checks the ACTIVE zoneset on every switch, per VSAN, and reports the shared zones and whether
        both are logged in (FLOGI/FCNS). Use it for 'can host X see array port Y'."""
        def one(sw):
            aliases = parse_device_alias(_txt(sw, "show device-alias database"))

            def resolve(x):
                try:
                    return norm_wwn(x), [a for a, p in aliases.items() if p == norm_wwn(x)]
                except ValueError:
                    if x in aliases:
                        return aliases[x], [x]
                    raise ValueError(f"{x!r} is neither a WWPN nor a device-alias on {sw}") from None
            wa, aa = resolve(member_a)
            wb, ab = resolve(member_b)

            def has(m, w, al):
                return w in m["pwwns"] or bool(set(m["aliases"]) & set(al))
            shared = []
            for z in parse_zonesets(_txt(sw, "show zoneset active")):
                if any(has(m, wa, aa) for m in z["members"]) and any(has(m, wb, ab) for m in z["members"]):
                    shared.append({"zoneset": z["zoneset"], "vsan": z["vsan"], "zone": z["zone"]})
            logged = {r["pwwn"]: r for r in parse_flogi(_txt(sw, "show flogi database"))}
            ns = {r["pwwn"] for r in parse_fcns(_txt(sw, "show fcns database"))}
            return {"a": {"pwwn": wa, "aliases": aa, "flogi_here": logged.get(wa), "in_fcns": wa in ns},
                    "b": {"pwwn": wb, "aliases": ab, "flogi_here": logged.get(wb), "in_fcns": wb in ns},
                    "shared_active_zones": shared, "zoned_together": bool(shared)}

        res, errors = _fan_out(switch, one)
        out = {"switches": res, "zoned_together_on": [s for s, r in res.items() if r["zoned_together"]]}
        if errors:
            out["errors"] = errors
        return out

    @mcp.tool(annotations=RO)
    def port_channel_health(switch: str = "", port_channel: int = 0) -> dict:
        """Port-channel health (ISLs and F-port-channels to UCS Fabric Interconnects): for every
        port-channel (or one), its state, mode, speed, trunk VSANs, member list with state, and per member:
        state, speed, B2B credits and non-zero error/discard/credit counters. Flags members that are down,
        speed mismatches and members with errors - typical causes of uneven load or path problems."""
        def one(sw):
            db = parse_port_channels(_txt(sw, "show port-channel database"))
            if port_channel:
                db = {k: v for k, v in db.items() if k == int(port_channel)}
                if not db:
                    raise ValueError(f"port-channel {port_channel} not found on {sw}")
            pcs = {}
            for pc, d in sorted(db.items()):
                name = f"port-channel{pc}"
                pinfo = parse_interfaces(_txt(sw, f"show interface {name}")).get(name, {})
                members, problems = [], []
                speeds = set()
                for mem in d["members"]:
                    ifc = mem["interface"]
                    mi = parse_interfaces(_txt(sw, f"show interface {ifc}")).get(ifc, {})
                    nz = _nonzero(mi.get("counters", {}))
                    sp = mi.get("info", {}).get("speed")
                    speeds.add(sp)
                    members.append({"interface": ifc, "member_state": mem["state"], "state": mi.get("state"),
                                    "speed": sp, "tx_b2b": mi.get("info", {}).get("tx_b2b"),
                                    "rx_b2b": mi.get("info", {}).get("rx_b2b"), "nonzero_counters": nz})
                    if mem["state"].lower() not in ("up",):
                        problems.append(f"{ifc} member state is {mem['state']}")
                    if nz:
                        problems.append(f"{ifc} has non-zero counters: {nz}")
                if len({s for s in speeds if s}) > 1:
                    problems.append(f"members run at different speeds: {sorted(s for s in speeds if s)}")
                pcs[name] = {"state": pinfo.get("state"), **pinfo.get("info", {}),
                             "port_channel_counters": _nonzero(pinfo.get("counters", {})),
                             "members_up": sum(1 for m in members if m["member_state"].lower() == "up"),
                             "members_total": len(members), "members": members, "problems": problems,
                             "database_info": d["info"]}
            return pcs

        res, errors = _fan_out(switch, one)
        out = {"switches": res}
        if errors:
            out["errors"] = errors
        return out

    @mcp.tool(annotations=RO)
    def scan_port_errors(switch: str = "", top: int = 25, include_down: bool = True) -> dict:
        """Scan every interface on one or all switches and rank those with non-zero error, discard,
        CRC, link-failure, sync/signal-loss, timeout or credit counters; also list ports that are down
        or errDisabled (with the reason). Counters are cumulative since the last clear/reboot - use
        show_logging_onboard error-stats for timing, and re-run later to see if they still grow."""
        def one(sw):
            ifs = parse_interfaces(_txt(sw, "show interface"))
            ranked = []
            down = []
            for name, d in ifs.items():
                nz = _nonzero(d["counters"])
                if nz:
                    ranked.append({"interface": name, "state": d["state"], **{k: d["info"].get(k) for k in
                                   ("mode", "speed", "port_vsan", "description") if d["info"].get(k)},
                                   "total": sum(nz.values()), "counters": nz})
                st = (d["state"] or "").lower()
                if include_down and not st.startswith(("up", "trunking")):
                    down.append({"interface": name, "state": d["state"]})
            ranked.sort(key=lambda r: r["total"], reverse=True)
            return {"interfaces_scanned": len(ifs), "with_errors": len(ranked),
                    "top": ranked[:max(1, min(int(top), 500))],
                    "not_up": [x for x in down if "administratively" not in x["state"].lower()],
                    "admin_down_count": sum(1 for x in down if "administratively" in x["state"].lower())}

        res, errors = _fan_out(switch, one)
        out = {"switches": res}
        if errors:
            out["errors"] = errors
        return out

    @mcp.tool(annotations=RO)
    def flogi_summary(switch: str = "", vsan: int = 0) -> dict:
        """Logins per interface and VSAN. Interfaces with many logins are usually F-port-channels to UCS
        Fabric Interconnects (NPV) or other NPV edge devices; single logins are direct hosts/arrays.
        Includes per-VSAN totals - quick way to see where each FI fabric attaches."""
        def one(sw):
            rows = parse_flogi(_txt(sw, f"show flogi database vsan {int(vsan)}" if vsan else "show flogi database"))
            per_if = defaultdict(lambda: {"logins": 0, "vsans": set()})
            for r in rows:
                per_if[r["interface"]]["logins"] += 1
                per_if[r["interface"]]["vsans"].add(r["vsan"])
            ifs = sorted(({"interface": k, "logins": v["logins"], "vsans": sorted(v["vsans"]),
                           "likely": "NPV uplink (e.g. UCS FI)" if v["logins"] > 2 else "direct device"}
                          for k, v in per_if.items()), key=lambda x: -x["logins"])
            return {"total_logins": len(rows), "per_vsan": dict(Counter(r["vsan"] for r in rows)),
                    "interfaces": ifs}

        res, errors = _fan_out(switch, one)
        out = {"switches": res}
        if errors:
            out["errors"] = errors
        return out
