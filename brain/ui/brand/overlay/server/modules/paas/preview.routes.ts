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

paasPreview.use((req, res, next) => {
  if (valid(req)) return next();
  res.status(401).type('html').send('<p style="font:14px system-ui;padding:24px">Signed out: reload the page and open this again.</p>');
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
  try { file = fs.realpathSync(path.join(home, rel)); } catch { res.status(404).send('Not found'); return; }
  if (!file.startsWith(home + path.sep) || path.relative(home, file).split(path.sep).some((s) => s.startsWith('.'))) {
    res.status(403).send('Only files under the home folder (not hidden ones)');
    return;
  }
  if (fs.statSync(file).isDirectory()) {
    const items = fs.readdirSync(file).filter((n) => !n.startsWith('.')).sort();
    const here = `/preview/~/${path.relative(home, file)}`.replace(/\/?$/, '/');
    res.type('html').send(`<pre style="font:13px/1.6 ui-monospace,monospace;padding:16px">${items
      .map((n) => `<a href="${encodeURI(here + n)}">${n.replace(/[<>&]/g, '')}</a>`).join('\n')}</pre>`);
    return;
  }
  res.sendFile(file, { dotfiles: 'allow' });
});

paasPreview.all(/^\/(\d{1,5})(\/.*)?$/, (req, res) => {
  const port = Number(req.params[0]);
  if (!req.params[1]) { res.redirect(`/preview/${port}/${req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : ''}`); return; }
  const own = ownPorts();
  if (port < 1 || port > 65535 || port === Number(process.env.SERVER_PORT) || (own && !own.has(port))) {
    res.status(403).type('html').send(`<p style="font:14px system-ui;padding:24px">Port ${port}: nothing of yours listens there.
      Only web apps started by this account can be shown (start it, e.g. <code>uvicorn app:app --port ${port}</code>).</p>`);
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
    if (!res.headersSent) res.status(502).type('html').send(`<p style="font:14px system-ui;padding:24px">Nothing answers on port ${port}.</p>`);
    else res.destroy();
  });
  req.pipe(up);
});
