// Usage backend: tokens and estimated cost from Claude Code's own session logs (~/.claude/projects/**/*.jsonl).
// Read-only, local; per-file cache keyed by mtime so a refresh only re-reads what changed.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.join(process.env.HOME || '', '.claude', 'projects');
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

const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  const url = new URL(req.url, 'http://x');
  if (req.method === 'GET' && url.pathname === '/summary') {
    const days = Math.min(Math.max(parseInt(url.searchParams.get('days') || '30', 10) || 30, 1), 365);
    try { res.end(JSON.stringify(summary(days))); } catch (e) { res.writeHead(500); res.end(JSON.stringify({ error: String(e) })); }
    return;
  }
  res.writeHead(404); res.end('{"error":"not found"}');
});
server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ ready: true, port: server.address().port })));
