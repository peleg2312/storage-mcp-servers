"""Offline test of the wrapped mds-mcp: fake NX-API, tools work, guard blocks non-show/chained commands."""
import asyncio
import os

os.environ.update(MDS_1_NAME="mds-fab-a", MDS_1_HOST="10.0.0.1", MDS_1_USERNAME="ro", MDS_1_PASSWORD="x",
                  MDS_2_NAME="mds-fab-b", MDS_2_HOST="10.0.0.2", MDS_2_USERNAME="ro", MDS_2_PASSWORD="y")

import requests  # noqa: E402
import entry  # noqa: E402
import main  # noqa: E402

SENT = []


class R:
    status_code = 200

    def __init__(self, cmd):
        self.cmd = cmd

    def raise_for_status(self):
        pass

    def json(self):
        if "flogi" in self.cmd:
            return {"result": {"body": {"TABLE_flogi_entry": {"ROW_flogi_entry": [
                {"interface": "fc1/5", "vsan": 100, "fcid": "0x010203", "port_name": "20:00:00:25:b5:0a:00:01"}]}}}}
        return {"result": {"body": {"sys_ver_str": "9.4(2)"}}}


def fake_post(url, json=None, **kw):
    cmd = json[0]["params"]["cmd"]
    SENT.append((url, cmd, json[0]["method"]))
    return R(cmd)


main.requests.post = fake_post
requests.post = fake_post


async def m():
    tools = await main.mcp.list_tools()
    prompts = await main.mcp.list_prompts()
    print(len(tools), "tools,", [p.name for p in prompts])
    assert "READ-ONLY gateway to Cisco MDS" in main.mcp.instructions

    async def call(n, **a):
        return (await main.mcp.call_tool(n, a)).structured_content

    print((await call("list_switches")))
    r = await call("show_flogi_database", switch="mds-fab-a")
    print("flogi:", str(r)[:160])
    await call("show_version", switch="mds-fab-b")
    await call("show_interface_counters_detailed_for", switch="mds-fab-a", interface="fc1/5")
    for bad in ("show version ; configure terminal", "show run | include x", "show version\nreload",
                "configure terminal", "clear counters", "show logging > bootflash:x"):
        try:
            main._run_cli("mds-fab-a", bad)
            raise SystemExit(f"NOT BLOCKED: {bad!r}")
        except ValueError as e:
            print("blocked:", str(e)[:80])
    for bad_if in ("fc1/1 ; conf t", "fc1/1 | x"):
        try:
            await call("show_interface_for", switch="mds-fab-a", interface=bad_if)
            raise SystemExit("bad interface accepted")
        except Exception:
            pass
    assert all(c.startswith("show ") and not any(x in c for x in ";|>\n") for _, c, _ in SENT), SENT
    print("commands sent:", [c for _, c, _ in SENT])
    print("ALL TESTS PASSED")


asyncio.run(m())
