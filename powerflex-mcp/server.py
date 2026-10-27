"""
Read-only MCP server for Dell PowerFlex (ScaleIO / VxFlex OS) through the PowerFlex REST API:
the Gateway (3.x) or PowerFlex Manager (4.x / 5.x).

Read-only is enforced at the HTTP layer: the session object refuses any request that is not a GET,
except a short list of POSTs that only read (sign-in, querySelectedStatistics, queryMdmCluster,
queryBySelectedIds / queryIdByKey, the 4.x metrics query). Every other POST, PUT, PATCH, DELETE and
any URL outside the REST API is blocked before it is sent. Use a Monitor (read-only) account as well.
"""

import logging
import os
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote

import requests
import urllib3
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

log = logging.getLogger("powerflex-mcp")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# Read-only HTTP layer
# ---------------------------------------------------------------------------

_PREFIXES = ("/api/", "/rest/", "/dtapi/")
_READ_POSTS = re.compile(
    r"^(/rest/auth/(login|refresh)"
    r"|/api/instances/querySelectedStatistics"
    r"|/api/instances/System/action/queryMdmCluster"
    r"|/api/types/[A-Za-z]+/instances/action/(queryBySelectedIds|queryIdByKey)"
    r"|/dtapi/rest/v1/metrics/query)/?$")


class ReadOnlyViolation(Exception):
    pass


def check_read_only(method: str, url: str) -> None:
    """Raise unless the request only reads data."""
    method = method.upper()
    path = requests.utils.urlparse(url).path
    if not path.startswith(_PREFIXES) or ".." in path.split("/"):
        raise ReadOnlyViolation(f"Blocked request outside the PowerFlex REST API: {path}")
    if method in ("GET", "HEAD"):
        return
    if method == "POST" and _READ_POSTS.match(path):
        return
    raise ReadOnlyViolation(f"Blocked {method} {path}: this server is read-only")


class ReadOnlySession(requests.Session):
    def request(self, method, url, *args, **kwargs):
        check_read_only(method, url)
        return super().request(method, url, *args, **kwargs)


class Gateway:
    """One PowerFlex Gateway (3.x: GET /api/login -> token) or PowerFlex Manager
    (4.x+: POST /rest/auth/login -> bearer token). Signs in again on 401 (4.x tokens live 5 min)."""

    def __init__(self, name, host, username, password, port="443", verify="false", timeout="60"):
        self.name, self.host = name, host
        self.base = f"https://{host}:{port}"
        self._user, self._pw = username, password
        self.s = ReadOnlySession()
        self.s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        verify = (verify or "false").strip()
        if verify.lower() in ("false", "0", "no"):
            self.s.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        elif verify.lower() not in ("true", "1", "yes"):
            self.s.verify = verify  # path to a CA bundle
        self.timeout = float(timeout or 60)
        self.api = None          # "manager" (4.x+) or "gateway" (3.x), found at first sign-in
        self._lock = threading.Lock()

    def _login(self):
        self.s.auth = None
        self.s.headers.pop("Authorization", None)
        r = self.s.post(self.base + "/rest/auth/login", json={"username": self._user, "password": self._pw},
                        timeout=self.timeout)
        if r.status_code == 200 and "access_token" in (r.json() if r.content else {}):
            self.s.headers["Authorization"] = "Bearer " + r.json()["access_token"]
            self.api = "manager"
            return
        if r.status_code in (401, 403):
            raise PermissionError(f"PowerFlex Manager {self.name} refused the sign-in ({r.status_code})")
        r = self.s.get(self.base + "/api/login", auth=(self._user, self._pw), timeout=self.timeout)
        if r.status_code in (401, 403):
            raise PermissionError(f"PowerFlex Gateway {self.name} refused the sign-in ({r.status_code})")
        if r.status_code >= 400:
            raise RuntimeError(f"PowerFlex sign-in failed on {self.name}: {r.status_code} {r.text[:200]}")
        self.s.auth = (self._user, r.json())   # 3.x: the token is the password from now on
        self.api = "gateway"

    def _do(self, method, path, params=None, body=None):
        with self._lock:
            if self.api is None:
                self._login()
        for attempt in (1, 2):
            r = self.s.request(method, self.base + path, params=params, json=body, timeout=self.timeout)
            if r.status_code == 401 and attempt == 1:
                with self._lock:
                    self._login()
                continue
            break
        if r.status_code == 404:
            raise LookupError(f"Not found: {path}")
        if r.status_code in (401, 403):
            raise PermissionError(f"PowerFlex refused access ({r.status_code}) to {path}")
        if r.status_code >= 400:
            msg = r.text[:500]
            try:
                msg = r.json().get("message", msg)
            except Exception:
                pass
            raise RuntimeError(f"PowerFlex error {r.status_code} on {path}: {msg}")
        return r.json() if r.content else {}

    def get(self, path, params=None):
        return self._do("GET", path, params=params)

    def post(self, path, body):
        return self._do("POST", path, body=body)


# ---------------------------------------------------------------------------
# Several gateways / systems from one Secret
# ---------------------------------------------------------------------------

def _load_gateways() -> dict:
    """POWERFLEX_<N>_HOST/_USERNAME/_PASSWORD (+ _NAME, _PORT, _VERIFY_SSL, _TIMEOUT) for any number of
    Gateways / PowerFlex Managers; un-numbered POWERFLEX_HOST/... also works for one."""
    env = os.environ
    idx = sorted({int(m.group(1)) for k in env for m in [re.match(r"POWERFLEX_(\d+)_HOST$", k)] if m})
    prefixes = [f"POWERFLEX_{i}_" for i in idx]
    if not prefixes and env.get("POWERFLEX_HOST"):
        prefixes = ["POWERFLEX_"]
    out = {}
    for p in prefixes:
        missing = [k for k in ("HOST", "USERNAME", "PASSWORD") if not env.get(p + k)]
        if missing:
            raise SystemExit(f"{p}{missing[0]} is not set")
        name = (env.get(p + "NAME") or env[p + "HOST"]).strip()
        if name in out:
            raise SystemExit(f"Duplicate PowerFlex name {name!r}")
        out[name] = Gateway(name, env[p + "HOST"], env[p + "USERNAME"], env[p + "PASSWORD"],
                            port=env.get(p + "PORT", "443"),
                            verify=env.get(p + "VERIFY_SSL", env.get("POWERFLEX_VERIFY_SSL", "false")),
                            timeout=env.get(p + "TIMEOUT", env.get("POWERFLEX_TIMEOUT", "60")))
    if not out:
        raise SystemExit("No PowerFlex configured: set POWERFLEX_1_HOST, POWERFLEX_1_USERNAME, "
                         "POWERFLEX_1_PASSWORD (and _2_, _3_ ... for more)")
    return out


class Registry:
    MAP_TTL = 600

    def __init__(self):
        self._lock = threading.Lock()
        self._gws = None
        self._map, self._map_ts, self.map_errors = None, 0.0, {}

    @property
    def gateways(self) -> dict:
        with self._lock:
            if self._gws is None:
                self._gws = _load_gateways()
                log.info("Configured PowerFlex gateways: %s", ", ".join(self._gws))
            return self._gws

    def system_map(self, refresh=False) -> dict:
        """system id -> {gateway, name}"""
        with self._lock:
            fresh = self._map is not None and time.time() - self._map_ts < self.MAP_TTL
        if fresh and not refresh:
            return self._map
        m, errors = {}, {}
        for name, g in self.gateways.items():
            try:
                for s in g.get("/api/types/System/instances"):
                    m[s["id"]] = {"gateway": name, "name": s.get("name") or ""}
            except Exception as e:
                errors[name] = str(e)
                log.warning("PowerFlex %s unreachable while listing systems: %s", name, e)
        with self._lock:
            self._map, self._map_ts, self.map_errors = m, time.time(), errors
        return m


REG = Registry()


def system(system_id: str = "") -> tuple:
    """(system id, Gateway) from an id, a system name, POWERFLEX_DEFAULT_SYSTEM, or the only system."""
    key = (system_id or os.getenv("POWERFLEX_DEFAULT_SYSTEM", "")).strip()
    m = REG.system_map()
    if not key:
        if len(m) == 1:
            key = next(iter(m))
        else:
            raise ValueError(f"system_id is required; systems: {_systems_brief(m)}")
    for attempt in (m, REG.system_map(refresh=True)):
        for sid, v in attempt.items():
            if key.lower() in (sid.lower(), v["name"].lower()):
                return sid, REG.gateways[v["gateway"]]
    raise LookupError(f"Unknown PowerFlex system {key!r}; systems: {_systems_brief(REG.system_map())}")


def _systems_brief(m):
    return [f"{k} ({v['name']})" if v["name"] else k for k, v in m.items()]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def q(s) -> str:
    return quote(str(s), safe="")


def ts_iso(sec):
    try:
        return datetime.fromtimestamp(int(sec), timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return sec


def instances(g, typ):
    return g.get(f"/api/types/{typ}/instances")


def related(g, typ, oid, rel):
    return g.get(f"/api/instances/{typ}::{q(oid)}/relationships/{rel}")


def resolve(g, typ, key: str) -> dict:
    """An object of a type by id or (case-insensitive) name."""
    key = (key or "").strip()
    if re.fullmatch(r"[0-9a-fA-F]{16}", key):
        try:
            return g.get(f"/api/instances/{typ}::{key.lower()}")
        except LookupError:
            pass
    objs = instances(g, typ)
    for o in objs:
        if key.lower() in (str(o.get("id", "")).lower(), str(o.get("name") or "").lower()):
            return o
    names = sorted(str(o.get("name") or o.get("id")) for o in objs)
    raise LookupError(f"No {typ} {key!r}. Known ({len(names)}): {names[:30]}")


_FIELDS = {
    "ProtectionDomain": ["id", "name", "protectionDomainState", "rebuildNetworkThrottlingEnabled",
                         "rebalanceNetworkThrottlingEnabled", "overallIoNetworkThrottlingEnabled", "fglDefaultNumConcurrentWrites"],
    "StoragePool": ["id", "name", "protectionDomainId", "mediaType", "dataLayout", "sparePercentage",
                    "rebuildEnabled", "rebalanceEnabled", "zeroPaddingEnabled", "compressionMethod",
                    "useRmcache", "useRfcache", "capacityAlertHighThreshold", "capacityAlertCriticalThreshold",
                    "persistentChecksumState", "rebuildIoPriorityPolicy"],
    "Sds": ["id", "name", "sdsState", "mdmConnectionState", "membershipState", "maintenanceState",
            "protectionDomainId", "faultSetId", "ipList", "drlMode", "rmcacheEnabled", "onVmWare",
            "softwareVersionInfo", "authenticationError", "sdsDecoupled", "fglNumConcurrentWrites"],
    "Sdc": ["id", "name", "sdcIp", "sdcIps", "sdcGuid", "mdmConnectionState", "sdcApproved", "osType",
            "softwareVersionInfo", "perfProfile", "hostOsFullType", "systemId", "peerMdmId", "sdcType"],
    "Volume": ["id", "name", "sizeInKb", "volumeType", "storagePoolId", "vtreeId", "ancestorVolumeId",
               "creationTime", "mappedSdcInfo", "accessModeLimit", "compressionMethod", "dataLayout",
               "volumeReplicationState", "replicationTimeStamp", "lockedAutoSnapshot", "snplIdOfAutoSnapshot",
               "useRmcache", "nsid", "genType"],
    "Device": ["id", "name", "deviceCurrentPathName", "sdsId", "storagePoolId", "deviceState", "errorState",
               "mediaType", "capacityLimitInKb", "maxCapacityInKb", "ssdEndOfLifeState", "temperatureState",
               "mediaFailureState", "deviceOriginalPathName", "aggregatedState", "accelerationPoolId"],
    "FaultSet": ["id", "name", "protectionDomainId"],
}


def row(typ, o: dict, full=False) -> dict:
    if full:
        r = dict(o)
    else:
        r = {k: o[k] for k in _FIELDS.get(typ, o) if o.get(k) not in (None, "", [])}
    for k in list(r):
        if k.endswith("InKb") and isinstance(r[k], (int, float)):
            r[k[:-4] + "_gb"] = round(r.pop(k) / 1048576, 2)
    if isinstance(r.get("creationTime"), (int, float)):
        r["creationTime_utc"] = ts_iso(r.pop("creationTime"))
    if r.get("mappedSdcInfo"):
        r["mappedSdcInfo"] = [{k: m.get(k) for k in ("sdcId", "sdcName", "sdcIp", "accessMode",
                               "limitIops", "limitBwInMbps") if m.get(k) not in (None, "")}
                              for m in r["mappedSdcInfo"]]
    r.pop("links", None)
    return r


def cap(items, limit):
    limit = max(1, min(int(limit), 5000))
    return {"total": len(items), "returned": min(len(items), limit), "items": items[:limit]}


# ---------------------------------------------------------------------------
# Statistics: PowerFlex returns live counters; turn them into rates, latency and GB
# ---------------------------------------------------------------------------

_KPI = re.compile(r"^(userData|primary|secondary|total|fwdRebuild|bckRebuild|normRebuild|rebalance)\w*(Bwc|Latency)$"
                  r"|CapacityInKb$|InUseInKb$|Ratio$|^num|[Ee]fficiency")


def derive(stats: dict, only=None) -> dict:
    """Bwc {numSeconds, totalWeightInKb, numOccured} -> _iops and _mbps; *Latency -> _ms
    (totalWeightInKb / numOccured is microseconds); *InKb -> _gb."""
    out = {}
    for k, v in stats.items():
        if only is not None and k not in only:
            continue
        if isinstance(v, dict) and "numOccured" in v and "totalWeightInKb" in v:
            n, w, secs = v.get("numOccured") or 0, v.get("totalWeightInKb") or 0, v.get("numSeconds") or 0
            if k.endswith("Latency"):
                out[k + "_ms"] = round(w / n / 1000, 3) if n else 0.0
            else:
                out[k + "_iops"] = round(n / secs, 1) if secs else 0.0
                out[k + "_mbps"] = round(w / secs / 1024, 2) if secs else 0.0
        elif k.endswith("InKb") and isinstance(v, (int, float)):
            out[k[:-4] + "_gb"] = round(v / 1048576, 2)
        elif k != "links":
            out[k] = v
    return out


def capacity_view(st: dict) -> dict:
    """Net (usable, one copy) used % when the counters exist, else raw used % of (max - spare)."""
    gb = lambda k: round(st[k] / 1048576, 2) if isinstance(st.get(k), (int, float)) else None
    out = {}
    if gb("netCapacityInUseInKb") is not None and gb("netUnusedCapacityInKb") is not None:
        used, free = gb("netCapacityInUseInKb"), gb("netUnusedCapacityInKb")
        out.update(net_used_gb=used, net_free_gb=free,
                   net_used_pct=round(100 * used / (used + free), 1) if used + free else 0.0)
    mx, spare, inuse = gb("maxCapacityInKb"), gb("spareCapacityInKb") or 0, gb("capacityInUseInKb")
    if mx and inuse is not None:
        out.update(raw_max_gb=mx, raw_spare_gb=spare, raw_in_use_gb=inuse,
                   raw_used_pct=round(100 * inuse / (mx - spare), 1) if mx > spare else None)
    for k in ("snapCapacityInUseInKb", "thickCapacityInUseInKb", "thinCapacityInUseInKb",
              "thinCapacityAllocatedInKb", "degradedHealthyCapacityInKb", "degradedFailedCapacityInKb",
              "failedCapacityInKb", "inMaintenanceCapacityInKb", "unreachableUnusedCapacityInKb"):
        if gb(k):
            out[k[:-4] + "_gb"] = gb(k)
    for k, v in st.items():
        if re.search(r"Ratio$|[Ee]fficiency", k) and isinstance(v, (int, float)):
            out[k] = round(v, 2)
    return out


def io_view(st: dict) -> dict:
    """Host IO of an object: IOPS, MB/s and latency (read / write / total)."""
    d = derive(st)
    out = {}
    for side in ("Read", "Write"):
        for pre in ("userData", "primary"):
            if f"{pre}{side}Bwc_iops" in d:
                out[f"{side.lower()}_iops"] = d[f"{pre}{side}Bwc_iops"]
                out[f"{side.lower()}_mbps"] = d[f"{pre}{side}Bwc_mbps"]
                break
        if f"userDataSdc{side}Latency_ms" in d:
            out[f"{side.lower()}_latency_ms"] = d[f"userDataSdc{side}Latency_ms"]
    if "read_iops" in out or "write_iops" in out:
        out["total_iops"] = round(out.get("read_iops", 0) + out.get("write_iops", 0), 1)
        out["total_mbps"] = round(out.get("read_mbps", 0) + out.get("write_mbps", 0), 2)
    return out


def summarise(samples: list) -> dict:
    """One sample -> the values; several -> avg / max / min / last per numeric value."""
    if len(samples) == 1:
        return samples[0]
    out = {}
    for k in samples[-1]:
        vals = [s[k] for s in samples if isinstance(s.get(k), (int, float)) and not isinstance(s.get(k), bool)]
        if len(vals) == len(samples):
            out[k] = {"avg": round(statistics.fmean(vals), 3), "max": max(vals), "min": min(vals), "last": vals[-1]}
        else:
            out[k] = samples[-1][k]
    return out


def sampled(fn, samples, interval_seconds):
    samples = max(1, min(int(samples), 60))
    interval = max(1.0, float(interval_seconds))
    if samples * interval > 300:
        raise ValueError("samples * interval_seconds must be <= 300 (PowerFlex keeps no history in the API; "
                         "use Grafana / CloudIQ / PowerFlex Manager for longer windows)")
    out = []
    for i in range(samples):
        if i:
            time.sleep(interval)
        out.append(fn())
    return out


def stats_of(g, typ, oid):
    return g.get(f"/api/instances/{typ}::{q(oid)}/relationships/Statistics")


_IO_PROPS = {"Volume": ["userDataReadBwc", "userDataWriteBwc", "userDataSdcReadLatency", "userDataSdcWriteLatency"],
             "Sdc": ["userDataReadBwc", "userDataWriteBwc", "userDataSdcReadLatency", "userDataSdcWriteLatency"],
             "Sds": ["primaryReadBwc", "primaryWriteBwc", "totalReadBwc", "totalWriteBwc"]}


def bulk_stats(g, typ, ids, props=None, workers=8):
    """id -> statistics for many objects: one querySelectedStatistics call, else one GET each."""
    props = props or _IO_PROPS[typ]
    try:
        r = g.post("/api/instances/querySelectedStatistics",
                   {"selectedStatisticsList": [{"type": typ, "allIds": "", "properties": props}]})
        by_id = r.get(typ) if isinstance(r, dict) else None
        if isinstance(by_id, dict) and by_id:
            return by_id
    except (RuntimeError, LookupError) as e:
        log.info("querySelectedStatistics for %s not usable (%s); one call per object", typ, e)

    def one(i):
        try:
            return i, stats_of(g, typ, i)
        except Exception:
            return i, None
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return {i: s for i, s in ex.map(one, ids) if s is not None}


RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

# ---------------------------------------------------------------------------
# Guidance for the connecting model
# ---------------------------------------------------------------------------

INSTRUCTIONS = """\
You are connected to a READ-ONLY gateway to Dell PowerFlex (ScaleIO / VxFlex OS) systems, through
their PowerFlex Gateway (3.x) or PowerFlex Manager (4.x / 5.x) REST API. No tool can change anything.
Explore freely, but never tell the user you changed, fixed, acknowledged or removed something; for a
change give the exact steps (PowerFlex Manager GUI or scli) for the user to run.

== OBJECTS AND IDS ==
System (MDM cluster) > Protection Domain (PD) > Storage Pool (SP) > Volumes, built from SDS (storage
servers) and their Devices (disks); Fault Sets group SDSs that may fail together. SDC = the client
driver on a host (ESXi, Linux, Windows); volumes are mapped to SDCs. SDR / RCG = replication;
SDT / Host = NVMe over TCP (4.x+).
- Ids are 16 hex characters. Every tool also accepts the object's name (case-insensitive).
- system_id may be omitted when there is one system; it accepts the id or the system name.
- Linux sees a volume as /dev/disk/by-id/emc-vol-<systemId>-<volumeId>; ESXi as an eui. id;
  find_volume takes any of these, a name or an id.
- Statistics are LIVE: rates over the last few seconds, there is no history in the API. For an average
  and a peak, use samples (e.g. samples=6, interval_seconds=10 = one minute) and say so. For hours or
  days, say that history lives in PowerFlex Manager / CloudIQ / Grafana, not here.
- Times are UTC.

== WORKFLOWS ==
Orientation / "how is PowerFlex": list_systems -> get_health (one call: MDM cluster, PDs, SDS, SDC,
  devices, pools, rebuild / rebalance, alerts) -> get_capacity -> get_performance_overview.
Alerts: get_alerts (newest first). Explain SIO / dial-home codes from the docs library when connected.
Capacity: get_capacity (system, each PD and pool: net used %, raw, spare, snapshots, thin/thick,
  degraded / failed capacity, compression and efficiency ratios).
Performance: get_performance_overview (system IO, pools, top volumes / SDCs / SDSs by IOPS, worst
  latency volumes and SDCs), then get_statistics for one object (properties "KPI" default, "ALL", or
  raw names from list_statistics_properties).
Host mapping: get_sdc (its volumes), get_volume (its SDCs, snapshots in the same VTree, pool, PD),
  find_volume for an id the host shows.
Rebuild / rebalance / degraded data: get_health, then get_storage_pool for the pool (rebuild and
  rebalance rates, pending capacity) and list_devices problems_only=True.
Replication: get_replication (peer systems, RCGs with state and RPO; one RCG for its pairs).
Anything else: powerflex_get(path) for any GET of the REST API; metrics_query for the 4.x+ metrics API.

== READING THE NUMBERS (rules of thumb, not SLAs) ==
- Latency is ms seen by the SDCs (userDataSdc*Latency). All-flash PowerFlex is usually well under
  1 ms; sustained > 2 ms deserves a look, > 5 ms is a real problem. Write latency includes the
  second copy on another SDS, so it is normally a bit higher than reads.
- One volume or SDC slow while its pool and others are fine -> host side (queue depth, CPU, network
  of that host). Many volumes in one pool slow -> pool / SDS / devices / rebuild; check
  rebuild / rebalance IO, SDS IO and device errors at the same moment.
- degraded / failed capacity > 0 means data is not fully protected right now; rebuild must finish
  (pending rebuild capacity -> 0). failed capacity > 0 is urgent.
- Capacity: net used % above the pool's capacityAlertHighThreshold (often 80%) is a warning, above
  capacityAlertCriticalThreshold (often 90%) critical. Spare must stay >= the largest SDS / fault set.
- SDS not Connected / not Joined, device errorState other than None, MDM cluster not ClusteredNormal,
  SDC disconnected: report each with its name, IP and PD.

== ANSWER STYLE ==
Lead with the conclusion, then the evidence (numbers, sample window, object names), then the next
check. Say clearly when data is missing or a gateway was unreachable (unreachable_gateways).
"""

mcp = FastMCP("powerflex-readonly", instructions=INSTRUCTIONS)

# ---------------------------------------------------------------------------
# Systems and health
# ---------------------------------------------------------------------------


@mcp.tool(annotations=RO)
def test_connection() -> dict:
    """Check every configured PowerFlex Gateway / Manager: reachable, sign-in OK, API kind (gateway 3.x
    or manager 4.x+), REST version and the systems it manages. Run this first when something fails."""
    out = []
    for name, g in REG.gateways.items():
        try:
            systems = g.get("/api/types/System/instances")
            try:
                version = g.get("/api/version")
            except Exception:
                version = None
            out.append({"gateway": name, "host": g.host, "ok": True, "api": g.api, "rest_version": version,
                        "systems": [{"id": s["id"], "name": s.get("name"),
                                     "version": s.get("systemVersionName")} for s in systems]})
        except Exception as e:
            out.append({"gateway": name, "host": g.host, "ok": False, "error": str(e)})
    REG.system_map(refresh=True)
    return {"gateways": out}


@mcp.tool(annotations=RO)
def list_systems(refresh: bool = False) -> dict:
    """All PowerFlex systems (MDM clusters) across the configured gateways: id, name, gateway. Start here."""
    m = REG.system_map(refresh=refresh)
    out = {"systems": [{"system_id": k, **v} for k, v in sorted(m.items())]}
    if REG.map_errors:
        out["unreachable_gateways"] = REG.map_errors
    return out


@mcp.tool(annotations=RO)
def get_system(system_id: str = "") -> dict:
    """System details: version, MDM cluster (mode, state, primary / secondary / tie-breaker nodes),
    capacity alert thresholds, restricted SDC mode, install id, and object counts."""
    sid, g = system(system_id)
    s = g.get(f"/api/instances/System::{sid}")
    s.pop("links", None)
    try:
        s["mdmCluster"] = g.post("/api/instances/System/action/queryMdmCluster", {})
    except Exception as e:
        s["mdmCluster"] = {"error": str(e)}
    try:
        st = stats_of(g, "System", sid)
        s["counts"] = {k: v for k, v in st.items() if k.startswith("num") and isinstance(v, int)}
    except Exception:
        pass
    return s


def _bad(o, field, good):
    v = o.get(field)
    return v is not None and v not in good


@mcp.tool(annotations=RO)
def get_health(system_id: str = "") -> dict:
    """One-call health check: MDM cluster state, protection domains, SDS (state, MDM connection,
    membership, maintenance), SDC connections, device errors, pool degraded / failed / pending rebuild
    capacity and used %, rebuild and rebalance activity, and alert counts by severity."""
    sid, g = system(system_id)
    issues, counts = [], {}

    def issue(sev, obj, text, **extra):
        issues.append({"severity": sev, "object": obj, "issue": text, **extra})

    try:
        mdm = g.post("/api/instances/System/action/queryMdmCluster", {})
        state = mdm.get("clusterState")
        counts["mdm_cluster"] = {"state": state, "mode": mdm.get("clusterMode"),
                                 "good_nodes": mdm.get("goodNodesNum"), "good_replicas": mdm.get("goodReplicasNum")}
        if state and state != "ClusteredNormal":
            issue("critical", "MDM cluster", f"cluster state {state}", mode=mdm.get("clusterMode"))
    except Exception as e:
        counts["mdm_cluster"] = {"error": str(e)}

    pds = {p["id"]: p for p in instances(g, "ProtectionDomain")}
    counts["protection_domains"] = len(pds)
    for p in pds.values():
        if _bad(p, "protectionDomainState", ("Active",)):
            issue("critical", f"PD {p.get('name')}", f"state {p['protectionDomainState']}")
    pdn = lambda i: (pds.get(i) or {}).get("name") or i

    sds = instances(g, "Sds")
    counts["sds"] = len(sds)
    for s in sds:
        probs = [f"{f}={s[f]}" for f, good in (("sdsState", ("Normal",)), ("mdmConnectionState", ("Connected",)),
                 ("membershipState", ("Joined",)), ("maintenanceState", ("NoMaintenance",)))
                 if _bad(s, f, good)]
        if probs:
            issue("critical" if "mdmConnectionState" in " ".join(probs) else "warning", f"SDS {s.get('name')}",
                  ", ".join(probs), ips=[i.get("ip") for i in s.get("ipList") or []], pd=pdn(s.get("protectionDomainId")))

    sdcs = instances(g, "Sdc")
    down = [c for c in sdcs if _bad(c, "mdmConnectionState", ("Connected",))]
    counts["sdc"] = {"total": len(sdcs), "disconnected": len(down)}
    for c in down[:50]:
        issue("warning", f"SDC {c.get('name') or c.get('sdcIp')}", f"mdmConnectionState={c.get('mdmConnectionState')}",
              ip=c.get("sdcIp"))

    devs = instances(g, "Device")
    bad_devs = [d for d in devs if _bad(d, "deviceState", ("Normal",)) or _bad(d, "errorState", ("None",))]
    counts["devices"] = {"total": len(devs), "with_problems": len(bad_devs)}
    sds_name = {s["id"]: s.get("name") for s in sds}
    for d in bad_devs[:100]:
        issue("critical" if "Fail" in str(d.get("deviceState")) + str(d.get("errorState")) else "warning",
              f"device {d.get('name') or d.get('deviceCurrentPathName')} on SDS {sds_name.get(d.get('sdsId'))}",
              f"deviceState={d.get('deviceState')}, errorState={d.get('errorState')}", path=d.get("deviceCurrentPathName"))

    pools = instances(g, "StoragePool")
    counts["storage_pools"] = len(pools)
    pool_rows = []
    for p in pools:
        try:
            st = stats_of(g, "StoragePool", p["id"])
        except Exception as e:
            pool_rows.append({"pool": p.get("name"), "error": str(e)})
            continue
        c = capacity_view(st)
        d = derive(st)
        r = {"pool": p.get("name"), "pd": pdn(p.get("protectionDomainId")),
             "used_pct": c.get("net_used_pct", c.get("raw_used_pct"))}
        risky = {k[:-4] + "_gb": round(v / 1048576, 2) for k, v in st.items()
                 if re.search(r"(degraded|failed|pending|inMaintenance|unreachable)\w*CapacityInKb$", k, re.I)
                 and isinstance(v, (int, float)) and v > 0}
        rebuild = {k: v for k, v in d.items() if re.search(r"(Rebuild|rebalance)\w*_mbps$", k) and v}
        r.update(risky)
        if rebuild:
            r["rebuild_rebalance_mbps"] = rebuild
        pool_rows.append(r)
        if any("failed" in k.lower() for k in risky):
            issue("critical", f"pool {p.get('name')}", "failed capacity > 0 (data without a copy)", **risky)
        elif any("degraded" in k.lower() for k in risky):
            issue("warning", f"pool {p.get('name')}", "degraded capacity > 0 (rebuild needed / running)", **risky)
        hi, crit = p.get("capacityAlertHighThreshold") or 80, p.get("capacityAlertCriticalThreshold") or 90
        u = r["used_pct"]
        if isinstance(u, (int, float)) and u >= hi:
            issue("critical" if u >= crit else "warning", f"pool {p.get('name')}",
                  f"used {u}% (thresholds {hi}% / {crit}%)")

    try:
        al = _alerts(g)
        by = {}
        for a in al:
            by[a.get("severity")] = by.get(a.get("severity"), 0) + 1
        counts["alerts"] = by
    except Exception as e:
        counts["alerts"] = {"error": str(e)}

    order = {"critical": 0, "warning": 1}
    issues.sort(key=lambda i: order.get(i["severity"], 2))
    return {"system_id": sid, "status": "OK" if not issues else
            ("CRITICAL" if issues[0]["severity"] == "critical" else "WARNING"),
            "issues": issues, "counts": counts, "pools": pool_rows}


@mcp.tool(annotations=RO)
def get_capacity(system_id: str = "") -> dict:
    """Capacity for the system, every protection domain and every storage pool: net used / free and
    used %, raw max / spare / in use, snapshots, thin / thick, degraded / failed capacity,
    compression and efficiency ratios, alert thresholds."""
    sid, g = system(system_id)
    out = {"system_id": sid, "system": capacity_view(stats_of(g, "System", sid))}
    pds = instances(g, "ProtectionDomain")
    out["protection_domains"] = [{"pd": p.get("name"), "id": p["id"], **capacity_view(stats_of(g, "ProtectionDomain", p["id"]))}
                                 for p in pds]
    pdn = {p["id"]: p.get("name") for p in pds}
    out["storage_pools"] = [{"pool": p.get("name"), "id": p["id"], "pd": pdn.get(p.get("protectionDomainId")),
                             "media": p.get("mediaType"), "layout": p.get("dataLayout"),
                             "thresholds_pct": [p.get("capacityAlertHighThreshold"), p.get("capacityAlertCriticalThreshold")],
                             **capacity_view(stats_of(g, "StoragePool", p["id"]))}
                            for p in instances(g, "StoragePool")]
    out["notes"] = ["net_* = usable capacity (one copy); raw_* counts both copies of the data.",
                    "raw_used_pct = in use / (max - spare)."]
    return out


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


@mcp.tool(annotations=RO)
def list_protection_domains(system_id: str = "") -> dict:
    """Protection domains with state and network throttling settings."""
    _, g = system(system_id)
    return {"protection_domains": [row("ProtectionDomain", p) for p in instances(g, "ProtectionDomain")]}


@mcp.tool(annotations=RO)
def list_storage_pools(system_id: str = "", protection_domain: str = "") -> dict:
    """Storage pools: PD, media type, data layout (medium / fine granularity), spare %, rebuild /
    rebalance enabled, compression, capacity alert thresholds. Filter by protection domain (id or name)."""
    _, g = system(system_id)
    pools = instances(g, "StoragePool")
    if protection_domain:
        pd = resolve(g, "ProtectionDomain", protection_domain)
        pools = [p for p in pools if p.get("protectionDomainId") == pd["id"]]
    return {"storage_pools": [row("StoragePool", p) for p in pools]}


@mcp.tool(annotations=RO)
def get_storage_pool(storage_pool: str, system_id: str = "", full: bool = False) -> dict:
    """One storage pool (id or name): settings, capacity, live IO, rebuild / rebalance rates and pending
    capacity, and its devices grouped by state. full=True returns every field and raw statistic."""
    _, g = system(system_id)
    p = resolve(g, "StoragePool", storage_pool)
    st = stats_of(g, "StoragePool", p["id"])
    d = derive(st)
    out = {"pool": row("StoragePool", p, full), "capacity": capacity_view(st), "io": io_view(st),
           "rebuild_rebalance": {k: v for k, v in d.items() if re.search(r"Rebuild|rebalance|pending", k, re.I) and v}}
    try:
        devs = related(g, "StoragePool", p["id"], "Device")
        states = {}
        for x in devs:
            k = f"{x.get('deviceState')}/{x.get('errorState')}"
            states[k] = states.get(k, 0) + 1
        out["devices"] = {"total": len(devs), "by_state_error": states}
    except Exception as e:
        out["devices"] = {"error": str(e)}
    if full:
        out["statistics"] = d
    return out


@mcp.tool(annotations=RO)
def list_sds(system_id: str = "", protection_domain: str = "", problems_only: bool = False) -> dict:
    """SDS (storage data servers): state, MDM connection, membership, maintenance mode, IPs and roles,
    PD, fault set, version. problems_only=True keeps those not Normal / Connected / Joined / NoMaintenance."""
    _, g = system(system_id)
    sds = instances(g, "Sds")
    if protection_domain:
        pd = resolve(g, "ProtectionDomain", protection_domain)
        sds = [s for s in sds if s.get("protectionDomainId") == pd["id"]]
    if problems_only:
        sds = [s for s in sds if _bad(s, "sdsState", ("Normal",)) or _bad(s, "mdmConnectionState", ("Connected",))
               or _bad(s, "membershipState", ("Joined",)) or _bad(s, "maintenanceState", ("NoMaintenance",))]
    return {"sds": [row("Sds", s) for s in sds]}


@mcp.tool(annotations=RO)
def get_sds(sds: str, system_id: str = "", full: bool = False) -> dict:
    """One SDS (id or name): details, its devices (path, pool, state, errors, capacity) and live IO
    (primary / total reads and writes, rebuild and rebalance)."""
    _, g = system(system_id)
    s = resolve(g, "Sds", sds)
    st = stats_of(g, "Sds", s["id"])
    d = derive(st)
    return {"sds": row("Sds", s, full),
            "devices": [row("Device", x) for x in related(g, "Sds", s["id"], "Device")],
            "io": {k: v for k, v in d.items() if k.endswith(("_iops", "_mbps", "_ms")) and (v or full)},
            "capacity": capacity_view(st)}


@mcp.tool(annotations=RO)
def list_sdc(system_id: str = "", name_contains: str = "", disconnected_only: bool = False,
             limit: int = 1000) -> dict:
    """SDC (clients: ESXi / Linux / Windows hosts): name, IP, GUID, MDM connection, approved, OS,
    version, performance profile. Filter by name or IP substring, or only disconnected ones."""
    _, g = system(system_id)
    sdcs = instances(g, "Sdc")
    if name_contains:
        n = name_contains.lower()
        sdcs = [c for c in sdcs if n in str(c.get("name") or "").lower() or n in str(c.get("sdcIp") or "")]
    if disconnected_only:
        sdcs = [c for c in sdcs if _bad(c, "mdmConnectionState", ("Connected",))]
    return cap([row("Sdc", c) for c in sdcs], limit)


@mcp.tool(annotations=RO)
def get_sdc(sdc: str, system_id: str = "") -> dict:
    """One SDC (id, name or IP): details, mapped volumes (size, pool) and live IO with latency."""
    _, g = system(system_id)
    try:
        c = resolve(g, "Sdc", sdc)
    except LookupError:
        c = next((x for x in instances(g, "Sdc") if sdc in (x.get("sdcIp"), *(x.get("sdcIps") or []))), None)
        if not c:
            raise
    vols = related(g, "Sdc", c["id"], "Volume")
    pools = {p["id"]: p.get("name") for p in instances(g, "StoragePool")}
    out = {"sdc": row("Sdc", c),
           "volumes": [{"id": v["id"], "name": v.get("name"), "size_gb": round((v.get("sizeInKb") or 0) / 1048576, 2),
                        "pool": pools.get(v.get("storagePoolId")), "type": v.get("volumeType")} for v in vols]}
    try:
        out["io"] = io_view(stats_of(g, "Sdc", c["id"]))
    except Exception as e:
        out["io"] = {"error": str(e)}
    return out


@mcp.tool(annotations=RO)
def list_volumes(system_id: str = "", name_contains: str = "", storage_pool: str = "", sdc: str = "",
                 unmapped_only: bool = False, snapshots: bool = True, limit: int = 500) -> dict:
    """Volumes and snapshots: name, size, type (thin / thick / snapshot), pool, mapped SDCs, created.
    Filter by name substring, storage pool, SDC (id / name), unmapped_only, or snapshots=False."""
    _, g = system(system_id)
    if sdc:
        vols = related(g, "Sdc", resolve(g, "Sdc", sdc)["id"], "Volume")
    else:
        vols = instances(g, "Volume")
    if storage_pool:
        pid = resolve(g, "StoragePool", storage_pool)["id"]
        vols = [v for v in vols if v.get("storagePoolId") == pid]
    if name_contains:
        vols = [v for v in vols if name_contains.lower() in str(v.get("name") or "").lower()]
    if unmapped_only:
        vols = [v for v in vols if not v.get("mappedSdcInfo")]
    if not snapshots:
        vols = [v for v in vols if v.get("volumeType") != "Snapshot" and not v.get("ancestorVolumeId")]
    vols.sort(key=lambda v: str(v.get("name") or ""))
    return cap([row("Volume", v) for v in vols], limit)


@mcp.tool(annotations=RO)
def get_volume(volume: str, system_id: str = "", full: bool = False) -> dict:
    """One volume (id or name): size, type, pool and PD, mapped SDCs with IOPS / bandwidth limits,
    snapshots and parent in the same VTree, replication state, and live IO with latency."""
    sid, g = system(system_id)
    v = resolve(g, "Volume", volume)
    out = {"volume": row("Volume", v, full), "linux_device": f"/dev/disk/by-id/emc-vol-{sid}-{v['id']}"}
    try:
        p = g.get(f"/api/instances/StoragePool::{v['storagePoolId']}")
        out["storage_pool"] = p.get("name")
        out["protection_domain"] = g.get(f"/api/instances/ProtectionDomain::{p['protectionDomainId']}").get("name")
    except Exception:
        pass
    if v.get("vtreeId"):
        try:
            tree = related(g, "VTree", v["vtreeId"], "Volume")
            out["vtree"] = [{"id": x["id"], "name": x.get("name"), "type": x.get("volumeType"),
                             "parent": x.get("ancestorVolumeId"), "created_utc": ts_iso(x.get("creationTime"))}
                            for x in tree if x["id"] != v["id"]]
        except Exception:
            pass
    try:
        st = stats_of(g, "Volume", v["id"])
        out["io"] = io_view(st)
        if full:
            out["statistics"] = derive(st)
    except Exception as e:
        out["io"] = {"error": str(e)}
    return out


@mcp.tool(annotations=RO)
def find_volume(key: str, system_id: str = "") -> dict:
    """Find volumes from what a host shows: /dev/disk/by-id/emc-vol-<system>-<volume>, an eui. id
    (ESXi / NVMe), a 16-hex volume id, or a name / name substring. Searches every system when
    system_id is omitted."""
    k = key.strip().lower()
    m = re.search(r"emc-vol-([0-9a-f]{16})-([0-9a-f]{16})", k)
    hexes = re.sub(r"^eui\.", "", k)
    candidates = []
    if m:
        candidates = [m.group(2)]
    elif re.fullmatch(r"[0-9a-f]{32}", hexes):
        candidates = [hexes[16:], hexes[:16]]
    elif re.fullmatch(r"[0-9a-f]{16}", hexes):
        candidates = [hexes]
    targets = [system(system_id)] if system_id else [system(s) for s in REG.system_map()]
    found = []
    for sid, g in targets:
        for c in candidates:
            try:
                v = g.get(f"/api/instances/Volume::{c}")
                found.append({"system_id": sid, **row("Volume", v)})
            except LookupError:
                pass
        if not candidates:
            for v in instances(g, "Volume"):
                if k == str(v.get("name") or "").lower() or k in str(v.get("name") or "").lower():
                    found.append({"system_id": sid, **row("Volume", v)})
    return {"key": key, "found": len(found), "volumes": found[:100]}


@mcp.tool(annotations=RO)
def list_devices(system_id: str = "", sds: str = "", storage_pool: str = "", problems_only: bool = False,
                 limit: int = 2000) -> dict:
    """Devices (disks) with path, SDS, pool, state, error state, media, capacity, SSD wear and
    temperature. Filter by SDS or pool (id / name); problems_only=True keeps state != Normal or errors."""
    _, g = system(system_id)
    if sds:
        devs = related(g, "Sds", resolve(g, "Sds", sds)["id"], "Device")
    elif storage_pool:
        devs = related(g, "StoragePool", resolve(g, "StoragePool", storage_pool)["id"], "Device")
    else:
        devs = instances(g, "Device")
    if problems_only:
        devs = [d for d in devs if _bad(d, "deviceState", ("Normal",)) or _bad(d, "errorState", ("None",))]
    sds_name = {s["id"]: s.get("name") for s in instances(g, "Sds")}
    rows = [dict(row("Device", d), sds=sds_name.get(d.get("sdsId"))) for d in devs]
    return cap(rows, limit)


@mcp.tool(annotations=RO)
def list_fault_sets(system_id: str = "") -> dict:
    """Fault sets with their protection domain and member SDS names."""
    _, g = system(system_id)
    sds = instances(g, "Sds")
    return {"fault_sets": [dict(row("FaultSet", f), sds=[s.get("name") for s in sds if s.get("faultSetId") == f["id"]])
                           for f in instances(g, "FaultSet")]}


@mcp.tool(annotations=RO)
def get_replication(system_id: str = "", rcg: str = "") -> dict:
    """Native asynchronous replication: peer systems (PeerMdm), replication consistency groups (state,
    direction, consistency mode, RPO, activity, errors) and SDRs. With rcg (id / name): its volume pairs."""
    _, g = system(system_id)
    out = {}
    for key, typ in (("peer_systems", "PeerMdm"), ("rcgs", "ReplicationConsistencyGroup"), ("sdrs", "Sdr")):
        try:
            out[key] = [{k: v for k, v in o.items() if k != "links"} for o in instances(g, typ)]
        except LookupError:
            out[key] = []
    if rcg:
        r = resolve(g, "ReplicationConsistencyGroup", rcg)
        out["pairs"] = [{k: v for k, v in o.items() if k != "links"}
                        for o in related(g, "ReplicationConsistencyGroup", r["id"], "ReplicationPair")]
        try:
            out["rcg_statistics"] = derive(stats_of(g, "ReplicationConsistencyGroup", r["id"]))
        except Exception:
            pass
    if not any(out.get(k) for k in ("peer_systems", "rcgs", "sdrs")):
        out["note"] = "No replication configured on this system."
    return out


@mcp.tool(annotations=RO)
def list_snapshot_policies(system_id: str = "") -> dict:
    """Snapshot policies: schedule (auto snapshot creation cadence, retention levels), state, source volumes."""
    _, g = system(system_id)
    try:
        return {"snapshot_policies": [{k: v for k, v in o.items() if k != "links"}
                                      for o in instances(g, "SnapshotPolicy")]}
    except LookupError:
        return {"snapshot_policies": [], "note": "Snapshot policies need PowerFlex 3.5 or later."}


@mcp.tool(annotations=RO)
def list_nvme(system_id: str = "") -> dict:
    """NVMe over TCP (PowerFlex 4.x+): NVMe hosts and SDT targets with their state and IPs."""
    _, g = system(system_id)
    out = {}
    for key, typ in (("hosts", "Host"), ("sdt_targets", "Sdt")):
        try:
            out[key] = [{k: v for k, v in o.items() if k != "links"} for o in instances(g, typ)]
        except LookupError:
            out[key] = []
    if not out["hosts"] and not out["sdt_targets"]:
        out["note"] = "No NVMe/TCP objects (PowerFlex 3.x, or NVMe/TCP not used)."
    return out


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def _alerts(g):
    rows = []
    for path in ("/api/types/Alert/instances",) + (("/rest/v1/alerts",) if g.api == "manager" else ()):
        try:
            r = g.get(path)
        except LookupError:
            continue
        items = r if isinstance(r, list) else r.get("items") or r.get("alerts") or r.get("content") or []
        for a in items:
            a = {k: v for k, v in a.items() if k != "links"}
            a["_source"] = path
            rows.append(a)
        if rows:
            break
    return rows


@mcp.tool(annotations=RO)
def get_alerts(system_id: str = "", severity: str = "", text: str = "", limit: int = 100) -> dict:
    """Active PowerFlex alerts, newest first: type / name, severity, start time, affected object.
    severity: substring match, comma-separate several (e.g. "CRITICAL,HIGH"). text: match in any field.
    Explain SIO / dial-home codes from the docs library when it is connected."""
    sid, g = system(system_id)
    rows = _alerts(g)
    sevs = [s.strip().lower() for s in severity.split(",") if s.strip()]
    if sevs:
        rows = [a for a in rows if any(s in str(a.get("severity", "")).lower() for s in sevs)]
    if text:
        rows = [a for a in rows if text.lower() in str(a).lower()]
    t = lambda a: str(a.get("startTime") or a.get("lastObserved") or a.get("timestamp") or "")
    rows.sort(key=t, reverse=True)
    by = {}
    for a in rows:
        by[a.get("severity")] = by.get(a.get("severity"), 0) + 1
    out = {"system_id": sid, "total": len(rows), "by_severity": by, "alerts": rows[:max(1, min(int(limit), 1000))]}
    if not rows:
        out["note"] = "No active alerts returned by the API."
    return out


# ---------------------------------------------------------------------------
# Performance / statistics
# ---------------------------------------------------------------------------

_STAT_TYPES = ("System", "ProtectionDomain", "StoragePool", "Sds", "Sdc", "Volume", "Device", "FaultSet",
               "ReplicationConsistencyGroup", "VTree", "Sdr", "Sdt", "Host")


@mcp.tool(annotations=RO)
def list_statistics_properties(object_type: str = "System", system_id: str = "") -> dict:
    """Raw statistic names PowerFlex returns for an object type (System, ProtectionDomain, StoragePool,
    Sds, Sdc, Volume, Device, FaultSet, ReplicationConsistencyGroup, VTree ...), read from the first
    object of that type. Use the names in get_statistics properties."""
    sid, g = system(system_id)
    if object_type not in _STAT_TYPES:
        raise ValueError(f"object_type must be one of {list(_STAT_TYPES)}")
    oid = sid if object_type == "System" else (instances(g, object_type) or [{}])[0].get("id")
    if not oid:
        return {"object_type": object_type, "properties": [], "note": "No object of this type."}
    st = stats_of(g, object_type, oid)
    kinds = {k: ("rate (iops / mbps)" if isinstance(v, dict) and not k.endswith("Latency") else
                 "latency (ms)" if isinstance(v, dict) else "capacity (gb)" if k.endswith("InKb") else type(v).__name__)
             for k, v in st.items() if k != "links"}
    return {"object_type": object_type, "sample_object": oid, "properties": kinds}


@mcp.tool(annotations=RO)
def get_statistics(object_type: str, object: str = "", system_id: str = "", properties: str = "KPI",
                   samples: int = 1, interval_seconds: float = 10) -> dict:
    """Live statistics of one object, converted to IOPS, MB/s, latency ms and GB.

    object_type: System, ProtectionDomain, StoragePool, Sds, Sdc, Volume, Device, FaultSet,
                 ReplicationConsistencyGroup, VTree, Sdr. object: id or name (not needed for System).
    properties: "KPI" (IO, latency, rebuild / rebalance, capacity, counts), "ALL", or comma-separated
                raw names from list_statistics_properties (e.g. "userDataReadBwc,userDataSdcReadLatency").
    samples / interval_seconds: take several samples (<= 300 s in total) for avg / max / min / last.
    """
    sid, g = system(system_id)
    if object_type not in _STAT_TYPES:
        raise ValueError(f"object_type must be one of {list(_STAT_TYPES)}")
    if object_type == "System":
        oid, name = sid, REG.system_map().get(sid, {}).get("name")
    else:
        if not object:
            raise ValueError(f"object (id or name) is required for {object_type}")
        o = resolve(g, object_type, object)
        oid, name = o["id"], o.get("name")
    mode = properties.strip().upper()
    names = None if mode in ("KPI", "ALL") else {p.strip() for p in properties.split(",") if p.strip()}

    def one():
        st = stats_of(g, object_type, oid)
        if names:
            bad = names - set(st)
            if bad:
                raise ValueError(f"Unknown statistics for {object_type}: {sorted(bad)}. "
                                 "Use list_statistics_properties.")
            return derive(st, names)
        if mode == "KPI":
            return {**io_view(st), **derive(st, {k for k in st if _KPI.search(k)})}
        return derive(st)

    s = sampled(one, samples, interval_seconds)
    return {"system_id": sid, "object_type": object_type, "object": {"id": oid, "name": name},
            "taken_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "samples": len(s), "interval_seconds": interval_seconds if len(s) > 1 else None,
            "statistics": summarise(s)}


@mcp.tool(annotations=RO)
def get_performance_overview(system_id: str = "", top_n: int = 10, samples: int = 1,
                             interval_seconds: float = 10) -> dict:
    """System-wide performance snapshot: system IO and latency, every storage pool (IO, latency, used %,
    rebuild / rebalance), the busiest volumes, SDCs and SDSs by IOPS, and the volumes and SDCs with
    the worst latency. samples > 1 averages the system / pool numbers over samples * interval_seconds.
    Start performance work here."""
    sid, g = system(system_id)
    n = max(1, min(int(top_n), 50))
    out = {"system_id": sid, "taken_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    out["system"] = summarise(sampled(lambda: io_view(stats_of(g, "System", sid)), samples, interval_seconds))
    pools = instances(g, "StoragePool")

    def pools_now():
        rows = {}
        for p in pools:
            st = stats_of(g, "StoragePool", p["id"])
            c = capacity_view(st)
            d = derive(st)
            rows[p.get("name")] = {**io_view(st), "used_pct": c.get("net_used_pct", c.get("raw_used_pct")),
                                   "rebuild_rebalance_mbps": round(sum(v for k, v in d.items()
                                                                       if re.search(r"(Rebuild|rebalance)\w*_mbps$", k)), 2)}
        return rows
    ps = sampled(pools_now, samples, interval_seconds)
    out["storage_pools"] = {name: summarise([p[name] for p in ps]) for name in ps[-1]}

    names = {}
    for typ in ("Volume", "Sdc", "Sds"):
        objs = instances(g, typ)
        names[typ] = {o["id"]: o.get("name") or o.get("sdcIp") or o["id"] for o in objs}
        st = bulk_stats(g, typ, list(names[typ]))
        rows = [{"id": i, "name": names[typ].get(i), **io_view(s)} for i, s in st.items()]
        rows = [r for r in rows if r.get("total_iops") is not None]
        key = typ.lower() + ("s" if typ != "Sds" else "")
        out[f"top_{key}_by_iops"] = sorted(rows, key=lambda r: r.get("total_iops") or 0, reverse=True)[:n]
        if typ != "Sds":
            busy = [r for r in rows if (r.get("total_iops") or 0) >= 50]
            worst = lambda r: max(r.get("read_latency_ms") or 0, r.get("write_latency_ms") or 0)
            out[f"worst_latency_{key}"] = sorted(busy, key=worst, reverse=True)[:n]
    out["notes"] = ["Live rates over the last few seconds (no history in the PowerFlex API).",
                    "Worst-latency lists only include objects doing >= 50 IOPS.",
                    "Latency in ms as seen by the SDCs; MB/s; IOPS per second."]
    return out


@mcp.tool(annotations=RO)
def metrics_query(resource_type: str, metrics: str, ids: str = "", system_id: str = "") -> dict:
    """PowerFlex 4.x+ metrics API (POST /dtapi/rest/v1/metrics/query), passed through as is.
    resource_type e.g. volume, sdc, sds, storage_pool, protection_domain, system, device.
    metrics: comma-separated names (an unknown name returns PowerFlex's error with the valid names).
    ids: comma-separated object ids (empty = all). Not available on 3.x gateways."""
    _, g = system(system_id)
    body = {"resource_type": resource_type, "metrics": [m.strip() for m in metrics.split(",") if m.strip()],
            "ids": [i.strip() for i in ids.split(",") if i.strip()]}
    return {"request": body, "response": g.post("/dtapi/rest/v1/metrics/query", body)}


# ---------------------------------------------------------------------------
# Escape hatch
# ---------------------------------------------------------------------------

@mcp.tool(annotations=RO)
def powerflex_get(path: str, params: dict | None = None, system_id: str = "") -> dict:
    """GET any PowerFlex REST endpoint not covered by another tool, e.g.
    "/api/types/AccelerationPool/instances", "/api/instances/Volume::<id>/relationships/Statistics",
    "/api/types/User/instances", or on PowerFlex Manager "/rest/v1/events", "/Api/V1/ManagedDevice".
    path must start with /api/, /rest/ or /dtapi/. GET only."""
    if ".." in path or not path.startswith(_PREFIXES):
        raise ValueError(f"path must start with one of {_PREFIXES} and not contain ..")
    _, g = system(system_id)
    r = g.get(path, params)
    return r if isinstance(r, dict) else {"result": r}


# ---------------------------------------------------------------------------
# Prompts: ready-made workflows a client can offer to the user
# ---------------------------------------------------------------------------

@mcp.prompt()
def daily_health_check(system_id: str = "") -> str:
    """Morning health report for PowerFlex."""
    target = f"PowerFlex system {system_id}" if system_id else "every system from list_systems"
    return (f"Produce a morning health report for {target}: get_health (MDM cluster, SDS, SDC, devices, pools, "
            "rebuild / rebalance), get_capacity (net used % per pool against its thresholds), get_alerts "
            "(group repeats, explain codes from the docs library), get_performance_overview with samples=6 "
            "interval_seconds=10, and get_replication. End with a table of issues ranked by urgency and one "
            "next action each. Flag any gateway that was unreachable.")


@mcp.prompt()
def troubleshoot_volume_latency(volume_or_sdc: str, system_id: str = "") -> str:
    """Investigate slow PowerFlex storage reported for a volume, datastore or host."""
    return (f"Slow storage is reported for: {volume_or_sdc} (system {system_id or 'find it with list_systems'}). "
            "1) Resolve it: find_volume / get_volume (pool, PD, mapped SDCs) or get_sdc (its volumes). "
            "2) get_statistics for the volume and for each SDC with samples=6 interval_seconds=10. "
            "3) The same for its storage pool, and get_performance_overview to see if the system is busy. "
            "4) get_health: rebuild / rebalance running, degraded capacity, SDS or device problems in that PD. "
            "5) get_alerts for anything that coincides. 6) If vCenter / Aria tools are connected, check the "
            "host side for the same device. Conclude: host, pool / SDS / devices, rebuild, or network, with numbers.")


@mcp.prompt()
def capacity_report(system_id: str = "") -> str:
    """Capacity and efficiency report."""
    return (f"Capacity report for {('system ' + system_id) if system_id else 'all systems'}: get_capacity "
            "(net used / free and used % per pool and PD, snapshots, thin / thick, compression and efficiency), "
            "the 10 largest volumes per pool (list_volumes), unmapped volumes (list_volumes unmapped_only=True) "
            "as reclaim candidates, and whether spare covers the largest SDS / fault set. Flag pools above "
            "their capacityAlertHighThreshold.")


@mcp.prompt()
def rebuild_status(system_id: str = "") -> str:
    """Is data fully protected; rebuild / rebalance progress."""
    return ("Check data protection: get_health (degraded / failed / pending capacity per pool, SDS and device "
            "problems), get_storage_pool for each affected pool, then again after 2-3 minutes to show the trend "
            "of pending rebuild capacity and the rebuild MB/s. Estimate time to complete from the two samples "
            "and say which SDS or device caused it.")


@mcp.prompt()
def replication_health(system_id: str = "") -> str:
    """Native replication status."""
    return ("Check replication: get_replication (peer systems and their connection, every RCG with state, "
            "direction, consistency, RPO and errors), then get_replication rcg=<name> for any RCG not healthy "
            "to list its pairs. Report RCGs that are not consistent / active or are behind their RPO first.")


if __name__ == "__main__":
    import mcp_auth
    REG.gateways  # validate the Secret at startup, not on first call
    mcp_auth.run(mcp)
