import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';

import express from 'express';
// @ts-expect-error -- no type declarations for jsonwebtoken in this checkout (auth.middleware.ts uses @ts-nocheck)
import jwt from 'jsonwebtoken';

import { appConfigDb } from '../database/index.js';

/**
 * Peleg As A Service: the Browser tab. Pages served on this VM, shown inside the UI:
 *   /preview/<port>/<path>   a web app listening on that port, owned by this account (FastAPI docs, Grafana, ...)
 *   /preview/~/<path>        a file under the home folder (HTML reports with their pictures)
 *   /preview/_open           the last page `paas-open` asked for (the Browser tab polls it)
 * An iframe cannot send the UI's token, so signing in also sets the cookie paas_preview (Path=/preview, signed,
 * 12 h; previewCookie() below, called by authenticateToken). Only ports whose listening socket belongs to this
 * account: another user's app (or root's) shown here would run in this UI's origin and could read its token.
 */
export const paasPreview = express.Router();

const COOKIE = 'paas_preview';
const TTL = 12 * 3600;
const OPEN_FILE = path.join(os.homedir(), '.claude-code-ui', 'browser-open.json');
const LOCAL = /^https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?::(\d+))?(\/[^"'\s]*)?/;
let secret: string | null = null;
const key = () => (secret ??= process.env.JWT_SECRET || appConfigDb.getOrCreateJwtSecret());

const cookieOf = (req: express.Request, name: string) =>
  (req.headers.cookie || '').split(/;\s*/).find((c) => c.startsWith(`${name}=`))?.slice(name.length + 1);

const valid = (req: express.Request) => {
  try {
    return Boolean((jwt.verify(cookieOf(req, COOKIE) || '', key()) as { preview?: number }).preview);
  } catch { return false; }
};

/** after a good sign-in check: (re)issue the preview cookie when it is missing or has under an hour left */
export function previewCookie(req: express.Request, res: express.Response, userId: number) {
  try {
    const d = jwt.verify(cookieOf(req, COOKIE) || '', key()) as { exp: number };
    if (d.exp - Date.now() / 1000 > 3600) return;
  } catch { /* missing or expired: issue one */ }
  const v = jwt.sign({ preview: userId }, key(), { expiresIn: TTL });
  res.append('Set-Cookie', `${COOKIE}=${v}; HttpOnly; SameSite=Strict; Path=/preview; Max-Age=${TTL}`);
}

/** listening TCP ports owned by this account (Linux); null where /proc is missing (the Mac demo: all allowed) */
function ownPorts(): Set<number> | null {
  if (!fs.existsSync('/proc/net/tcp')) return null;
  const uid = process.getuid?.();
  const ports = new Set<number>();
  for (const f of ['/proc/net/tcp', '/proc/net/tcp6']) {
    let text = '';
    try { text = fs.readFileSync(f, 'utf8'); } catch { continue; }
    for (const line of text.split('\n').slice(1)) {
      const c = line.trim().split(/\s+/);
      if (c[3] === '0A' && Number(c[7]) === uid) ports.add(parseInt(c[1].split(':')[1], 16));   // 0A = LISTEN
    }
  }
  return ports;
}

// in every proxied HTML page: requests the page makes from script to "/x" or "http://localhost:<port>/x" go
// through /preview/<port>/ too, and so do the links its router pushes into the address bar.
// ponytail: elements a script creates with an absolute src are not rewritten, and WebSockets (live reload) are
// not proxied; add a MutationObserver / an upgrade handler if an app needs them.
const shim = (port: number) => `<script>(function(){var P='/preview/${port}';
function fix(u){try{var x=new URL(String(u),location.href);}catch(e){return u;}
var m=/^(localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|\\[::1\\])$/.test(x.hostname);
if(m&&x.origin!==location.origin)return '/preview/'+(x.port||80)+x.pathname+x.search+x.hash;
if(x.origin===location.origin&&x.pathname.indexOf('/preview/')!==0)return P+x.pathname+x.search+x.hash;return u;}
var F=window.fetch;window.fetch=function(i,o){return F.call(this,i instanceof Request?new Request(fix(i.url),i):fix(i),o);};
var O=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m,u){arguments[1]=fix(u);return O.apply(this,arguments);};
if(window.EventSource){var E=window.EventSource;window.EventSource=function(u,c){return new E(fix(u),c);};}
['pushState','replaceState'].forEach(function(k){var h=history[k];history[k]=function(s,t,u){return h.call(history,s,t,u==null?u:fix(u));};});
})();</script>`;

function rewriteHtml(html: string, port: number) {
  const base = `/preview/${port}`;
  const out = html
    .replace(/(\s(?:src|href|action|poster|formaction)\s*=\s*["'])\/(?!\/)/gi, `$1${base}/`)
    .replace(new RegExp(LOCAL.source, 'g'), (_m, p, rest) => `/preview/${p || 80}${rest || '/'}`);
  const head = out.search(/<head[^>]*>/i);
  if (head < 0) return shim(port) + out;
  const end = out.indexOf('>', head) + 1;
  return out.slice(0, end) + shim(port) + out.slice(end);
}

const escHtml = (v: unknown) => String(v ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c] as string));
const ICONS: Record<string, string> = {
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  plug: '<path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0z"/><path d="M12 18v4"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
};
const icon = (n: string, size = 22) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[n]}</svg>`;
const PAGE_CSS = `:root{color-scheme:light dark;--bg:#f6f7fb;--card:#fff;--fg:#14162b;--muted:#5d6280;--line:#e3e5ef;--chip:#eef0f7;--accent:#6d5df6}
@media (prefers-color-scheme:dark){:root{--bg:#0d0f1c;--card:#151829;--fg:#e8eaf6;--muted:#9aa0bf;--line:#262a42;--chip:#1e2238;--accent:#a78bfa}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}
.wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px 16px}
.card{width:100%;max-width:520px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:28px 26px}
.ic{width:46px;height:46px;border-radius:12px;display:grid;place-items:center;color:#fff;background:linear-gradient(135deg,#a78bfa,#60a5fa 60%,#22d3ee);margin-bottom:14px}
h1{font-size:18px;margin:0 0 6px}p{margin:0 0 10px;color:var(--muted)}
code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--chip);border-radius:6px;padding:2px 6px;color:var(--fg);word-break:break-all}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}.chips a{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;text-decoration:none;color:var(--fg);background:var(--chip);border:1px solid var(--line);border-radius:999px;padding:3px 11px}
.chips a:hover,.row:hover{border-color:var(--accent)}a{color:var(--accent)}
.list{max-width:860px;margin:0 auto;padding:20px 16px}.crumbs{font:13px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted);margin:0 0 12px;word-break:break-all}
.crumbs a{text-decoration:none}.rows{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.row{display:flex;align-items:center;gap:10px;padding:9px 14px;border-bottom:1px solid var(--line);text-decoration:none;color:var(--fg);border-left:2px solid transparent}
.row:last-child{border-bottom:0}.row .n{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.row .m{color:var(--muted);font-size:12px;white-space:nowrap}
.row svg{color:var(--muted);flex:none}.row.d svg{color:var(--accent)}.empty{padding:28px;text-align:center;color:var(--muted)}
@media (max-width:560px){.row .m.t{display:none}}`;
const page = (title: string, body: string) =>
  `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escHtml(title)}</title><style>${PAGE_CSS}</style></head><body>${body}</body></html>`;
function sendCard(res: express.Response, status: number, ic: string, title: string, html: string) {
  res.status(status).type('html').send(page(title, `<div class="wrap"><div class="card"><div class="ic">${icon(ic)}</div><h1>${escHtml(title)}</h1>${html}</div></div>`));
}
const portChips = () => {
  const own = [...(ownPorts() || [])].filter((p) => p !== Number(process.env.SERVER_PORT)).sort((a, b) => a - b);
  return own.length ? `<p style="margin-top:14px">Running now under your account:</p><div class="chips">${own.map((p) => `<a href="/preview/${p}/">localhost:${p}</a>`).join('')}</div>` : '';
};

paasPreview.use((req, res, next) => {
  if (valid(req)) return next();
  sendCard(res, 401, 'lock', 'Signed out', '<p>Your sign-in ended (it lasts 12 hours). Reload the web UI, sign in, and open this page again.</p>');
});

paasPreview.get('/_open', (_req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  try { res.json(JSON.parse(fs.readFileSync(OPEN_FILE, 'utf8'))); } catch { res.json({}); }
});

// this account's listening ports (the Browser tab's shortcuts), without the UI's own
paasPreview.get('/_ports', (_req, res) => {
  const own = ownPorts();
  res.json({ ports: own ? [...own].filter((p) => p !== Number(process.env.SERVER_PORT)).sort((a, b) => a - b) : [] });
});

// files under the home folder; no hidden files or folders (~/.claude, ~/.ssh)
paasPreview.get(/^\/~(\/.*)?$/, (req, res) => {
  const home = fs.realpathSync(os.homedir());
  const rel = decodeURIComponent(req.params[0] || '/');
  let file: string;
  const shown = `~${path.posix.normalize(rel.replace(/\\/g, '/'))}`;
  try { file = fs.realpathSync(path.join(home, rel)); } catch {
    const up = path.posix.dirname(path.posix.normalize(`/${rel}`));
    sendCard(res, 404, 'search', 'Not found', `<p>There is no file or folder <code>${escHtml(shown)}</code>.</p>
      <p>Check the name, or open <a href="/preview/~${encodeURI(up === '/' ? '/' : `${up}/`)}">~${escHtml(up === '/' ? '/' : `${up}/`)}</a> to pick it from the list.</p>`);
    return;
  }
  if ((file !== home && !file.startsWith(home + path.sep)) || path.relative(home, file).split(path.sep).some((s) => s.startsWith('.'))) {
    sendCard(res, 403, 'shield', 'Not shown here', `<p><code>${escHtml(shown)}</code> is hidden or outside your home folder.</p>
      <p>The Browser tab shows files under your home folder only, and never hidden ones such as <code>~/.ssh</code> or <code>~/.claude</code>.</p>`);
    return;
  }
  if (fs.statSync(file).isDirectory()) {
    const relDir = path.relative(home, file).split(path.sep).filter(Boolean);
    const here = `/preview/~/${relDir.map(encodeURIComponent).join('/')}`.replace(/\/?$/, '/');
    const items = fs.readdirSync(file).filter((n) => !n.startsWith('.')).map((n) => {
      try { const st = fs.statSync(path.join(file, n)); return { n, dir: st.isDirectory(), size: st.size, mtime: st.mtimeMs }; } catch { return null; }
    }).filter(Boolean) as { n: string; dir: boolean; size: number; mtime: number }[];
    items.sort((a, b) => Number(b.dir) - Number(a.dir) || a.n.localeCompare(b.n));
    const size = (b: number) => (b >= 1048576 ? `${(b / 1048576).toFixed(1)} MB` : b >= 1024 ? `${Math.round(b / 1024)} KB` : `${b} B`);
    const when = (ms: number) => new Date(ms).toLocaleString('sv-SE').slice(0, 16);   // the VM's local time, 2026-10-28 14:05
    const crumbs = [`<a href="/preview/~/">~</a>`, ...relDir.map((s, i) =>
      `<a href="/preview/~/${relDir.slice(0, i + 1).map(encodeURIComponent).join('/')}/">${escHtml(s)}</a>`)].join(' / ');
    const rows = items.map((it) => `<a class="row${it.dir ? ' d' : ''}" href="${here}${encodeURIComponent(it.n)}${it.dir ? '/' : ''}">${icon(it.dir ? 'folder' : 'file', 18)}
      <span class="n">${escHtml(it.n)}</span><span class="m">${it.dir ? '' : size(it.size)}</span><span class="m t">${when(it.mtime)}</span></a>`).join('');
    res.type('html').send(page(`~/${relDir.join('/')}`, `<div class="list"><div class="crumbs">${crumbs} /</div>
      <div class="rows">${rows || '<div class="empty">This folder is empty</div>'}</div></div>`));
    return;
  }
  res.sendFile(file, { dotfiles: 'allow' });
});

paasPreview.all(/^\/(\d{1,5})(\/.*)?$/, (req, res) => {
  const port = Number(req.params[0]);
  if (!req.params[1]) { res.redirect(`/preview/${port}/${req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : ''}`); return; }
  const own = ownPorts();
  if (port < 1 || port > 65535 || port === Number(process.env.SERVER_PORT) || (own && !own.has(port))) {
    const self = port === Number(process.env.SERVER_PORT);
    sendCard(res, 403, 'plug', self ? 'That is this web UI' : `Nothing of yours on port ${port}`, self
      ? '<p>This port is the web UI itself, so it cannot be shown inside it.</p>'
      : `<p>The Browser tab shows web apps that <b>your account</b> runs on this VM (other people's apps and system services stay hidden).</p>
         <p>Start yours, for example <code>uvicorn main:app --port ${port}</code>, then press reload.</p>${portChips()}`);
    return;
  }
  const base = `/preview/${port}`;
  const headers: http.OutgoingHttpHeaders = { ...req.headers, host: `127.0.0.1:${port}`, 'accept-encoding': 'identity',
    'x-forwarded-prefix': base };
  const cookies = (req.headers.cookie || '').split(/;\s*/).filter((c) => c && !c.startsWith('paas_'));
  if (cookies.length) headers.cookie = cookies.join('; '); else delete headers.cookie;
  delete headers.authorization;
  const up = http.request({ host: '127.0.0.1', port, method: req.method, path: req.url.slice(`/${port}`.length) || '/', headers }, (ur) => {
    const h = { ...ur.headers };
    delete h['x-frame-options'];
    delete h['content-security-policy'];
    if (h.location) h.location = h.location.replace(LOCAL, (_m, p, rest) => `/preview/${p || 80}${rest || '/'}`).replace(/^\/(?!\/|preview\/)/, `${base}/`);
    if (h['set-cookie']) h['set-cookie'] = h['set-cookie'].map((c) => (/;\s*path=/i.test(c)
      ? c.replace(/(;\s*path=)\/?/i, `$1${base}/`) : `${c}; Path=${base}/`));
    if (!/text\/html/i.test(String(h['content-type'] || ''))) {
      res.writeHead(ur.statusCode || 502, h);
      ur.pipe(res);
      return;
    }
    const parts: Buffer[] = [];
    ur.on('data', (d) => parts.push(d));
    ur.on('end', () => {
      const body = rewriteHtml(Buffer.concat(parts).toString('utf8'), port);
      delete h['content-length'];
      delete h['transfer-encoding'];
      res.writeHead(ur.statusCode || 502, h);
      res.end(body);
    });
  });
  up.on('error', () => {
    if (!res.headersSent) sendCard(res, 502, 'plug', `Port ${port} is not answering`, `<p>The app on port ${port} closed the connection or is still starting.</p>
      <p>Check its terminal for errors, then press reload.</p>${portChips()}`);
    else res.destroy();
  });
  req.pipe(up);
});
