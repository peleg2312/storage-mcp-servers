---
description: Build (or bring up to date) the code graph of this git repository
---
Build the code graph of the git repository we are in, then report its size.

1. Call the code-graph MCP tool `list_graph_stats_tool`. No nodes yet: call `build_or_update_graph_tool` with a full
   build (a large code base can take a few minutes; say so). Nodes there: `build_or_update_graph_tool` updates only the
   changed files.
2. Tell the user in two lines: files, nodes, edges, and that the graph stays up to date by itself after edits made
   here (after `git pull` or a branch switch: /code-graph:build again).
If the code-graph server says it is being prepared, tell the user it is ready in their next session.
