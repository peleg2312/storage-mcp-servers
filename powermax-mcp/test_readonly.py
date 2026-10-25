"""Offline tests: fake Unisphere REST API; all tools work and writes never reach the network."""
import asyncio
import json
import os
import re
import time
from urllib.parse import urlparse, parse_qsl

import requests

os.environ.update(UNISPHERE_1_NAME="dc1", UNISPHERE_1_HOST="u4p-a.test", UNISPHERE_1_USERNAME="mon", UNISPHERE_1_PASSWORD="x",
                  UNISPHERE_2_NAME="dc2", UNISPHERE_2_HOST="u4p-b.test", UNISPHERE_2_USERNAME="mon", UNISPHERE_2_PASSWORD="y")
import server  # noqa: E402

A = "000197900123"
B = "000197900456"
NOW = int(time.time() * 1000) // 300000 * 300000
SENT = []
HOSTS = []


def perf_rows(metrics, n=12):
    return [{"timestamp": NOW - (n - 1 - i) * 300000, **{m: float(i + 1) * (2 if "Response" in m else 10) for m in metrics}}
            for i in range(n)]


def route(method, path, qs, body):
    v = "/univmax/restapi/100"
    if path == "/univmax/restapi/version":
        return {"version": "T10.1.0.5", "api_version": "101"}
    path = path.replace("/univmax/restapi/101", v)
    if method == "POST":
        m = re.match(r"/univmax/restapi/performance/(\w+)/(keys|metrics)", path)
        cat, kind = m.groups()
        if kind == "keys":
            info = {"StorageGroup": ("storageGroupInfo", [{"storageGroupId": "SG_ESX01"}, {"storageGroupId": "SG_ORA"}]),
                    "FEDirector": ("feDirectorInfo", [{"directorId": "FA-1D"}, {"directorId": "FA-2D"}])}[cat]
            return {info[0]: [dict(x, firstAvailableDate=NOW - 86400000, lastAvailableDate=NOW) for x in info[1]]}
        rows = perf_rows(body["metrics"])
        return {"resultList": {"result": rows[:10], "from": 1, "to": 10}, "count": len(rows),
                "maxPageSize": 10, "id": "it-perf", "expirationTime": 0}
    if path == "/univmax/restapi/common/Iterator/it-perf/page":
        return {"result": perf_rows(["HostIOs", "HostMBs", "ResponseTime", "ReadResponseTime", "WriteResponseTime"])[10:]}
    if path == "/univmax/restapi/performance/Array/keys":
        return {"arrayInfo": [{"symmetrixId": A, "firstAvailableDate": NOW - 86400000, "lastAvailableDate": NOW}]}
    m = re.match(rf"/univmax/restapi/performance/Array/help/{A}/(\w+)/metrics/(All|Kpi)", path)
    if m:
        return {"metricName": ["HostIOs", "HostMBs", "ResponseTime", "ReadResponseTime", "WriteResponseTime", "PercentBusy"]}
    if path == f"/univmax/restapi/performance/Array/help/{A}/categories":
        return {"categoryName": ["Array", "StorageGroup", "FEDirector", "FEPort", "Host"]}
    table = {
        f"{v}/system/symmetrix": {"symmetrixId": [A, B]},
        f"{v}/system/symmetrix/{B}": {"symmetrixId": B, "local": False},
        f"{v}/system/symmetrix/{A}": {"symmetrixId": A, "model": "PowerMax_8500", "ucode": "10.1.0.0", "local": True},
        f"{v}/system/symmetrix/{A}/health": {"health_score_metric": [{"metric": "OVERALL", "health_score": 95}]},
        f"{v}/sloprovisioning/symmetrix/{A}/srp": {"srpId": ["SRP_1"]},
        f"{v}/sloprovisioning/symmetrix/{A}/srp/SRP_1": {"srpId": "SRP_1", "srp_capacity": {"usable_total_tb": 500}},
        f"{v}/sloprovisioning/symmetrix/{A}/storagegroup": {"storageGroupId": ["SG_ESX01", "SG_ORA"]},
        f"{v}/sloprovisioning/symmetrix/{A}/storagegroup/SG_ESX01": {"storageGroupId": "SG_ESX01", "cap_gb": 2048},
        f"{v}/sloprovisioning/symmetrix/{A}/volume": {"resultList": {"result": [{"volumeId": "00ABC"}]}, "count": 1, "maxPageSize": 1000, "id": "it1"},
        f"{v}/sloprovisioning/symmetrix/{A}/volume/00ABC": {"volumeId": "00ABC", "cap_gb": 1024, "wwn": "60000970000197900123533030414243"},
        f"{v}/sloprovisioning/symmetrix/{A}/host": {"hostId": ["esx01"]},
        f"{v}/sloprovisioning/symmetrix/{A}/hostgroup": {"hostGroupId": ["esx_cluster"]},
        f"{v}/sloprovisioning/symmetrix/{A}/host/esx01": {"hostId": "esx01", "initiator": ["10000090fa123456"]},
        f"{v}/sloprovisioning/symmetrix/{A}/initiator": {"initiatorId": ["FA-1D:4:10000090fa123456", "FA-2D:4:10000090fa999999"]},
        f"{v}/sloprovisioning/symmetrix/{A}/initiator/FA-1D%3A4%3A10000090fa123456": {"host": "esx01", "logged_in": True, "on_fabric": True, "maskingview": ["esx01_MV"], "symmetrixPortKey": [{"directorId": "FA-1D", "portId": "4"}]},
        f"{v}/sloprovisioning/symmetrix/{A}/maskingview": {"maskingViewId": ["esx01_MV"]},
        f"{v}/sloprovisioning/symmetrix/{A}/maskingview/esx01_MV": {"maskingViewId": "esx01_MV", "hostId": "esx01", "portGroupId": "PG_FA1D", "storageGroupId": "SG_ESX01"},
        f"{v}/sloprovisioning/symmetrix/{A}/maskingview/esx01_MV/connections": {"maskingViewConnection": [{"volumeId": "00ABC", "host_lun_address": "0001", "dir_port": "FA-1D:4", "logged_in": True}]},
        f"{v}/sloprovisioning/symmetrix/{A}/portgroup/PG_FA1D": {"portGroupId": "PG_FA1D", "symmetrixPortKey": [{"directorId": "FA-1D", "portId": "4"}]},
        f"{v}/system/symmetrix/{A}/director": {"directorId": ["FA-1D"]},
        f"{v}/system/symmetrix/{A}/director/FA-1D": {"directorId": "FA-1D", "availability": "Online"},
        f"{v}/system/symmetrix/{A}/director/FA-1D/port": {"symmetrixPortKey": [{"directorId": "FA-1D", "portId": "4"}]},
        f"{v}/system/symmetrix/{A}/director/FA-1D/port/4": {"symmetrixPort": {"identifier": "50000973b001234", "negotiated_speed": "32"}},
        f"{v}/replication/symmetrix/{A}/rdf_group": {"rdfGroupID": [{"rdfgNumber": 10, "label": "RDF_10"}]},
        f"{v}/replication/symmetrix/{A}/rdf_group/10": {"rdfgNumber": 10, "modes": ["Synchronous"], "remoteSymmetrix": "000197900456"},
        f"{v}/replication/symmetrix/{A}/storagegroup/SG_ESX01": {"storageGroupName": "SG_ESX01", "rdf": True},
        f"{v}/replication/symmetrix/{A}/storagegroup/SG_ESX01/snapshot": {"name": ["daily"]},
        f"{v}/replication/symmetrix/{A}/storagegroup/SG_ESX01/rdf_group": {"rdfgs": [10]},
        f"{v}/replication/symmetrix/{A}/storagegroup/SG_ESX01/rdf_group/10": {"states": ["Synchronized"]},
        f"{v}/system/alert_summary": {"serverAlertSummary": {"fatal_unacknowledged_count": 0}},
        f"{v}/system/alert": {"alertId": ["101", "105", "103"]},
        f"{v}/system/symmetrix/{A}/audit_log_record": {"resultList": {"result": [{"record_id": 1, "entry_date": NOW // 1000, "user_name": "admin", "message": "Modify SG"}]}, "count": 1, "maxPageSize": 1000, "id": "it2"},
    }
    m = re.match(rf"{v}/system/alert/(\d+)$", path)
    if m:
        return {"alertId": m.group(1), "severity": "CRITICAL" if m.group(1) == "105" else "WARNING",
                "created_date": f"Oct-21-2026 10:{m.group(1)[-2:]}:00.000", "description": "Port FA-1D:4 link down",
                "array": A, "state": "NEW", "acknowledged": False}
    if path in table:
        return table[path]
    return None


def route_b(method, path):
    v = "/univmax/restapi/100"
    if path == "/univmax/restapi/version":
        return {"version": "T10.0.1.2"}  # no api_version -> derived "100"
    return {f"{v}/system/symmetrix": {"symmetrixId": [B]},
            f"{v}/system/symmetrix/{B}": {"symmetrixId": B, "model": "PowerMax_2500", "local": True},
            f"{v}/system/alert": {"alertId": ["7"]},
            f"{v}/system/alert/7": {"alertId": "7", "severity": "FATAL", "array": B, "description": "SRDF link down",
                                   "created_date": "Oct-21-2026 18:59:00.000", "created_date_milliseconds": NOW + 60000},
            f"{v}/system/alert_summary": {"fatal": 1}}.get(path)


def fake_send(self, prep, **kw):
    u = urlparse(prep.url)
    body = json.loads(prep.body) if prep.body else None
    SENT.append((prep.method, u.path, parse_qsl(u.query)))
    HOSTS.append(u.hostname)
    data = route_b(prep.method, u.path) if u.hostname == "u4p-b.test" else route(prep.method, u.path, u.query, body)
    r = requests.Response()
    r.status_code = 200 if data is not None else 404
    r._content = json.dumps(data or {"message": "not found"}).encode()
    r.url = prep.url
    return r


requests.Session.send = fake_send


async def main():
    tools = await server.mcp.list_tools()
    print(len(tools), "tools:", sorted(t.name for t in tools))
    prompts = await server.mcp.list_prompts()
    print("prompts:", [p.name for p in prompts])
    assert all(getattr(t.annotations, "read_only_hint", None) or t.annotations.readOnlyHint for t in tools)

    async def call(name, **a):
        r = await server.mcp.call_tool(name, a)
        return r.structured_content

    tc = await call("test_connection")
    print("unispheres:", [(x["unisphere"], x["ok"], x["api_version_used"], x["arrays"]) for x in tc["unispheres"]])
    assert [x["api_version_used"] for x in tc["unispheres"]] == ["101", "100"]
    arrs = {r["array_id"]: r["managed_by"] for r in (await call("list_arrays"))["arrays"]}
    assert arrs == {A: "dc1", B: "dc2"}, arrs
    HOSTS.clear()
    gb = await call("get_array", array_id=B)
    assert gb["model"] == "PowerMax_2500" and set(HOSTS) == {"u4p-b.test"}, (gb, HOSTS)
    print("routing:", arrs, "-> get_array(B) went to", set(HOSTS))
    try:
        await call("get_array")
        raise SystemExit("ambiguous array accepted")
    except Exception as e:
        assert "array_id is required" in str(e)
    await call("get_array_health", array_id=A); await call("list_srps", array_id=A)
    sg = await call("get_storage_group", array_id=A, storage_group="SG_ESX01")
    assert sg["volumes"][0]["volumeId"] == "00ABC"
    w = await call("find_wwpn", array_id=A, wwpn="10:00:00:90:FA:12:34:56")
    assert w["initiators"][0]["masking_views"][0]["storage_group"] == "SG_ESX01", w
    print("find_wwpn:", w["initiators"][0]["masking_views"])
    mv = await call("get_masking_view", array_id=A, masking_view="esx01_MV")
    assert mv["connections_total"] == 1
    await call("get_port_group", array_id=A, port_group="PG_FA1D"); await call("get_host", array_id=A, host="esx01")
    await call("list_hosts", array_id=A); await call("list_masking_views", array_id=A); await call("list_storage_groups", array_id=A)
    d = await call("list_directors", array_id=A, include_ports=True)
    assert d["directors"][0]["ports"]
    await call("get_port", array_id=A, director="fa-1d", port="4")
    rep = await call("get_replication", array_id=A, storage_group="SG_ESX01")
    assert rep["srdf"] and rep["snapshots"] == ["daily"]
    await call("get_replication", array_id=A)
    al = await call("get_alerts", since_hours=24, limit=10)
    assert al["total_matching"] == 4 and al["alerts"][0]["unisphere"] == "dc2", al["alerts"][0]
    print("alerts merged:", [(x["unisphere"], x["alertId"], x["severity"], x["created_utc"]) for x in al["alerts"]])
    al1 = await call("get_alerts", array_id=A, severity="CRITICAL,WARNING")
    assert {x["unisphere"] for x in al1["alerts"]} == {"dc1"} and al1["filters"]["array"] == A
    alert_q = [q for m, p, q in SENT if p.endswith("/system/alert")][0]
    assert any(k == "created_date" and v.startswith(">") for k, v in alert_q), alert_q
    au = await call("get_audit_log", array_id=A, hours_back=24)
    assert au["returned"] == 1
    aq = [q for m, p, q in SENT if p.endswith("audit_log_record")][0]
    assert [k for k, _ in aq].count("entry_date") == 2, aq
    print("audit:", au["records"][0]["entry_date_utc"], au["records"][0]["message"])
    await call("list_performance_categories", array_id=A)
    await call("list_performance_metrics", array_id=A, category="StorageGroup", kpi_only=True)
    k = await call("list_performance_keys", array_id=A, category="StorageGroup")
    assert k["total"] == 2
    p = await call("get_performance", array_id=A, category="StorageGroup", storage_group="SG_ESX01",
                   metrics="HostIOs,ResponseTime", minutes_back=60, raw=True, max_points=5)
    assert p["samples"] == 12 and p["summary"]["ResponseTime"]["max"] == 24.0, p["summary"]
    print("perf summary:", p["summary"]["ResponseTime"], "series pts:", len(p["series"]))
    try:
        await call("get_performance", array_id=A, category="StorageGroup", storage_group="SG_ESX01", metrics="Bogus")
        raise SystemExit("bad metric accepted")
    except Exception as e:
        assert "Unknown metrics" in str(e)
    ov = await call("get_performance_overview", array_id=A, minutes_back=60, top_n=5)
    assert ov["top_storage_groups_by_iops"] and ov["fe_directors"]
    print("overview top SG:", ov["top_storage_groups_by_iops"][0]["storage_group"], "FE:", len(ov["fe_directors"]))
    await call("unisphere_get", array_id=A, path=f"/sloprovisioning/symmetrix/{A}/srp/SRP_1")
    s_ = await call("get_alert_summary")
    assert set(s_["by_unisphere"]) == {"dc1", "dc2"}

    # ---- writes must be blocked before send ----
    n_before = len(SENT)
    s = server.U(A).s
    base = server.U(A).base
    attempts = [
        ("PUT", f"{base}/100/sloprovisioning/symmetrix/{A}/storagegroup/SG_ESX01"),
        ("DELETE", f"{base}/100/sloprovisioning/symmetrix/{A}/volume/00ABC"),
        ("PATCH", f"{base}/100/sloprovisioning/symmetrix/{A}/host/esx01"),
        ("POST", f"{base}/100/sloprovisioning/symmetrix/{A}/storagegroup"),
        ("POST", f"{base}/100/replication/symmetrix/{A}/storagegroup/SG_ESX01/snapshot"),
        ("POST", f"{base}/performance/Array/register"),
        ("POST", f"{base}/performance/../100/sloprovisioning/symmetrix/{A}/storagegroup"),
        ("GET", "https://evil.example/other"),
    ]
    for meth, url in attempts:
        try:
            s.request(meth, url, json={})
            raise SystemExit(f"NOT BLOCKED: {meth} {url}")
        except server.ReadOnlyViolation as e:
            print("blocked:", e)
    try:
        await call("unisphere_get", path="/../sloprovisioning")
        raise SystemExit("path traversal accepted")
    except Exception:
        pass
    assert len(SENT) == n_before, "a blocked request reached the network"
    bad = [(m, p) for m, p, _ in SENT if m not in ("GET",) and not re.search(r"/performance/\w+/(keys|metrics)$", p)]
    assert not bad, bad
    print("methods sent:", sorted({m for m, _, _ in SENT}), "requests:", len(SENT))
    print("ALL TESTS PASSED")


asyncio.run(main())
