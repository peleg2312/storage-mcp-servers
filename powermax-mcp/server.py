"""
Read-only MCP server for Dell PowerMax / VMAX via Unisphere for PowerMax REST API.

Read-only is enforced at the HTTP layer: the session object refuses any request
that is not a GET, except POSTs to the two Unisphere performance *query*
endpoints (/performance/<Category>/keys and /performance/<Category>/metrics),
which only read statistics. PUT, PATCH, DELETE and every other POST are blocked
before anything is sent. Use a Unisphere user with the Monitor role as well.
"""

import logging
import os
import re
import statistics
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote

import requests
import urllib3
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

log = logging.getLogger("powermax-mcp")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# Read-only HTTP layer
# ---------------------------------------------------------------------------

REST_ROOT = "/univmax/restapi"
_PERF_QUERY = re.compile(r"^/univmax/restapi/performance/[A-Za-z0-9_]+/(keys|metrics)/?$")


class ReadOnlyViolation(Exception):
    pass


def check_read_only(method: str, url: str) -> None:
    """Raise unless the request only reads data."""
    method = method.upper()
    path = requests.utils.urlparse(url).path
    if not path.startswith(REST_ROOT):
        raise ReadOnlyViolation(f"Blocked request outside Unisphere REST API: {path}")
    if method in ("GET", "HEAD"):
        return
    if method == "POST" and _PERF_QUERY.match(path):
        return
    raise ReadOnlyViolation(f"Blocked {method} {path}: this server is read-only")


class ReadOnlySession(requests.Session):
    def request(self, method, url, *args, **kwargs):
        check_read_only(method, url)
        return super().request(method, url, *args, **kwargs)


class Unisphere:
    def __init__(self, name, host, username, password, port="8443", verify="false",
                 api_version="", timeout="120"):
        self.name = name
        self.host = host
        self.base = f"https://{host}:{port}{REST_ROOT}"
        self.s = ReadOnlySession()
        self.s.auth = (username, password)
        self.s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        verify = (verify or "false").strip()
        if verify.lower() in ("false", "0", "no"):
            self.s.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        elif verify.lower() not in ("true", "1", "yes"):
            self.s.verify = verify  # path to a CA bundle
        self.timeout = float(timeout or 120)
        self._version = (api_version or "").strip() or None
        self._vlock = threading.Lock()

    # -- low level --
    def _do(self, method, path, params=None, body=None):
        r = self.s.request(method, self.base + path, params=params, json=body, timeout=self.timeout)
        if r.status_code == 404:
            raise LookupError(f"Not found: {path}")
        if r.status_code in (401, 403):
            raise PermissionError(f"Unisphere refused access ({r.status_code}) to {path}")
        if r.status_code >= 400:
            msg = r.text[:500]
            try:
                msg = r.json().get("message", msg)
            except Exception:
                pass
            raise RuntimeError(f"Unisphere error {r.status_code} on {path}: {msg}")
        return r.json() if r.content else {}

    def get(self, path, params=None):
        return self._do("GET", path, params=params)

    def perf_post(self, category, kind, body):
        return self._do("POST", f"/performance/{category}/{kind}", body=body)

    @property
    def version(self):
        with self._vlock:
            if not self._version:
                info = self.get("/version")
                v = info.get("api_version")
                if not v:  # e.g. "T9.2.1.6" -> "92"
                    m = re.search(r"(\d+)\.(\d+)", info.get("version", ""))
                    v = f"{m.group(1)}{m.group(2)}" if m else "100"
                self._version = str(v)
                log.info("Unisphere %s, REST API version %s", info.get("version"), self._version)
            return self._version

    def vget(self, path, params=None):
        return self.get(f"/{self.version}{path}", params=params)

    def iterate(self, resp, limit=None):
        """Return all rows of a paged (iterator) response, up to limit."""
        rows = list(resp.get("resultList", {}).get("result", []))
        count, page = int(resp.get("count") or 0), int(resp.get("maxPageSize") or 0)
        it = resp.get("id")
        start = len(rows) + 1
        while it and page and start <= count and (limit is None or len(rows) < limit):
            end = min(start + page - 1, count)
            rows += self.get(f"/common/Iterator/{it}/page", {"from": start, "to": end}).get("result", [])
            start = end + 1
        return rows if limit is None else rows[:limit]


# ---------------------------------------------------------------------------
# Multi-Unisphere registry (all instances configured from one Secret)
# ---------------------------------------------------------------------------

def _load_unispheres() -> dict:
    """UNISPHERE_<N>_HOST/_USERNAME/_PASSWORD (+ _NAME, _PORT, _VERIFY_SSL, _API_VERSION, _TIMEOUT)
    for any number of Unisphere servers; un-numbered UNISPHERE_HOST/... also works for one."""
    env = os.environ
    idx = sorted({int(m.group(1)) for k in env for m in [re.match(r"UNISPHERE_(\d+)_HOST$", k)] if m})
    prefixes = [f"UNISPHERE_{i}_" for i in idx]
    if not prefixes and env.get("UNISPHERE_HOST"):
        prefixes = ["UNISPHERE_"]
    out = {}
    for p in prefixes:
        missing = [k for k in ("HOST", "USERNAME", "PASSWORD") if not env.get(p + k)]
        if missing:
            raise SystemExit(f"{p}{missing[0]} is not set")
        name = (env.get(p + "NAME") or env[p + "HOST"]).strip()
        if name in out:
            raise SystemExit(f"Duplicate Unisphere name {name!r}")
        out[name] = Unisphere(name, env[p + "HOST"], env[p + "USERNAME"], env[p + "PASSWORD"],
                              port=env.get(p + "PORT", "8443"),
                              verify=env.get(p + "VERIFY_SSL", env.get("UNISPHERE_VERIFY_SSL", "false")),
                              api_version=env.get(p + "API_VERSION", ""),
                              timeout=env.get(p + "TIMEOUT", env.get("UNISPHERE_TIMEOUT", "120")))
    if not out:
        raise SystemExit("No Unisphere configured: set UNISPHERE_1_HOST, UNISPHERE_1_USERNAME, "
                         "UNISPHERE_1_PASSWORD (and _2_, _3_ ... for more)")
    return out


class Registry:
    MAP_TTL = 600

    def __init__(self):
        self._lock = threading.Lock()
        self._unis = None
        self._map, self._map_ts = None, 0.0

    @property
    def unispheres(self) -> dict:
        with self._lock:
            if self._unis is None:
                self._unis = _load_unispheres()
                log.info("Configured Unisphere servers: %s", ", ".join(self._unis))
            return self._unis

    def get(self, name: str) -> Unisphere:
        unis = self.unispheres
        if name:
            if name in unis:
                return unis[name]
            for u in unis.values():
                if u.host == name:
                    return u
            raise ValueError(f"Unknown unisphere {name!r}; configured: {list(unis)}")
        if len(unis) == 1:
            return next(iter(unis.values()))
        raise ValueError(f"Several Unisphere servers are configured, pass unisphere=one of {list(unis)}")

    def array_map(self, refresh=False) -> dict:
        """array serial -> list of {unisphere, local} for every Unisphere that sees it."""
        with self._lock:
            fresh = self._map is not None and time.time() - self._map_ts < self.MAP_TTL
        if fresh and not refresh:
            return self._map
        m, errors = {}, {}
        for name, u in self.unispheres.items():
            try:
                for a in u.vget("/system/symmetrix").get("symmetrixId", []):
                    try:
                        local = bool(u.vget(f"/system/symmetrix/{a}").get("local", True))
                    except Exception:
                        local = True
                    m.setdefault(a, []).append({"unisphere": name, "local": local})
            except Exception as e:
                errors[name] = str(e)
                log.warning("Unisphere %s unreachable while mapping arrays: %s", name, e)
        with self._lock:
            self._map, self._map_ts, self.map_errors = m, time.time(), errors
        return m

    def for_array(self, a: str) -> Unisphere:
        """Unisphere to use for an array: the one where it is local (performance data and
        full management live there), otherwise any that sees it."""
        unis = self.unispheres
        if len(unis) == 1:
            return next(iter(unis.values()))
        seen = self.array_map().get(a) or self.array_map(refresh=True).get(a)
        if not seen:
            raise LookupError(f"Array {a} is not managed by any configured Unisphere "
                              f"({list(unis)}). Call list_arrays to see what is available.")
        best = next((x for x in seen if x["local"]), seen[0])
        return unis[best["unisphere"]]


REG = Registry()
_PIN: dict = {}  # array -> unisphere name forced by caller


def U(a: str = "", unisphere: str = "") -> Unisphere:
    if unisphere:
        return REG.get(unisphere)
    if a:
        if a in _PIN:
            return REG.get(_PIN[a])
        return REG.for_array(a)
    return REG.get("")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def q(s: str) -> str:
    return quote(str(s), safe="")


def first_list(d: dict):
    for v in d.values():
        if isinstance(v, list):
            return v
    return []


def cap(items, limit):
    limit = max(1, min(int(limit), 5000))
    return {"total": len(items), "returned": min(len(items), limit), "items": items[:limit]}


def sid(array_id: str) -> str:
    a = (array_id or os.getenv("POWERMAX_DEFAULT_ARRAY", "")).strip()
    if not a:
        arrays = sorted(REG.array_map())
        if len(arrays) == 1:
            return arrays[0]
        raise ValueError(f"array_id is required; available arrays: {arrays}")
    if not re.fullmatch(r"\d{12}", a):
        raise ValueError("array_id must be the 12-digit serial, e.g. 000197900123")
    return a


def ms_to_iso(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return ms


def parse_time(t: str) -> int:
    """ISO-8601 (UTC if no zone) -> epoch ms."""
    dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def norm_wwn(w: str) -> str:
    return re.sub(r"[^0-9a-fA-F]", "", w).lower()


RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

# ---------------------------------------------------------------------------
# Guidance for the connecting model
# ---------------------------------------------------------------------------

INSTRUCTIONS = """\
You are connected to a READ-ONLY gateway to Dell PowerMax / VMAX storage arrays, through one or
more Unisphere for PowerMax servers. No tool can change anything on an array. Explore freely,
but never tell the user you changed, fixed, acknowledged or deleted something.

== IDENTIFIERS ==
- array_id: 12-digit serial, e.g. 000197900123. If unknown, call list_arrays. If exactly one array
  exists you may omit it. Each array is routed automatically to the Unisphere that manages it
  locally, so you normally never pass a Unisphere name, except for get_alerts, get_alert_summary
  and unisphere_get when you want one specific server.
- Storage group, host, host group, masking view and port group names are case-sensitive; copy
  them exactly from tool output.
- volume_id: 5-hex device id (00ABC). Director: FA-1D (front-end), RF/RE (SRDF), DF/DN (back-end),
  OR (FC/iSCSI/NVMe-oF front end on PowerMax 2500/8500). Port: director + number, e.g. FA-1D:4.
- WWPN/WWN may be given with or without colons, any case.
- All times are UTC. Convert to the user's local time when you present them if you know it.

== WORKFLOWS ==
Orientation / "how is the array":
  list_arrays -> get_array -> get_array_health -> list_srps (capacity) -> get_alert_summary.
Events ("any alerts/problems"):
  get_alerts (newest first, default last 24h). Narrow with severity="FATAL,CRITICAL",
  state="NEW", text="..." or object_type. Group repeated alerts and give counts, first/last time.
Logs ("who changed what"):
  get_audit_log for a window <= 24h (larger windows are slow on Unisphere). Filter with
  user_name, host_name or message. Summarise by user and action, then list notable entries.
Host / SAN mapping:
  find_wwpn(wwpn) -> host, masking views, storage groups, port groups, login state.
  get_masking_view -> array ports + volumes + host LUN ids. get_storage_group -> capacity,
  service level, volumes. find_volume_by_wwn maps a host's NAA/WWN back to the array volume.
Performance:
  1. get_performance_overview first (array KPIs, busiest and slowest storage groups, FE busy).
  2. get_performance for the object in question. category + id parameter:
     Array (none) | StorageGroup (storage_group) | FEDirector, BEDirector, RDFDirector (director)
     | FEPort (director + port) | Host (host) | Initiator (initiator) | PortGroup (port_group)
     | SRP (srp) | RDFS / RDFA (rdf_group) | Volume (volume). list_performance_categories shows
     what the array supports, list_performance_keys the valid object ids.
  3. metrics: "KPI" (default) is the right start; "ALL" returns every metric; or name them
     ("HostIOs,HostMBs,ResponseTime,ReadResponseTime,WriteResponseTime"). Wrong names return
     the list of valid ones.
  4. Each metric comes back as avg / max (+ time) / min / last over the window.
     data_format="Average": each 5-min sample is an interval average (default).
     data_format="Maximum": each sample is the interval peak -> use it for true peaks/spikes.
     For "average and peak", call twice (Average and Maximum) and report both.
  5. The window ends at the newest collected sample (usually 5-15 min behind now). Use
     minutes_back (default 60) or start/end in ISO-8601 UTC. Say which window you used.
Replication: get_replication(storage_group) for SnapVX snapshots and SRDF state of one SG;
  get_replication() for all RDF groups on the array.
Anything else: unisphere_get(path) can GET any REST endpoint (e.g. /sloprovisioning/symmetrix/
  <id>/srp/SRP_1, /system/symmetrix/<id>/director/FA-1D/port/4).

== READING THE NUMBERS (rules of thumb, not SLAs) ==
- Response times are ms. All-flash PowerMax front-end ResponseTime is typically well under 1 ms;
  sustained > 1 ms deserves a look, > 3-5 ms is usually a real problem. Reads served from flash
  are slower than writes absorbed by cache, so ReadResponseTime > WriteResponseTime is normal.
- High WriteResponseTime + high PercentCacheWP (write pending) -> back-end or SRDF/S pressure.
- FEDirector / FEPort PercentBusy sustained > 70% -> front-end saturation; compare HostIOs/HostMBs.
- One SG slow while the array, its ports and other SGs are fine -> usually host, HBA queue depth or
  SAN path. Check the fabric if MDS tools are available (CRC errors, txwait, slow drain on the
  switch ports where the host and array ports log in) and the server side if UCS tools are.
- SRDF/S: write response time on the R1 includes the link round trip; check RDFDirector busy and
  the remote array. SRDF/A: watch cycle time and RDFA metrics.
- Capacity: report SRP used %, subscription %, data reduction ratio; flag used > 80%.

== CROSS-SYSTEM TRACING (if other MCP servers are connected) ==
UCS Central find_wwpn / get_service_profile_vhbas -> host WWPNs and VSAN
-> MDS show_flogi_database / show_fcns_database / show_zoneset_active_vsan -> switch ports + zones
-> this server find_wwpn -> masking view, storage group, array ports.
Use the same WWPN at every hop and present the full path as a table.

== ANSWER STYLE ==
Lead with the conclusion, then the evidence (numbers, time window, object names), then the next
check you recommend. Say clearly when data is missing, stale, or a Unisphere was unreachable
(tools report unreachable_unispheres).
"""

mcp = FastMCP("powermax-readonly", instructions=INSTRUCTIONS)

# ---------------------------------------------------------------------------
# Inventory tools
# ---------------------------------------------------------------------------


@mcp.tool(annotations=RO)
def test_connection() -> dict:
    """Check every configured Unisphere: reachable, credentials OK, Unisphere and REST API version,
    and which arrays it manages (local or remote/SRDF). Run this first when something fails."""
    out = []
    for name, u in REG.unispheres.items():
        try:
            info = u.get("/version")
            arrays = u.vget("/system/symmetrix").get("symmetrixId", [])
            out.append({"unisphere": name, "host": u.host, "ok": True, "version": info.get("version"),
                        "api_version_used": u.version, "arrays": arrays})
        except Exception as e:
            out.append({"unisphere": name, "host": u.host, "ok": False, "error": str(e)})
    REG.array_map(refresh=True)
    return {"unispheres": out}


@mcp.tool(annotations=RO)
def list_unispheres() -> dict:
    """List configured Unisphere servers (name and host)."""
    return {"unispheres": [{"name": n, "host": u.host} for n, u in REG.unispheres.items()]}


@mcp.tool(annotations=RO)
def list_arrays(refresh: bool = False) -> dict:
    """List all PowerMax/VMAX arrays across every configured Unisphere (12-digit serials), with the
    Unisphere(s) that see each one and whether it is local there. Start here."""
    m = REG.array_map(refresh=refresh)
    rows = []
    for a, seen in sorted(m.items()):
        best = next((x for x in seen if x["local"]), seen[0])
        rows.append({"array_id": a, "managed_by": best["unisphere"], "seen_by": seen})
    out = {"arrays": rows}
    if getattr(REG, "map_errors", None):
        out["unreachable_unispheres"] = REG.map_errors
    return out


@mcp.tool(annotations=RO)
def get_array(array_id: str = "") -> dict:
    """Array details: model, PowerMaxOS/ucode version, local/remote, capacity and system settings."""
    a = sid(array_id)
    return U(a).vget(f"/system/symmetrix/{a}")


@mcp.tool(annotations=RO)
def get_array_health(array_id: str = "") -> dict:
    """Array health scores (overall, configuration, capacity, system utilisation, SG response, ...)."""
    a = sid(array_id)
    return U(a).vget(f"/system/symmetrix/{a}/health")


@mcp.tool(annotations=RO)
def list_srps(array_id: str = "") -> dict:
    """Storage resource pools with capacity, used/free, subscription, data reduction and efficiency."""
    a = sid(array_id)
    u = U(a)
    ids = u.vget(f"/sloprovisioning/symmetrix/{a}/srp").get("srpId", [])
    return {"srps": [u.vget(f"/sloprovisioning/symmetrix/{a}/srp/{q(s)}") for s in ids]}


@mcp.tool(annotations=RO)
def list_storage_groups(array_id: str = "", name_contains: str = "", limit: int = 500) -> dict:
    """List storage group names (filter by substring). Use get_storage_group for details."""
    a = sid(array_id)
    names = U(a).vget(f"/sloprovisioning/symmetrix/{a}/storagegroup").get("storageGroupId", [])
    if name_contains:
        names = [n for n in names if name_contains.lower() in n.lower()]
    return cap(sorted(names), limit)


@mcp.tool(annotations=RO)
def get_storage_group(storage_group: str, array_id: str = "", include_volumes: bool = True,
                      volume_limit: int = 200) -> dict:
    """Storage group details (capacity, service level, SRP, child SGs, masking views, compression)
    and optionally its volumes with size and WWN."""
    a = sid(array_id)
    u = U(a)
    sg = u.vget(f"/sloprovisioning/symmetrix/{a}/storagegroup/{q(storage_group)}")
    if include_volumes:
        resp = u.vget(f"/sloprovisioning/symmetrix/{a}/volume", {"storageGroupId": storage_group})
        vols = [r.get("volumeId") for r in u.iterate(resp, limit=volume_limit)]
        details = []
        for v in vols:
            d = u.vget(f"/sloprovisioning/symmetrix/{a}/volume/{q(v)}")
            details.append({k: d.get(k) for k in ("volumeId", "volume_identifier", "cap_gb",
                            "allocated_percent", "wwn", "type", "status", "emulation")})
        sg["volumes"] = details
        sg["volumes_total"] = int(resp.get("count") or len(vols))
    return sg


@mcp.tool(annotations=RO)
def get_volume(volume_id: str, array_id: str = "") -> dict:
    """Volume details: size, WWN, identifier, storage groups, allocation, status. volume_id like 00ABC."""
    a = sid(array_id)
    return U(a).vget(f"/sloprovisioning/symmetrix/{a}/volume/{q(volume_id.upper())}")


@mcp.tool(annotations=RO)
def find_volume_by_wwn(wwn: str, array_id: str = "") -> dict:
    """Find a volume from the WWN/NAA id the host sees (e.g. 60000970000197900123533030304142)."""
    a = sid(array_id)
    u = U(a)
    w = norm_wwn(wwn).upper()
    resp = u.vget(f"/sloprovisioning/symmetrix/{a}/volume", {"wwn": w})
    vols = [r.get("volumeId") for r in u.iterate(resp, limit=10)]
    return {"wwn": w, "volumes": [u.vget(f"/sloprovisioning/symmetrix/{a}/volume/{q(v)}") for v in vols]}


@mcp.tool(annotations=RO)
def list_hosts(array_id: str = "", name_contains: str = "", include_host_groups: bool = True) -> dict:
    """List hosts (initiator groups) and host groups."""
    a = sid(array_id)
    u = U(a)
    hosts = u.vget(f"/sloprovisioning/symmetrix/{a}/host").get("hostId", [])
    out = {"hosts": hosts}
    if include_host_groups:
        out["host_groups"] = u.vget(f"/sloprovisioning/symmetrix/{a}/hostgroup").get("hostGroupId", [])
    if name_contains:
        out = {k: [n for n in v if name_contains.lower() in n.lower()] for k, v in out.items()}
    return out


@mcp.tool(annotations=RO)
def get_host(host: str, array_id: str = "") -> dict:
    """Host details: initiators (WWPNs), masking views, host flags, port flags, LUN count."""
    a = sid(array_id)
    return U(a).vget(f"/sloprovisioning/symmetrix/{a}/host/{q(host)}")


@mcp.tool(annotations=RO)
def find_wwpn(wwpn: str, array_id: str = "") -> dict:
    """Trace a host WWPN through the array: initiator(s) -> host -> masking views -> storage groups and
    port groups, plus login state on the array ports. Pair with MDS/UCS tools for an end-to-end path."""
    a = sid(array_id)
    u = U(a)
    w = norm_wwn(wwpn)
    if len(w) != 16:
        raise ValueError("WWPN must have 16 hex digits")
    ids = u.vget(f"/sloprovisioning/symmetrix/{a}/initiator").get("initiatorId", [])
    matches = [i for i in ids if w in norm_wwn(i.split(":")[-1])]
    out = []
    for i in matches:
        d = u.vget(f"/sloprovisioning/symmetrix/{a}/initiator/{q(i)}")
        mvs = []
        for mv in d.get("maskingview", []) or []:
            try:
                m = u.vget(f"/sloprovisioning/symmetrix/{a}/maskingview/{q(mv)}")
                mvs.append({"masking_view": mv, "storage_group": m.get("storageGroupId"),
                            "port_group": m.get("portGroupId"), "host": m.get("hostId") or m.get("hostGroupId")})
            except LookupError:
                mvs.append({"masking_view": mv})
        out.append({"initiator": i, "host": d.get("host"), "host_group": d.get("hostGroup"),
                    "logged_in": d.get("logged_in"), "on_fabric": d.get("on_fabric"),
                    "array_ports": d.get("symmetrixPortKey"), "flags": d.get("flags_in_effect"),
                    "masking_views": mvs})
    return {"wwpn": w, "found": bool(out), "initiators": out}


@mcp.tool(annotations=RO)
def list_masking_views(array_id: str = "", name_contains: str = "") -> dict:
    """List masking view names."""
    a = sid(array_id)
    mvs = U(a).vget(f"/sloprovisioning/symmetrix/{a}/maskingview").get("maskingViewId", [])
    return {"masking_views": [m for m in mvs if name_contains.lower() in m.lower()]}


@mcp.tool(annotations=RO)
def get_masking_view(masking_view: str, array_id: str = "", include_connections: bool = True,
                     limit: int = 500) -> dict:
    """Masking view: host, port group, storage group, and connections (initiator, array port,
    volume, host LUN id, logged in)."""
    a = sid(array_id)
    u = U(a)
    mv = u.vget(f"/sloprovisioning/symmetrix/{a}/maskingview/{q(masking_view)}")
    if include_connections:
        c = u.vget(f"/sloprovisioning/symmetrix/{a}/maskingview/{q(masking_view)}/connections")
        conns = c.get("maskingViewConnection", [])
        mv["connections"] = conns[:limit]
        mv["connections_total"] = len(conns)
    return mv


@mcp.tool(annotations=RO)
def get_port_group(port_group: str, array_id: str = "") -> dict:
    """Port group details: member director ports and masking views."""
    a = sid(array_id)
    return U(a).vget(f"/sloprovisioning/symmetrix/{a}/portgroup/{q(port_group)}")


@mcp.tool(annotations=RO)
def list_directors(array_id: str = "", include_ports: bool = False) -> dict:
    """List directors (FA front-end, OR/RF replication, DS/DF back-end, EM...) with status;
    optionally their ports with WWN, speed and status."""
    a = sid(array_id)
    u = U(a)
    base = f"/system/symmetrix/{a}/director"
    try:
        ids = u.vget(base).get("directorId", [])
    except LookupError:  # older Unisphere: directors under sloprovisioning
        base = f"/sloprovisioning/symmetrix/{a}/director"
        ids = u.vget(base).get("directorId", [])
    out = []
    for d in ids:
        info = u.vget(f"{base}/{q(d)}")
        if include_ports:
            keys = u.vget(f"{base}/{q(d)}/port").get("symmetrixPortKey", [])
            info["ports"] = [u.vget(f"{base}/{q(d)}/port/{q(k['portId'])}") for k in keys]
        out.append(info)
    return {"directors": out}


@mcp.tool(annotations=RO)
def get_port(director: str, port: str, array_id: str = "") -> dict:
    """One director port: WWN, negotiated speed, status, port flags, number of logged-in initiators."""
    a = sid(array_id)
    u = U(a)
    for base in (f"/system/symmetrix/{a}/director", f"/sloprovisioning/symmetrix/{a}/director"):
        try:
            return u.vget(f"{base}/{q(director.upper())}/port/{q(port)}")
        except LookupError:
            continue
    raise LookupError(f"Port {director}:{port} not found")


@mcp.tool(annotations=RO)
def get_replication(storage_group: str = "", array_id: str = "") -> dict:
    """Replication status. With storage_group: its SnapVX snapshots and SRDF groups/state.
    Without: all RDF groups on the array (mode, remote array, link state)."""
    a = sid(array_id)
    u = U(a)
    if storage_group:
        out = {"storage_group": storage_group}
        try:
            out["replication"] = u.vget(f"/replication/symmetrix/{a}/storagegroup/{q(storage_group)}")
        except LookupError:
            out["replication"] = None
        try:
            out["snapshots"] = u.vget(f"/replication/symmetrix/{a}/storagegroup/{q(storage_group)}/snapshot").get("name", [])
        except LookupError:
            out["snapshots"] = []
        try:
            nums = u.vget(f"/replication/symmetrix/{a}/storagegroup/{q(storage_group)}/rdf_group").get("rdfgs", [])
            out["srdf"] = [u.vget(f"/replication/symmetrix/{a}/storagegroup/{q(storage_group)}/rdf_group/{n}")
                           for n in nums]
        except LookupError:
            out["srdf"] = []
        return out
    groups = u.vget(f"/replication/symmetrix/{a}/rdf_group").get("rdfGroupID", [])
    details = []
    for g in groups:
        n = g.get("rdfgNumber") if isinstance(g, dict) else g
        try:
            details.append(u.vget(f"/replication/symmetrix/{a}/rdf_group/{n}"))
        except LookupError:
            details.append(g)
    return {"rdf_groups": details}


# ---------------------------------------------------------------------------
# Events (alerts) and logs (audit)
# ---------------------------------------------------------------------------

_SEV = {"FATAL": 0, "CRITICAL": 1, "WARNING": 2, "MINOR": 3, "INFORMATION": 4, "NORMAL": 5}


@mcp.tool(annotations=RO)
def get_alert_summary(unisphere: str = "") -> dict:
    """Alert counts per array and severity (acknowledged/unacknowledged), for every Unisphere
    (or one, by name). Quick event overview."""
    unis = [REG.get(unisphere)] if unisphere else list(REG.unispheres.values())
    out = {}
    for u in unis:
        try:
            out[u.name] = u.vget("/system/alert_summary")
        except Exception as e:
            out[u.name] = {"error": str(e)}
    return {"by_unisphere": out}


@mcp.tool(annotations=RO)
def get_alerts(array_id: str = "", severity: str = "", state: str = "", since_hours: float = 24,
               alert_type: str = "", object_type: str = "", text: str = "",
               include_acknowledged: bool = True, unisphere: str = "", limit: int = 50) -> dict:
    """Unisphere alerts (array events), newest first, merged across all Unisphere servers.

    array_id: only alerts for that array (asks the Unisphere that manages it).
    severity: FATAL, CRITICAL, WARNING, MINOR, INFORMATION, NORMAL (comma-separate several).
    state: NEW, ACKNOWLEDGED, CLEARED. alert_type: ARRAY, PERFORMANCE, SERVER.
    since_hours: look-back window (0 = no time filter). object_type e.g. Director, Port, SRP.
    text: match in the alert description. unisphere: limit to one Unisphere by name.
    """
    base = {}
    if array_id:
        a = sid(array_id)
        base["array"] = a
        unis = [U(a, unisphere)]
    else:
        unis = [REG.get(unisphere)] if unisphere else list(REG.unispheres.values())
    if state:
        base["state"] = state.upper()
    if alert_type:
        base["type"] = alert_type.upper()
    if object_type:
        base["object_type"] = object_type
    if text:
        base["description"] = text
    if not include_acknowledged:
        base["acknowledged"] = "false"
    if since_hours and since_hours > 0:
        t = datetime.fromtimestamp(time.time() - since_hours * 3600, timezone.utc)
        base["created_date"] = ">" + t.strftime("%b-%d-%Y %H:%M:%S.000")
    sevs = [x.strip().upper() for x in severity.split(",") if x.strip()] or [None]
    lim = max(1, min(int(limit), 500))
    found, errors = [], {}
    for u in unis:
        try:
            ids = []
            for sv in sevs:
                p = dict(base, **({"severity": sv} if sv else {}))
                ids += u.vget("/system/alert", p).get("alertId", [])
            ids = list(dict.fromkeys(ids))
            ids.sort(key=lambda x: int(x) if str(x).isdigit() else 0, reverse=True)  # ids grow over time
            found.append((u, ids))
        except Exception as e:
            errors[u.name] = str(e)
    total = sum(len(ids) for _, ids in found)
    alerts = []
    for u, ids in found:
        for i in ids[:lim]:
            d = u.vget(f"/system/alert/{q(i)}")
            row = {k: d.get(k) for k in ("alertId", "created_date", "severity", "state", "type",
                   "array", "object", "object_type", "description", "acknowledged")}
            row["unisphere"] = u.name
            row["_ts"] = d.get("created_date_milliseconds") or _alert_ts(d.get("created_date"))
            alerts.append(row)
    alerts.sort(key=lambda x: x["_ts"] or 0, reverse=True)
    alerts = alerts[:lim]
    for r in alerts:
        r["created_utc"] = ms_to_iso(r.pop("_ts")) if r.get("_ts") else None
    out = {"total_matching": total, "returned": len(alerts), "filters": base, "alerts": alerts}
    if errors:
        out["unreachable_unispheres"] = errors
    return out


def _alert_ts(s):
    try:
        return int(datetime.strptime(s, "%b-%d-%Y %H:%M:%S.%f").replace(tzinfo=timezone.utc).timestamp() * 1000)
    except Exception:
        return 0


@mcp.tool(annotations=RO)
def get_audit_log(array_id: str = "", hours_back: float = 24, start: str = "", end: str = "",
                  user_name: str = "", host_name: str = "", message: str = "",
                  limit: int = 200) -> dict:
    """Array audit log: configuration changes, logins and API/CLI activity with user, host and
    application. Window = last hours_back hours, or start/end ISO-8601 (UTC). Keep it <= 24h."""
    a = sid(array_id)
    end_s = parse_time(end) // 1000 if end else int(time.time())
    start_s = parse_time(start) // 1000 if start else int(end_s - hours_back * 3600)
    if end_s - start_s > 7 * 86400:
        raise ValueError("Audit log window is limited to 7 days; narrow the range")
    params = [("entry_date", f">{start_s}"), ("entry_date", f"<{end_s}")]
    for k, v in (("user_name", user_name), ("host_name", host_name), ("message", message)):
        if v:
            params.append((k, v))
    u = U(a)
    resp = u.vget(f"/system/symmetrix/{a}/audit_log_record", params)
    rows = u.iterate(resp, limit=max(1, min(int(limit), 5000))) if resp.get("count") else []
    rows.sort(key=lambda r: r.get("entry_date", 0), reverse=True)
    for r in rows:
        if isinstance(r.get("entry_date"), (int, float)):
            ed = r["entry_date"]
            r["entry_date_utc"] = ms_to_iso(ed if ed > 1e11 else ed * 1000)
    return {"array_id": a, "window_utc": [ms_to_iso(start_s * 1000), ms_to_iso(end_s * 1000)],
            "total": int(resp.get("count") or 0), "returned": len(rows), "records": rows}


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

_NEW_KEY_CATEGORIES = {"Volume", "EMDirector", "Endpoint", "SDNASFileSystem", "SDNASInterface",
                       "SDNASNode", "SDNASServer"}
_ID_FIELDS = {
    "storage_group": "storageGroupId", "director": "directorId", "port": "portId",
    "host": "hostId", "initiator": "initiatorId", "port_group": "portGroupId",
    "srp": "srpId", "rdf_group": "rdfGroupId", "volume": "volumeId",
}


def _array_key(category):
    return "systemId" if category in _NEW_KEY_CATEGORIES else "symmetrixId"


def _last_available(a) -> int:
    keys = U(a).get("/performance/Array/keys")
    for k in keys.get("arrayInfo", []):
        if k.get("symmetrixId") == a:
            return int(k["lastAvailableDate"])
    raise LookupError(f"Array {a} is not registered for performance data collection in Unisphere")


def _window(a, minutes_back, start, end):
    if start or end:
        e = parse_time(end) if end else _last_available(a)
        s = parse_time(start) if start else e - int(minutes_back) * 60000
    else:
        e = _last_available(a)
        s = e - int(minutes_back) * 60000
    return s, e


def _summarise(rows, metrics):
    out = {}
    for m in metrics:
        pts = [(r.get("timestamp"), r.get(m)) for r in rows if isinstance(r.get(m), (int, float))]
        if not pts:
            continue
        vals = [v for _, v in pts]
        tmax, vmax = max(pts, key=lambda p: p[1])
        out[m] = {"avg": round(statistics.fmean(vals), 3), "max": round(vmax, 3),
                  "max_at_utc": ms_to_iso(tmax), "min": round(min(vals), 3),
                  "last": round(vals[-1], 3), "samples": len(vals)}
    return out


@mcp.tool(annotations=RO)
def list_performance_categories(array_id: str = "") -> dict:
    """Performance categories this array supports (Array, StorageGroup, FEDirector, FEPort, Host,
    Initiator, PortGroup, SRP, RDFDirector, RDFS, BEDirector, Board, DiskGroup, Volume, ...)."""
    a = sid(array_id)
    return {"categories": U(a).get(f"/performance/Array/help/{a}/categories").get("categoryName", [])}


@mcp.tool(annotations=RO)
def list_performance_metrics(category: str, array_id: str = "", kpi_only: bool = False) -> dict:
    """Metric names available for a category. kpi_only=True returns the key performance indicators."""
    a = sid(array_id)
    mode = "Kpi" if kpi_only else "All"
    r = U(a).get(f"/performance/Array/help/{a}/{q(category)}/metrics/{mode}")
    return {"category": category, "metrics": r.get("metricName", [])}


@mcp.tool(annotations=RO)
def list_performance_keys(category: str, array_id: str = "", director: str = "",
                          storage_group: str = "", limit: int = 500) -> dict:
    """Object ids that have performance data in a category, with first/last available sample time.
    FEPort/BEPort/RDFPort need director. Use this to get exact ids for get_performance."""
    a = sid(array_id)
    u = U(a)
    if category == "Array":
        r = u.get("/performance/Array/keys")
    else:
        body = {_array_key(category): a}
        if director:
            body["directorId"] = director.upper()
        if storage_group:
            body["storageGroupId"] = storage_group
        r = u.perf_post(category, "keys", body)
    items = first_list(r)
    for it in items:
        for k in ("firstAvailableDate", "lastAvailableDate"):
            if k in it:
                it[k + "_utc"] = ms_to_iso(it[k])
    return cap(items, limit)


@mcp.tool(annotations=RO)
def get_performance(category: str, array_id: str = "", storage_group: str = "", director: str = "",
                    port: str = "", host: str = "", initiator: str = "", port_group: str = "",
                    srp: str = "", rdf_group: str = "", volume: str = "", metrics: str = "KPI",
                    minutes_back: int = 60, start: str = "", end: str = "",
                    data_format: str = "Average", raw: bool = False, max_points: int = 60) -> dict:
    """Performance statistics for any category/object.

    category: e.g. Array, StorageGroup, FEDirector, FEPort, Host, Initiator, PortGroup, SRP,
              RDFDirector, RDFS, BEDirector, Volume.
    Object id params by category: StorageGroup->storage_group, FEDirector/RDFDirector/BEDirector->director,
              FEPort->director+port, Host->host, Initiator->initiator, PortGroup->port_group,
              SRP->srp, RDFS/RDFA->rdf_group, Volume->volume. Array needs none.
    metrics: "KPI" (default), "ALL", or comma-separated names (e.g. "HostIOs,ResponseTime,HostMBs").
    Window: last minutes_back minutes up to the newest sample, or start/end ISO-8601 UTC.
    data_format: Average or Maximum. Returns per-metric avg/max/min/last; raw=True adds the series
    (downsampled to max_points).
    """
    a = sid(array_id)
    u = U(a)
    if data_format.capitalize() not in ("Average", "Maximum"):
        raise ValueError("data_format must be Average or Maximum")
    mup = metrics.strip().upper()
    if mup in ("KPI", "ALL"):
        mode = "Kpi" if mup == "KPI" else "All"
        mlist = u.get(f"/performance/Array/help/{a}/{q(category)}/metrics/{mode}").get("metricName", [])
    else:
        mlist = [m.strip() for m in metrics.split(",") if m.strip()]
        avail = _available_metrics(a, category)
        bad = [m for m in mlist if avail and m not in avail]
        if bad:
            raise ValueError(f"Unknown metrics for {category}: {bad}. "
                             "Use list_performance_metrics to see valid names.")
    if not mlist:
        raise ValueError(f"No metrics resolved for category {category}")
    s, e = _window(a, minutes_back, start, end)
    body = {"startDate": s, "endDate": e, "dataFormat": data_format.capitalize(), "metrics": mlist,
            _array_key(category): a}
    ids = {"storage_group": storage_group, "director": director.upper(), "port": port, "host": host,
           "initiator": initiator, "port_group": port_group, "srp": srp, "rdf_group": rdf_group,
           "volume": volume.upper()}
    for k, v in ids.items():
        if v:
            body[_ID_FIELDS[k]] = v
    resp = u.perf_post(category, "metrics", body)
    rows = u.iterate(resp) if resp.get("resultList") else first_list(resp)
    rows.sort(key=lambda r: r.get("timestamp", 0))
    out = {"array_id": a, "category": category,
           "object": {k: v for k, v in ids.items() if v},
           "window_utc": [ms_to_iso(s), ms_to_iso(e)], "data_format": data_format.capitalize(),
           "samples": len(rows), "summary": _summarise(rows, mlist)}
    if not rows:
        out["note"] = "No samples in this window. Check list_performance_keys for data availability."
    if raw and rows:
        step = max(1, -(-len(rows) // max(1, int(max_points))))
        out["series"] = [dict(r, time_utc=ms_to_iso(r.get("timestamp"))) for r in rows[::step]]
    return out


_METRIC_CACHE: dict = {}


def _available_metrics(a, category):
    key = (a, category)
    if key not in _METRIC_CACHE:
        _METRIC_CACHE[key] = set(U(a).get(
            f"/performance/Array/help/{a}/{q(category)}/metrics/All").get("metricName", []))
    return _METRIC_CACHE[key]


def _pick(a, category, wanted):
    avail = _available_metrics(a, category)
    return [m for m in wanted if m in avail] if avail else wanted


@mcp.tool(annotations=RO)
def get_performance_overview(array_id: str = "", minutes_back: int = 60, top_n: int = 10,
                             max_storage_groups: int = 300) -> dict:
    """Array-wide performance snapshot: array KPIs, the busiest storage groups (IOPS, MB/s), storage
    groups with the worst response time, and front-end director busy %. Start performance work here."""
    from concurrent.futures import ThreadPoolExecutor

    a = sid(array_id)
    u = U(a)
    s, e = _window(a, minutes_back, "", "")

    def stats(category, body_ids, metrics):
        body = {"startDate": s, "endDate": e, "dataFormat": "Average", "metrics": metrics,
                _array_key(category): a, **body_ids}
        resp = u.perf_post(category, "metrics", body)
        rows = u.iterate(resp) if resp.get("resultList") else first_list(resp)
        return _summarise(rows, metrics)

    out = {"array_id": a, "window_utc": [ms_to_iso(s), ms_to_iso(e)]}
    arr_m = u.get(f"/performance/Array/help/{a}/Array/metrics/Kpi").get("metricName", []) or \
        _pick(a, "Array", ["HostIOs", "HostMBs", "HostReads", "HostWrites", "PercentCacheWP",
                            "ReadResponseTime", "WriteResponseTime"])
    out["array"] = stats("Array", {}, arr_m)

    sg_m = _pick(a, "StorageGroup", ["HostIOs", "HostMBs", "ResponseTime", "ReadResponseTime",
                                     "WriteResponseTime"])
    sgs = [k.get("storageGroupId") for k in first_list(u.perf_post("StorageGroup", "keys", {"symmetrixId": a}))]
    limit_sg = max(1, min(int(max_storage_groups), 2000))

    def sg_row(name):
        try:
            sm = stats("StorageGroup", {"storageGroupId": name}, sg_m)
        except Exception as ex:
            log.debug("SG %s: %s", name, ex)
            return None
        row = {"storage_group": name, **{m: sm.get(m, {}).get("avg") for m in sg_m}}
        row["ResponseTime_max"] = sm.get("ResponseTime", {}).get("max")
        return row

    with ThreadPoolExecutor(max_workers=int(os.getenv("PERF_WORKERS", "8"))) as ex:
        sg_rows = [r for r in ex.map(sg_row, sgs[:limit_sg]) if r]
    n = max(1, min(int(top_n), 50))
    out["top_storage_groups_by_iops"] = sorted(sg_rows, key=lambda r: r.get("HostIOs") or 0, reverse=True)[:n]
    busy = [r for r in sg_rows if (r.get("HostIOs") or 0) >= 50]
    out["worst_response_time_storage_groups"] = sorted(
        busy, key=lambda r: r.get("ResponseTime") or 0, reverse=True)[:n]
    out["notes"] = ["Worst-RT list only includes SGs averaging >= 50 IOPS to avoid idle-SG noise.",
                    "Response times are in ms; IO rates per second; MB/s for HostMBs."]
    if len(sgs) > limit_sg:
        out["notes"].append(f"Only {limit_sg} of {len(sgs)} storage groups were scanned.")

    fe_m = _pick(a, "FEDirector", ["PercentBusy", "HostIOs", "HostMBs"])

    def fe_row(d):
        try:
            sm = stats("FEDirector", {"directorId": d}, fe_m)
        except Exception:
            return None
        row = {"director": d, **{m: sm.get(m, {}).get("avg") for m in fe_m}}
        row["PercentBusy_max"] = sm.get("PercentBusy", {}).get("max")
        return row

    dirs = [k.get("directorId") for k in first_list(u.perf_post("FEDirector", "keys", {"symmetrixId": a}))]
    with ThreadPoolExecutor(max_workers=int(os.getenv("PERF_WORKERS", "8"))) as ex:
        fe = [r for r in ex.map(fe_row, dirs) if r]
    out["fe_directors"] = sorted(fe, key=lambda r: r.get("PercentBusy") or 0, reverse=True)
    return out


# ---------------------------------------------------------------------------
# Escape hatch
# ---------------------------------------------------------------------------

@mcp.tool(annotations=RO)
def unisphere_get(path: str, params: dict | None = None, versioned: bool = True,
                  unisphere: str = "", array_id: str = "") -> dict:
    """GET any Unisphere REST endpoint not covered by another tool. path is relative to
    /univmax/restapi/<version>, e.g. "/sloprovisioning/symmetrix/000197900123/srp/SRP_1".
    versioned=False for unversioned paths like "/performance/Array/keys". GET only.
    Pick the server with unisphere=<name>, or array_id to use the Unisphere that manages that array."""
    if not path.startswith("/") or ".." in path:
        raise ValueError("path must start with / and not contain ..")
    u = U(sid(array_id) if array_id else "", unisphere)
    return u.vget(path, params) if versioned else u.get(path, params)

# ---------------------------------------------------------------------------
# Prompts: ready-made workflows a client can offer to the user
# ---------------------------------------------------------------------------

@mcp.prompt()
def daily_health_check(array_id: str = "") -> str:
    """Morning health report for one array (or all arrays)."""
    target = f"PowerMax array {array_id}" if array_id else "every array from list_arrays"
    return (f"Produce a morning health report for {target}. For each array: get_array (model, "
            "PowerMaxOS), get_array_health, list_srps (used %, subscription %, data reduction), "
            "get_alerts since_hours=24 severity FATAL,CRITICAL,WARNING (group repeats), get_audit_log "
            "for the last 24h (configuration changes by user), get_performance_overview for 60 minutes, "
            "and get_replication() for RDF group state. End with a table of issues ranked by urgency "
            "and one next action each. Flag any Unisphere that was unreachable.")


@mcp.prompt()
def troubleshoot_host_latency(host_or_wwpn: str, array_id: str = "", hours: int = 2) -> str:
    """Investigate slow storage reported by a host."""
    return (f"A host reports slow storage: {host_or_wwpn}. Array: {array_id or 'find it with list_arrays/find_wwpn'}. "
            "1) Resolve host -> masking views -> storage groups -> port group (find_wwpn or get_host). "
            f"2) For each storage group, get_performance over the last {hours} hours with metrics "
            "HostIOs,HostMBs,ResponseTime,ReadResponseTime,WriteResponseTime, once Average and once Maximum. "
            "3) FEPort PercentBusy for every port in the port group, plus Host and Initiator categories. "
            "4) get_performance_overview to see whether the whole array is busy. "
            "5) get_alerts and get_audit_log over the same window for anything that coincides. "
            "6) If MDS or UCS tools are connected, check the fabric ports and the server vHBAs for the same WWPNs. "
            "Conclude: array, front-end ports, replication, or host/SAN side - with the numbers.")


@mcp.prompt()
def what_changed(hours: int = 24, array_id: str = "") -> str:
    """Explain recent changes and events on an array."""
    return (f"Summarise what changed on {('array ' + array_id) if array_id else 'each array'} in the last {hours} "
            "hours: get_audit_log grouped by user and action (split into windows of 24h if longer), and get_alerts "
            "for the same period. Put changes and alerts on one timeline and point out alerts that follow a change.")


@mcp.prompt()
def capacity_report(array_id: str = "") -> str:
    """Capacity and efficiency report."""
    return (f"Capacity report for {('array ' + array_id) if array_id else 'all arrays'}: list_srps (usable, used, "
            "free, subscription %, data reduction ratio), the 10 largest storage groups by capacity "
            "(list_storage_groups then get_storage_group include_volumes=False), and any capacity alerts "
            "(get_alerts text='capacity' since_hours=168). Flag SRPs above 80% used.")


@mcp.prompt()
def srdf_health(array_id: str = "") -> str:
    """Replication (SRDF / SnapVX) status."""
    return (f"Check replication on {('array ' + array_id) if array_id else 'all arrays'}: get_replication() for every "
            "RDF group (mode, state, remote array), get_performance category RDFDirector (PercentBusy) and RDFS/RDFA "
            "for busy groups over 60 minutes, and get_alerts text='RDF' since_hours=24. Report groups not in a "
            "healthy state (Synchronized / Consistent) first.")


if __name__ == "__main__":
    import mcp_auth
    REG.unispheres  # validate the Secret at startup, not on first call
    mcp_auth.run(mcp)
