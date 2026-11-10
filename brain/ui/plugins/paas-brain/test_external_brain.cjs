// Brain tab with an external brain active: the Memory tab browses its own knowledge (grouped pages, inbox, search), opens a
// page read-only, proposes a change (POST ext-propose: a branch + merge request in its GitLab) and a new page from a
// template, and keeps the person's own notes one click away; the Team tab shows its settings as fields (secrets masked).
// Mounts index.js with a stubbed host api in headless Chromium:  node brain/ui/plugins/paas-brain/test_external_brain.cjs
let chromium;
try { ({ chromium } = require('playwright')); } catch { console.log('skipped: playwright not installed'); process.exit(77); }
const http = require('http');
const fs = require('fs');
const path = require('path');

const PLUGIN = path.join(__dirname, 'index.js');
const HTML = `<!doctype html><meta charset="utf-8"><title>ext</title><style>:root{--foreground:0 0% 0%;--muted-foreground:0 0% 40%;--border:0 0% 80%;--accent:0 0% 90%;--background:0 0% 100%;--input:0 0% 80%}</style>
<div id="root"></div>
<script type="module">
  import { mount } from './index.js';
  const calls = [];
  const external = { team: 'redbull', plugin: 'team-brain', title: 'Platform brain', save: 'merge-request',
    folders: ['knowledge', 'runbooks'], inbox: 'inbox', templates: 'templates', index: 'INDEX.md',
    pages: [{ path: 'knowledge/networking/ingress.md', title: 'Ingress is AKO, not MetalLB', area: 'networking', mtime: 1762700000000 },
            { path: 'runbooks/hypershift/nodepool.md', title: 'NodePool stuck Updating', area: 'hypershift', mtime: 1762700000000 }],
    inboxPages: [{ path: 'inbox/2026-11-01-raw.md', title: 'Raw capture', area: '', mtime: 1762700000000 }],
    templatePages: [{ path: 'templates/knowledge.md', title: 'Knowledge page', area: '', mtime: 1762700000000 }] };
  const team = { name: 'redbull', title: 'Platform brain', description: 'OpenShift fleet', local: true, skills: 5, agents: 1, mcp: ['team-knowledge'],
    mcp_added: ['team-knowledge'], external: true, plugin: 'team-brain', env: ['TEAM_BRAIN_DIR'],
    settings: [{ name: 'GRAFANA_URL', about: '', secret: false, optional: false, set: false },
               { name: 'GRAFANA_SERVICE_ACCOUNT_TOKEN', about: '', secret: true, optional: false, set: false },
               { name: 'TEAM_BRAIN_DIR', about: "where this brain's repository is (set for you)", secret: false, optional: true, set: true }] };
  const api = {
    rpc: async (method, route, body) => {
      calls.push([method, route, body]);
      if (route === 'overview') return { library: { sources: '', version: '' }, pluginTeam: 'redbull', pluginName: 'team-brain', pluginExternal: true,
        external, hooks: [], mcp: [], skills: [], agents: [], memory: [{ name: 'notes.md', text: '# My notes', editable: true }], captures: [], canShare: false };
      if (method === 'GET' && route === 'team') return { installed: true, active: 'redbull', teams: [team] };
      if (route === 'team-sync') return { ok: true, out: 'brain redbull: up to date with its repository' };
      if (route.startsWith('ext-page')) {
        const p = decodeURIComponent(route.split('path=')[1]);
        return { ok: true, path: p, text: p.startsWith('templates/') ? '---\\ntitle: <title>\\n---\\n## Symptom\\n' : '---\\ntitle: Ingress is AKO\\n---\\nBody\\n' };
      }
      if (route === 'ext-propose') return { ok: true, url: 'https://gitlab.example.com/platform/team-brain/-/merge_requests/42', out: 'Merge request: https://gitlab.example.com/platform/team-brain/-/merge_requests/42' };
      if (route === 'team-env') return { ok: true, out: 'brain redbull: settings GRAFANA_URL, TEAM_BRAIN_DIR' };
      return { ok: true, out: '' };
    },
  };
  window.__calls = calls;
  location.hash = '#brain-memory';
  mount(document.getElementById('root'), api);
</script>`;

(async () => {
  const srv = http.createServer((req, res) => {
    if (req.url === '/index.js') { res.setHeader('content-type', 'text/javascript'); res.end(fs.readFileSync(PLUGIN)); return; }
    res.setHeader('content-type', 'text/html'); res.end(HTML);
  });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`http://127.0.0.1:${srv.address().port}/`);
  const calls = () => page.evaluate(() => window.__calls);
  // the Memory tab: its pages grouped by folder / area, its inbox, its index, a filter
  await page.locator('.em-row').first().waitFor({ timeout: 10000 });
  const text = await page.locator('.pane').textContent();
  for (const s of ['Platform brain', 'knowledge / networking', 'runbooks / hypershift', 'Ingress is AKO, not MetalLB', 'Inbox: waiting to be curated (1)', 'merge requests'])
    if (!text.includes(s)) throw new Error(`memory tab misses "${s}"`);
  await page.locator('.em-q').fill('nodepool');
  if (await page.locator('.em-row:visible').count() !== 1) throw new Error('filter');
  await page.locator('.em-q').fill('');
  // open a page: read-only, then propose a change -> a merge request link
  await page.locator('.em-open[data-path="knowledge/networking/ingress.md"]').click();
  await page.locator('.em-text').waitFor();
  if (!(await page.locator('.em-text').getAttribute('readonly') !== null)) throw new Error('page should open read-only');
  await page.locator('.em-edit').click();
  await page.locator('.em-text').fill('---\ntitle: Ingress is AKO\n---\nBody, fixed\n');
  await page.locator('.em-title').fill('brain(networking): ingress fix');
  await page.locator('.em-send').click();
  await page.locator('.em-result a').waitFor({ timeout: 5000 });
  const prop = (await calls()).filter((c) => c[1] === 'ext-propose');
  if (prop.length !== 1 || prop[0][2].path !== 'knowledge/networking/ingress.md' || prop[0][2].create || !/fixed/.test(prop[0][2].text)) throw new Error('propose: ' + JSON.stringify(prop));
  if (await page.locator('.em-result a').getAttribute('href') !== 'https://gitlab.example.com/platform/team-brain/-/merge_requests/42') throw new Error('MR link');
  // a new page from a template, into the inbox
  await page.locator('.em-new').click();
  await page.locator('.em-dir').selectOption('inbox');
  await page.locator('.em-file').fill('2026-11-10-new-quirk');
  await page.locator('.em-tpl').selectOption('templates/knowledge.md');
  await page.waitForFunction(() => document.querySelector('.em-text').value.includes('## Symptom'));
  await page.locator('.em-send').click();
  await page.locator('.em-result a').waitFor({ timeout: 5000 });
  const p2 = (await calls()).filter((c) => c[1] === 'ext-propose')[1];
  if (p2[2].path !== 'inbox/2026-11-10-new-quirk.md' || !p2[2].create) throw new Error('new page: ' + JSON.stringify(p2));
  // the person's own notes, and back
  await page.locator('.em-back').click();
  await page.locator('.em-own').click();
  await page.locator('.em-kb').waitFor();
  if (!/My notes/.test(await page.locator('textarea.mt').inputValue())) throw new Error('own notes');
  await page.locator('.em-kb').click();
  await page.locator('.em-row').first().waitFor();
  // the Team tab: settings as fields, secrets masked, the needed count, saved as pairs
  await page.locator('button', { hasText: 'Team' }).first().click();
  await page.locator('.tmore > summary').waitFor();
  await page.locator('.tmore > summary').click();
  if (!/2 needed/.test(await page.locator('.tenv > summary').textContent())) throw new Error('needed count');
  if (await page.locator('.te-f[data-k="GRAFANA_SERVICE_ACCOUNT_TOKEN"]').getAttribute('type') !== 'password') throw new Error('secret masked');
  await page.locator('.te-f[data-k="GRAFANA_URL"]').fill('https://grafana.internal');
  await page.locator('.te-go').click();
  await page.waitForFunction(() => window.__calls.some((c) => c[1] === 'team-env'));
  const env = (await calls()).find((c) => c[1] === 'team-env');
  if (JSON.stringify(env[2].pairs) !== JSON.stringify(['GRAFANA_URL=https://grafana.internal'])) throw new Error('team-env pairs: ' + JSON.stringify(env[2]));
  if (errors.length) throw new Error('console errors: ' + errors.join(' | '));
  console.log('external brain tab ok');
  await browser.close(); srv.close();
})().catch((e) => { console.error(e); process.exit(1); });
