paas-kit  -  VM-wide add-ons for Claude, kept apart from the brain
====================================================================

One install (root) and every user on the VM has all of it on, including users created later, whatever brain (team)
they use, or none - no question asked, and users cannot turn it off (Claude's managed settings rank above anyone's
own settings). Only root turns parts off (below). It does not change the brain, any team repository,
managed-settings.json or anyone's own settings.

WHAT IS IN IT
  rtk                shorter shell output for the model. After a command ran, long output of tests (pytest, go test,
                     cargo, vitest, ctest), linters (mypy, ruff, tsc), grep / rg / find, git log / diff / status and
                     long logs (journalctl, oc / kubectl logs, tail) is filtered: failures, errors and changed lines
                     stay, passing noise goes (e.g. 149 lines of pytest -> 13 with the failure and its diff). The
                     command itself is never changed, so the brain's guard and the permission rules see exactly what
                     runs. The model gets the full output with "| cat" at the end of the command. A command the model
                     writes as "rtk ..." is refused (it would hide the real command from the guard).
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
              paas-kit gain            your rtk savings
  in Claude:  /code-graph:build        /fastapi-api:new my-api  (the skills load by themselves when they fit)
  root:       paas-kit headroom off | on               all sessions straight to the model / through Headroom
              paas-kit headroom profile max | safe     max also shortens logs and long text (the model can ask for
                                                       hidden lines back); safe (default) never drops anything
              paas-kit headroom upstream <url>         another model address
              paas-kit plugin off | on rtk             a plugin for every user (also code-graph, fastapi-api)
  logs:       journalctl -u paas-headroom              savings: paas-kit status

REMOVE
  sudo sh /opt/paas-kit/kit/uninstall.sh

LICENSES
  rtk (rtk-ai/rtk v1.2.1, built from source as a static binary): see /opt/paas-kit/kit/rtk/LICENSE.
  Headroom, code-review-graph, ast-grep, FastAPI and the rest: their own licenses in the wheels.

FILES
  /opt/paas-kit/{kit,bin,venv,tiktoken}   /etc/paas-kit/kit.json   /etc/claude-code/managed-settings.d/60-paas-kit.json
  /etc/systemd/system/paas-headroom.service, paas-kit-watch.{service,timer}
  /usr/local/bin/{paas-kit,code-review-graph,ast-grep}   (rtk itself: /opt/paas-kit/bin/rtk, not on the PATH)
