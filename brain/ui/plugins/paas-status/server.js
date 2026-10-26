// Status backend: the brain-health checks that need no model, and Claude Code usage (tokens, estimated cost). Read-only and local: files under
// ~/.claude, the guard hook run on a test command, `claude mcp list`, and the machine's disk / memory / load.
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFile, spawnSync } from 'node:child_process';

const HOME = os.homedir();
const CL = path.join(HOME, '.claude');
const read = (p) => { try { return fs.readFileSync(p, 'utf8'); } catch { return null; } };
const gb = (n) => `${(n / 1073741824).toFixed(1)} GB`;

function machine() {
  const disk = (p) => {
    try { const s = fs.statfsSync(p); return { path: p, total: s.blocks * s.bsize, free: s.bavail * s.bsize }; } catch { return null; }
  };
  return { host: os.hostname(), os: `${os.type()} ${os.release()}`, uptime: os.uptime(), load: os.loadavg(),
    cpus: os.cpus().length, mem: { total: os.totalmem(), free: os.freemem() }, disks: [disk('/'), fs.statSync(HOME).dev !== fs.statSync('/').dev && disk(HOME)].filter(Boolean) };
}

function brain() {
  const out = [];
  const add = (group, name, status, detail) => out.push({ group, name, status, detail });
  for (const d of machine().disks) {
    const pct = 100 - (d.free / d.total) * 100;
    add('Machine', `Disk ${d.path}`, pct > 95 ? 'fail' : pct > 85 ? 'warn' : 'ok', `${gb(d.free)} free of ${gb(d.total)} (${pct.toFixed(0)}% used)`);
  }

  const lib = path.join(CL, 'brain', 'library');
  const ver = read(path.join(lib, 'VERSION'))?.trim();
  const docs = read(path.join(lib, 'MANIFEST.md'))?.match(/\*\*(\d+) unique documents, (\d+) sections\*\*/);
  add('Docs library', 'Version', ver ? 'ok' : 'fail', ver || `missing: ${lib} (run brain/install.sh)`);
  if (ver) add('Docs library', 'Content', docs ? 'ok' : 'warn', docs ? `${Number(docs[1]).toLocaleString()} documents, ${Number(docs[2]).toLocaleString()} sections` : 'MANIFEST.md unreadable');

  let settings = {};
  try { settings = JSON.parse(read(path.join(CL, 'settings.json')) || '{}'); } catch { add('Settings', 'settings.json', 'fail', 'not valid JSON'); }
  const hooks = JSON.stringify(settings.hooks || {});
  const guard = path.join(CL, 'hooks', 'block-write-tools.py');
  if (!hooks.includes('block-write-tools.py')) add('Read-only guard', 'Installed', 'fail', 'not in ~/.claude/settings.json (run brain/install.sh)');
  else if (!/mcp__\.\*\|Bash/.test(hooks)) add('Read-only guard', 'Installed', 'warn', 'guards MCP tools only (old install): re-run brain/install.sh');
  else add('Read-only guard', 'Installed', 'ok', 'MCP tools and shell commands');
  if (fs.existsSync(guard)) {
    const r = spawnSync('python3', [guard], { input: JSON.stringify({ tool_name: 'Bash', tool_input: { command: 'scli --add_volume' } }), timeout: 10000 });
    add('Read-only guard', 'Blocks an infrastructure change', r.status === 2 ? 'ok' : 'fail',
      r.status === 2 ? 'test "scli --add_volume" was blocked' : `test command not blocked (exit ${r.status ?? 'timeout'})`);
  }
  for (const [file, what] of [['docs-hints.py', 'docs meaning of alerts in results'], ['docs-leads.py', 'library leads per request'], ['session-start.py', 'session status']]) {
    const ok = hooks.includes(file) && fs.existsSync(path.join(CL, 'hooks', file));
    add('Hooks', file, ok ? 'ok' : 'warn', ok ? what : `missing (${what})`);
  }
  const env = settings.autoMode?.environment || [];
  add('Settings', 'Auto mode knows this VM', env.some((e) => /air-gapped/.test(e)) ? 'ok' : 'warn',
    env.some((e) => /air-gapped/.test(e)) ? 'autoMode.environment set by the brain' : 'not set: re-run brain/install.sh');
  for (const f of ['environment.md', 'notes.md']) {
    const t = read(path.join(CL, 'brain', f));
    add('Brain files', f, t ? 'ok' : 'warn', t ? `${t.split('\n').length} lines` : 'missing');
  }
  const ui = read(path.join(CL, 'paas-ui', 'VERSION'))?.trim();
  if (ui) add('Web UI', 'Version', 'ok', ui);
  return out;
}

// ---- usage: tokens and estimated cost from Claude Code's own session logs (~/.claude/projects/**/*.jsonl),
// per-file cache keyed by mtime so a refresh only re-reads what changed
const ROOT = path.join(CL, 'projects');
// API list prices, $ per million tokens: [input, output, cache read]. Cache writes: 1.25x input (5 min), 2x (1 hour).
const PRICES = [
  [/fable|mythos/, [10, 50, 0.25]], [/opus-5-5/, [4, 20, 0.2]], [/opus/, [5, 25, 0.5]],
  [/sonnet-5/, [2, 10, 0.2]], [/sonnet/, [3, 15, 0.3]], [/haiku-5/, [0.1, 0.5, 0.01]], [/haiku/, [1, 5, 0.1]],
];
const price = (model) => (PRICES.find(([re]) => re.test(model || '')) || [null, [4, 20, 0.2]])[1];
const cache = new Map();   // file -> {mtime, rows}

function rowsOf(file) {
  const st = fs.statSync(file);
  const hit = cache.get(file);
  if (hit && hit.mtime === st.mtimeMs) return hit.rows;
  const rows = new Map();  // message id -> row (streamed messages repeat their usage)
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    if (!line.includes('"usage"')) continue;
    let d;
    try { d = JSON.parse(line); } catch { continue; }
    const m = d.message;
    if (d.type !== 'assistant' || !m?.usage || m.model === '<synthetic>') continue;
    const u = m.usage;
    const c1h = u.cache_creation?.ephemeral_1h_input_tokens ?? 0;
    const c5m = (u.cache_creation_input_tokens ?? 0) - c1h;
    const [pin, pout, pread] = price(m.model);
    rows.set(m.id || `${d.uuid}`, {
      day: (d.timestamp || '').slice(0, 10), model: m.model, project: d.cwd || path.basename(path.dirname(file)),
      session: d.sessionId, input: u.input_tokens ?? 0, output: u.output_tokens ?? 0,
      cacheRead: u.cache_read_input_tokens ?? 0, cacheWrite: u.cache_creation_input_tokens ?? 0,
      cost: ((u.input_tokens ?? 0) * pin + (u.output_tokens ?? 0) * pout + (u.cache_read_input_tokens ?? 0) * pread
        + c5m * pin * 1.25 + c1h * pin * 2) / 1e6,
    });
  }
  const list = [...rows.values()];
  cache.set(file, { mtime: st.mtimeMs, rows: list });
  return list;
}

function files(dir, out = []) {
  let entries = [];
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) files(p, out);
    else if (e.name.endsWith('.jsonl')) out.push(p);
  }
  return out;
}

function summary(days) {
  const since = new Date(Date.now() - days * 864e5).toISOString().slice(0, 10);
  const add = (map, key, r) => {
    const a = map.get(key) || { key, tokens: 0, output: 0, cost: 0, messages: 0 };
    a.tokens += r.input + r.output + r.cacheRead + r.cacheWrite; a.output += r.output; a.cost += r.cost; a.messages += 1;
    map.set(key, a);
  };
  const byDay = new Map(), byModel = new Map(), byProject = new Map(), bySession = new Map();
  const total = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, cost: 0, messages: 0 };
  for (const f of files(ROOT)) {
    for (const r of rowsOf(f)) {
      if (r.day < since) continue;
      for (const k of ['input', 'output', 'cacheRead', 'cacheWrite', 'cost']) total[k] += r[k];
      total.messages += 1;
      add(byDay, r.day, r); add(byModel, r.model, r); add(byProject, r.project, r);
      add(bySession, `${r.session}|${r.project}`, r);
    }
  }
  const top = (m, n) => [...m.values()].sort((a, b) => b.cost - a.cost).slice(0, n);
  const daysList = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(Date.now() - i * 864e5).toISOString().slice(0, 10);
    daysList.push(byDay.get(d) || { key: d, tokens: 0, output: 0, cost: 0, messages: 0 });
  }
  return { days: daysList, total, sessions: bySession.size, models: top(byModel, 8), projects: top(byProject, 10),
    topSessions: top(bySession, 10).map((s) => ({ ...s, session: s.key.split('|')[0], project: s.key.split('|')[1] })) };
}

// `claude mcp list` starts every server to check it (10-60 s): cached for two minutes, one run at a time
let mcpCache = null;
let mcpRun = null;
const claudeBin = () => process.env.CLAUDE_CLI_PATH || [path.join(HOME, '.local', 'bin', 'claude'), '/usr/local/bin/claude'].find((p) => fs.existsSync(p)) || 'claude';
function mcp(fresh) {
  if (!fresh && mcpCache && Date.now() - mcpCache.at < 120000) return Promise.resolve(mcpCache);
  mcpRun ??= new Promise((resolve) => {
    execFile(claudeBin(), ['mcp', 'list'], { timeout: 120000, cwd: HOME, maxBuffer: 1 << 20 }, (err, stdout) => {
      const servers = [];
      for (const line of String(stdout || '').split('\n')) {
        const m = line.match(/^([\w.@/-]+): .* - (.+)$/);
        if (!m) continue;
        const s = m[2];
        servers.push({ name: m[1], status: /failed to connect|✗|✘/i.test(s) ? 'fail' : /auth|fail/i.test(s) || !/connected/i.test(s) ? 'warn' : 'ok', detail: s.replace(/^[✓✔✗✘!]\s*/, '') });
      }
      mcpCache = { at: Date.now(), servers, error: servers.length ? null : (err ? String(err.message).split('\n')[0] : 'no MCP servers configured') };
      mcpRun = null;
      resolve(mcpCache);
    });
  });
  return mcpRun;
}

const server = http.createServer(async (req, res) => {
  // only this user's UI may call (it sends the key it gave this process; other users on the VM cannot read it)
  if (process.env.PAAS_PLUGIN_KEY && req.headers['x-paas-key'] !== process.env.PAAS_PLUGIN_KEY) { res.writeHead(403); res.end('{"error":"forbidden"}'); return; }
  res.setHeader('Content-Type', 'application/json');
  const url = new URL(req.url, 'http://x');
  try {
    if (req.method === 'GET' && url.pathname === '/status') return res.end(JSON.stringify({ machine: machine(), checks: brain() }));
    if (req.method === 'GET' && url.pathname === '/summary') {
      const days = Math.min(Math.max(parseInt(url.searchParams.get('days') || '30', 10) || 30, 1), 365);
      return res.end(JSON.stringify(summary(days)));
    }
    if (req.method === 'GET' && url.pathname === '/mcp') return res.end(JSON.stringify(await mcp(url.searchParams.get('fresh') === '1')));
  } catch (e) {
    res.writeHead(500); return res.end(JSON.stringify({ error: String(e) }));
  }
  res.writeHead(404); res.end('{"error":"not found"}');
});
server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ ready: true, port: server.address().port })));
