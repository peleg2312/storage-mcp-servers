"""Offline tests: a fake 3.x Gateway and a fake 4.x PowerFlex Manager; every tool works, statistics are
converted correctly, and writes never reach the network."""
import asyncio
import json
import os
from urllib.parse import urlparse

import requests

os.environ.update(POWERFLEX_1_NAME="gw3", POWERFLEX_1_HOST="gw3.test", POWERFLEX_1_USERNAME="mon", POWERFLEX_1_PASSWORD="x",
                  POWERFLEX_2_NAME="pfm4", POWERFLEX_2_HOST="pfm4.test", POWERFLEX_2_USERNAME="mon", POWERFLEX_2_PASSWORD="y")
import server  # noqa: E402

S3, S4 = "1a2b3c4d5e6f7081", "9f8e7d6c5b4a3921"
PD, POOL, SDS1, SDS2, SDC1, SDC2 = "aa00000000000001", "bb00000000000001", "cc00000000000001", "cc00000000000002", "dd00000000000001", "dd00000000000002"
V1, V2, SNAP, DEV1, DEV2 = "ee00000000000001", "ee00000000000002", "ee00000000000003", "ff00000000000001", "ff00000000000002"
V4, HOST1 = "ee00000000000004", "de00000000000001"
SENT, AUTH = [], []
EXPIRE_ONCE = {"pfm4": True}


def bwc(iops, mbps, secs=5):
    return {"numSeconds": secs, "numOccured": iops * secs, "totalWeightInKb": int(mbps * 1024 * secs)}


def lat(ms, n=1000):
    return {"numSeconds": 5, "numOccured": n, "totalWeightInKb": int(ms * 1000 * n)}


IO = {"userDataReadBwc": bwc(1000, 40), "userDataWriteBwc": bwc(500, 20),
      "userDataSdcReadLatency": lat(0.5), "userDataSdcWriteLatency": lat(1.2)}
SLOW = {"userDataReadBwc": bwc(200, 5), "userDataWriteBwc": bwc(100, 2),
        "userDataSdcReadLatency": lat(6.0), "userDataSdcWriteLatency": lat(9.0)}
KB = 1048576
CAPA = {"maxCapacityInKb": 100 * KB, "spareCapacityInKb": 10 * KB, "capacityInUseInKb": 76 * KB,
        "netCapacityInUseInKb": 38 * KB, "netUnusedCapacityInKb": 7 * KB, "degradedHealthyCapacityInKb": 2 * KB,
        "snapCapacityInUseInKb": 1 * KB, "compressionRatio": 1.8, "fwdRebuildReadBwc": bwc(100, 50),
        "primaryReadBwc": bwc(1500, 60), "primaryWriteBwc": bwc(600, 22), "numOfVolumes": 3}


def objects(system_id):
    o = _objects(system_id)
    if system_id == S4:   # 4.x: an OpenShift worker on NVMe/TCP with one CSI volume
        o["Host"] = [{"id": HOST1, "name": "ocp-worker-1", "hostOsFullType": "Linux", "nqn": "nqn.2014-08.org:w1"}]
        o["Volume"].append({"id": V4, "name": "k8s-1a2b3c4d5e", "sizeInKb": 20 * KB, "volumeType": "ThinProvisioned",
                            "storagePoolId": POOL, "vtreeId": "1100000000000004",
                            "mappedSdcInfo": [{"sdcId": HOST1, "sdcName": "ocp-worker-1", "hostType": "NVMeHost"}]})
    return o


def _objects(system_id):
    return {
        "System": [{"id": system_id, "name": "pf-" + system_id[:4], "systemVersionName": "DellEMC PowerFlex Version: R3_6.0.0"}],
        "ProtectionDomain": [{"id": PD, "name": "PD1", "protectionDomainState": "Active"}],
        "StoragePool": [{"id": POOL, "name": "SP_SSD", "protectionDomainId": PD, "mediaType": "SSD",
                         "capacityAlertHighThreshold": 80, "capacityAlertCriticalThreshold": 90}],
        "Sds": [{"id": SDS1, "name": "sds-01", "sdsState": "Normal", "mdmConnectionState": "Connected",
                 "membershipState": "Joined", "maintenanceState": "NoMaintenance", "protectionDomainId": PD,
                 "ipList": [{"ip": "10.0.0.11", "role": "all"}]},
                {"id": SDS2, "name": "sds-02", "sdsState": "Normal", "mdmConnectionState": "Disconnected",
                 "membershipState": "Joined", "maintenanceState": "NoMaintenance", "protectionDomainId": PD,
                 "ipList": [{"ip": "10.0.0.12", "role": "all"}]}],
        "Sdc": [{"id": SDC1, "name": "esx01", "sdcIp": "10.1.0.1", "mdmConnectionState": "Connected"},
                {"id": SDC2, "name": "esx02", "sdcIp": "10.1.0.2", "mdmConnectionState": "Connected"}],
        "Volume": [{"id": V1, "name": "ds_prod01", "sizeInKb": 512 * KB, "volumeType": "ThinProvisioned",
                    "storagePoolId": POOL, "vtreeId": "1100000000000001", "creationTime": 1790000000,
                    "mappedSdcInfo": [{"sdcId": SDC1, "sdcName": "esx01", "sdcIp": "10.1.0.1", "limitIops": 0}]},
                   {"id": V2, "name": "ds_test02", "sizeInKb": 256 * KB, "volumeType": "ThinProvisioned",
                    "storagePoolId": POOL, "vtreeId": "1100000000000002", "mappedSdcInfo": [
                        {"sdcId": SDC2, "sdcName": "esx02", "sdcIp": "10.1.0.2"}]},
                   {"id": SNAP, "name": "ds_prod01_snap", "sizeInKb": 512 * KB, "volumeType": "Snapshot",
                    "storagePoolId": POOL, "vtreeId": "1100000000000001", "ancestorVolumeId": V1}],
        "Device": [{"id": DEV1, "name": "sds01-nvme0", "deviceCurrentPathName": "/dev/nvme0n1", "sdsId": SDS1,
                    "storagePoolId": POOL, "deviceState": "Normal", "errorState": "None", "maxCapacityInKb": 50 * KB},
                   {"id": DEV2, "name": "sds02-nvme0", "deviceCurrentPathName": "/dev/nvme0n1", "sdsId": SDS2,
                    "storagePoolId": POOL, "deviceState": "Normal", "errorState": "DeviceErrorReported"}],
        "FaultSet": [{"id": "fa00000000000001", "name": "FS1", "protectionDomainId": PD}],
        "ReplicationConsistencyGroup": [{"id": "ab00000000000001", "name": "rcg_prod", "currConsistMode": "Consistent",
                                         "rpoInSeconds": 60}],
        "PeerMdm": [{"id": "ac00000000000001", "name": "dr-site", "peerSystemId": "7777777777777777"}],
        "Alert": [{"id": "1", "alertType": "SDS_DISCONNECTED", "severity": "ALERT_CRITICAL",
                   "startTime": "2026-10-27T08:00:00Z", "affectedObject": {"type": "Sds", "objectId": SDS2}},
                  {"id": "2", "alertType": "DEVICE_FAILED", "severity": "ALERT_HIGH", "startTime": "2026-10-27T09:00:00Z"}],
    }


def stats(typ, oid):
    if typ == "Volume":
        return {**(SLOW if oid == V2 else IO), "numOfMappedSdcs": 1}
    if typ == "Sdc":
        return SLOW if oid == SDC2 else IO
    if typ == "Device":
        return {"avgReadLatencyInMicrosec": 200}
    return {**IO, **CAPA}


def route(host, method, path, body):
    sys_id = S3 if host == "gw3.test" else S4
    obj = objects(sys_id)
    if path == "/rest/auth/login":
        return (200, {"access_token": "tok4", "refresh_token": "r"}) if host == "pfm4.test" else (404, {"message": "no"})
    if path == "/api/login":
        return (200, "tok3")
    if path == "/api/version":
        return (200, "3.6" if host == "gw3.test" else "4.5")
    if path == "/api/instances/System/action/queryMdmCluster":
        return (200, {"clusterState": "ClusteredNormal", "clusterMode": "ThreeNodes", "goodNodesNum": 3, "goodReplicasNum": 2})
    if path == "/api/instances/querySelectedStatistics":
        sel = body["selectedStatisticsList"][0]
        assert sel["allIds"] == "" and sel["properties"]
        if host == "pfm4.test":
            return (400, {"message": "bulk not supported here"})   # exercises the per-object fallback
        return (200, {sel["type"]: {o["id"]: stats(sel["type"], o["id"]) for o in obj[sel["type"]]}})
    if path == "/dtapi/rest/v1/metrics/query":
        return (200, {"resource_type": body["resource_type"], "resources": []})
    if path == "/rest/v1/alerts":
        return (404, {})
    if path == "/rest/v1/events":
        return (200, [{"id": "e1", "severity": "MAJOR", "message": "SDC ocp-worker-2 disconnected", "timestamp": "2026-10-27T10:00:00Z"},
                      {"id": "e2", "severity": "INFO", "message": "Rebuild started", "timestamp": "2026-10-27T11:00:00Z"},
                      {"id": "e0", "severity": "INFO", "message": "old", "timestamp": "2020-01-01T00:00:00Z"}])
    if path.endswith("/action/querySdsNetworkLatencyMeters"):
        return (200, [{"ipAddress": "10.0.0.12", "averageMessageWaitTimeInUsec": 350}])
    if path.endswith("/action/querySdsConnectivityStatus"):
        return (200, {"allSdssConnected": True})
    parts = path.strip("/").split("/")
    if parts[:2] == ["api", "types"] and parts[3:] == ["instances"]:
        return (200, obj[parts[2]]) if parts[2] in obj else (404, {"message": "unknown type"})
    if parts[:2] == ["api", "instances"] and "::" in parts[2]:
        typ, oid = parts[2].split("::")
        if parts[3:] == ["relationships", "Statistics"]:
            return (200, stats(typ, oid))
        if parts[3:4] == ["relationships"]:
            rel = parts[4]
            if typ == "VTree":
                return (200, [v for v in obj["Volume"] if v["vtreeId"] == oid])
            if typ in ("Sdc", "Host") and rel == "Volume":
                return (200, [v for v in obj["Volume"] if any(m["sdcId"] == oid for m in v.get("mappedSdcInfo", []))])
            if rel == "Device":
                key = {"Sds": "sdsId", "StoragePool": "storagePoolId"}[typ]
                return (200, [d for d in obj["Device"] if d[key] == oid])
            if rel == "ReplicationPair":
                return (200, [{"id": "ad00000000000001", "localVolumeId": V1, "remoteVolumeId": "9" * 16}])
        for o in obj.get(typ, []):
            if o["id"] == oid:
                return (200, o)
        return (404, {"message": "not found"})
    return (404, {"message": f"no route {path}"})


def fake_send(self, prep, **kw):
    u = urlparse(prep.url)
    body = json.loads(prep.body) if prep.body else None
    SENT.append((prep.method, u.hostname, u.path))
    AUTH.append((u.hostname, u.path, prep.headers.get("Authorization", "")))
    code, data = route(u.hostname, prep.method, u.path, body)
    if u.hostname == "pfm4.test" and u.path == "/api/types/Sds/instances" and EXPIRE_ONCE["pfm4"]:
        EXPIRE_ONCE["pfm4"] = False
        code, data = 401, {"message": "token expired"}
    r = requests.Response()
    r.status_code = code
    r._content = json.dumps(data).encode()
    r.url = prep.url
    return r


requests.Session.send = fake_send


async def main():
    tools = await server.mcp.list_tools()
    print(len(tools), "tools:", sorted(t.name for t in tools))
    print("prompts:", [p.name for p in await server.mcp.list_prompts()])
    assert all(t.annotations.read_only_hint for t in tools)

    async def call(name, **a):
        return (await server.mcp.call_tool(name, a)).structured_content

    tc = await call("test_connection")
    print("gateways:", [(x["gateway"], x["ok"], x["api"], x["rest_version"]) for x in tc["gateways"]])
    assert [x["api"] for x in tc["gateways"]] == ["gateway", "manager"], tc
    assert any(h == "gw3.test" and a.startswith("Basic ") for h, p, a in AUTH if p == "/api/types/System/instances")
    assert any(h == "pfm4.test" and a == "Bearer tok4" for h, p, a in AUTH if p == "/api/types/System/instances")
    systems = {s["system_id"]: s["gateway"] for s in (await call("list_systems"))["systems"]}
    assert systems == {S3: "gw3", S4: "pfm4"}, systems
    try:
        await call("get_system")
        raise SystemExit("ambiguous system accepted")
    except Exception as e:
        assert "system_id is required" in str(e)
    s = await call("get_system", system_id="pf-" + S4[:4])         # by name, routed to the 4.x manager
    assert s["id"] == S4 and s["mdmCluster"]["clusterState"] == "ClusteredNormal"

    h = await call("get_health", system_id=S4)                     # Sds list returns 401 once -> signs in again
    assert not EXPIRE_ONCE["pfm4"]
    print("health:", h["status"], [(i["severity"], i["object"], i["issue"]) for i in h["issues"]])
    objs = [i["object"] for i in h["issues"]]
    assert h["status"] == "CRITICAL" and "SDS sds-02" in objs and any("sds02-nvme0" in o for o in objs)
    assert any(o == "pool SP_SSD" and "degraded" in i["issue"] for o, i in zip(objs, h["issues"]))
    assert any(o == "pool SP_SSD" and "used 84.4%" in i["issue"] for o, i in zip(objs, h["issues"])), h["issues"]
    assert h["counts"]["alerts"] == {"ALERT_CRITICAL": 1, "ALERT_HIGH": 1}

    c = await call("get_capacity", system_id=S3)
    sp = c["storage_pools"][0]
    assert sp["net_used_pct"] == 84.4 and sp["raw_used_pct"] == 84.4 and sp["compressionRatio"] == 1.8, sp
    print("capacity pool:", {k: sp[k] for k in ("pool", "net_used_gb", "net_used_pct", "raw_used_pct", "degradedHealthyCapacity_gb")})

    await call("list_protection_domains", system_id=S3)
    assert (await call("list_storage_pools", system_id=S3, protection_domain="pd1"))["storage_pools"][0]["name"] == "SP_SSD"
    gp = await call("get_storage_pool", system_id=S3, storage_pool="SP_SSD")
    assert gp["io"]["read_iops"] == 1000.0 and gp["rebuild_rebalance"]["fwdRebuildReadBwc_mbps"] == 50.0, gp
    assert gp["devices"]["by_state_error"] == {"Normal/None": 1, "Normal/DeviceErrorReported": 1}
    assert [x["name"] for x in (await call("list_sds", system_id=S3, problems_only=True))["sds"]] == ["sds-02"]
    gs = await call("get_sds", system_id=S3, sds="sds-01")
    assert gs["devices"][0]["deviceCurrentPathName"] == "/dev/nvme0n1"
    assert (await call("list_sdc", system_id=S3, name_contains="10.1.0.2"))["total"] == 1
    gc = await call("get_sdc", system_id=S3, sdc="10.1.0.1")       # by IP
    assert gc["volumes"][0]["name"] == "ds_prod01" and gc["io"]["read_latency_ms"] == 0.5, gc
    lv = await call("list_volumes", system_id=S3, snapshots=False)
    assert lv["total"] == 2 and lv["items"][0]["size_gb"] == 512.0
    assert (await call("list_volumes", system_id=S3, sdc="esx02"))["items"][0]["name"] == "ds_test02"
    gv = await call("get_volume", system_id=S3, volume="DS_PROD01")
    assert gv["storage_pool"] == "SP_SSD" and gv["protection_domain"] == "PD1"
    assert gv["vtree"][0]["name"] == "ds_prod01_snap" and gv["io"]["write_latency_ms"] == 1.2
    assert gv["linux_device"] == f"/dev/disk/by-id/emc-vol-{S3}-{V1}"
    assert gv["volume"]["creationTime_utc"].startswith("2026-")
    fv = await call("find_volume", key=f"/dev/disk/by-id/emc-vol-{S3}-{V1}")
    assert fv["found"] == 1 and fv["volumes"][0]["system_id"] == S3     # the path names the system
    assert (await call("find_volume", key="eui." + S3 + V2, system_id=S3))["volumes"][0]["name"] == "ds_test02"
    assert (await call("find_volume", key="prod", system_id=S3))["found"] == 2
    ld = await call("list_devices", system_id=S3, problems_only=True)
    assert ld["total"] == 1 and ld["items"][0]["sds"] == "sds-02"
    assert (await call("list_fault_sets", system_id=S3))["fault_sets"][0]["sds"] == []
    rep = await call("get_replication", system_id=S3, rcg="rcg_prod")
    assert rep["rcgs"][0]["rpoInSeconds"] == 60 and rep["pairs"] and rep["sdrs"] == []
    assert "note" in await call("list_snapshot_policies", system_id=S3)
    assert "note" in await call("list_nvme", system_id=S3)
    hv = await call("get_sdc", system_id=S4, sdc="OCP-WORKER-1")     # NVMe/TCP host by name
    assert hv["type"] == "nvme_host" and hv["volumes"][0]["name"] == "k8s-1a2b3c4d5e" and hv["io"]["read_latency_ms"] == 0.5, hv
    fh = await call("find_volume", key=f"{S4}-{V4}")                  # CSI PV volumeHandle -> only that system
    assert fh["found"] == 1 and fh["volumes"][0]["system_id"] == S4 and fh["volumes"][0]["mappedSdcInfo"][0]["hostType"] == "NVMeHost", fh
    assert (await call("find_volume", key="nvme-eui." + S4 + V4, system_id=S4))["volumes"][0]["name"] == "k8s-1a2b3c4d5e"
    assert (await call("list_volumes", system_id=S4, name_contains="k8s-", unmapped_only=False))["total"] == 1
    ev = await call("get_events", system_id=S4, since_hours=0)
    assert [e["id"] for e in ev["events"]] == ["e2", "e1", "e0"], ev
    assert (await call("get_events", system_id=S4, since_hours=24 * 365 * 3, severity="major"))["total"] == 1
    assert "showevents" in (await call("get_events", system_id=S3))["note"]
    nl = await call("get_network_latency", system_id=S3)
    assert nl["protection_domains"][0]["connectivity"]["allSdssConnected"] is True
    assert nl["sds"][0]["latency_meters"][0]["averageMessageWaitTime_ms"] == 0.35, nl
    al = await call("get_alerts", system_id=S3, severity="critical")
    assert al["total"] == 1 and al["alerts"][0]["alertType"] == "SDS_DISCONNECTED"
    assert (await call("get_alerts", system_id=S3))["alerts"][0]["id"] == "2"           # newest first

    props = await call("list_statistics_properties", object_type="Volume", system_id=S3)
    assert props["properties"]["userDataSdcReadLatency"] == "latency (ms)"
    st = await call("get_statistics", object_type="Volume", object="ds_test02", system_id=S3)
    assert st["statistics"]["read_latency_ms"] == 6.0 and st["statistics"]["total_iops"] == 300.0, st
    st2 = await call("get_statistics", object_type="System", system_id=S3, properties="ALL", samples=2, interval_seconds=1)
    assert st2["statistics"]["userDataReadBwc_iops"]["avg"] == 1000.0 and st2["statistics"]["maxCapacity_gb"]["max"] == 100.0
    try:
        await call("get_statistics", object_type="Volume", object=V1, system_id=S3, properties="bogusName")
        raise SystemExit("bad statistic accepted")
    except Exception as e:
        assert "Unknown statistics" in str(e)
    try:
        await call("get_statistics", object_type="System", system_id=S3, samples=60, interval_seconds=10)
        raise SystemExit("long sampling accepted")
    except Exception as e:
        assert "<= 300" in str(e)
    for sys_id in (S3, S4):                                         # S3: bulk query, S4: per-object fallback
        ov = await call("get_performance_overview", system_id=sys_id, top_n=5)
        assert ov["top_volumes_by_iops"][0]["name"] == "ds_prod01", ov["top_volumes_by_iops"]
        assert ov["worst_latency_volumes"][0]["name"] == "ds_test02"
        assert ov["worst_latency_sdcs"][0]["name"] == "esx02" and ov["top_sds_by_iops"]
        assert ov["storage_pools"]["SP_SSD"]["rebuild_rebalance_mbps"] == 50.0
        assert ("top_nvme_hosts_by_iops" in ov) == (sys_id == S4), list(ov)
    print("overview:", ov["system"], "| worst vol:", ov["worst_latency_volumes"][0])
    assert (await call("metrics_query", system_id=S4, resource_type="volume", metrics="host_read_iops"))["response"]
    await call("powerflex_get", system_id=S3, path="/api/types/FaultSet/instances")

    # ---- writes must be blocked before send ----
    n_before = len(SENT)
    g = server.REG.gateways["gw3"]
    b = g.base
    attempts = [
        ("POST", f"{b}/api/types/Volume/instances"),                                   # create volume
        ("POST", f"{b}/api/instances/Volume::{V1}/action/removeVolume"),
        ("POST", f"{b}/api/instances/Volume::{V1}/action/addMappedSdc"),
        ("POST", f"{b}/api/instances/System/action/snapshotVolumes"),
        ("POST", f"{b}/api/instances/Sds::{SDS1}/action/enterMaintenanceMode"),
        ("PUT", f"{b}/api/instances/Volume::{V1}"),
        ("DELETE", f"{b}/rest/v1/whatever"),
        ("POST", f"{b}/api/instances/querySelectedStatistics/../Volume::{V1}/action/removeVolume"),
        ("POST", f"{b}/rest/auth/logout"),
        ("POST", f"{b}/api/instances/Sds::{SDS1}/action/setSdsNetworkLimits"),
        ("POST", f"{b}/api/instances/Sds::x/action/querySdsNetworkLatencyMeters"),         # id must be 16 hex
        ("POST", f"{b}/api/instances/ProtectionDomain::{PD}/action/setSdsNetworkLimits"),
        ("GET", f"{b}/../etc/passwd"),
        ("GET", "https://evil.example/other"),
    ]
    for meth, url in attempts:
        try:
            g.s.request(meth, url, json={})
            raise SystemExit(f"NOT BLOCKED: {meth} {url}")
        except server.ReadOnlyViolation as e:
            print("blocked:", e)
    for bad in ("/../api/types/Volume/instances", "/etc/passwd", "api/types"):
        try:
            await call("powerflex_get", system_id=S3, path=bad)
            raise SystemExit(f"bad path accepted: {bad}")
        except Exception:
            pass
    assert len(SENT) == n_before, "a blocked request reached the network"
    posts = sorted({p for m, _, p in SENT if m != "GET"})
    assert all(server._READ_POSTS.match(p) for p in posts), posts
    print("POSTs sent (all read-only queries):", posts, "| requests:", len(SENT))
    print("ALL TESTS PASSED")


asyncio.run(main())
