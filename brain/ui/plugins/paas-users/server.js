// Users backend (installed for root only): runs paas-user (brain/multiuser/paas-user). Passwords go to it on stdin,
// never on a command line or into a log.
import http from 'node:http';
import fs from 'node:fs';
import { execFile } from 'node:child_process';

const BIN = process.env.PAAS_USER_BIN || ['/opt/paas/bin/paas-user', '/usr/local/sbin/paas-user'].find((p) => fs.existsSync(p)) || 'paas-user';
const NAME = /^[a-z_][a-z0-9_.-]{0,31}$/;
const run = (args, input) => new Promise((resolve) => {
  const p = execFile(BIN, args, { timeout: 120000, maxBuffer: 4 << 20 }, (err, stdout, stderr) => resolve({ ok: !err, out: `${stdout}${stderr}`.trim() }));
  p.stdin.end(input ? `${input}\n` : '');
});

function body(req) {
  return new Promise((resolve, reject) => {
    let s = '';
    req.on('data', (c) => { s += c; if (s.length > 10000) req.destroy(); });
    req.on('end', () => { try { resolve(JSON.parse(s || '{}')); } catch (e) { reject(e); } });
  });
}
const pw = (b) => String(b.password || '');
const name = (b) => (NAME.test(String(b.name || '')) ? b.name : null);

const routes = {
  'GET /list': async () => {
    const r = await run(['list', '--json']);
    return r.ok ? { ok: true, users: JSON.parse(r.out || '[]') } : r;
  },
  'POST /add': async (b) => {
    if (!name(b)) return { ok: false, out: 'Name: lower-case letters, digits, . _ - (e.g. dana)' };
    if (pw(b).length < 8 || /[\r\n:]/.test(pw(b))) return { ok: false, out: 'Password: at least 8 characters, no line breaks or colons' };
    return run(['add', b.name], pw(b));
  },
  'POST /passwd': async (b) => (name(b) && pw(b).length >= 8 && !/[\r\n:]/.test(pw(b)) ? run(['passwd', b.name], pw(b)) : { ok: false, out: 'Password: at least 8 characters, no line breaks or colons' }),
  'POST /lock': async (b) => (name(b) ? run(['lock', b.name]) : { ok: false, out: 'Unknown user' }),
  'POST /unlock': async (b) => (name(b) ? run(['unlock', b.name]) : { ok: false, out: 'Unknown user' }),
  'POST /remove': async (b) => (name(b) ? run(['remove', b.name, ...(b.deleteHome ? ['--delete-home'] : [])]) : { ok: false, out: 'Unknown user' }),
};

const server = http.createServer(async (req, res) => {
  // only this user's UI may call (it sends the key it gave this process; other users on the VM cannot read it)
  if (process.env.PAAS_PLUGIN_KEY && req.headers['x-paas-key'] !== process.env.PAAS_PLUGIN_KEY) { res.writeHead(403); res.end('{"error":"forbidden"}'); return; }
  res.setHeader('Content-Type', 'application/json');
  if (process.getuid?.() !== 0) { res.end('{"ok":false,"out":"Only root manages users"}'); return; }
  const fn = routes[`${req.method} ${new URL(req.url, 'http://x').pathname}`];
  if (!fn) { res.writeHead(404); res.end('{"error":"not found"}'); return; }
  try { res.end(JSON.stringify(await fn(req.method === 'POST' ? await body(req) : {}))); } catch (e) { res.writeHead(500); res.end(JSON.stringify({ error: String(e.message || e) })); }
});
server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ ready: true, port: server.address().port })));
