# brain/plugin: a team's brain as a Claude Code plugin

`python3 brain/plugin/build.py <out-dir> [--team <name>] [--no-hooks]` builds the plugin `paas-brain-<team>` (team
`san` by default) from `brain/claude` and `brain/teams/<team>` (`brain/teams/README.md` explains the profiles):

- `<out-dir>/.claude-plugin/marketplace.json` and `<out-dir>/paas-brain-<team>/` with `plugin.json` (version =
  `library/VERSION`, else the date)
- `skills/`, `agents/`: the team's lists resolved (`brain/teams/<team>/skills|agents` first, then `brain/claude`)
- `hooks/` (every brain hook) and `hooks/hooks.json`, written by `brain/merge_settings.py` with
  `${CLAUDE_PLUGIN_ROOT}/hooks/<script>`, so matchers and timeouts are the VM's; `--no-hooks` for a VM whose hooks are
  managed settings (the multi-user VM)
- `bin/docs-local` + `.mcp.json`: the stdio library search over `~/.claude/brain/library`
- `brain/`: persona.md, storage.md (the team's rules), environment / tool-map / notes templates, coding.md. A plugin
  cannot activate these; `paas-team use <team>` puts them in place
- `team.json`: name, title, version, the resolved skill and agent names, the MCP servers the team starts with

`brain/teams/publish.py` wraps the plugin into a team repository (plugin + `knowledge/`), the thing people clone and
`claude plugin marketplace add` installs from. `sh install-laptop.sh [--team <name>]` (repository root) does it for a
laptop: builds the team repositories into `~/.claude/brain/team-sources`, adds the chosen team
(`~/.claude/brain/teams/<team>`), installs and enables its plugin (`paas-team` in plugin mode), and does what a
plugin cannot: the rules (`~/.claude/brain/main.md` imported from `~/.claude/CLAUDE.md`, never replacing your own),
persona and storage rules, tools in `~/.claude/tools`, the library. Check: `claude plugin list`, `/mcp` inside claude,
`paas-team`.

The VM runs the same plugin (`paas-team` in plugin mode wherever `claude` is installed), so one install exists for
everyone: skills are `/paas-brain-<team>:<skill>` everywhere, hooks and docs-local come with the plugin. On the multi-user
VM the managed settings run every brain hook for every account (enforced) and the plugin's copies step aside
(`CLAUDE_PLUGIN_ROOT` set and the managed settings naming the script), so nothing runs twice. A laptop lacks the web UI,
the multi-user parts, the dev tools and the banner. `session-start.py` recognises the guard inside the plugin.
