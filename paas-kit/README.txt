paas-kit  -  VM-wide add-ons for Claude, kept apart from the brain
====================================================================

One install (root) and every user on the VM has it, including users created later, whatever brain (team) they use,
or none. It does not change the brain, any team repository, managed-settings.json or anyone's own settings.

WHAT IS IN IT
  Headroom           a small local service between Claude and the model (GLM). Before each request reaches the
                     model it makes tool results smaller: JSON lists from the MCP servers (volumes, hosts, ports,
                     pods ...) become one compact table - every row and every value kept, 50-70% fewer tokens on
                     large lists. More room in the context, faster answers, fewer cut-off results.
                     If Headroom stops, a check every minute sends new sessions straight to the model again.
  code-graph plugin  for large code bases: a graph of the git repository (functions, classes, imports, callers,
                     tests) the model asks instead of reading many files - what a change breaks, who calls what,
                     review context. Built once per repository (/code-graph:build), kept up to date after edits.
                     Plus ast-grep (structural code search) on the PATH.
  fastapi-api plugin build Python REST APIs offline: /fastapi-api:new <name> (template with tests), `paas-kit venv`
                     (FastAPI, uvicorn, pydantic, SQLAlchemy, alembic, psycopg, httpx, pytest, ruff, mypy from the
                     kit's wheels, Python 3.12 or 3.9), the rules skill and an api-reviewer agent.

NEEDS
  RHEL 9 (or similar) with python3.12:  dnf install -y python3.12      About 1.5 GB free in /opt.

INSTALL (root)
  unzip paas-kit-<version>.zip
  sudo sh paas-kit/install.sh
      It finds the model address the VM uses today (managed settings, /etc/environment, /etc/profile.d or the
      users' settings). If it says NOT FOUND:  sudo sh paas-kit/install.sh --upstream https://<your-glm-address>
  paas-kit status                      check: "answering", "new sessions through Headroom", plugins on
  Start a new Claude session (web UI: a new chat) - running sessions keep the old setting until restarted.

UPDATE
  unzip the new zip, sudo sh paas-kit/install.sh  (settings in /etc/paas-kit/kit.json are kept)

USE
  everyone:   paas-kit status          paas-kit venv .          paas-kit graph build | update | status
  in Claude:  /code-graph:build        /fastapi-api:new my-api  (the skills load by themselves when they fit)
  root:       paas-kit headroom off | on               all sessions straight to the model / through Headroom
              paas-kit headroom profile max | safe     max also shortens logs and long text (the model can ask for
                                                       hidden lines back); safe (default) never drops anything
              paas-kit headroom upstream <url>         another model address
              paas-kit plugin off | on code-graph      a plugin for every user (also fastapi-api)
  logs:       journalctl -u paas-headroom              savings: paas-kit status

REMOVE
  sudo sh /opt/paas-kit/kit/uninstall.sh

NOT IN THIS KIT
  rtk (shortens shell command output): its build was blocked by this session's safety check, because rtk rewrites
  the shell commands Claude runs, which sits next to the brain's read-only guard. It can be added once you decide
  that is wanted.

FILES
  /opt/paas-kit/{kit,bin,venv,tiktoken}   /etc/paas-kit/kit.json   /etc/claude-code/managed-settings.d/60-paas-kit.json
  /etc/systemd/system/paas-headroom.service, paas-kit-watch.{service,timer}
  /usr/local/bin/{paas-kit,code-review-graph,ast-grep}   paas Market source "paas-kit" (when paas-market is there)
