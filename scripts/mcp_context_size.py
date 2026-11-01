#!/usr/bin/env python3
"""What each MCP server of this repository hands Claude at session start: its instructions and every tool's name, description
and input schema, in bytes and approximate tokens (bytes / 4). Run it on a machine with the servers' packages (a venv with
`pip install fastmcp requests ucscsdk prefab-ui`); the servers are imported, not started, and no backend is contacted.
With Claude Code's tool search on (ENABLE_TOOL_SEARCH=true, set by brain/merge_settings.py) only the names and the
instructions load upfront; the schemas are what the setting keeps out of every session. docs-local is measured through
its own tools/list. The NetApp ontap and harvest servers are not in this repository and are not measured.

  python3 scripts/mcp_context_size.py            (from the repository root)"""
import asyncio, importlib.util, json, os, sys, subprocess
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("MCP_AUTH_TOKENS", "x" * 32)
for k, v in (("MDS_1_HOST", "mds.example"), ("MDS_1_USERNAME", "ro"), ("MDS_1_PASSWORD", "x")):   # the upstream MDS server wants a switch at import
    os.environ.setdefault(k, v)
def load(path, name):
    sys.path.insert(0, os.path.dirname(path))
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    sys.path.pop(0); return m
async def measure(mcp):
    tools = await mcp.list_tools() if hasattr(mcp, "list_tools") else await mcp.get_tools()
    if isinstance(tools, dict): tools = list(tools.values())
    out = []
    for t in tools:
        mt = t.to_mcp_tool() if hasattr(t, "to_mcp_tool") else t
        d = mt.model_dump(exclude_none=True) if hasattr(mt, "model_dump") else dict(mt)
        out.append((d.get("name"), len(json.dumps({"name": d.get("name"), "description": d.get("description", ""), "inputSchema": d.get("inputSchema") or d.get("parameters")}))))
    return out
rows = []
for name, path, attr in (("powermax", "powermax-mcp/server.py", "mcp"), ("powerflex", "powerflex-mcp/server.py", "mcp"), ("ucsc", "ucsc-mcp/server.py", "mcp"), ("mds", "mds-mcp/entry.py", "mcp")):
    try:
        m = load(os.path.join(R, path), name.replace("-", "_"))
        mcp = getattr(m, attr, None) or getattr(m, "server", None) or getattr(getattr(m, "main", None), "mcp", None)
        tools = asyncio.run(measure(mcp))
        ins = len(getattr(mcp, "instructions", "") or "")
        tot = sum(b for _, b in tools)
        rows.append((name, len(tools), ins, tot, max(tools, key=lambda x: x[1]) if tools else ("", 0)))
    except Exception as e:
        rows.append((name, 0, 0, 0, (f"failed: {type(e).__name__}: {str(e)[:80]}", 0)))
# docs-local: ask the stdlib server itself
p = subprocess.run([sys.executable, os.path.join(R, "docs-search-mcp/mcp_stdio.py")], input='{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n', capture_output=True, text=True, timeout=30, env=dict(os.environ, DOCS_DB="/nonexistent"))
try:
    tl = [l for l in p.stdout.splitlines() if l.startswith("{")][-1]; tools = json.loads(tl)["result"]["tools"]
    rows.append(("docs-local", len(tools), 0, sum(len(json.dumps(t)) for t in tools), max(((t["name"], len(json.dumps(t))) for t in tools), key=lambda x: x[1])))
except Exception as e:
    rows.append(("docs-local", 0, 0, 0, (f"failed: {p.stderr[-100:]}", 0)))
print(f"{'server':<11}{'tools':>6}{'instr B':>9}{'schemas B':>11}{'~tokens':>9}  largest tool")
T = 0
for name, n, ins, tot, big in rows:
    tok = (ins + tot) // 4; T += tok
    print(f"{name:<11}{n:>6}{ins:>9}{tot:>11}{tok:>9}  {big[0]} ({big[1]} B)")
print(f"{'total':<11}{'':>6}{'':>9}{'':>11}{T:>9}  (bytes/4; the API's count differs by about 10 percent)")
