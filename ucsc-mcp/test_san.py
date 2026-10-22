"""Offline test of the UCS Central SAN tools (reuses the fake UCS Central from test_readonly.py)."""
import asyncio

src = open(__file__.replace("test_san.py", "test_readonly.py")).read().split("async def main")[0]
g = {"__name__": "fake"}
exec(compile(src, "test_readonly_fake", "exec"), g)
server, DC1, SENT = g["server"], g["DC1"], g["SENT"]

SP, BL, W = g["SP"], g["BL"], g["W"]
WB = "20:00:00:25:B5:0B:00:01"
D = "compute/sys-1008"
DC1.update({
    "vnicFc": f'<vnicFc dn="{SP}/fc-vHBA-A" name="vHBA-A" addr="{W}" switchId="A" pinToGroupName="pg-a" />'
              f'<vnicFc dn="{SP}/fc-vHBA-B" name="vHBA-B" addr="{WB}" switchId="B" pinToGroupName="" />',
    "vnicFcIf": f'<vnicFcIf dn="{SP}/fc-vHBA-A/if-default" name="vsan-100" operVnetName="vsan-100" />'
                f'<vnicFcIf dn="{SP}/fc-vHBA-B/if-default" name="vsan-200" operVnetName="vsan-200" />',
    "adaptorHostFcIf": f'<adaptorHostFcIf dn="{BL}/adaptor-1/host-fc-1" name="vHBA-A" wwn="{W}" switchId="A" operState="up" linkState="up" />'
                       f'<adaptorHostFcIf dn="{BL}/adaptor-1/host-fc-2" name="vHBA-B" wwn="{WB}" switchId="B" operState="link-down" linkState="down" />',
    "adaptorFcPortStats": f'<adaptorFcPortStats dn="{BL}/adaptor-1/host-fc-1/fc-port-stats" rxBadFrames="0" txBadFrames="0" />'
                          f'<adaptorFcPortStats dn="{BL}/adaptor-1/host-fc-2/fc-port-stats" rxBadFrames="42" txBadFrames="0" />',
    "fcPIo": f'<fcPIo dn="{D}/switch-A/slot-1/switch-fc/port-1" switchId="A" slotId="1" portId="1" ifRole="network" adminState="enabled" operState="up" operSpeed="32gbps" isPortChannelMember="yes" />'
             f'<fcPIo dn="{D}/switch-A/slot-1/switch-fc/port-2" switchId="A" slotId="1" portId="2" ifRole="network" adminState="enabled" operState="up" operSpeed="32gbps" isPortChannelMember="yes" />'
             f'<fcPIo dn="{D}/switch-B/slot-1/switch-fc/port-1" switchId="B" slotId="1" portId="1" ifRole="network" adminState="enabled" operState="link-down" operSpeed="indeterminate" isPortChannelMember="yes" />'
             f'<fcPIo dn="{D}/switch-B/slot-1/switch-fc/port-2" switchId="B" slotId="1" portId="2" ifRole="network" adminState="enabled" operState="up" operSpeed="32gbps" isPortChannelMember="yes" />',
    "fcErrStats": f'<fcErrStats dn="{D}/switch-A/slot-1/switch-fc/port-2/err-stats" crcRx="120" crcRxDelta="9" linkFailures="2" linkFailuresDelta="0" />'
                  f'<fcErrStats dn="{D}/switch-A/slot-1/switch-fc/port-1/err-stats" crcRx="0" crcRxDelta="0" />'
                  f'<fcErrStats dn="{D}/switch-B/slot-1/switch-fc/port-2/err-stats" discardTx="5" discardTxDelta="0" />',
    "fabricFcSanPc": f'<fabricFcSanPc dn="{D}/fabric/san/A/pc-10" switchId="A" portId="10" name="pc10" adminState="enabled" operState="up" operSpeed="64gbps" />'
                     f'<fabricFcSanPc dn="{D}/fabric/san/B/pc-20" switchId="B" portId="20" name="pc20" adminState="enabled" operState="up" operSpeed="32gbps" />',
    "fabricFcSanPcEp": f'<fabricFcSanPcEp dn="{D}/fabric/san/A/pc-10/ep-slot-1-port-1" slotId="1" portId="1" adminState="enabled" operState="up" />'
                       f'<fabricFcSanPcEp dn="{D}/fabric/san/A/pc-10/ep-slot-1-port-2" slotId="1" portId="2" adminState="enabled" operState="up" />'
                       f'<fabricFcSanPcEp dn="{D}/fabric/san/B/pc-20/ep-slot-1-port-1" slotId="1" portId="1" adminState="enabled" operState="down" operStateReason="link-failure" />'
                       f'<fabricFcSanPcEp dn="{D}/fabric/san/B/pc-20/ep-slot-1-port-2" slotId="1" portId="2" adminState="enabled" operState="up" />',
    "fabricSanPinGroup": '<fabricSanPinGroup dn="org-root/san-pin-group-pg-a" name="pg-a" />',
    "fabricSanPinTarget": f'<fabricSanPinTarget dn="org-root/san-pin-group-pg-a/target-A" fabricId="A" epDn="{D}/fabric/san/A/pc-10" targetStatus="valid" />',
    "fabricVsan": '<fabricVsan dn="compute/sys-1008/fabric/san/A/net-vsan-100" id="100" name="vsan-100" switchId="A" zoningState="disabled" />',
})
DC1["faultInst"] += f'<faultInst dn="{D}/switch-B/slot-1/switch-fc/port-1/fault-F0727" severity="major" code="F0727" ack="no" descr="FC uplink port 1/1 on fabric B is down" created="2026-10-22T08:00:00" />'


async def main():
    names = {t.name for t in await server.mcp.list_tools()}
    new = ("list_fc_port_channels", "get_fc_port_errors", "get_vhba_pinning", "trace_service_profile_san",
           "get_domain_fc_health")
    assert all(n in names for n in new), names
    print(len(names), "tools; prompts:", [p.name for p in await server.mcp.list_prompts()])

    async def call(n, **a):
        return (await server.mcp.call_tool(n, a)).structured_content

    pcs = await call("list_fc_port_channels", domain="1008", central="ucsc-dc1")
    r = pcs["results"][0]
    assert {p["port_channel"] for p in r["port_channels"]} == {"10", "20"}
    pc20 = next(p for p in r["port_channels"] if p["port_channel"] == "20")
    assert pc20["members_up"] == 1 and pc20["members"][0]["reason"] == "link-failure"
    print("pc problems:", pcs["problems"])
    assert any("pc-20: 1/2" in x for x in pcs["problems"])

    er = await call("get_fc_port_errors", domain="1008", central="ucsc-dc1")
    assert er["items"][0]["port"] == "1/2" and er["items"][0]["last_interval"] == {"crc_rx": 9}, er["items"][0]
    assert er["ports_with_current_errors"] == 1 and er["total"] == 2
    print("errors:", [(x["fabric"], x["port"], x["last_interval"], x["totals"]) for x in er["items"]])

    pin = await call("get_vhba_pinning", service_profile="esx01")
    pa = {v["name"]: v for v in pin["vhbas"]}
    assert pa["vHBA-A"]["targets"][0]["target"].endswith("/pc-10") and pa["vHBA-B"]["mode"].startswith("dynamic")

    t = await call("trace_service_profile_san", service_profile="esx01")
    print("trace problems:")
    for p in t["problems"]:
        print("   -", p)
    paths = {p["vhba"]: p for p in t["paths"]}
    assert paths["vHBA-A"]["vsan"] == ["vsan-100"] and paths["vHBA-B"]["adapter_interface"]["rx_bad_frames"] == 42
    assert t["domain"] == "1008" and set(t["fabric_interconnect"]) == {"A", "B"}
    pr = " | ".join(t["problems"])
    for frag in ("vHBA-B: adapter link_state down", "bad frames rx=42", "FI FC uplink 1/1 is link-down",
                 "errors now {'crc_rx': 9}", "port-channel 20 has 1/2 members up"):
        assert frag in pr, frag
    assert paths["vHBA-A"]["next_hops"]["mds"] == f"trace_wwpn pwwn={W}"

    h = await call("get_domain_fc_health", domain="1008", central="ucsc-dc1")
    print("domain fc health: down", h["enabled_ports_not_up"], "| errors now", h["ports_with_errors_now"],
          "| vHBA links", h["vhba_adapter_interfaces_by_link_state"], "| fc faults", [f["code"] for f in h["fc_faults"]])
    assert h["enabled_ports_not_up"] == [{"fabric": "B", "port": "1/1", "role": "network", "oper_state": "link-down"}]
    assert "F0727" in [f["code"] for f in h["fc_faults"]] and h["vsans"][0]["id"] == "100"

    try:
        await server.mcp.call_tool("trace_service_profile_san", {"service_profile": "nope"})
        raise SystemExit("unknown SP accepted")
    except Exception as e:
        assert "No service profile named" in str(e)
    writes = [m for _, m in SENT if m not in server.ALLOWED_XML_METHODS]
    assert not writes
    print("ALL TESTS PASSED")


asyncio.run(main())
