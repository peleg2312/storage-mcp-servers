"""Offline test of the SAN composite tools with realistic NX-OS text output (fabric A + B)."""
import asyncio
import os

os.environ.update(MDS_1_NAME="mds-fab-a", MDS_1_HOST="10.0.0.1", MDS_1_USERNAME="ro", MDS_1_PASSWORD="x",
                  MDS_2_NAME="mds-fab-b", MDS_2_HOST="10.0.0.2", MDS_2_USERNAME="ro", MDS_2_PASSWORD="y")

import requests  # noqa: E402
import entry  # noqa: E402,F401
import main  # noqa: E402

HOST = "20:00:00:25:b5:0a:00:01"
ARR = "50:00:09:73:00:12:34:56"

A = {
    "show device-alias database": """\
device-alias name esx01_hba0 pwwn 20:00:00:25:b5:0a:00:01
device-alias name vmax_fa1d4 pwwn 50:00:09:73:00:12:34:56
device-alias name vmax_old pwwn 50:00:09:73:00:99:99:99

Total number of entries = 3
""",
    "show flogi database": """\
--------------------------------------------------------------------------------
INTERFACE        VSAN    FCID           PORT NAME               NODE NAME
--------------------------------------------------------------------------------
fc1/9            100   0x010500  50:00:09:73:00:12:34:56 50:00:09:73:00:12:34:00
                           [vmax_fa1d4]
port-channel10   100   0x010400  20:00:00:25:b5:0a:00:01 20:00:00:25:b5:00:00:01
                           [esx01_hba0]
port-channel10   100   0x010401  20:00:00:25:b5:0a:00:03 20:00:00:25:b5:00:00:03
port-channel10   100   0x010402  20:00:00:25:b5:0a:00:05 20:00:00:25:b5:00:00:05

Total number of flogi = 4.
""",
    "show fcns database": """\
VSAN 100:
--------------------------------------------------------------------------
FCID        TYPE  PWWN                    (VENDOR)        FC4-TYPE:FEATURE
--------------------------------------------------------------------------
0x010400    N     20:00:00:25:b5:0a:00:01                 scsi-fcp:init fc-gs
                  [esx01_hba0]
0x010500    N     50:00:09:73:00:12:34:56 (EMC)           scsi-fcp:target
                  [vmax_fa1d4]

Total number of entries = 2
""",
    "show zoneset active": """\
zoneset name ZS_FAB_A vsan 100
  zone name z_esx01_vmax vsan 100
  * fcid 0x010400 [pwwn 20:00:00:25:b5:0a:00:01] [esx01_hba0]
  * fcid 0x010500 [pwwn 50:00:09:73:00:12:34:56] [vmax_fa1d4]

  zone name z_esx01_old vsan 100
  * fcid 0x010400 [device-alias esx01_hba0]
    device-alias vmax_old

  zone name z_other vsan 100
    pwwn 20:00:00:25:b5:0a:00:09
""",
    "show port-channel database": """\
port-channel 10
    Administrative channel mode is active
    Operational channel mode is active
    Last membership update succeeded
    First operational port is fc1/1
    2 ports in total, 1 ports up
    Ports:   fc1/1    [up] *
             fc1/2    [down]
""",
    "show port-channel database interface port-channel10": """\
port-channel 10
    2 ports in total, 1 ports up
    Ports:   fc1/1    [up] *
             fc1/2    [down]
""",
    "show interface port-channel10": """\
port-channel10 is trunking
    Hardware is Fibre Channel
    Port WWN is 24:0a:00:de:fb:00:00:00
    Admin port mode is F, trunk mode is on
    Port mode is TF
    Port vsan is 1
    Operating Speed is 32 Gbps
    Trunk vsans (admin allowed and active) (1,100)
    Trunk vsans (up)                       (100)
    Member[1] : fc1/1
    Member[2] : fc1/2
""",
    "show interface fc1/1": """\
fc1/1 is trunking
    Port description is FI-A uplink 1
    Port mode is TF
    Operating Speed is 32 Gbps
    Transmit B2B Credit is 64
    Receive B2B Credit is 32
    5 minutes input rate 1024 bits/sec,128 bytes/sec, 2 frames/sec
    1234 frames input,567890 bytes
      0 discards,7 errors
      7 invalid CRC/FCS,0 unknown class
      0 too long,0 too short
    2345 frames output,678901 bytes
      0 discards,0 errors
    3 input OLS,2 LRR,0 NOS,0 loop inits
    1 link failures,0 sync losses,0 signal losses
      12 Transmit B2B credit transitions to zero
""",
    "show interface fc1/2": """\
fc1/2 is down (Link failure or not-connected)
    Port description is FI-A uplink 2
    Port mode is F
    Operating Speed is 16 Gbps
      0 discards,0 errors
""",
}
A["show interface"] = A["show interface fc1/1"] + A["show interface fc1/2"] + A["show interface port-channel10"] + """\
fc1/9 is up
    Port mode is F
    Operating Speed is 32 Gbps
      0 discards,0 errors
      0 invalid CRC/FCS,0 unknown class
fc1/20 is down (Administratively down)
    Port mode is auto
"""
A["show flogi database vsan 100"] = A["show flogi database"]
B = {k: "" for k in A}
B["show device-alias database"] = A["show device-alias database"]
B["show port-channel database"] = ""
B["show interface"] = "fc1/1 is up\n    Port mode is F\n      0 discards,0 errors\n"
SENT = []


class R:
    status_code = 200

    def __init__(self, d):
        self._d, self.text = d, str(d)

    def json(self):
        return self._d


def fake_post(url, json=None, **kw):
    cmd, method = json[0]["params"]["cmd"], json[0]["method"]
    sw = A if "10.0.0.1" in url else B
    SENT.append(cmd)
    if cmd not in sw:
        return R({"jsonrpc": "2.0", "error": {"code": -32602, "message": "Input CLI command error",
                                               "data": {"msg": "% Invalid command"}}, "id": 1})
    return R({"jsonrpc": "2.0", "result": {"msg": sw[cmd]}, "id": 1})


main.requests.post = fake_post
requests.post = fake_post


async def m():
    names = {t.name for t in await main.mcp.list_tools()}
    for t in ("trace_wwpn", "zone_check", "port_channel_health", "scan_port_errors", "flogi_summary"):
        assert t in names, t
    print(len(names), "tools; prompts:", [p.name for p in await main.mcp.list_prompts()])

    async def call(n, **a):
        return (await main.mcp.call_tool(n, a)).structured_content

    t = await call("trace_wwpn", pwwn="20000025B50A0001")
    a = t["switches"]["mds-fab-a"]
    assert t["logged_in_on"] == ["mds-fab-a"], t["logged_in_on"]
    assert a["flogi"][0]["interface"] == "port-channel10" and a["flogi"][0]["alias"] == "esx01_hba0"
    assert a["fcns"][0]["fc4"].startswith("scsi-fcp:init") and a["device_aliases"] == ["esx01_hba0"]
    zn = {z["zone"]: z for z in a["zones"]}
    assert set(zn) == {"z_esx01_vmax", "z_esx01_old"}, zn.keys()
    assert zn["z_esx01_vmax"]["other_members"][0]["pwwns"] == [ARR] and zn["z_esx01_vmax"]["other_members"][0]["logged_in"]
    old = zn["z_esx01_old"]["other_members"][0]
    assert old["aliases"] == ["vmax_old"] and old["pwwns"] == ["50:00:09:73:00:99:99:99"] and not old["logged_in"]
    lp = a["login_ports"]["port-channel10"]
    assert [x["interface"] for x in lp["port_channel_members"]] == ["fc1/1", "fc1/2"] and lp["mode"] == "TF"
    print("trace warnings A:", a["warnings"])
    assert any("vmax_old" in w for w in a["warnings"])
    assert t["switches"]["mds-fab-b"]["warnings"] == ["not logged in (no FLOGI) on this switch"]

    z = await call("zone_check", member_a=HOST, member_b="vmax_fa1d4")
    assert z["zoned_together_on"] == ["mds-fab-a"]
    assert z["switches"]["mds-fab-a"]["shared_active_zones"][0]["zone"] == "z_esx01_vmax"
    assert z["switches"]["mds-fab-a"]["b"]["in_fcns"] is True
    z2 = await call("zone_check", member_a=HOST, member_b="20:00:00:25:b5:0a:00:09", switch="mds-fab-a")
    assert z2["zoned_together_on"] == []

    pc = await call("port_channel_health", switch="mds-fab-a")
    p10 = pc["switches"]["mds-fab-a"]["port-channel10"]
    print("pc10:", p10["members_up"], "/", p10["members_total"], p10["problems"])
    assert p10["members_up"] == 1 and p10["trunk_vsans_up"] == "100" and p10["speed"] == "32 Gbps"
    m1 = p10["members"][0]["nonzero_counters"]
    assert m1["invalid crc/fcs"] == 7 and m1["link failures"] == 1 and m1["transmit b2b credit transitions to zero"] == 12, m1
    assert any("different speeds" in x for x in p10["problems"]) and any("fc1/2 member state is down" in x for x in p10["problems"])

    sc = await call("scan_port_errors", switch="mds-fab-a")
    s = sc["switches"]["mds-fab-a"]
    print("scan:", [(x["interface"], x["total"]) for x in s["top"]], "not up:", s["not_up"], "admin down:", s["admin_down_count"])
    assert s["top"][0]["interface"] == "fc1/1" and s["admin_down_count"] == 1
    assert [x["interface"] for x in s["not_up"]] == ["fc1/2"]

    fs = await call("flogi_summary", switch="mds-fab-a")
    f = fs["switches"]["mds-fab-a"]
    assert f["interfaces"][0] == {"interface": "port-channel10", "logins": 3, "vsans": [100],
                                  "likely": "NPV uplink (e.g. UCS FI)"} and f["per_vsan"] == {"100": 4} or f["per_vsan"] == {100: 4}
    print("flogi summary:", f["interfaces"])

    try:
        await main.mcp.call_tool("trace_wwpn", {"pwwn": "nope"})
        raise SystemExit("bad wwpn accepted")
    except Exception as e:
        assert "16 hex digits" in str(e)
    assert all(c.startswith("show ") and not any(x in c for x in ";|>\n`") for c in SENT)
    print("commands used:", sorted(set(SENT)))
    print("ALL TESTS PASSED")


asyncio.run(m())
