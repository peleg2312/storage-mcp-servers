paas-kit  -  VM-wide add-ons for Claude, kept apart from the brain
====================================================================

One install (root) and every user on the VM has all of it on, including users created later, whatever brain (team)
they use, or none - no question asked, and users cannot turn it off (Claude's managed settings rank above anyone's
own settings). Only root turns parts off (below). It does not change the brain, any team repository,
managed-settings.json or anyone's own settings.

WHAT IS IN IT
  rtk                shorter shell output for the model, with rtk's own Claude Code hook, as rtk ships it: every
                     command rtk knows runs in its short form - git, ls, tree, cat / head / tail, grep / rg / find,
                     tests (pytest, go, cargo, npm, vitest ...), linters, builds, oc / kubectl / docker / helm, curl,
                     aws, psql ... ("git status" becomes "rtk git status": the same command, compact output). The model
                     types plain commands and never needs to know. What rtk cut: rtk recall <hash> (rtk prints it).
                     One check in front: a command the model writes as "rtk ..." itself is refused (the brain's
                     read-only guard does not look inside "rtk oc delete ..."); rtk's own rewrites are not affected.
                     rtk is built from source with a patch (rtk-patches/), tested command by command on storage,
                     Kubernetes, Linux and coding output: oc / kubectl get pods lists every unhealthy pod with its real
                     reason (rtk as shipped counts crash-looping pods as running and shows 10); grep keeps whole lines;
                     no list is cut any more (rtk cut pytest failures at 5, ls at 50, df / rsync at 20 lines, ...).
                     Left as typed by default, because rtk loses facts there: oc / kubectl logs (last 100 lines only),
                     oc / kubectl describe, aws (JSON reduced to one sample item), ps (command lines cut), ruff (rule
                     summary without file:line), ls -l (owner, date, exact size). Root: paas-kit rtk exclude <cmd
                     prefix or ^regex>... | none | default.
  Headroom           a small local service between Claude and the model (GLM). Profile safe (the default):
                     strict lossless - JSON lists from the MCP servers become compact tables, every row and value kept
                     (measured: volume list 70%, host list 53%, port list 68% fewer tokens). profile full
                     adds Headroom's other compressors: long logs keep their errors and the rest is fetched
                     back on request (lossy, not recommended). Kompress (Headroom's AI text compressor) is not shipped:
                     in testing it saved 2-11%, cost ~0.8 GB RAM and seconds of CPU, and damaged answers.
                     Runs in token mode: every tool result is compressed, also when Claude makes many tool calls in
                     a row (Headroom's cache mode does not then); the compressed form is the same on every request,
                     so the model server's prompt cache keeps working.
                     If Headroom stops, a check every minute sends new sessions straight to the model again.
  code-graph plugin  for large code bases: a graph of the git repository (functions, classes, imports, callers,
                     tests) the model asks instead of reading many files - what a change breaks, who calls what,
                     review context. Built once per repository (/code-graph:build), kept up to date after edits.
                     Plus ast-grep (structural code search) on the PATH.
  fastapi-api plugin build Python REST APIs offline: /fastapi-api:new <name> (template with tests), `paas-kit venv`
                     (FastAPI, uvicorn, pydantic, SQLAlchemy, alembic, psycopg, httpx, pytest, ruff, mypy from the
                     kit's wheels, Python 3.12 or 3.9), the rules skill and an api-reviewer agent.

NEEDS
  RHEL 9 (or similar) with python3.12:  dnf install -y python3.12      About 1.5 GB free in /opt; Headroom uses
  about 0.3 GB of memory.

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
              paas-kit headroom profile safe | full    safe (default): JSON tables only / full: every compressor
              paas-kit rtk exclude oc kubectl grep     commands rtk leaves as typed (none / default)
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
  /usr/local/bin/{paas-kit,code-review-graph,ast-grep,rtk}
