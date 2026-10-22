"""Offline tests: two fake UCS Centrals; every tool works, multi-instance merge works,
and write attempts never reach the network."""
import asyncio
import os
import re

os.environ.update(UCSC_1_NAME="ucsc-dc1", UCSC_1_HOST="ucsc1.test", UCSC_1_USERNAME="ro", UCSC_1_PASSWORD="x",
                  UCSC_2_NAME="ucsc-dc2", UCSC_2_HOST="ucsc2.test", UCSC_2_USERNAME="ro", UCSC_2_PASSWORD="y")

from ucscsdk.ucscsession import UcscSession  # noqa: E402
from ucscsdk.mometa.ls.LsServer import LsServer  # noqa: E402
from ucscsdk.ucscmethodfactory import config_conf_mo  # noqa: E402
import server  # noqa: E402

SENT = []
SP = "org-root/ls-esx01"
W = "20:00:00:25:B5:0A:00:01"
BL = "compute/sys-1008/chassis-1/blade-1"
DC1 = {
    "computeSystem": '<computeSystem dn="compute/sys-1008" id="1008" name="dc1-ucs" address="10.0.0.5" fwPackageVersion="4.2(3d)" subscribeStatus="subscribed" inventoryStatus="ok" />',
    "networkElement": '<networkElement dn="compute/sys-1008/switch-A" id="A" model="UCS-FI-6454" serial="FDO1" oobIfIp="10.0.0.6" operability="operable" />'
                      '<networkElement dn="compute/sys-1008/switch-B" id="B" model="UCS-FI-6454" serial="FDO2" oobIfIp="10.0.0.7" operability="operable" />',
    "equipmentChassis": '<equipmentChassis dn="compute/sys-1008/chassis-1" id="1" model="UCSB-5108" operability="operable" operState="operable" />',
    "equipmentPsu": '<equipmentPsu dn="compute/sys-1008/chassis-1/psu-2" id="2" model="PSU" operability="inoperable" />',
    "equipmentFan": "", "equipmentIOCard": "",
    "computeBlade": f'<computeBlade dn="{BL}" model="UCSB-B200-M5" serial="FCH1" operState="ok" operability="operable" association="associated" assignedToDn="{SP}" />'
                    '<computeBlade dn="compute/sys-1008/chassis-1/blade-2" model="UCSB-B200-M5" serial="FCH2" operState="inoperable" operability="inoperable" association="none" />',
    "computeRackUnit": "",
    "faultInst": '<faultInst dn="compute/sys-1008/chassis-1/psu-2/fault-F0369" severity="major" code="F0369" ack="no" descr="PSU 2 failed" created="2026-10-20T10:00:00" />'
                 f'<faultInst dn="{SP}/fault-F0001" severity="critical" code="F0001" ack="no" descr="SP config failure" created="2026-10-19T10:00:00" />'
                 f'<faultInst dn="{BL}/fault-F0283" severity="minor" code="F0283" ack="yes" descr="vHBA link down" created="2026-10-21T09:00:00" />',
    "lsServer": f'<lsServer dn="{SP}" name="esx01" type="instance" assocState="associated" configState="applied" pnDn="{BL}" />',
    "vnicFc": f'<vnicFc dn="{SP}/fc-vHBA-A" name="vHBA-A" addr="{W}" switchId="A" operIdentPoolName="org-root/wwn-pool-WWPN-A" />',
    "vnicFcIf": f'<vnicFcIf dn="{SP}/fc-vHBA-A/if-default" name="vsan-100" operVnetName="vsan-100" />',
    "vnicEther": f'<vnicEther dn="{SP}/ether-eth0" name="eth0" addr="00:25:B5:00:00:01" switchId="A" />',
    "fcpoolInitiator": f'<fcpoolInitiator dn="org-root/wwn-pool-WWPN-A/initiator-{W}" id="{W}" assigned="yes" assignedToDn="{SP}/fc-vHBA-A" />',
    "fcpoolInitiators": '<fcpoolInitiators dn="org-root/wwn-pool-WWPN-A" name="WWPN-A" purpose="port-wwn-assignment" size="256" assigned="40" />',
    "fcpoolBlock": '<fcpoolBlock dn="org-root/wwn-pool-WWPN-A/block-1" from="20:00:00:25:B5:0A:00:00" to="20:00:00:25:B5:0A:00:FF" />',
    "adaptorUnit": f'<adaptorUnit dn="{BL}/adaptor-1" id="1" model="UCSB-MLOM-40G-04" operability="operable" />',
    "adaptorHostFcIf": f'<adaptorHostFcIf dn="{BL}/adaptor-1/host-fc-1" name="vHBA-A" wwn="{W}" switchId="A" operState="up" />',
    "fcPIo": '<fcPIo dn="compute/sys-1008/switch-A/slot-1/switch-fc/port-1" switchId="A" slotId="1" portId="1" adminState="enabled" operState="up" operSpeed="32gbps" />'
             '<fcPIo dn="compute/sys-1008/switch-B/slot-1/switch-fc/port-1" switchId="B" slotId="1" portId="1" adminState="enabled" operState="link-down" operSpeed="indeterminate" />',
    "fabricVsan": '<fabricVsan dn="fabric/san/A/net-vsan-100" id="100" name="vsan-100" switchId="A" zoningState="disabled" />',
    "firmwareRunning": '<firmwareRunning dn="sys/mgmt/fw-system" deployment="system" type="system" version="2.0(1q)" />',
    "aaaModLR": '<aaaModLR dn="sys/audit/1" id="1" created="2026-10-21T08:00:00" user="admin" descr="Service profile esx01 modified" ind="modification" />'
                '<aaaModLR dn="sys/audit/2" id="2" created="2026-10-21T09:00:00" user="ops" descr="VLAN 20 created" ind="creation" />',
    "eventInst": '<eventInst dn="event-log/1" id="1" created="2026-10-21T09:30:00" descr="Domain 1008 inventory sync" severity="info" />',
}
DC2 = {
    "computeSystem": '<computeSystem dn="compute/sys-2001" id="2001" name="dc2-ucs" address="10.1.0.5" />',
    "computeBlade": '<computeBlade dn="compute/sys-2001/chassis-1/blade-1" model="UCSB-B200-M6" serial="FCH9" operState="ok" operability="operable" />',
    "faultInst": '<faultInst dn="compute/sys-2001/fault-F0207" severity="critical" code="F0207" ack="no" descr="FI B unreachable" created="2026-10-21T11:00:00" />',
}
TOP = {"ucsc1.test": '<topSystem dn="sys" name="ucs-central-dc1" address="10.0.0.2" />',
       "ucsc2.test": '<topSystem dn="sys" name="ucs-central-dc2" address="10.1.0.2" />'}


def fake_post_xml(self, xml_str, read=True, dme="central-mgr"):
    if isinstance(xml_str, bytes):
        xml_str = xml_str.decode()
    method = re.match(r"\s*<(\w+)", xml_str).group(1)
    SENT.append((self.ip, method))
    data = DC1 if self.ip == "ucsc1.test" else DC2
    if method == "aaaLogin":
        return '<aaaLogin cookie="" response="yes" outCookie="c1" outRefreshPeriod="600" outPriv="read-only" outVersion="2.0(1q)" outSessionId="s1" />'
    if method == "configResolveDn":
        dn = re.search(r'dn="([^"]*)"', xml_str).group(1)
        body = ""
        if dn == "sys":
            body = TOP[self.ip]
        else:
            for objs in data.values():
                for m in re.finditer(r"<\w+ [^>]*/>", objs):
                    if f'dn="{dn}"' in m.group(0):
                        body = m.group(0)
        return f'<configResolveDn dn="{dn}" cookie="c1" response="yes"><outConfig>{body}</outConfig></configResolveDn>'
    if method in ("configResolveClass", "configResolveChildren"):
        cid = re.search(r'classId="(\w+)"', xml_str).group(1)
        objs = data.get(cid, "")
        if method == "configResolveChildren":
            parent = re.search(r'inDn="([^"]*)"', xml_str).group(1)
            objs = "".join(m.group(0) for m in re.finditer(r"<\w+ [^>]*/>", objs)
                           if re.search(rf'dn="{re.escape(parent)}/[^/"]+"', m.group(0)))
        return f'<{method} cookie="c1" response="yes"><outConfigs>{objs}</outConfigs></{method}>'
    if method == "aaaLogout":
        return '<aaaLogout cookie="" response="yes" outStatus="success" />'
    raise AssertionError(f"Write method reached the network: {method}")


UcscSession.post_xml = fake_post_xml


async def main():
    tools = await server.mcp.list_tools()
    print(len(tools), "tools:", sorted(t.name for t in tools))
    print("prompts:", [p.name for p in await server.mcp.list_prompts()])
    assert all(getattr(t.annotations, "read_only_hint", None) or t.annotations.readOnlyHint for t in tools)

    async def call(name, **args):
        return (await server.mcp.call_tool(name, args)).structured_content

    tc = await call("test_connection")
    assert all(x["ok"] for x in tc["centrals"]), tc
    print("centrals:", [(x["central"], x["ucs_central"]) for x in tc["centrals"]])
    d = await call("list_domains")
    assert {r["central"] for r in d["items"]} == {"ucsc-dc1", "ucsc-dc2"} and d["total"] == 2
    fl = await call("list_faults", severity="critical,major")
    assert [f["code"] for f in fl["items"]] == ["F0207", "F0001", "F0369"], [f["code"] for f in fl["items"]]
    print("faults merged:", [(f["central"], f["severity"], f["code"]) for f in fl["items"]])
    h = await call("get_domain_health", domain="1008", central="ucsc-dc1")
    assert h["servers"]["not_operable"] == 1 and any(p["class"] == "equipmentPsu" for p in h["hardware_problems"])
    print("domain health:", h["servers"], h["faults_by_severity"], [p["dn"] for p in h["hardware_problems"]])
    s = await call("get_server", dn=BL)
    assert s["fc_interfaces"][0]["wwpn"] == W and s["faults"][0]["code"] == "F0283" and s["central"] == "ucsc-dc1"
    sp = await call("get_service_profile", sp_dn=SP)
    assert sp["vhbas"][0]["vsan"] == ["vsan-100"] and sp["vnics"][0]["mac"] and sp["faults"][0]["code"] == "F0001"
    print("service profile:", sp["name"], sp["assoc_state"], sp["vhbas"][0]["wwpn"], sp["vhbas"][0]["fabric"])
    fw = await call("find_wwpn", wwpn="20000025b50a0001")
    r = fw["results"][0]
    assert r["vhbas"][0]["service_profile_dn"] == SP and r["physical_interfaces"][0]["server_dn"] == BL
    up = await call("list_fc_uplinks", problems_only=True)
    assert up["total"] == 1 and up["items"][0]["switch_id"] == "B"
    print("FC uplinks down:", [(u["domain"], u["switch_id"], u["port_id"], u["oper_state"]) for u in up["items"]])
    au = await call("get_audit_log")
    assert au["items"][0]["user"] == "ops"
    for t, a in [("list_centrals", {}), ("list_fabric_interconnects", {}), ("list_chassis", {}),
                 ("list_servers", {"problems_only": True}), ("list_service_profiles", {}),
                 ("get_service_profile_vhbas", {"sp_dn": SP}), ("list_wwn_pools", {}), ("list_vsans", {}),
                 ("list_firmware", {}), ("get_events", {}), ("get_object", {"dn": SP}),
                 ("query_class", {"class_id": "computeBlade", "prop": "model", "value": "UCSB-B200-M5"})]:
        await call(t, **a)
    try:
        await call("get_domain_health", domain="1008")
        raise SystemExit("ambiguous domain accepted")
    except Exception as e:
        assert "pass central" in str(e)

    # ---- writes must be blocked before reaching the network ----
    c = server.centrals()["ucsc-dc1"]
    h = c._h
    n = len(SENT)
    mo = LsServer(parent_mo_or_dn="org-root", name="hacked")
    for fn in (lambda: h.add_mo(mo), lambda: h.set_mo(mo), lambda: h.remove_mo(mo), lambda: h.commit(),
               lambda: h.file_download("x", "/tmp", "f"),
               lambda: h.post_elem(config_conf_mo(cookie="c1", dn="org-root/ls-hacked", in_config=None))):
        try:
            fn()
            raise SystemExit("WRITE NOT BLOCKED")
        except server.ReadOnlyViolation as e:
            print("blocked:", e)
    assert len(SENT) == n
    writes = [m for _, m in SENT if m not in server.ALLOWED_XML_METHODS]
    assert not writes, writes
    print("XML methods sent:", sorted({m for _, m in SENT}))
    print("ALL TESTS PASSED")


asyncio.run(main())
