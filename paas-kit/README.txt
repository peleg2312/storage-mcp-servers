paas-kit  -  VM-wide add-ons for Claude, kept apart from the brain
====================================================================

One install (root) and every user on the VM has all of it on, including users created later, whatever brain (team)
they use, or none - no question asked, and users cannot turn it off (Claude's managed settings rank above anyone's
own settings). Only root turns parts off (below). It does not change the brain, any team repository,
managed-settings.json or anyone's own settings.

WHAT IS IN IT
  rtk                shorter shell output for the model, two ways:
                     1. commands that only read are run in rtk's short form - git status / log / diff, ls, tree,
                        cat / head / tail, grep / rg / find, tests (pytest, go, cargo, npm test, vitest ...), linters,
                        builds, oc / kubectl / helm get-describe-logs, docker ps, curl GET, aws describe / ls,
                        psql -c SELECT, systemctl status. "git status" becomes "rtk git status": the same command,
                        compact output. The kit's guard around it: a command is rewritten only when every part of it
                        reads (oc delete, kubectl apply, curl POST, git push, helm upgrade, sudo, > file ... always run
                        exactly as typed), rtk's form has the same commands and files, every guard hook (the brain's
                        read-only guard, a team's) lets the original through without a block or a question, and it
                        adds no permission prompt. Root: paas-kit rtk rewrite off (only step 2 then).
                     2. long output of the rest (tests, linters, grep / find, git, logs) is filtered after it ran:
                        failures, errors and changed lines stay (e.g. 149 lines of pytest -> 13 with the failure).
                     The full output: rtk recall <hash> (shown when rtk cut something), or "| cat" at the end.
                     A command the model writes as "rtk ..." itself is refused (except rtk recall / rtk gain).
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
              paas-kit rtk rewrite off | on            rtk only filters output after commands ran / also runs them short
  logs:       journalctl -u paas-headroom              savings: paas-kit status

REMOVE
  sudo sh /opt/paas-kit/kit/uninstall.sh

LICENSES
  rtk (rtk-ai/rtk v1.2.1, built from source as a static binary): see /opt/paas-kit/kit/rtk/LICENSE.
  Headroom, code-review-graph, ast-grep, FastAPI and the rest: their own licenses in the wheels.

FILES
  /opt/paas-kit/{kit,bin,venv,tiktoken}   /etc/paas-kit/kit.json   /etc/claude-code/managed-settings.d/60-paas-kit.json
  /etc/systemd/system/paas-headroom.service, paas-kit-watch.{service,timer}
  /usr/local/bin/{paas-kit,code-review-graph,ast-grep,rtk}
