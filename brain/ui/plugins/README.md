# UI tabs

Each tab is `<name>/index.js` (`mount(container, api)`, `unmount`). The host loads it through a Blob URL, so a tab
cannot import sibling files.

## Shared module

`shared.js` is the one place for the common stylesheet and helpers. `sync-shared.py` pastes it at the top of every
`*/index.js`, between the `// >>> paas shared` and `// <<< paas shared` lines. Never edit that block in a tab.

- Edit `shared.js`, then run `python3 brain/ui/plugins/sync-shared.py`.
- `python3 brain/ui/plugins/sync-shared.py --check` exits 1 when a tab is out of date.
- Give the tab's root element class `paas` and add `<style>${PAAS_CSS}</style>`.
- Helpers: `esc`, `el`, `icon`, `header`, `errorBlock`, `emptyBlock`, `statusLine`, `confirmInline`, `busy`,
  `fmtSize`, `fmtTime`. A tab must not define these names itself (sync drops a duplicate one-line `esc`, `fmtSize`, `fmtTime`).
- No `alert`/`confirm`/`prompt`: use `confirmInline` and `statusLine`.
