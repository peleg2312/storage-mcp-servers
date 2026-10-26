// Reports backend: the files Claude saved in ~/storage-reports (report-export skill). Read-only, local; paths are
// confined to that folder (symlinks resolved), files over 25 MB are listed but not sent.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.env.PAAS_REPORTS_DIR || path.join(process.env.HOME || '', 'storage-reports');
const MAX = 25 * 1024 * 1024;
const TEXT = /\.(csv|tsv|md|txt|log|json|ya?ml|html?|xml|svg|sh|py|tf)$/i;

function list(dir = ROOT, depth = 0, out = []) {
  let entries = [];
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    if (e.name.startsWith('.')) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory() && depth < 3) list(p, depth + 1, out);
    else if (e.isFile()) {
      const st = fs.statSync(p);
      out.push({ path: path.relative(ROOT, p), size: st.size, mtime: st.mtimeMs });
    }
  }
  return out;
}

// the file under ROOT named by rel, or null (outside ROOT, missing, not a file)
function resolveReport(rel, root = ROOT) {
  let file, base;
  try { base = fs.realpathSync(root); file = fs.realpathSync(path.resolve(base, String(rel || ''))); } catch { return null; }
  if (!file.startsWith(base + path.sep) || !fs.statSync(file).isFile()) return null;
  return file;
}

function send(res, code, body) { res.writeHead(code); res.end(JSON.stringify(body)); }

const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  const url = new URL(req.url, 'http://x');
  if (req.method !== 'GET') return send(res, 405, { error: 'read-only' });
  if (url.pathname === '/list') {
    return send(res, 200, { root: ROOT, exists: fs.existsSync(ROOT), files: list().sort((a, b) => b.mtime - a.mtime) });
  }
  if (url.pathname === '/file') {
    const file = resolveReport(url.searchParams.get('path'));
    if (!file) return send(res, 404, { error: 'not found in ~/storage-reports' });
    const size = fs.statSync(file).size;
    if (size > MAX) return send(res, 413, { error: 'file over 25 MB: copy it with scp' });
    const text = TEXT.test(file);
    const data = fs.readFileSync(file);
    return send(res, 200, { name: path.basename(file), size, encoding: text ? 'utf8' : 'base64',
      data: text ? data.toString('utf8') : data.toString('base64') });
  }
  send(res, 404, { error: 'not found' });
});
server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ ready: true, port: server.address().port })));
