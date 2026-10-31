'use strict';
/**
 * Peleg As A Service sign-in gate (GATE-SPEC.md): the only listener on the network (HTTPS :3001, runs as root).
 * It checks a VM account's password with su, makes sure that user's own UI instance runs (paas-ui@<user>, 127.0.0.1
 * only) and forwards the browser to it. Routing comes only from the signed paas_gate cookie.
 * Node standard library plus the UI's own node-pty; nothing is fetched from the internet.
 */
const fs = require('fs');
const http = require('http');
const https = require('https');
const net = require('net');
const crypto = require('crypto');
const { execFile } = require('child_process');

const ETC = '/etc/paas';
const APP = '/opt/paas/ui/app';

// ---- pure helpers (tested by --self-test, which runs before anything under /etc/paas is read) -------------------

/** Users to stop: seen before, silent for more than idleMs, no open WebSocket, no claude process (running: a Set). 0 = never. */
function idleUsers(now, lastSeen, sockets, running, idleMs) {
  if (!idleMs) return [];
  return [...lastSeen].filter(([u, t]) => now - t > idleMs && !(sockets.get(u) > 0) && !running.has(u)).map(([u]) => u);
}

/** /etc/paas/allowed-groups: one group per line, # comments; paas-users when nothing is listed. */
function parseGroups(text) {
  const list = String(text || '').split('\n').map((l) => l.replace(/#.*/, '').trim().toLowerCase()).filter(Boolean);
  return list.length ? list : ['paas-users'];
}

if (process.argv.includes('--self-test')) {
  const assert = require('assert');
  const M = 60000;
  const seen = new Map([['idle', 0], ['ws', 0], ['claude', 0], ['young', 100 * M]]);
  const socks = new Map([['ws', 2], ['gone', 0]]);
  const claude = new Set(['claude']);
  assert.deepStrictEqual(idleUsers(120 * M + 1, seen, socks, claude, 120 * M), ['idle']);
  assert.deepStrictEqual(idleUsers(130 * M, new Map([['young', 100 * M]]), socks, claude, 120 * M), []);
  assert.deepStrictEqual(idleUsers(1e12, seen, socks, claude, 0), []);
  assert.deepStrictEqual(idleUsers(1e12, new Map([['gone', 0]]), socks, new Set(), 1), ['gone']);
  assert.deepStrictEqual(parseGroups(undefined), ['paas-users']);
  assert.deepStrictEqual(parseGroups('# nothing\n\n  \n'), ['paas-users']);
  assert.deepStrictEqual(parseGroups('paas-users\n# AD\nDomain-Admins  # all\n  eng@corp \n'), ['paas-users', 'domain-admins', 'eng@corp']);
  console.log('gate self-test ok');
  process.exit(0);
}

const pty = require(`${APP}/node_modules/node-pty`);
const PORT = Number(process.env.GATE_PORT || 3001);
const KEY = fs.readFileSync(`${ETC}/gate.key`);
const IDLE_MS = Math.max(0, Number(process.env.GATE_IDLE_MINUTES || 120) || 0) * 60000; // 0 = instances are never stopped for idleness
const COOKIE = 'paas_gate';
const SESSION_S = 12 * 3600;
const USER_RE = /^[a-z_][a-z0-9_.-]{0,63}$/; // AD names; lower-cased before the check
const WINDOW_MS = 10 * 60 * 1000;
const MAX_FAILURES = 5;
const MAX_IP_FAILURES = 30; // all names from one address (NAT users share it, so generous)
const MAX_IP_BUSY = 4; // password checks running at once per address
const FAIL_MS = 3500; // every failed sign-in answers after at least this long: unknown user looks like a wrong password
const BAD = 'Wrong username or password';
const lockedUser = (min) => `Too many wrong passwords for this username from this computer. Try again in ${min} minute${min === 1 ? '' : 's'}.`;
const lockedIp = (min) => `Too many sign-in attempts from this computer or network. Wait ${min} minute${min === 1 ? '' : 's'} and try again.`;
const minutesLeft = (list) => Math.max(1, Math.ceil(((list[0] || Date.now()) + WINDOW_MS - Date.now()) / 60000));
const LOGO = (() => { try { return fs.readFileSync(`${APP}/dist/logo.svg`, 'utf8'); } catch { return ''; } })();

const log = (msg) => console.log(`${new Date().toISOString()} ${msg}`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const run = (cmd, args, timeout = 10000) => new Promise((resolve) =>
  execFile(cmd, args, { timeout }, (err, stdout) => resolve(err ? null : String(stdout))));
const clientIp = (req) => String(req.socket.remoteAddress || '').replace(/^::ffff:/, '');

// ---- who may sign in -------------------------------------------------------------------------------------------

const failures = new Map(); // "user|ip" and "ip" -> times of failed (or still running) attempts
function recent(key) {
  const now = Date.now();
  const list = (failures.get(key) || []).filter((t) => now - t < WINDOW_MS);
  failures.set(key, list);
  return list;
}
const busy = new Map(); // ip -> password checks running
setInterval(() => { for (const k of failures.keys()) if (!recent(k).length) failures.delete(k); }, WINDOW_MS).unref();

let groupsCache = { t: 0, list: ['paas-users'] }; // /etc/paas/allowed-groups, read at most every 60 s
function allowedGroups() {
  if (Date.now() - groupsCache.t >= 60000) {
    let text = '';
    try { text = fs.readFileSync(`${ETC}/allowed-groups`, 'utf8'); } catch { /* missing: the default */ }
    groupsCache = { t: Date.now(), list: parseGroups(text) };
  }
  return groupsCache.list;
}

/** root, or a member of any allowed group (local or AD through sssd: `id` sees both). */
async function allowed(user) {
  if (user === 'root') return true;
  const out = await run('id', ['-nG', '--', user]);
  if (!out) return false;
  const have = out.trim().toLowerCase().split(/\s+/);
  return allowedGroups().some((g) => have.includes(g));
}

/** The same check as the UI's system-auth.ts: su asks for the password in a pty (as root, drop to nobody first). */
function checkPassword(user, password) {
  if (/[\r\n]/.test(password) || password.length > 512) return Promise.resolve(false);
  return new Promise((resolve) => {
    const proc = pty.spawn('runuser', ['-u', 'nobody', '--', 'su', user, '-c', 'exit 0'], {
      name: 'dumb', cols: 80, rows: 24, env: { PATH: '/usr/sbin:/usr/bin:/sbin:/bin', LANG: 'C', LC_ALL: 'C' },
    });
    let sent = false;
    let done = false;
    const finish = (ok) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try { process.kill(-proc.pid, 'SIGKILL'); } catch { /* already gone */ } // runuser and su too, not only the leader
      resolve(ok);
    };
    const timer = setTimeout(() => finish('timeout'), 15000); // slow, not wrong: the caller does not count it
    proc.onData((data) => {
      if (!sent && /password/i.test(data)) {
        sent = true;
        proc.write(`${password}\r`);
      }
    });
    proc.onExit(({ exitCode }) => finish(sent && exitCode === 0));
  });
}

// ---- per-user instances ----------------------------------------------------------------------------------------

const envPath = (user) => `${ETC}/users/${user}.env`;

/** The instance's port, or null when the user has no instance file (never signed in, or removed). */
const ports = new Map(); // user -> { p, t }: the file is read at most every 5 s per user
function instancePort(user) {
  const c = ports.get(user);
  if (c && Date.now() - c.t < 5000) return c.p;
  let p = null;
  try {
    const m = /^SERVER_PORT=(\d+)$/m.exec(fs.readFileSync(envPath(user), 'utf8'));
    p = m ? Number(m[1]) : null;
  } catch { /* no file */ }
  ports.set(user, { p, t: Date.now() });
  return p;
}

/** root: 41000; everyone else: one above the highest port in use, so a port is never reused while its file exists. */
function createEnv(user) {
  ports.clear(); // read the files fresh: the port is picked from what is on disk now
  if (instancePort(user)) return;
  let port = 41000;
  if (user !== 'root') {
    for (const f of fs.readdirSync(`${ETC}/users`)) {
      if (f.endsWith('.env')) port = Math.max(port, instancePort(f.slice(0, -4)) || 0);
    }
    port += 1;
  }
  const claude = ['/usr/local/bin/claude', '/usr/bin/claude'].find((p) => fs.existsSync(p)) || '/usr/local/bin/claude';
  const env = `SERVER_PORT=${port}\nJWT_SECRET=${crypto.randomBytes(32).toString('hex')}\nPAAS_LOGIN_USERS=${user}\n`
    + `CLAUDE_CLI_PATH=${claude}\nPATH=/opt/paas/ui/node/bin:/usr/local/bin:/usr/bin:/bin\n`; // paas-user's, without its sbin dirs
  try {
    fs.writeFileSync(envPath(user), env, { flag: 'wx', mode: 0o600 });
    ports.delete(user);
    log(`created ${envPath(user)} (port ${port})`);
  } catch (e) {
    if (e.code !== 'EEXIST') throw e; // the Users page made it at the same moment
  }
}

const healthy = (port) => new Promise((resolve) => {
  const req = http.get({ host: '127.0.0.1', port, path: '/health', timeout: 2000 }, (res) => {
    res.resume();
    resolve(res.statusCode === 200);
  });
  req.on('error', () => resolve(false)).on('timeout', () => req.destroy());
});

/** First sign-in, or a home without the brain: paas-user provision (never fatal; one run per user at a time). */
const provisioning = new Map();
function provisionUser(user) {
  if (!provisioning.has(user)) {
    provisioning.set(user, new Promise((resolve) => {
      log(`provisioning ${user}`);
      execFile('/opt/paas/bin/paas-user', ['provision', user], { timeout: 60000 }, (err, stdout, stderr) => {
        if (err) log(`provision ${user} failed: ${String(stderr || err.message).trim().split('\n').pop()}`);
        resolve();
      });
    }).finally(() => provisioning.delete(user)));
  }
  return provisioning.get(user);
}
async function homeOf(user) {
  const line = await run('getent', ['passwd', user]);
  return line ? line.trim().split(':')[5] || null : null;
}

const starting = new Map(); // user -> promise of the port (one start at a time per user)
function ensureInstance(user) {
  if (!starting.has(user)) {
    starting.set(user, (async () => {
      createEnv(user);
      const port = instancePort(user);
      if (await healthy(port)) return port;
      log(`starting paas-ui@${user}`);
      await run('systemctl', ['start', `paas-ui@${user}`], 30000);
      for (const end = Date.now() + 60000; Date.now() < end; await sleep(500)) {
        if (await healthy(port)) return port;
      }
      log(`paas-ui@${user} did not answer /health within 60 s`);
      return null;
    })().finally(() => starting.delete(user)));
  }
  return starting.get(user);
}

/** The instance checks the password again, as its own user, and hands out the browser's token. */
const instanceLogin = (port, username, password) => new Promise((resolve) => {
  const body = JSON.stringify({ username, password });
  const req = http.request({
    host: '127.0.0.1', port, path: '/api/auth/login', method: 'POST', timeout: 30000,
    headers: { 'content-type': 'application/json', 'content-length': Buffer.byteLength(body) },
  }, (res) => {
    let data = '';
    res.setEncoding('utf8');
    res.on('data', (c) => { data += c; });
    res.on('end', () => {
      let token = null;
      try { token = JSON.parse(data).token; } catch { /* not JSON */ }
      resolve({ status: res.statusCode, body: data, token: typeof token === 'string' ? token : null });
    });
  });
  req.on('error', () => resolve({ status: 502, token: null })).on('timeout', () => req.destroy());
  req.end(body);
});

/** A socket to the user's instance, starting the instance when it is not running (crash, reboot, stopped). */
async function connectUpstream(user) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const port = attempt ? await ensureInstance(user) : instancePort(user);
    if (!port) return null;
    const sock = await new Promise((resolve) => {
      const s = net.connect(port, '127.0.0.1');
      s.once('connect', () => resolve(s)).once('error', () => resolve(null));
    });
    if (sock) return sock.on('error', () => { /* the request or pipe using it reports it */ });
  }
  return null;
}

// ---- idle stop: an instance nobody uses gives its RAM back; the next request starts it again (connectUpstream) ----

const lastSeen = new Map(); // user -> time of the last forwarded request
const sockets = new Map(); // user -> open upgraded (WebSocket) connections
const touch = (user) => lastSeen.set(user, Date.now());

const hasClaude = (user) => new Promise((resolve) => // pgrep: exit 1 = none; any other failure counts as "running" (do not stop)
  execFile('pgrep', ['-u', user, '-x', 'claude'], { timeout: 5000 }, (err) => resolve(!err || err.code !== 1)));

let sweeping = false;
async function idleSweep() {
  if (sweeping) return;
  sweeping = true;
  try {
    const out = await run('systemctl', ['list-units', '--plain', '--no-legend', '--state=active', 'paas-ui@*.service']);
    if (out === null) return;
    const up = out.split('\n').map((l) => /^paas-ui@(.+)\.service\s/.exec(l.trim())).filter(Boolean).map((m) => m[1]);
    for (const u of up) if (!lastSeen.has(u)) touch(u); // running before the gate started: the clock starts now
    for (const u of [...lastSeen.keys()]) if (!up.includes(u)) lastSeen.delete(u);
    const quiet = idleUsers(Date.now(), lastSeen, sockets, new Set(), IDLE_MS);
    const busyClaude = new Set();
    for (const u of quiet) if (await hasClaude(u)) busyClaude.add(u);
    for (const u of idleUsers(Date.now(), lastSeen, sockets, busyClaude, IDLE_MS)) {
      if (!idleUsers(Date.now(), lastSeen, sockets, busyClaude, IDLE_MS).includes(u)) continue; // used while we were checking
      log(`stopping idle paas-ui@${u}`);
      lastSeen.delete(u);
      await run('systemctl', ['stop', `paas-ui@${u}`], 30000);
    }
  } finally { sweeping = false; }
}

// ---- session cookie: <user>.<expiry>.<hmac> --------------------------------------------------------------------

const sign = (v) => crypto.createHmac('sha256', KEY).update(v).digest('hex');
function newCookie(user) {
  const v = `${user}.${Math.floor(Date.now() / 1000) + SESSION_S}`;
  return `${COOKIE}=${v}.${sign(v)}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${SESSION_S}`;
}
const CLEAR = `${COOKIE}=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0`;

/** [the gate cookie's value, the other cookies as one header] */
function splitCookies(header) {
  let gate = null;
  const rest = [];
  for (const part of (header || '').split(';')) {
    const p = part.trim();
    if (!p) continue;
    if (p.startsWith(`${COOKIE}=`)) gate = gate ?? p.slice(COOKIE.length + 1);
    else rest.push(p);
  }
  return [gate, rest.join('; ')];
}

function sessionUser(req) {
  const m = /^([a-z_][a-z0-9_.-]{0,63})\.(\d{1,12})\.([0-9a-f]{64})$/.exec(splitCookies(req.headers.cookie)[0] || '');
  if (!m || Number(m[2]) < Date.now() / 1000) return null;
  if (!crypto.timingSafeEqual(Buffer.from(sign(`${m[1]}.${m[2]}`), 'hex'), Buffer.from(m[3], 'hex'))) return null;
  if (fs.existsSync(`${ETC}/users/${m[1]}.locked`)) return null; // paas-user lock: the cookie dies with the account
  return instancePort(m[1]) ? m[1] : null;
}

// ---- pages -----------------------------------------------------------------------------------------------------

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const signInPage = (error, username = '') => `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark light">
<title>Sign in - Peleg As A Service</title><style>
:root{--g:linear-gradient(120deg,#a78bfa 0%,#818cf8 30%,#60a5fa 55%,#22d3ee 80%,#34d399 100%);--bg:#0d0f1a;--card:#141725;
--fg:#eceff8;--muted:#9aa1b8;--line:#23273a;--input:#0f1120;--inline:#2c3148;--errfg:#fca5a5;--errbg:rgba(248,113,113,.12);
--foot:#9aa1b8;--warn:#fbbf24;--ring:#c4b5fd;--btnfg:#0b0d1a}
@media(prefers-color-scheme:light){:root{--g:linear-gradient(120deg,#6d28d9,#4f46e5 30%,#1d4ed8 55%,#0e7490 80%,#047857);--bg:#f6f7fb;--card:#fff;
--fg:#14172a;--muted:#555c74;--line:#d9dcea;--input:#fff;--inline:#9aa1b8;--errfg:#b42318;--errbg:rgba(180,35,24,.08);--foot:#555c74;
--warn:#92400e;--ring:#6d28d9;--btnfg:#fff}}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
padding:16px;font:15px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;color:var(--fg);background:var(--bg);
background-image:radial-gradient(40rem 28rem at 50% -8rem,rgba(167,139,250,.22),transparent 70%),
radial-gradient(30rem 22rem at 100% 110%,rgba(34,211,238,.14),transparent 70%),
radial-gradient(26rem 20rem at 0% 100%,rgba(52,211,153,.10),transparent 70%)}
.card{width:100%;max-width:400px;padding:32px;border-radius:16px;background:var(--card);border:1px solid var(--line);
box-shadow:0 20px 60px -20px rgba(0,0,0,.35)}.logo{display:flex;justify-content:center}.logo svg{width:64px;height:64px}
h1{margin:16px 0 4px;text-align:center;font-size:26px;background:var(--g);-webkit-background-clip:text;
background-clip:text;color:transparent}p.sub{margin:0 0 24px;text-align:center;color:var(--muted)}
label{display:block;margin:14px 0 6px;font-weight:600;font-size:14px}input{width:100%;padding:10px 12px;
border-radius:10px;border:1px solid var(--inline);background:var(--input);color:inherit;font:inherit;font-size:16px}
input:focus{border-color:#a78bfa}input:focus-visible,button:focus-visible{outline:3px solid var(--ring);outline-offset:2px}
.pw{position:relative}.pw input{padding-right:72px}
button{width:100%;margin-top:22px;padding:11px;min-height:44px;border:0;border-radius:10px;touch-action:manipulation;
background:var(--g);color:var(--btnfg);font-family:inherit;font-weight:600;font-size:16px;line-height:1.2;cursor:pointer}
button:hover{filter:brightness(1.08)}button:disabled{opacity:.7;cursor:wait;filter:none}
button.eye{position:absolute;right:4px;top:50%;transform:translateY(-50%);width:auto;margin:0;padding:4px 10px;min-height:36px;
background:none;color:var(--muted);font-size:13px}button.eye:hover{filter:none;color:var(--fg)}
small{display:block;margin-top:6px;color:var(--warn);font-size:13px}
.err{margin:0 0 8px;padding:10px 12px;border-radius:10px;background:var(--errbg);color:var(--errfg);font-size:14px}
.slow{margin:12px 0 0;text-align:center;color:var(--muted);font-size:13px}
.foot{margin-top:22px;text-align:center;color:var(--foot);font-size:13px}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}</style></head><body><main>
<form class="card" method="post" action="/paas-gate/login" aria-labelledby="t"><div class="logo" aria-hidden="true">${LOGO}</div><h1 id="t">Peleg As A Service</h1>
<p class="sub">Sign in with this VM's account</p>${error ? `<p class="err" id="err" role="alert">${esc(error)}</p>` : ''}
<label for="u">Username</label><input id="u" name="username" value="${esc(username)}" autocomplete="username" autocapitalize="none" required ${username ? '' : 'autofocus'} ${error ? 'aria-describedby="err"' : ''}>
<label for="p">Password</label><div class="pw"><input id="p" name="password" type="password" autocomplete="current-password" required ${username ? 'autofocus' : ''} ${error ? 'aria-describedby="err"' : ''}>
<button type="button" class="eye" id="eye" aria-label="Show password" aria-pressed="false">Show</button></div>
<small id="caps" role="status" hidden>Caps Lock is on</small>
<button type="submit" id="go">Sign In</button><p class="slow" id="slow" role="status" hidden>Still working. A first sign-in can take up to a minute while your workspace starts.</p>
<div class="foot">Runs on this VM · read-only toward infrastructure</div></form></main>
<noscript><style>.pw button,#caps{display:none}</style></noscript>
<script>try{localStorage.removeItem('auth-token')}catch(e){}
var f=document.querySelector('form'),b=document.getElementById('go'),p=document.getElementById('p'),e=document.getElementById('eye'),
c=document.getElementById('caps'),w=document.getElementById('slow'),t;
f.addEventListener('submit',function(){p.type='password';b.disabled=true;b.textContent='Signing in…';b.setAttribute('aria-busy','true');
t=setTimeout(function(){w.hidden=false},4000)});
addEventListener('pageshow',function(v){if(v.persisted){clearTimeout(t);b.disabled=false;b.textContent='Sign In';b.removeAttribute('aria-busy');w.hidden=true}});
e.onclick=function(){var s=p.type==='password';p.type=s?'text':'password';e.textContent=s?'Hide':'Show';e.setAttribute('aria-pressed',s);
e.setAttribute('aria-label',(s?'Hide':'Show')+' password')};
p.onkeyup=p.onkeydown=function(k){c.hidden=!(k.getModifierState&&k.getModifierState('CapsLock'))};p.onblur=function(){c.hidden=true};
</script></body></html>`;

const signedInPage = (token) => '<!doctype html><meta charset="utf-8"><title>Signing in - Peleg As A Service</title><script>'
  + `localStorage.setItem('auth-token', ${JSON.stringify(token).replace(/</g, '\\u003c')});location.replace('/');</script>`
  + '<noscript><meta http-equiv="refresh" content="0;url=/"></noscript><p style="font:16px system-ui;padding:24px">Signing you in\u2026</p>';

function send(res, status, type, body) {
  res.writeHead(status, { 'content-type': type, 'cache-control': 'no-store', 'x-frame-options': 'DENY' });
  res.end(body);
}
const sendJson = (res, status, obj) => send(res, status, 'application/json', typeof obj === 'string' ? obj : JSON.stringify(obj));
const sendPage = (res, status, error, username) => send(res, status, 'text/html; charset=utf-8', signInPage(error, username));

// ---- sign-in / sign-out ----------------------------------------------------------------------------------------

const readBody = (req, max) => new Promise((resolve) => {
  const chunks = [];
  let size = 0;
  const timer = setTimeout(() => { resolve(null); req.destroy(); }, 10000); // a slow-drip body is dropped
  req.on('data', (c) => {
    size += c.length;
    if (size > max) { resolve(null); req.destroy(); } else chunks.push(c);
  });
  req.on('end', () => { clearTimeout(timer); resolve(Buffer.concat(chunks).toString('utf8')); });
  req.on('error', () => { clearTimeout(timer); resolve(null); });
});

function credentials(req, body) {
  try {
    const o = /json/.test(req.headers['content-type'] || '') ? JSON.parse(body) : Object.fromEntries(new URLSearchParams(body));
    return [typeof o.username === 'string' ? o.username : '', typeof o.password === 'string' ? o.password : ''];
  } catch { return ['', '']; }
}

/** POST /paas-gate/login (the gate's form: answers a page) and POST /api/auth/login (the UI's own form: JSON). */
async function login(req, res, asJson) {
  const started = Date.now();
  const ip = clientIp(req);
  const [rawName, password] = credentials(req, (await readBody(req, 8192)) || '');
  const username = rawName.toLowerCase(); // sssd with case_sensitive = false resolves any case to one account
  const valid = USER_RE.test(username);
  const fail = async (status, msg, why, retryMin) => {
    log(`sign-in failed user=${valid ? username : '(invalid)'} ip=${ip}${why ? ` (${why})` : ''}`);
    if (status === 401) await sleep(Math.max(0, FAIL_MS - (Date.now() - started)));
    if (retryMin) res.setHeader('retry-after', String(retryMin * 60));
    if (asJson) sendJson(res, status, { error: msg }); else sendPage(res, status, msg, valid ? username : '');
  };
  if (!valid || !password) return fail(401, BAD);
  const key = `${username}|${ip}`;
  const attempts = recent(key);
  if (attempts.length >= MAX_FAILURES) return fail(429, lockedUser(minutesLeft(attempts)), 'locked', minutesLeft(attempts));
  const perIp = recent(ip);
  if (perIp.length >= MAX_IP_FAILURES || (busy.get(ip) || 0) >= MAX_IP_BUSY) {
    const m = minutesLeft(perIp);
    return fail(429, lockedIp(m), 'address limit', m);
  }
  attempts.push(Date.now()); // counted while it runs, so parallel guesses cannot get around the limit
  perIp.push(Date.now());
  busy.set(ip, (busy.get(ip) || 0) + 1);
  let ok = false;
  try { ok = (await allowed(username)) && (await checkPassword(username, password)); } finally {
    if (busy.get(ip) > 1) busy.set(ip, busy.get(ip) - 1); else busy.delete(ip);
  }
  if (ok === 'timeout') { // the VM was slow, the password was not judged: no strike against the user
    recent(key).pop();
    recent(ip).pop();
    return fail(503, 'The VM did not answer in time. Try again in a moment.', 'password check timed out');
  }
  if (!ok) return fail(401, BAD);
  const first = !fs.existsSync(envPath(username));
  const home = first ? null : await homeOf(username);
  if (first || !home || !fs.existsSync(`${home}/.claude/brain`)) await provisionUser(username);
  touch(username);
  const port = await ensureInstance(username);
  const r = port ? await instanceLogin(port, username, password) : { status: 502, token: null };
  if (!r.token) {
    return r.status === 429 ? fail(429, lockedUser(10), 'instance locked', 10)
      : fail(502, 'Your workspace did not start. Try again in a minute.', `instance answered ${r.status}`);
  }
  recent(key).pop(); // the right password does not count against the limit
  recent(ip).pop();
  log(`sign-in ok user=${username} ip=${ip}`);
  res.setHeader('set-cookie', newCookie(username));
  if (asJson) sendJson(res, 200, r.body); else send(res, 200, 'text/html; charset=utf-8', signedInPage(r.token));
}

// ---- forwarding ------------------------------------------------------------------------------------------------

const DROP = new Set(['connection', 'keep-alive', 'proxy-connection', 'te', 'trailer', 'upgrade', 'cookie',
  'x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-host']);
function forwardHeaders(req) {
  const h = {};
  for (const [k, v] of Object.entries(req.headers)) if (!DROP.has(k)) h[k] = v;
  const others = splitCookies(req.headers.cookie)[1];
  if (others) h.cookie = others;
  h['x-forwarded-for'] = clientIp(req);
  h['x-forwarded-proto'] = 'https';
  return h;
}

async function proxy(req, res, user) {
  touch(user);
  res.on('close', () => touch(user)); // a long download or chat stream counts until it ends
  const sock = await connectUpstream(user);
  if (!sock) return sendJson(res, 502, { error: 'Your workspace did not start. Try again in a minute.' });
  const up = http.request({ method: req.method, path: req.url, headers: forwardHeaders(req), createConnection: () => sock }, (ur) => {
    const h = { ...ur.headers };
    delete h.connection;
    delete h['keep-alive'];
    res.writeHead(ur.statusCode, h);
    ur.pipe(res); // streamed: chat, downloads
  });
  up.on('error', () => {
    if (!res.headersSent) sendJson(res, 502, { error: 'Your workspace stopped answering' }); else res.destroy();
  });
  res.on('close', () => { if (!res.writableFinished) up.destroy(); });
  req.pipe(up); // streamed: uploads
}

function upgrade(req, socket, head) {
  socket.on('error', () => socket.destroy());
  const user = sessionUser(req);
  if (!user) return socket.end('HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\nConnection: close\r\n\r\n');
  touch(user);
  connectUpstream(user).then((up) => {
    if (!up) return socket.end('HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n');
    if (socket.destroyed) return up.destroy();
    const h = { ...forwardHeaders(req), connection: 'Upgrade', upgrade: req.headers.upgrade };
    let raw = `${req.method} ${req.url} HTTP/1.1\r\n`;
    for (const [k, v] of Object.entries(h)) for (const one of [].concat(v)) raw += `${k}: ${one}\r\n`;
    up.write(`${raw}\r\n`);
    if (head.length) up.write(head);
    sockets.set(user, (sockets.get(user) || 0) + 1);
    let counted = true;
    const close = () => {
      if (counted) { counted = false; sockets.set(user, Math.max(0, sockets.get(user) - 1)); touch(user); }
      up.destroy();
      socket.destroy();
    };
    up.on('close', close);
    socket.on('close', close);
    up.pipe(socket).pipe(up);
  });
}

async function handle(req, res) {
  const path = req.url.split('?')[0];
  const post = req.method === 'POST';
  if (post && (path === '/paas-gate/login' || path === '/api/auth/login')) return login(req, res, path === '/api/auth/login');
  const user = sessionUser(req);
  if ((post && path === '/api/auth/logout') || (req.method === 'GET' && path === '/paas-gate/logout')) {
    res.setHeader('set-cookie', CLEAR);
    if (user) log(`sign-out user=${user} ip=${clientIp(req)}`);
    if (user && post) return proxy(req, res, user); // the instance's own sign-out answer; the UI then shows sign-in
    return sendPage(res, 200);
  }
  if (!user) {
    if (req.method === 'GET' && (path === '/' || /text\/html/.test(req.headers.accept || ''))) return sendPage(res, 200);
    return sendJson(res, 401, { error: 'Sign in' });
  }
  return proxy(req, res, user);
}

const server = https.createServer({
  cert: fs.readFileSync(`${ETC}/tls/paas-ui.crt`),
  key: fs.readFileSync(`${ETC}/tls/paas-ui.key`),
  requestTimeout: 0, // large uploads on slow links; instances have their own limits
}, (req, res) => handle(req, res).catch((e) => {
  log(`error ${req.method} ${req.url.split('?')[0]}: ${e.message}`);
  if (!res.headersSent) sendJson(res, 500, { error: 'Gate error' }); else res.destroy();
}));
server.on('upgrade', upgrade);
server.listen(PORT, '0.0.0.0', () => log(`gate listening on https://0.0.0.0:${PORT}`));
if (IDLE_MS) setInterval(() => idleSweep().catch((e) => log(`idle sweep: ${e.message}`)), 60000).unref();
