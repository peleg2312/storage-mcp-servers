"""An MCP server with no tools: the code-graph plugin outside a git repository."""
import json
import sys

for line in sys.stdin:
    try:
        m = json.loads(line)
    except ValueError:
        continue
    if m.get("id") is None:
        continue
    meth = m.get("method")
    if meth == "initialize":
        res = {"protocolVersion": (m.get("params") or {}).get("protocolVersion", "2025-06-18"),
               "capabilities": {"tools": {}}, "serverInfo": {"name": "code-graph (not a git repository)", "version": "1"},
               "instructions": "Start Claude inside a git repository to use the code graph."}
    elif meth == "tools/list":
        res = {"tools": []}
    elif meth == "ping":
        res = {}
    else:
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], "error": {"code": -32601, "message": "no tools here"}}) + "\n")
        sys.stdout.flush()
        continue
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": res}) + "\n")
    sys.stdout.flush()
