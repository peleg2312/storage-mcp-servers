---
name: code-graph
description: Use for questions that follow the code more than one step - what a change will break, callers of callers, which flows or tests a change touches, reviewing a diff, how the modules fit together - in a git repository. Uses the code-graph MCP tools (a prebuilt graph). For a one-step lookup (where X is defined, who calls X directly) Grep is faster.
---
# Code graph: answer code questions from the graph, read only what it points to

The `code-graph` MCP server holds a graph of the git repository Claude runs in: every file, function, class,
import, call and test, kept on disk in `.code-review-graph/` (ignored by git). Its answers are small; reading
files to find the same thing costs far more context. Load its tools with one ToolSearch:
`select:mcp__code-graph__list_graph_stats_tool,mcp__code-graph__query_graph_tool,mcp__code-graph__get_impact_radius_tool,mcp__code-graph__semantic_search_nodes_tool`
(add the others below when the task needs them).

## When to use it (measured on this VM's own code)
- One step - where is X defined, which files call X directly: **use Grep**, not the graph (Grep answered these in half the
  time with the same result; the graph only added tool loading and turns).
- More than one step - callers of callers, what breaks if X changes, impact of a diff, flows, architecture, review:
  **use the graph** (2.4x faster, 44% fewer input tokens, and fewer mistakes than grep-and-read).

## First: is there a graph?
`list_graph_stats_tool`. No nodes -> `build_or_update_graph_tool` (a big repository takes minutes; tell the
user), or the user runs `/code-graph:build`. After a `git pull` or a branch switch: `build_or_update_graph_tool`
(only changed files). Edits made in this session update the graph by themselves.

## Which tool
| question | tool |
|---|---|
| where is X / what is like X | `semantic_search_nodes_tool` (name or words), then `query_graph_tool` |
| who calls f / what f calls / imports / tests of f | `query_graph_tool` (pattern: callers_of, callees_of, imports_of, importers_of, tests_for, children_of) |
| what breaks if I change f or these files | `get_impact_radius_tool` (changed files or nodes) |
| review the current diff | `detect_changes_tool`, then `get_review_context_tool` |
| the smallest context to work on f | `get_minimal_context_tool` |
| the shape of the system | `get_architecture_overview_tool`, `list_flows_tool` / `get_flow_tool` |
| which flows a change touches | `get_affected_flows_tool` |
| walk from a node N steps | `traverse_graph_tool` |
| refactor targets | `find_large_functions_tool` |

## Rules
1. Graph first, then read: open only the files and line ranges the graph names (Read with offset / limit).
2. Before changing a function used elsewhere: `get_impact_radius_tool`, and say which callers and tests change.
3. A review of a change: list the affected callers and tests that are not covered by the diff.
4. The graph is structure, not truth about behaviour: confirm in the code before you state how something works.
5. Structural search in the shell (patterns, not text): `ast-grep run -p 'foo($A)' -l python src/`.
