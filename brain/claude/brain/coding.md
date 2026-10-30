# Coding rules (writing or changing code, scripts, services, apps; not storage operations)
Read once per session before the first code change. After Andrej Karpathy's notes on how LLMs go wrong when
coding (multica-ai/andrej-karpathy-skills, MIT); judgement beats these rules on a trivial edit.

1. **Think before coding.** State the assumptions you make. When the request allows several readings, list them
   and ask instead of picking one silently. When a simpler approach exists, say so before building the asked one.
2. **Simplicity first.** Build only what was asked: no speculative features, options or configuration, no
   abstraction for code used once, no handling of errors that cannot happen. A solution much longer than the
   problem needs is wrong: rewrite it shorter.
3. **Surgical changes.** Touch only what the request needs. Keep the file's style, names and formatting even
   where you would do it differently. Do not refactor working code. Report unrelated dead code, do not delete it;
   remove only what your own change orphaned (imports, variables, functions). Every changed line traces back to
   the request.
4. **Goal-driven.** Turn the task into something checkable before starting: a failing test before a bug fix, a
   command that proves a feature. Multi-step work: each step with its check. Iterate until the check passes, then
   stop.

## Tools and conventions
- The library holds the backend stack's docs (FastAPI, Pydantic, pydantic-settings, Starlette, uvicorn, httpx, pytest,
  SQLAlchemy, fastmcp, the MCP Python SDK and specification: vendors `python` / `mcp`): search them (docs-lookup) before
  writing against an API; house conventions for services and MCP servers: the `fastapi-service` skill.
- His PostgreSQL / MongoDB schemas and data: the **databases** MCP (`db_list` first; writes only on connections marked
  writable, each confirmed by him). Terraform: the `terraform` skill (plan yes; apply to infrastructure is his).
- To show him his app, its API docs or any page it serves: `paas-open <port>/<path>` opens it in the web UI's
  **Browser** tab (only apps this account started).
- Tests and builds run quietly (`pytest -q --tb=short`, quiet flags; the full trace only when the short one does
  not explain it). Read the part of a file you need, not the whole file again.
