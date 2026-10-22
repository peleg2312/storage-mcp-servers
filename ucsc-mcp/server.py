"""
Read-only MCP server for Cisco UCS Central (one or many UCS Central instances).

Read-only is enforced in three layers:
  1. Every XML request leaving the process is checked against an allowlist of
     query/session methods (configResolve*, aaaLogin/Refresh/Logout/KeepAlive).
     Anything else (configConfMo, configConfMos, ...) is refused before it is
     sent, no matter which code path built it.
  2. The SDK's write helpers (add_mo, set_mo, remove_mo, commit, file upload/download) raise.
  3. Only query tools are registered, all annotated readOnlyHint=True.
Use a read-only UCS Central account as well (defence in depth).
"""

import logging
import os
import queue
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from ucscsdk.ucschandle import UcscHandle
from ucscsdk.ucscexception import UcscException
from ucscsdk.ucsccoreutils import load_class

log = logging.getLogger("ucsc-mcp")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# --------------------------------------------------------------------------
# Read-only enforcement
# --------------------------------------------------------------------------

ALLOWED_XML_METHODS = frozenset({
    "aaaLogin", "aaaLogout", "aaaRefresh", "aaaKeepAlive",
    "configResolveDn", "configResolveDns",
    "configResolveClass", "configResolveClasses",
    "configResolveChildren", "configResolveParent",
})


class ReadOnlyViolation(Exception):
    pass


class ReadOnlyUcscHandle(UcscHandle):
    """UcscHandle that can only send query and session methods."""

    def post_elem(self, elem, dme="central-mgr"):
        if elem.tag not in ALLOWED_XML_METHODS:
            raise ReadOnlyViolation(
                f"Blocked XML method '{elem.tag}': this server is read-only")
        return super().post_elem(elem, dme=dme)

    def _blocked(self, *args, **kwargs):
        raise ReadOnlyViolation("Configuration changes are disabled: this server is read-only")

    add_mo = set_mo = remove_mo = commit = commit_buffer_discard = _blocked
    file_upload = file_download = _blocked

    # ucscsdk serialises EVERY request in the process with one module-level lock, so separate
    # sessions (and separate UCS Centrals) could never run in parallel. Each handle here is used by
    # one thread at a time (session pool), so a per-handle lock keeps the SDK's ordering guarantee.
    def _tx_lock_acquire_conditional(self, elem):
        if elem.tag != "aaaLogout":
            self.__dict__.setdefault("_ro_tx_lock", threading.Lock()).acquire()

    def _tx_lock_release_conditional(self, elem):
        if elem.tag != "aaaLogout":
            self.__dict__["_ro_tx_lock"].release()


# --------------------------------------------------------------------------
# Multi-instance connections (all configured from one Secret)
# --------------------------------------------------------------------------

class Central:
    """One UCS Central instance with a small pool of logged-in sessions (UCSC_SESSIONS, default 3)
    so independent queries run in parallel."""

    def __init__(self, name, host, username, password, port=443, sessions=3):
        self.name, self.host, self.port = name, host, int(port)
        self._user, self._pw = username, password
        self._pool = queue.LifoQueue()
        self._created = 0
        self._max = max(1, int(sessions))
        self._plock = threading.Lock()

    def _login(self):
        h = ReadOnlyUcscHandle(self.host, self._user, self._pw, port=self.port)
        h.login()
        log.info("Logged in to UCS Central %s (%s), version %s", self.name, self.host, h.version)
        return h

    def _acquire(self):
        try:
            return self._pool.get_nowait()
        except queue.Empty:
            pass
        with self._plock:
            grow = self._created < self._max
            if grow:
                self._created += 1
        if grow:
            try:
                return self._login()
            except Exception:
                with self._plock:
                    self._created -= 1
                raise
        return self._pool.get(timeout=600)

    def _discard(self, h):
        try:
            h.logout()
        except Exception:
            pass
        with self._plock:
            self._created -= 1

    def call(self, fn):
        """Run fn(handle) on a pooled session; one automatic re-login on session/connection errors."""
        for attempt in (1, 2):
            h = self._acquire()
            try:
                result = fn(h)
            except ReadOnlyViolation:
                self._pool.put(h)
                raise
            except (UcscException, OSError) as e:
                self._discard(h)
                if attempt == 2:
                    raise
                log.warning("UCS Central %s call failed (%s); retrying with a new session", self.name, e)
                continue
            except Exception:
                self._pool.put(h)
                raise
            self._pool.put(h)
            return result


def _load_centrals() -> dict:
    """UCSC_<N>_HOST/_USERNAME/_PASSWORD (+ _NAME, _PORT) for any number of UCS Centrals;
    un-numbered UCSC_HOST/... also works for one."""
    env = os.environ
    idx = sorted({int(m.group(1)) for k in env for m in [re.match(r"UCSC_(\d+)_HOST$", k)] if m})
    prefixes = [f"UCSC_{i}_" for i in idx] or (["UCSC_"] if env.get("UCSC_HOST") else [])
    out = {}
    for p in prefixes:
        for k in ("HOST", "USERNAME", "PASSWORD"):
            if not env.get(p + k):
                raise SystemExit(f"{p}{k} is not set")
        name = (env.get(p + "NAME") or env[p + "HOST"]).strip()
        if name in out:
            raise SystemExit(f"Duplicate UCS Central name {name!r}")
        out[name] = Central(name, env[p + "HOST"], env[p + "USERNAME"], env[p + "PASSWORD"],
                            env.get(p + "PORT", "443"),
                            env.get(p + "SESSIONS", env.get("UCSC_SESSIONS", "3")))
    if not out:
        raise SystemExit("No UCS Central configured: set UCSC_1_HOST, UCSC_1_USERNAME, UCSC_1_PASSWORD "
                         "(and UCSC_2_... for more)")
    return out


_CENTRALS = None
_CLOCK = threading.Lock()


def centrals() -> dict:
    global _CENTRALS
    with _CLOCK:
        if _CENTRALS is None:
            _CENTRALS = _load_centrals()
            log.info("Configured UCS Central instances: %s", ", ".join(_CENTRALS))
        return _CENTRALS


def pick(central: str = "") -> list:
    """Centrals to query: the named one, or all of them."""
    cs = centrals()
    if not central:
        return list(cs.values())
    if central in cs:
        return [cs[central]]
    for c in cs.values():
        if c.host == central:
            return [c]
    raise ValueError(f"Unknown central {central!r}; configured: {list(cs)}")


def fan_out(central, fn):
    """Run fn(central) on each selected central in parallel. Returns (rows, errors)."""
    cs = pick(central)
    rows, errors = [], {}
    with ThreadPoolExecutor(max_workers=min(8, len(cs))) as ex:
        futs = {c.name: ex.submit(fn, c) for c in cs}
    for name, f in futs.items():
        try:
            rows += f.result()
        except ReadOnlyViolation:
            raise
        except Exception as e:
            errors[name] = str(e)
            log.warning("UCS Central %s failed: %s", name, e)
    return rows, errors


def find_dn(dn: str, central: str = ""):
    """Locate an object by DN on the given central or the first central that has it."""
    for c in pick(central):
        try:
            mo = c.call(lambda h: h.query_dn(dn))
        except ReadOnlyViolation:
            raise
        except Exception as e:
            log.debug("%s: %s", c.name, e)
            continue
        if mo is not None:
            return c, mo
    raise LookupError(f"No object at {dn!r} on {[c.name for c in pick(central)]}")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

_SAFE_VALUE = re.compile(r"^[\w.:/\-\[\] ]{1,256}$")
_TYPES = {"eq": "eq", "ne": "ne", "re": "re", "wcard": "re"}


def _filter(prop, value, ftype="eq"):
    """One server-side filter term. Values are restricted to safe characters."""
    if not _SAFE_VALUE.match(str(value)):
        raise ValueError(f"Unsupported characters in filter value: {value!r}")
    if ftype not in _TYPES:
        raise ValueError("filter type must be eq, ne or wcard")
    return f'({prop}, "{value}", type="{_TYPES[ftype]}")'


def _contains(prop, text):
    """Server-side case-insensitive 'contains' on a property (regex with escaped literal)."""
    if not _SAFE_VALUE.match(text):
        raise ValueError(f"Unsupported characters in search text: {text!r}")
    lit = re.sub(r"([.\[\]])", r"\\\1", text)
    return f'({prop}, "{lit}", type="re", flag="I")'


def _under(dn_prefix):
    """Server-side filter: objects whose DN is inside dn_prefix (e.g. a domain or an org)."""
    p = dn_prefix.rstrip("/")
    if not re.fullmatch(r"[\w.:\-/\[\]]{1,200}", p):
        raise ValueError(f"Unsupported characters in DN: {dn_prefix!r}")
    esc = re.sub(r"([.\[\]])", r"\\\1", p)
    return f'(dn, "^{esc}/", type="re")'


def _domain_filter(domain):
    if not domain:
        return None
    if not re.fullmatch(r"\d{1,10}", str(domain)):
        raise ValueError("domain must be the numeric id from list_domains")
    return _under(f"compute/sys-{domain}")


def _and(*parts):
    parts = [p for p in parts if p]
    return " and ".join(parts) if parts else None


def _any_of(prop, values):
    terms = [_filter(prop, v) for v in values]
    if not terms:
        return None
    return terms[0] if len(terms) == 1 else "(" + " or ".join(terms) + ")"


# ---- short-lived query cache: repeated questions in one conversation do not re-download -------
_CACHE_TTL = float(os.getenv("UCSC_CACHE_TTL", "120"))
_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()


def query(c, class_id, flt=None):
    """query_classid with a server-side filter and a TTL cache. If UCS Central rejects the filter,
    fall back to an unfiltered query (callers always re-check in Python)."""
    key = (c.name, class_id, flt)
    now = time.time()
    if _CACHE_TTL > 0:
        with _CACHE_LOCK:
            hit = _CACHE.get(key)
        if hit and now - hit[0] < _CACHE_TTL:
            return hit[1]
    try:
        mos = c.call(lambda h: h.query_classid(class_id, filter_str=flt))
    except (UcscException, OSError) as e:
        if not flt:
            raise
        log.warning("%s: filter on %s not accepted (%s); querying without filter", c.name, class_id, e)
        mos = query(c, class_id, None)
    if _CACHE_TTL > 0:
        with _CACHE_LOCK:
            _CACHE[key] = (now, mos)
            if len(_CACHE) > 500:
                for k, _ in sorted(_CACHE.items(), key=lambda kv: kv[1][0])[:100]:
                    _CACHE.pop(k, None)
    return mos


def _to_dict(mo, props=None):
    if props:
        return {p: getattr(mo, p, None) for p in ("dn", *props)}
    return {p: getattr(mo, p, None) for p in sorted(mo.prop_meta) if p != "child_action"}


def _in_domain(dn, domain):
    if not domain:
        return True
    return dn.startswith(f"compute/sys-{domain}/") or dn == f"compute/sys-{domain}"


def _domain_of(dn):
    m = re.match(r"compute/sys-(\d+)", dn or "")
    return m.group(1) if m else None


def _cap(items, limit, errors=None):
    limit = max(1, min(int(limit), 5000))
    out = {"total": len(items), "returned": min(len(items), limit), "items": items[:limit]}
    if errors:
        out["unreachable_centrals"] = errors
    return out


def _class_rows(central, class_id, props=None, flt=None, keep=lambda mo: True):
    def one(c):
        return [dict(_to_dict(m, props), central=c.name) for m in query(c, class_id, flt) if keep(m)]
    return fan_out(central, one)


def _bad(op):
    return op not in ("operable", "ok", "", None, "not-supported", "unknown")


RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

# --------------------------------------------------------------------------
# Guidance for the connecting model
# --------------------------------------------------------------------------

INSTRUCTIONS = """\
You are connected to a READ-ONLY gateway to Cisco UCS Central (one or more instances). UCS Central
manages many UCS Manager domains (fabric interconnect pairs with their blades and rack servers).
No tool can change anything; never tell the user you changed, acknowledged or fixed something.

== IDENTIFIERS ==
- central: name of a UCS Central instance (list_centrals). Optional everywhere: list tools query
  all instances in parallel and tag each row with "central"; DN tools search all instances.
- domain: numeric UCS domain id from list_domains (its DN is compute/sys-<id>). Domain ids are only
  unique within one central; when several centrals are configured, pass central too.
- DNs (distinguished names) identify everything; copy them exactly from tool output:
  blade compute/sys-1008/chassis-1/blade-3, rack server compute/sys-1008/rack-unit-2,
  fabric interconnect compute/sys-1008/switch-A, global service profile org-root/org-Prod/ls-esx01,
  vHBA <sp-dn>/fc-vHBA-A, WWPN pool org-root/wwn-pool-WWPN-A.
- Service profile (SP) = the logical server (identity, vHBAs/vNICs, policies); it is associated
  to a physical server (pn_dn). The physical server's assigned_to_dn points back to the SP.
- Fabric A / B = the two fabric interconnects; vHBA-A goes to fabric A and its SAN, vHBA-B to B.
- WWPN format 20:00:00:25:B5:xx:xx:xx (input may be any case, with or without colons).

== LARGE INVENTORIES: QUERY NARROWLY ==
UCS Central can hold tens of thousands of objects. Every filter argument is applied ON UCS Central,
so narrow calls are fast and broad ones are slow:
- Know a name? list_service_profiles name_contains=... (add org= or sp_type="instance").
- Know a server? get_server(dn) / get_service_profile(dn) read only that object's subtree.
- Know a WWPN? find_wwpn - never list everything to search for it.
- Scope to a domain (domain=) whenever the question is about one UCS domain.
- Use problems_only / severity / unacked_only instead of listing everything and filtering yourself.
- list results are capped (limit, default 200) and include totals and counts; raise limit only if
  the user really needs the full list. Identical queries within ~2 minutes come from a cache.

== WORKFLOWS ==
Health overview ("how is UCS"): list_domains -> get_domain_health for each domain with faults
  (operability problems, PSU/fan/IOM, fault counts) -> list_faults severity="critical,major".
Faults / events: list_faults (sorted critical -> info, newest first within a severity). Group
  identical codes, give counts, affected DNs and first/last time. Fault codes (F0xxx) are
  searchable in Cisco docs; explain what they mean when you know.
Logs: get_audit_log = UCS Central audit (who changed what); get_events = event log.
Server / SP troubleshooting: get_server(dn) for a blade/rack (hardware, adapters, physical FC
  interfaces with WWPN and fabric, associated SP, faults on it) or get_service_profile(dn)
  (association, policies, vHBAs with WWPN/fabric/VSAN, vNICs, faults).
SAN / storage questions:
  find_wwpn(wwpn) -> owning SP + vHBA + fabric + pool entry.
  get_service_profile_vhbas(sp_dn) -> all WWPNs, fabric A/B, VSAN per vHBA (feed these to MDS zoning).
  list_fc_uplinks(domain) -> FI FC uplink ports to the SAN (state, speed, peer) for SAN-side issues.
  list_vsans -> VSAN ids/names per fabric. list_wwn_pools -> pool size/used/blocks.
Inventory: list_servers, list_chassis, list_fabric_interconnects, list_service_profiles,
  list_firmware. Anything else: query_class(class_id) or get_object(dn) (read any object).

== READING RESULTS ==
- operability "operable" and oper_state "ok" are healthy; anything else (inoperable, degraded,
  removed, unknown, power-problem, thermal-problem...) is worth reporting.
- SP assoc_state "associated" + config_state "applied" is normal; "unassociated" means not on
  hardware; config_state "failed-to-apply" or pending changes mean an action is required in UCS.
- Faults with ack="no" are not acknowledged yet; "cleared" faults are history.
- A vHBA/host FC interface oper_state other than "up" while the server is powered on points to
  the FI uplink, VSAN or SAN side; check list_fc_uplinks and the MDS fabric.

== CROSS-SYSTEM TRACING (if other MCP servers are connected) ==
UCS: get_service_profile_vhbas -> WWPN + fabric + VSAN
-> MDS: show_flogi_database / show_fcns_database / show_zoneset_active_vsan (zone membership,
   switch port, CRC/txwait on that port)
-> PowerMax: find_wwpn -> masking view, storage group, array ports.
Use the same WWPN at every hop and present the end-to-end path as a table.

== ANSWER STYLE ==
Lead with the conclusion, then the evidence (DNs, states, counts, times), then the next check.
Mention when a central was unreachable (results include unreachable_centrals).
"""

mcp = FastMCP("ucs-central-readonly", instructions=INSTRUCTIONS)

# --------------------------------------------------------------------------
# Connection / inventory
# --------------------------------------------------------------------------


@mcp.tool(annotations=RO)
def test_connection() -> dict:
    """Log in to every configured UCS Central and return name, version and status. Run first if
    anything fails."""
    out = []
    for c in centrals().values():
        try:
            info = c.call(lambda h: {"ucs_central": h.ucs, "version": str(h.version)})
            out.append({"central": c.name, "host": c.host, "ok": True, **info})
        except Exception as e:
            out.append({"central": c.name, "host": c.host, "ok": False, "error": str(e)})
    return {"centrals": out}


@mcp.tool(annotations=RO)
def list_centrals() -> dict:
    """List configured UCS Central instances (name, host)."""
    return {"centrals": [{"name": c.name, "host": c.host} for c in centrals().values()]}


@mcp.tool(annotations=RO)
def list_domains(central: str = "", limit: int = 500) -> dict:
    """List UCS Manager domains registered with UCS Central: id, name, IP, site, firmware,
    connection/inventory status and fault aggregate."""
    props = ("id", "name", "address", "site", "product_family", "fw_package_version",
             "oper_group_dn", "subscribe_status", "inventory_status", "flt_aggr")
    rows, err = _class_rows(central, "computeSystem", props)
    return _cap(sorted(rows, key=lambda r: (r["central"], r["name"] or "")), limit, err)


@mcp.tool(annotations=RO)
def list_fabric_interconnects(domain: str = "", central: str = "") -> dict:
    """Fabric interconnects (A/B) per domain: model, serial, management IP, operability."""
    props = ("id", "model", "serial", "oob_if_ip", "operability", "total_memory")
    rows, err = _class_rows(central, "networkElement", props, flt=_domain_filter(domain),
                            keep=lambda m: _in_domain(m.dn, domain))
    for r in rows:
        r["domain"] = _domain_of(r["dn"])
    return _cap(rows, 1000, err)


@mcp.tool(annotations=RO)
def list_chassis(domain: str = "", central: str = "") -> dict:
    """Blade chassis per domain: model, serial, operability, oper state."""
    props = ("id", "model", "serial", "operability", "oper_state", "admin_state")
    rows, err = _class_rows(central, "equipmentChassis", props, flt=_domain_filter(domain),
                            keep=lambda m: _in_domain(m.dn, domain))
    for r in rows:
        r["domain"] = _domain_of(r["dn"])
    return _cap(rows, 2000, err)


@mcp.tool(annotations=RO)
def list_servers(domain: str = "", kind: str = "all", problems_only: bool = False, model: str = "",
                 serial: str = "", central: str = "", limit: int = 200) -> dict:
    """Physical blade and rack servers. domain: numeric id (empty = all). kind: blade, rack or all.
    problems_only: only servers whose operability/oper_state is not healthy. model / serial: filter
    (serial exact, model contains). Filters run on UCS Central, so narrow queries are fast."""
    props = ("model", "serial", "uuid", "oper_state", "operability", "oper_power", "association",
             "assigned_to_dn", "num_of_cpus", "num_of_cores", "total_memory", "num_of_fc_host_ifs", "usr_lbl")
    classes = {"blade": ["computeBlade"], "rack": ["computeRackUnit"]}.get(kind, ["computeBlade", "computeRackUnit"])

    def keep(m):
        if not _in_domain(m.dn, domain):
            return False
        if serial and (m.serial or "") != serial:
            return False
        if model and model.lower() not in (m.model or "").lower():
            return False
        return not problems_only or _bad(m.operability) or m.oper_state not in ("ok", None, "")
    flt = _and(_domain_filter(domain),
               'not (operability, "operable", type="eq")' if problems_only else None,
               _filter("serial", serial) if serial else None,
               _contains("model", model) if model else None)
    rows, err = [], {}
    for cid in classes:
        r, e = _class_rows(central, cid, props, flt=flt, keep=keep)
        rows += [dict(x, kind=cid, domain=_domain_of(x["dn"])) for x in r]
        err.update(e)
    return _cap(rows, limit, err)


@mcp.tool(annotations=RO)
def get_server(dn: str, central: str = "") -> dict:
    """Full view of one physical server (blade or rack) by DN: hardware, power, association to its
    service profile, adapters, physical host FC interfaces (WWPN, fabric, state), and active faults."""
    c, mo = find_dn(dn, central)
    sub = c.call(lambda h: h.query_dn(dn, hierarchy=True)) or []
    by = {}
    for m in sub:
        by.setdefault(m.get_class_id(), []).append(m)
    adapters = by.get("AdaptorUnit", [])
    fc_ifs = [{"dn": i.dn, "name": i.name, "wwpn": i.wwn, "node_wwn": i.node_wwn, "fabric": i.switch_id,
               "oper_state": i.oper_state, "operability": i.operability, "peer_dn": i.peer_dn}
              for i in by.get("AdaptorHostFcIf", [])]
    faults = [_to_dict(x, ("severity", "code", "descr", "created", "ack"))
              for x in by.get("FaultInst", []) if x.severity != "cleared"]
    keys = ("model", "serial", "uuid", "oper_state", "operability", "oper_power", "association",
            "assigned_to_dn", "availability", "num_of_cpus", "num_of_cores", "total_memory",
            "num_of_adaptors", "usr_lbl", "admin_state", "discovery")
    return {"central": c.name, "dn": dn, "domain": _domain_of(dn),
            **{k: getattr(mo, k, None) for k in keys},
            "adapters": [_to_dict(a, ("model", "serial", "operability", "oper_state")) for a in adapters],
            "fc_interfaces": fc_ifs, "faults": faults}


@mcp.tool(annotations=RO)
def get_domain_health(domain: str, central: str = "") -> dict:
    """One-call health summary of a UCS domain: FIs, chassis, servers, IOMs, PSUs and fans that are
    not operable, server association counts, and fault counts by severity (unacknowledged)."""
    cs = pick(central)
    if len(cs) > 1:
        raise ValueError("Several centrals are configured; pass central=<name> with a domain id")
    c = cs[0]

    dfl = _domain_filter(domain)
    not_ok = 'not (operability, "operable", type="eq")'

    def cls(cid, extra=None):
        return [m for m in query(c, cid, _and(dfl, extra)) if _in_domain(m.dn, domain)]

    def f():
        system = [m for m in query(c, "computeSystem", _filter("id", str(domain))) if m.id == str(domain)]
        jobs = {cid: (cid, not_ok) for cid in ("networkElement", "equipmentChassis", "equipmentIOCard",
                                               "equipmentPsu", "equipmentFan")}
        jobs.update({"computeBlade": ("computeBlade", None), "computeRackUnit": ("computeRackUnit", None),
                     "faultInst": ("faultInst", 'not (severity, "cleared", type="eq")')})
        with ThreadPoolExecutor(max_workers=4) as ex:
            res = dict(zip(jobs, ex.map(lambda j: cls(*j), jobs.values())))
        bad_hw = []
        for cid in ("networkElement", "equipmentChassis", "equipmentIOCard", "equipmentPsu", "equipmentFan",
                    "computeBlade", "computeRackUnit"):
            for m in res[cid]:
                if _bad(getattr(m, "operability", None)):
                    bad_hw.append({"class": cid, "dn": m.dn, "operability": m.operability,
                                   "model": getattr(m, "model", None), "serial": getattr(m, "serial", None)})
        servers = res["computeBlade"] + res["computeRackUnit"]
        faults = [m for m in res["faultInst"] if m.severity != "cleared"]
        return system, bad_hw, servers, faults
    system, bad_hw, servers, faults = f()
    if not system:
        raise LookupError(f"Domain {domain} not found on {c.name}; see list_domains")
    s = system[0]
    unacked = [x for x in faults if x.ack == "no"]
    return {
        "central": c.name, "domain": domain, "name": s.name, "address": s.address,
        "firmware": s.fw_package_version, "status": {"subscribe": s.subscribe_status, "inventory": s.inventory_status},
        "servers": {"total": len(servers), "by_association": dict(Counter(x.association for x in servers)),
                    "not_operable": sum(1 for x in servers if _bad(x.operability))},
        "hardware_problems": bad_hw,
        "faults_by_severity": dict(Counter(x.severity for x in faults)),
        "unacknowledged_by_severity": dict(Counter(x.severity for x in unacked)),
        "top_fault_codes": [{"code": k, "count": n} for k, n in Counter(x.code for x in faults).most_common(10)],
    }


@mcp.tool(annotations=RO)
def list_faults(severity: str = "", domain: str = "", unacked_only: bool = False, code: str = "",
                text: str = "", central: str = "", limit: int = 200) -> dict:
    """Active faults sorted by severity (critical, major, minor, warning, info, condition, cleared)
    then newest first. severity: one or comma-separated. domain: numeric id (empty = all, including
    UCS Central's own). code: e.g. F0283. text: substring of the description."""
    sevs = [x.strip().lower() for x in severity.split(",") if x.strip()]
    flt = _and(_any_of("severity", sevs), _domain_filter(domain),
               _filter("ack", "no") if unacked_only else None,
               _filter("code", code.upper()) if code else None,
               _contains("descr", text) if text else None)
    props = ("severity", "code", "cause", "descr", "created", "last_transition", "ack", "occur", "type")

    def keep(m):
        return (_in_domain(m.dn, domain) and (not sevs or m.severity in sevs)
                and (not unacked_only or m.ack == "no") and (not code or m.code == code.upper())
                and (not text or text.lower() in (m.descr or "").lower()))
    rows, err = _class_rows(central, "faultInst", props, flt=flt, keep=keep)
    order = {"critical": 0, "major": 1, "minor": 2, "warning": 3, "info": 4, "condition": 5, "cleared": 6}
    rows.sort(key=lambda r: r["created"] or "", reverse=True)
    rows.sort(key=lambda r: order.get(r["severity"], 9))
    for r in rows:
        r["domain"] = _domain_of(r["dn"])
    out = _cap(rows, limit, err)
    out["by_severity"] = dict(Counter(r["severity"] for r in rows))
    return out


@mcp.tool(annotations=RO)
def get_audit_log(user: str = "", text: str = "", central: str = "", limit: int = 200) -> dict:
    """UCS Central audit log (aaaModLR): who changed what and when, newest first. Filter by user or
    description text."""
    props = ("id", "created", "user", "descr", "ind", "severity")

    def keep(m):
        return (not user or (m.user or "").lower() == user.lower()) and \
               (not text or text.lower() in (m.descr or "").lower())
    flt = _and(_filter("user", user) if user else None, _contains("descr", text) if text else None)
    rows, err = _class_rows(central, "aaaModLR", props, flt=flt, keep=keep)
    rows.sort(key=lambda r: r["created"] or "", reverse=True)
    return _cap(rows, limit, err)


@mcp.tool(annotations=RO)
def get_events(text: str = "", central: str = "", limit: int = 200) -> dict:
    """UCS Central event log (eventInst), newest first, optionally filtered by description text."""
    props = ("id", "created", "descr", "severity")
    rows, err = _class_rows(central, "eventInst", props, flt=_contains("descr", text) if text else None,
                            keep=lambda m: not text or text.lower() in (m.descr or "").lower())
    rows.sort(key=lambda r: r["created"] or "", reverse=True)
    return _cap(rows, limit, err)


# --------------------------------------------------------------------------
# Service profiles and SAN identity
# --------------------------------------------------------------------------


@mcp.tool(annotations=RO)
def list_service_profiles(name_contains: str = "", sp_type: str = "", assoc_state: str = "",
                          org: str = "", server_dn: str = "", central: str = "", limit: int = 200) -> dict:
    """Service profiles and templates with association state and the physical server they run on.
    Filters run on UCS Central (fast even with tens of thousands of profiles) - always pass at least
    one when you can:
      name_contains (case-insensitive), sp_type (instance, initial-template, updating-template),
      assoc_state (associated, unassociated, ...), org (DN prefix, e.g. org-root/org-Prod),
      server_dn (the physical server, to find which profile runs on it).
    Returns counts by type and association state for everything that matched."""
    props = ("name", "type", "assoc_state", "assign_state", "pn_dn", "oper_state", "config_state",
             "oper_src_templ_name", "uuid", "domain", "usr_lbl")
    flt = _and(_contains("name", name_contains) if name_contains else None,
               _filter("type", sp_type) if sp_type else None,
               _filter("assoc_state", assoc_state) if assoc_state else None,
               _under(org) if org else None,
               _filter("pn_dn", server_dn) if server_dn else None)
    rows, err = _class_rows(central, "lsServer", props, flt=flt, keep=lambda m: (
        (not sp_type or m.type == sp_type) and (not assoc_state or m.assoc_state == assoc_state)
        and (not name_contains or name_contains.lower() in (m.name or "").lower())
        and (not org or m.dn.startswith(org.rstrip("/") + "/"))
        and (not server_dn or m.pn_dn == server_dn)))
    out = _cap(sorted(rows, key=lambda r: r["name"] or ""), limit, err)
    out["by_type"] = dict(Counter(r["type"] for r in rows))
    out["by_assoc_state"] = dict(Counter(r["assoc_state"] for r in rows))
    if out["total"] > out["returned"]:
        out["note"] = f"{out['total']} matched; narrow with name_contains / org / sp_type to see the rest."
    return out


def _sp_subtree(c, sp_dn):
    """vHBAs (with VSANs), vNICs and active faults of a service profile from ONE hierarchical read."""
    sub = c.call(lambda h: h.query_dn(sp_dn, hierarchy=True)) or []
    by = {}
    for m in sub:
        by.setdefault(m.get_class_id(), []).append(m)
    vsans = {}
    for i in by.get("VnicFcIf", []):
        vsans.setdefault(i.dn.rsplit("/", 1)[0], []).append(i.oper_vnet_name or i.name)
    vhbas = [{"name": v.name, "wwpn": v.addr, "fabric": v.switch_id,
              "wwpn_pool": v.oper_ident_pool_name or v.ident_pool_name,
              "template": v.oper_nw_templ_name or v.nw_templ_name, "order": v.oper_order or v.order,
              "dn": v.dn, "vsan": vsans.get(v.dn, [])} for v in by.get("VnicFc", [])]
    vnics = [{"name": v.name, "mac": v.addr, "fabric": v.switch_id, "dn": v.dn} for v in by.get("VnicEther", [])]
    faults = [_to_dict(x, ("severity", "code", "descr", "created", "ack"))
              for x in by.get("FaultInst", []) if x.severity != "cleared"]
    return vhbas, vnics, faults


@mcp.tool(annotations=RO)
def get_service_profile(sp_dn: str, central: str = "") -> dict:
    """Full service profile: association and config state, physical server, template, identity
    (UUID), policies, vHBAs (WWPN, fabric, VSAN), vNICs (MAC, fabric) and faults on the profile."""
    c, sp = find_dn(sp_dn, central)
    vhbas, vnics, faults = _sp_subtree(c, sp_dn)
    keys = ("name", "type", "assoc_state", "assign_state", "config_state", "oper_state", "pn_dn",
            "oper_src_templ_name", "uuid", "domain", "domain_group", "oper_boot_policy_name",
            "oper_bios_profile_name", "oper_host_fw_policy_name", "oper_maint_policy_name",
            "oper_local_disk_policy_name", "usr_lbl", "descr")
    return {"central": c.name, "dn": sp_dn, **{k: getattr(sp, k, None) for k in keys},
            "vhbas": vhbas, "vnics": vnics, "faults": faults}


@mcp.tool(annotations=RO)
def get_service_profile_vhbas(sp_dn: str, central: str = "") -> dict:
    """vHBAs of a service profile: WWPN, fabric (A/B), VSAN, WWPN pool, template. Use the WWPNs for
    MDS zoning/FLOGI checks and PowerMax masking."""
    c, sp = find_dn(sp_dn, central)
    return {"central": c.name, "service_profile": sp.name, "assoc_state": sp.assoc_state,
            "server": sp.pn_dn, "vhbas": _sp_subtree(c, sp_dn)[0]}


@mcp.tool(annotations=RO)
def find_wwpn(wwpn: str, central: str = "") -> dict:
    """Which service profile / vHBA owns a WWPN, and which physical FC interface currently carries
    it. Maps an MDS FLOGI/zoning entry or a PowerMax initiator back to a UCS server."""
    hexd = re.sub(r"[^0-9A-Fa-f]", "", wwpn).upper()
    if len(hexd) != 16:
        raise ValueError("WWPN must have 16 hex digits, e.g. 20:00:00:25:B5:0A:00:01")
    w = ":".join(hexd[i:i + 2] for i in range(0, 16, 2))

    def one(c):
        def f(h):
            def by(cid, prop):
                for val in (w, w.lower()):
                    hit = [m for m in h.query_classid(cid, filter_str=_filter(prop, val))
                           if (getattr(m, prop) or "").upper() == w]
                    if hit:
                        return hit
                return []
            return by("vnicFc", "addr"), by("fcpoolInitiator", "id"), by("adaptorHostFcIf", "wwn")
        vh, pool, phys = c.call(f)
        return [{"central": c.name,
                 "vhbas": [{"dn": v.dn, "service_profile_dn": v.dn.rsplit("/", 1)[0], "vhba": v.name,
                            "fabric": v.switch_id} for v in vh],
                 "pool_entries": [{"dn": p.dn, "assigned": p.assigned, "assigned_to": p.assigned_to_dn} for p in pool],
                 "physical_interfaces": [{"dn": p.dn, "server_dn": p.dn.split("/adaptor-")[0], "fabric": p.switch_id,
                                          "oper_state": p.oper_state, "peer_dn": p.peer_dn} for p in phys]}]
    rows, err = fan_out(central, one)
    hits = [r for r in rows if r["vhbas"] or r["pool_entries"] or r["physical_interfaces"]]
    out = {"wwpn": w, "found": bool(hits), "results": hits}
    if err:
        out["unreachable_centrals"] = err
    return out


@mcp.tool(annotations=RO)
def list_wwn_pools(central: str = "", limit: int = 500) -> dict:
    """WWPN/WWNN pools: purpose, size, assigned count and address blocks."""
    def one(c):
        def f(h):
            out = []
            for p in h.query_classid("fcpoolInitiators"):
                blocks = h.query_children(in_dn=p.dn, class_id="fcpoolBlock")
                out.append({"central": c.name, "dn": p.dn, "name": p.name, "purpose": p.purpose,
                            "size": p.size, "assigned": p.assigned,
                            "blocks": [{"from": b.r_from, "to": b.to} for b in blocks]})
            return out
        return c.call(f)
    rows, err = fan_out(central, one)
    return _cap(rows, limit, err)


@mcp.tool(annotations=RO)
def list_vsans(domain: str = "", central: str = "") -> dict:
    """VSANs (global and per domain): id, name, fabric (A/B or dual), FCoE VLAN, zoning state."""
    props = ("id", "name", "switch_id", "fcoe_vlan", "zoning_state", "oper_state")
    rows, err = _class_rows(central, "fabricVsan", props, flt=_domain_filter(domain),
                            keep=lambda m: not domain or _in_domain(m.dn, domain))
    return _cap(rows, 5000, err)


@mcp.tool(annotations=RO)
def list_fc_uplinks(domain: str = "", problems_only: bool = False, central: str = "") -> dict:
    """Fabric interconnect FC ports (uplinks to the SAN/MDS): FI, slot/port, WWN, speed, admin/oper
    state, role and peer. problems_only: ports that are enabled but not up."""
    props = ("switch_id", "slot_id", "port_id", "wwn", "oper_speed", "admin_state", "oper_state",
             "if_role", "peer_dn")

    def keep(m):
        if not _in_domain(m.dn, domain):
            return False
        return not problems_only or (m.admin_state == "enabled" and m.oper_state != "up")
    flt = _and(_domain_filter(domain),
               (_filter("admin_state", "enabled") + ' and not (oper_state, "up", type="eq")') if problems_only else None)
    rows, err = _class_rows(central, "fcPIo", props, flt=flt, keep=keep)
    for r in rows:
        r["domain"] = _domain_of(r["dn"])
    return _cap(rows, 5000, err)


@mcp.tool(annotations=RO)
def list_firmware(domain: str = "", central: str = "", limit: int = 2000) -> dict:
    """Running firmware versions (UCS Central, fabric interconnects, IOMs, servers, adapters)."""
    props = ("type", "deployment", "version", "package_version")
    rows, err = _class_rows(central, "firmwareRunning", props, flt=_domain_filter(domain),
                            keep=lambda m: _in_domain(m.dn, domain))
    return _cap(rows, limit, err)


# --------------------------------------------------------------------------
# Generic read access
# --------------------------------------------------------------------------


@mcp.tool(annotations=RO)
def get_object(dn: str, hierarchy: bool = False, central: str = "", limit: int = 300) -> dict:
    """Read any managed object by DN (optionally with its whole subtree)."""
    c, mo = find_dn(dn, central)
    if hierarchy:
        mos = c.call(lambda h: h.query_dn(dn, hierarchy=True))
        rows = [dict(_to_dict(m), class_id=m.get_class_id()) for m in mos]
    else:
        rows = [dict(_to_dict(mo), class_id=mo.get_class_id())]
    return dict(_cap(rows, limit), central=c.name)


@mcp.tool(annotations=RO)
def query_class(class_id: str, prop: str = "", value: str = "", match: str = "eq",
                domain: str = "", central: str = "", limit: int = 200) -> dict:
    """Read all objects of a UCS Central class with an optional property filter. Useful classes:
    computeBlade, computeRackUnit, lsServer, vnicFc, vnicEther, faultInst, equipmentChassis,
    equipmentPsu, equipmentFan, equipmentIOCard, networkElement, fcPIo, etherPIo, fabricVsan,
    fabricVlan, adaptorHostFcIf, firmwareRunning, macpoolPool, uuidpoolPool. match: eq, ne, wcard."""
    try:
        load_class(class_id[0].upper() + class_id[1:])
    except Exception:
        raise ValueError(f"Unknown UCS Central class '{class_id}'")
    if match not in ("eq", "ne", "wcard"):
        raise ValueError("match must be eq, ne or wcard")
    flt = None
    if prop:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", prop):
            raise ValueError("Invalid property name")
        flt = _filter(prop, value, match)
    flt = _and(flt, _domain_filter(domain))
    rows, err = _class_rows(central, class_id, None, flt=flt, keep=lambda m: _in_domain(m.dn, domain))
    return _cap(rows, limit, err)


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------


@mcp.prompt()
def ucs_health_check(central: str = "") -> str:
    """Daily health report across all UCS domains."""
    return (f"Produce a UCS health report{(' for UCS Central ' + central) if central else ' for all UCS Centrals'}. "
            "Run test_connection, list_domains, and get_domain_health for every domain. Then list_faults "
            "severity='critical,major' unacked_only=true (group by code with counts) and list_fc_uplinks "
            "problems_only=true. Finish with a table per domain (status, hardware problems, critical/major "
            "faults) and a ranked action list. Mention any central that was unreachable.")


@mcp.prompt()
def troubleshoot_server(server_or_service_profile: str) -> str:
    """Investigate a server or service profile."""
    return (f"Investigate UCS object '{server_or_service_profile}'. If it is a name, find it with "
            "list_service_profiles name_contains=... or list_servers. Then get_service_profile and get_server "
            "(association, config state, operability, power, adapters, FC interfaces, faults). Check the domain "
            "with get_domain_health and the SAN side with list_fc_uplinks for the same domain/fabric. "
            "Explain the most likely cause and the next step.")


@mcp.prompt()
def trace_san_path(service_profile_or_wwpn: str) -> str:
    """End-to-end SAN path for a host across UCS, MDS and PowerMax."""
    return (f"Trace the SAN paths of '{service_profile_or_wwpn}'. 1) UCS: get_service_profile_vhbas (or "
            "find_wwpn) for every WWPN with fabric and VSAN; list_fc_uplinks for that domain. 2) If MDS tools "
            "are available: for each WWPN find the FLOGI (switch, interface, VSAN), the active zones containing "
            "it, and errors on that interface. 3) If PowerMax tools are available: find_wwpn on the array for "
            "masking view, storage group and array ports, and check those ports are logged in. Present one row "
            "per WWPN: fabric, VSAN, switch port, zone(s), array port(s), storage group, status - and flag any "
            "WWPN that is missing at any hop.")


if __name__ == "__main__":
    import mcp_auth
    centrals()  # validate the Secret at startup, not on first call
    mcp_auth.run(mcp)
