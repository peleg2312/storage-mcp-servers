---
description: Start a new FastAPI service from the template (offline venv, tests run)
argument-hint: <name> [folder]
allowed-tools: Bash(cp:*), Bash(mkdir:*), Bash(ls:*), Bash(${CLAUDE_PLUGIN_ROOT}/bin/fastapi-venv:*)
---
Create a new FastAPI service named `$1` (folder: `$2`, else `./$1`).

1. If the folder exists and is not empty, stop and ask.
2. `mkdir -p <folder> && cp -R ${CLAUDE_PLUGIN_ROOT}/template/. <folder>/`
3. Put the name into `<folder>/pyproject.toml` (`name = "..."`) and `app/config.py` (`app_name` default).
4. `${CLAUDE_PLUGIN_ROOT}/bin/fastapi-venv <folder>`
5. In the folder: `.venv/bin/pytest -q` and `.venv/bin/ruff check .` — both must pass.
6. Tell the user in a few lines: the folder, how to run it (`.venv/bin/uvicorn app.main:app --reload`),
   where the docs are (/docs), and that the `fastapi-service` skill holds the rules for the next endpoints.
