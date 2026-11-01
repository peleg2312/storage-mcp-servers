// Brain tab, Team card: mounts index.js with a stubbed host api in headless Chromium and clicks through the switcher
// (one click switches, the only question is about unsaved edits, the editor keeps its own dropdown). Needs playwright with
// its Chromium; run_tests.sh skips it otherwise:  node brain/ui/plugins/paas-brain/test_team_card.cjs
let chromium;
try { ({ chromium } = require('playwright')); } catch { console.log('skipped: playwright not installed'); process.exit(77); }
const http = require('http');
const fs = require('fs');
const path = require('path');

const PLUGIN = path.join(__dirname, 'index.js');
const HTML = `<!doctype html><meta charset="utf-8"><title>smoke</title><style>:root{--foreground:0 0% 0%;--muted-foreground:0 0% 40%;--border:0 0% 80%;--accent:0 0% 90%;--background:0 0% 100%;--input:0 0% 80%}</style>
<div id="root"></div>
<script type="module">
  import { mount } from './index.js';
  const calls = [];
  let active = null;
  const teams = [
    { name: 'san', title: 'SAN', description: 'SAN team', local: true, skills: 20, agents: 8, mcp: ['docs-local', 'powermax'], mcp_added: ['docs-local'] },
    { name: 'nas', title: 'NAS', description: 'NAS team', local: true, skills: 18, agents: 4, mcp: ['docs-local', 'ontap'], mcp_added: ['docs-local', 'ontap'] },
  ];
  const api = {
    rpc: async (method, route, body) => {
      calls.push([method, route, body]);
      if (route === 'overview') return { library: { sources: '', version: '' }, pluginTeam: active, hooks: [], mcp: [],
        skills: active ? [{ name: 'share-access-check', description: 'SMB/NFS access', source: 'team', dir: 'share-access-check' }] : [],
        agents: active ? [{ name: 'nas-analyst', description: 'NAS analyst', source: 'team', file: 'nas-analyst.md' }] : [],
        memory: [{ name: 'notes.md', text: '# Notes', editable: true }], captures: [], canShare: false };
      if (method === 'GET' && route === 'team') return { installed: true, active, mode: 'plugin', teams };
      if (route === 'team-sync') return { ok: true, out: 'brain: in sync' };
      if (method === 'POST' && route === 'team') { active = body.name === 'none' ? null : body.name; return { ok: true, out: '' }; }
      if (route.startsWith('team-show')) return { ok: true, name: 'nas', title: 'NAS', description: 'NAS team', persona: 'p', rules: 'r', environment: 'e', skills: [], agents: [], mcp: [], mcp_servers: {}, available_skills: [], available_agents: [] };
      return { ok: true, out: '' };
    },
  };
  window.__calls = calls;
  location.hash = '#brain-team';
  mount(document.getElementById('root'), api);
</script>`;

(async () => {
  const srv = http.createServer((req, res) => {
    if (req.url === '/index.js') { res.setHeader('content-type', 'text/javascript'); res.end(fs.readFileSync(PLUGIN)); return; }
    res.setHeader('content-type', 'text/html'); res.end(HTML);
  });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const port = srv.address().port;
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`http://127.0.0.1:${port}/`);
  const seg = page.locator('.tseg button');
  await seg.first().waitFor({ timeout: 10000 });
  const labels = await seg.allTextContents();
  if (labels.join('|') !== 'No team|SAN|NAS') throw new Error('segments: ' + labels.join('|'));
  if (await seg.nth(0).getAttribute('aria-pressed') !== 'true') throw new Error('No team should be pressed at start');
  const sub0 = await page.locator('.tline').textContent();
  if (!/Your own rules and skills/.test(sub0)) throw new Error('intro text: ' + sub0);
  if (!/What a team is/.test(await page.locator('.pane').textContent())) throw new Error('explainer missing');
  if (await page.locator('.trow').count() !== 2) throw new Error('two team rows expected');
  // one click switches to NAS, no dialog
  await seg.nth(2).click();
  await page.locator('.tseg button[aria-pressed="true"]', { hasText: 'NAS' }).waitFor({ timeout: 10000 });
  const post = (await page.evaluate(() => window.__calls)).filter((c) => c[0] === 'POST' && c[1] === 'team');
  if (post.length !== 1 || post[0][2].name !== 'nas') throw new Error('POST team calls: ' + JSON.stringify(post));
  const status = await page.locator('.teambox .live').first().textContent();
  if (!/Now on NAS/.test(status)) throw new Error('status: ' + status);
  const sub1 = await page.locator('.tline').innerHTML();
  if (!/NAS<\/b>: NAS team · 18 skills, 4 agents, shared memory/.test(sub1)) throw new Error('team line: ' + sub1);
  const rowOn = await page.locator('.trow.on').innerHTML();
  if (!/your team now/.test(rowOn) || !/\/share-access-check/.test(rowOn) || !/nas-analyst/.test(rowOn)) throw new Error('active row: ' + rowOn);
  if (await page.locator('.confirm').count() !== 0) throw new Error('a confirm dialog appeared');
  // SAN shows the server still on placeholders as not set up
  await page.locator('.tseg button', { hasText: 'SAN' }).click();
  await page.locator('.tseg button[aria-pressed="true"]', { hasText: 'SAN' }).waitFor({ timeout: 10000 });
  const sub2 = await page.locator('.trow.on').innerHTML();
  if (!/powermax: not set up/.test(sub2)) throw new Error('not set up tag missing: ' + sub2);
  // the editor keeps its own team dropdown under More, preset to the active team
  await page.locator('.tmore > summary').click();
  const opts = await page.locator('.tsel option').allTextContents();
  const selected = await page.locator('.tsel').inputValue();
  if (opts.length !== 2 || selected !== 'san') throw new Error('editor dropdown: ' + JSON.stringify([opts, selected]));
  // back to no team with one click
  await page.locator('.tseg button', { hasText: 'No team' }).click();
  await page.locator('.tseg button[aria-pressed="true"]', { hasText: 'No team' }).waitFor({ timeout: 10000 });
  const status2 = await page.locator('.teambox .live').first().textContent();
  if (!/No team now/.test(status2)) throw new Error('status2: ' + status2);
  // an unsaved edit in the team editor asks before switching (More closed again with the re-render: open it first)
  await page.locator('.tmore > summary').click();
  await page.locator('.ted > summary').click();
  await page.locator('textarea[data-k="persona"]').waitFor({ timeout: 10000 });
  await page.locator('textarea[data-k="persona"]').fill('changed persona');
  await page.locator('.tseg button', { hasText: 'NAS' }).click();
  await page.locator('.confirm').waitFor({ timeout: 5000 });
  await page.locator('.confirm .c-no').click();
  if (await page.locator('.tseg button[aria-pressed="true"]').textContent() !== 'No team') throw new Error('cancel should keep no team');
  if (errors.length) throw new Error('console errors: ' + errors.join(' | '));
  console.log('team card smoke ok');
  await browser.close(); srv.close();
})().catch((e) => { console.error(e); process.exit(1); });
