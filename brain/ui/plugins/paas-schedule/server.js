// Schedule backend: prompts / skills run by `claude -p` at set times on this VM. Jobs live in
// ~/.claude/paas-schedule/jobs.json (shared by everyone signed in); each run's answer is saved to
// ~/storage-reports/scheduled/ and, as a normal Claude Code session, shows up under Conversations.
// ponytail: the clock runs inside the web UI service (systemd, always on with linger); a run missed while the
// service was down is caught up only within an hour. A real systemd timer per job if that ever matters.
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

const HOME = os.homedir();
const STORE = process.env.PAAS_SCHEDULE_STORE || path.join(HOME, '.claude', 'paas-schedule', 'jobs.json');
const OUT = path.join(HOME, 'storage-reports', 'scheduled');
const CATCH_UP_MS = 60 * 60 * 1000;
const RUN_TIMEOUT_MS = 30 * 60 * 1000;
const claudeBin = () => process.env.CLAUDE_CLI_PATH || [path.join(HOME, '.local', 'bin', 'claude'), '/usr/local/bin/claude'].find((p) => fs.existsSync(p)) || 'claude';

let jobs = [];
try { jobs = JSON.parse(fs.readFileSync(STORE, 'utf8')).jobs || []; } catch { /* first start */ }
const running = new Set();
function save() {
  fs.mkdirSync(path.dirname(STORE), { recursive: true });
  fs.writeFileSync(`${STORE}.tmp`, JSON.stringify({ jobs }, null, 2));
  fs.renameSync(`${STORE}.tmp`, STORE);
}

// the latest planned start at or before `now` (a Date), or null when the job never ran in the last week
function lastSlot(job, now = new Date()) {
  const [h, m] = job.time.split(':').map(Number);
  for (let back = 0; back <= 7; back++) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - back, h, m);
    if (d > now) continue;
    const wd = d.getDay();
    if (job.repeat === 'weekdays' && (wd === 0 || wd === 6)) continue;
    if (job.repeat === 'weekly' && wd !== Number(job.day)) continue;
    return d;
  }
  return null;
}
function nextSlot(job, now = new Date()) {
  for (let ahead = 0; ahead <= 8; ahead++) {
    const probe = new Date(now.getFullYear(), now.getMonth(), now.getDate() + ahead, 23, 59, 59);
    const s = lastSlot(job, probe);
    if (s && s > now) return s;
  }
  return null;
}

const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'job';
const stamp = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}-${String(d.getHours()).padStart(2, '0')}${String(d.getMinutes()).padStart(2, '0')}`;

function runJob(job, why) {
  if (running.has(job.id)) return false;
  running.add(job.id);
  const started = new Date();
  const cwd = job.folder.replace(/^~(?=\/|$)/, HOME);
  fs.mkdirSync(cwd, { recursive: true });
  const proc = spawn(claudeBin(), ['-p', job.prompt, '--output-format', 'json'], { cwd, env: process.env });
  let out = '';
  let err = '';
  proc.stdout.on('data', (c) => { out += c; });
  proc.stderr.on('data', (c) => { err += c; });
  const timer = setTimeout(() => proc.kill('SIGTERM'), RUN_TIMEOUT_MS);
  proc.on('close', (code) => {
    clearTimeout(timer);
    running.delete(job.id);
    let result = null;
    try { result = JSON.parse(out); } catch { /* not JSON: an error before the run started */ }
    const ok = code === 0 && result && !result.is_error;
    const text = result?.result ?? (err || out || `claude exited with code ${code}`);
    fs.mkdirSync(OUT, { recursive: true });
    const file = `${slug(job.name)}-${stamp(started)}.md`;
    fs.writeFileSync(path.join(OUT, file), `# ${job.name}\n\n_${started.toLocaleString()} · ${why} · ${ok ? 'finished' : 'failed'} in ${Math.round((Date.now() - started) / 1000)} s · prompt: ${job.prompt.replace(/\n/g, ' ')}_\n\n${text}\n`);
    const j = jobs.find((x) => x.id === job.id);
    if (!j) return;
    j.runs = [{ at: started.toISOString(), why, ok, seconds: Math.round((Date.now() - started) / 1000), report: file, session: result?.session_id || null }, ...(j.runs || [])].slice(0, 20);
    save();
  });
  return true;
}

function tick() {
  const now = new Date();
  for (const j of jobs) {
    if (!j.enabled) continue;
    const s = lastSlot(j, now);
    if (!s || now - s > CATCH_UP_MS || (j.lastSlot && new Date(j.lastSlot) >= s)) continue;
    j.lastSlot = s.toISOString();
    save();
    runJob(j, 'scheduled');
  }
}
setInterval(tick, 30000);

const TIME = /^([01]\d|2[0-3]):[0-5]\d$/;
function clean(b) {
  const job = {
    name: String(b.name || '').trim().slice(0, 80), prompt: String(b.prompt || '').trim().slice(0, 8000),
    folder: String(b.folder || '~/chats').trim() || '~/chats', repeat: ['daily', 'weekdays', 'weekly'].includes(b.repeat) ? b.repeat : 'daily',
    time: String(b.time || ''), day: Math.min(Math.max(Number(b.day) || 0, 0), 6), enabled: b.enabled !== false,
  };
  if (!job.name) return 'Give the job a name';
  if (!job.prompt) return 'Write the prompt (a question, or a skill such as /morning-check)';
  if (!TIME.test(job.time)) return 'Time as HH:MM, e.g. 07:00';
  if (!/^(~|\/)[\w./ -]*$/.test(job.folder) || job.folder.includes('..')) return 'Folder: a path like ~/chats or /home/peleg/storage-api';
  return job;
}

function body(req) {
  return new Promise((resolve, reject) => {
    let s = '';
    req.on('data', (c) => { s += c; if (s.length > 100000) req.destroy(); });
    req.on('end', () => { try { resolve(JSON.parse(s || '{}')); } catch (e) { reject(e); } });
  });
}

const view = (j) => ({ ...j, running: running.has(j.id), next: j.enabled ? nextSlot(j)?.toISOString() || null : null });
const routes = {
  'GET /jobs': () => ({ jobs: jobs.map(view), now: new Date().toISOString() }),
  'POST /job': (b) => {
    const job = clean(b);
    if (typeof job === 'string') return { ok: false, out: job };
    const old = jobs.find((x) => x.id === b.id);
    if (old) Object.assign(old, job, { lastSlot: lastSlot(job)?.toISOString() || null });   // no instant run after an edit
    else jobs.push({ ...job, id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`, runs: [], lastSlot: lastSlot(job)?.toISOString() || null });
    save();
    return { ok: true };
  },
  'POST /job-delete': (b) => { jobs = jobs.filter((x) => x.id !== b.id); save(); return { ok: true }; },
  'POST /run': (b) => {
    const j = jobs.find((x) => x.id === b.id);
    if (!j) return { ok: false, out: 'No such job' };
    return runJob(j, 'run now') ? { ok: true } : { ok: false, out: 'Already running' };
  },
  'GET /report': (_b, q) => {
    const name = path.basename(String(q.get('file') || ''));
    try { return { ok: true, text: fs.readFileSync(path.join(OUT, name), 'utf8') }; } catch { return { ok: false, out: 'Report not found' }; }
  },
};

const server = http.createServer(async (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  const url = new URL(req.url, 'http://x');
  const fn = routes[`${req.method} ${url.pathname}`];
  if (!fn) { res.writeHead(404); res.end('{"error":"not found"}'); return; }
  try {
    res.end(JSON.stringify(await fn(req.method === 'POST' ? await body(req) : {}, url.searchParams)));
  } catch (e) {
    res.writeHead(500); res.end(JSON.stringify({ error: String(e.message || e) }));
  }
});
if (process.argv[2] === '--self-test') {          // node server.js --self-test: the schedule arithmetic
  const at = (s) => new Date(s);
  const eq = (a, b) => { if (String(a) !== String(b)) { console.error(`FAIL ${a} != ${b}`); process.exit(1); } };
  eq(lastSlot({ repeat: 'daily', time: '07:00' }, at('2026-10-27T08:00')), at('2026-10-27T07:00'));
  eq(lastSlot({ repeat: 'daily', time: '07:00' }, at('2026-10-27T06:59')), at('2026-10-26T07:00'));
  eq(lastSlot({ repeat: 'weekdays', time: '07:00' }, at('2026-10-26T06:00')), at('2026-10-23T07:00'));   // Mon early -> Fri
  eq(nextSlot({ repeat: 'weekdays', time: '07:00' }, at('2026-10-24T09:00')), at('2026-10-26T07:00'));   // Sat -> Mon
  eq(nextSlot({ repeat: 'weekly', day: 3, time: '18:30' }, at('2026-10-28T19:00')), at('2026-11-04T18:30'));
  console.log('schedule self-test ok');
  process.exit(0);
}
server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ ready: true, port: server.address().port })));
