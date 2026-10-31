# brain/plugin: the brain as a Claude Code plugin (laptop install)

`python3 brain/plugin/build.py <out-dir>` builds a marketplace `paas-brain` from `brain/claude`:

- `.claude-plugin/marketplace.json` and `paas-brain/` with `plugin.json` (version = `library/VERSION`, else the date)
- `skills/`, `agents/`, `hooks/` (every brain hook) and `hooks/hooks.json`, written by `brain/merge_settings.py`
  with `${CLAUDE_PLUGIN_ROOT}/hooks/<script>`, so matchers and timeouts are the VM's
- `bin/docs-local` + `.mcp.json`: the stdio library search over `~/.claude/brain/library`

`sh install-laptop.sh` (repository root) builds it into `~/.claude/brain/plugin-market`, registers and installs it
(`claude plugin marketplace add`, `claude plugin install paas-brain@paas-brain`), and does what a plugin cannot:
the rules (`~/.claude/brain/main.md` imported from `~/.claude/CLAUDE.md`, never replacing your own), notes and
environment files, tools in `~/.claude/tools`, the library, the brain's git history.
Check: `claude plugin list`, `/mcp` inside claude.

Limits of the laptop way: no web UI, no multi-user parts, no dev tools or banner; skills are namespaced
(`/paas-brain:<skill>`); the read-only guard is a plugin hook, so a person can disable the plugin. The VM
(`install-vm.sh`, multi-user setup) is the enforced setup. `session-start.py` looks for the guard in
`~/.claude/settings.json` and may report it as not configured: the hooks live in the plugin.
