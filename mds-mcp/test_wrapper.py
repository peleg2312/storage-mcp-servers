"""Offline test of the wrapped mds-mcp: fake NX-API (JSON + text modes, errors), upstream tools,
extra tools (run_show, OBFL, parsed logs, slow drain), and the read-only command guard."""
import asyncio
import os

os.environ.update(MDS_1_NAME="mds-fab-a", MDS_1_HOST="10.0.0.1", MDS_1_USERNAME="ro", MDS_1_PASSWORD="x",
                  MDS_2_NAME="mds-fab-b", MDS_2_HOST="10.0.0.2", MDS_2_USERNAME="ro", MDS_2_PASSWORD="y")

import requests  # noqa: E402
import entry  # noqa: E402,F401
import main  # noqa: E402

SENT = []
LOG_A = """\
2026 Oct 22 08:01:02 mds-fab-a %PORT-5-IF_DOWN_LINK_FAILURE: %$VSAN 100%$ Interface fc1/5 is down (Link failure)
2026 Oct 22 08:01:09 mds-fab-a %PORT-5-IF_UP: %$VSAN 100%$ Interface fc1/5 is up in mode F
2026 Oct 22 09:15:44.512 mds-fab-a %PMON-SLOT1-3-RISING_THRESHOLD_REACHED: TX Credit Not Available has reached the rising threshold (port=fc1/7 [0x1006000], value=12)
2026 Oct 22 09:30:00 mds-fab-a %AUTHPRIV-6-SYSTEM_MSG: pam_unix(dcos_sshd:session): session opened for user mcp-ro - dcos_sshd[1234]
2026 Oct 22 09:40:01 mds-fab-a _f worker %AUTHPRIV-3-SYSTEM_MSG: authentication failure; user=bob - dcos_sshd[99]
2026 Oct 20 01:00:00 mds-fab-a %ZONE-2-ZS_MERGE_FAILED: %$VSAN 200%$ Zone merge failure, isolating interface port-channel10
"""
LOG_B = "2026 Oct 22 09:50:00 mds-fab-b %PORT-5-IF_DOWN_LINK_FAILURE: %$VSAN 101%$ Interface fc2/3 is down (Link failure)\n"
OBFL_TXWAIT = """\
----------------------------------------------------------------------------------------------------
| Interface | Delta TxWait Time     | Congestion | Timestamp                    |
|           | 2.5us ticks | seconds |            |                              |
----------------------------------------------------------------------------------------------------
| fc1/7     |    6815744  |  17     |   85%      | Thu Oct 22 09:15:40 2026     |
| fc1/7     |    4194304  |  10     |   52%      | Thu Oct 22 09:15:20 2026     |
"""


class R:
    def __init__(self, status, data):
        self.status_code, self._d, self.text = status, data, str(data)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self.status_code)

    def json(self):
        return self._d


def ok(result):
    return R(200, {"jsonrpc": "2.0", "result": result, "id": 1})


def err(msg, data_msg, code=-32602, status=500):
    return R(status, {"jsonrpc": "2.0", "error": {"code": code, "message": msg, "data": {"msg": data_msg}}, "id": 1})


def fake_post(url, json=None, **kw):
    req = json[0]
    cmd, method = req["params"]["cmd"], req["method"]
    sw = "a" if "10.0.0.1" in url else "b"
    SENT.append((sw, method, cmd))
    if cmd.startswith("show logging last"):
        return ok({"msg": LOG_A if sw == "a" else LOG_B})
    if cmd == "show clock":
        return ok({"msg": "10:00:00.123 IST Thu Oct 22 2026\nTime source is NTP\n"})
    if cmd.startswith("show logging onboard"):
        if method == "cli":
            return err("Input CLI command error", "Structured output unsupported")
        if "txwait" in cmd:
            return ok({"msg": OBFL_TXWAIT})
        if "bogus" in cmd:
            return err("Input CLI command error", "% Invalid command at '^' marker.")
        return ok({"msg": ""})
    if cmd == "show port-monitor":
        if method == "cli":
            return ok({"body": {}})  # empty JSON body -> auto falls back to text
        return ok({"msg": "Policy Name  : fabricmon_edge_policy\nAdmin status : Active\n"})
    if cmd == "show big-json":
        return ok({"body": {"rows": ["x" * 40] * 800}}) if method == "cli" else ok({"msg": "line\n" * 5 + "needle\n"})
    if cmd == "show license usage":
        return err("Input CLI command error", "% Permission denied for the role")
    if cmd == "show flogi database":
        return ok({"body": {"TABLE_flogi_entry": {"ROW_flogi_entry": [
            {"interface": "fc1/5", "vsan": 100, "fcid": "0x010203", "port_name": "20:00:00:25:b5:0a:00:01"}]}}})
    return ok({"body": {"sys_ver_str": "9.4(2)"}})


main.requests.post = fake_post
requests.post = fake_post


async def m():
    tools = await main.mcp.list_tools()
    names = {t.name for t in tools}
    prompts = [p.name for p in await main.mcp.list_prompts()]
    print(len(tools), "tools,", prompts)
    for t in ("run_show", "show_logging_onboard", "get_log_events", "slow_drain_check"):
        assert t in names, t
    assert "get_log_events" in main.mcp.instructions
    assert "show_users" not in names and "show_flogi_database_for" not in names and len(tools) == 27, len(tools)
    # no hidden tool is still named in the instructions or prompts
    texts = [main.mcp.instructions]
    for pr in await main.mcp.list_prompts():
        texts.append((await main.mcp.render_prompt(pr.name, {a.name: "x" for a in (pr.arguments or []) if a.required})).messages[0].content.text)
    import re as _re
    used = set(_re.findall(r"\bshow_\w+", " ".join(texts)))
    assert not used & entry.HIDDEN, used & entry.HIDDEN

    async def call(n, **a):
        return (await main.mcp.call_tool(n, a)).structured_content

    async def call_err(n, **a):
        try:
            await main.mcp.call_tool(n, a)
        except Exception as e:
            return str(e)
        raise SystemExit(f"{n}{a} should have failed")

    # upstream tools still work
    r = await call("show_flogi_database", switch="mds-fab-a")
    assert r["response"]["result"]["body"]["TABLE_flogi_entry"]

    # parsed syslog across both switches
    ev = await call("get_log_events", max_severity=5)
    codes = [e["event"] for e in ev["events"]]
    print("log events:", codes)
    assert ev["events"][0]["switch"] == "mds-fab-b"  # newest first across switches
    assert "PMON-3-RISING_THRESHOLD_REACHED" in codes and "ZONE-2-ZS_MERGE_FAILED" in codes
    assert "AUTHPRIV-3-SYSTEM_MSG" in codes  # line with extra process token parsed
    assert not {"severity_name", "facility", "mnemonic", "slot", "_dt"} & set(ev["events"][0])
    pm = next(e for e in ev["events"] if e["event"].endswith("RISING_THRESHOLD_REACHED"))
    assert pm["interfaces"] == ["fc1/7"]
    zm = next(e for e in ev["events"] if e["event"].startswith("ZONE-"))
    assert zm["vsan"] == "200" and zm["interfaces"] == ["port-channel10"]
    print("summary:", ev["summary"]["by_severity"], ev["summary"]["top_interfaces"][:3])
    e24 = await call("get_log_events", switch="mds-fab-a", since_hours=24, max_severity=7)
    assert all("Oct 20" not in e["time"] for e in e24["events"]) and e24["total_matching"] == 5
    one = await call("get_log_events", interface="fc1/5", max_severity=7)
    assert {e["event"].split("-", 2)[2] for e in one["events"]} == {"IF_DOWN_LINK_FAILURE", "IF_UP"}
    fz = await call("get_log_events", facility="zone", max_severity=7)  # facility filter runs before the output fields are dropped
    assert fz["total_matching"] == 1

    # OBFL (text only) and errors
    ob = await call("show_logging_onboard", section="txwait", switch="mds-fab-a")
    assert "fc1/7" in ob["text"] and ob["command"] == "show logging onboard txwait"
    ob2 = await call("show_logging_onboard", section="error-stats", switch="mds-fab-a", module=1)
    assert ob2["command"] == "show logging onboard module 1 error-stats" and "note" in ob2
    e1 = await call_err("show_logging_onboard", section="bogus", switch="mds-fab-a")
    print("invalid section ->", e1[:110])
    assert "not valid on this switch" in e1
    e2 = await call_err("run_show", command="show license usage", switch="mds-fab-a")
    print("permission ->", e2[:110])
    assert "role is not allowed" in e2

    # run_show: JSON, auto fallback to text, grep
    rs = await call("run_show", command="show version", switch="mds-fab-a")
    assert rs["format"] == "json"
    rs2 = await call("run_show", command="show port-monitor", switch="mds-fab-a", grep="policy")
    assert rs2["format"] == "text" and rs2["returned_lines"] == 1, rs2
    rs3 = await call("run_show", command="show logging onboard txwait", switch="mds-fab-a", grep="52%")
    assert rs3["format"] == "text" and rs3["returned_lines"] == 1

    # big JSON falls back to text (cap), explicit json errors, small JSON unchanged
    big = await call("run_show", command="show big-json", switch="mds-fab-a")
    assert big["format"] == "text" and "note" in big and "needle" in big["text"], big
    assert "output='text'" in await call_err("run_show", command="show big-json", switch="mds-fab-a", output="json")
    # slow drain bundle
    sd = await call("slow_drain_check", switch="mds-fab-a")
    a = sd["switches"]["mds-fab-a"]
    assert "fc1/7" in a["txwait"]["text"] and a["log_warnings_by_interface"][0]["interface"] == "fc1/7"
    print("slow drain:", a["log_warnings_by_interface"], list(a))

    # guard: never send anything but one plain show
    for ok_cmd in ("show running-config interface fc1/1", "show run zone"):  # sections stay allowed
        await call("run_show", command=ok_cmd, switch="mds-fab-a")
    n = len(SENT)
    for bad in ("show version ; configure terminal", "show run | include x", "show version\nreload",
                "configure terminal", "clear counters", "show running-config", "show run", "show startup-config",
                "show snmp community", "show tacacs-server", "show aaa authentication", "show logging > bootflash:x", "show tech-support"):
        await call_err("run_show", command=bad, switch="mds-fab-a")
    await call_err("show_logging_onboard", section="txwait ; reload", switch="mds-fab-a")
    await call_err("show_logging_onboard", section="txwait | x", switch="mds-fab-a")
    assert len(SENT) == n, SENT[n:]
    assert all(c.startswith("show ") and not any(x in c for x in ";|>\n`") for _, _, c in SENT), SENT
    print("methods:", sorted({m for _, m, _ in SENT}), "commands:", sorted({c for _, _, c in SENT}))
    print("ALL TESTS PASSED")


asyncio.run(m())
