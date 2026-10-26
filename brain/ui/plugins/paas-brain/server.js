// Brain backend: the docs library (search, add by url / upload via add-docs), skills, agents, hooks, MCP servers
// and memory files of this VM's Claude Code. Local only; reachable through the UI's signed-in plugin proxy.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';

const HOME = process.env.HOME || '';
const C = path.join(HOME, '.claude');
const LIB = path.join(C, 'brain', 'library');
const INBOX = path.join(C, 'brain', 'inbox');
const ADD_DOCS = path.join(HOME, '.local', 'bin', 'add-docs');
const DEST = /^[a-z0-9][\w.-]{0,40}\/[\w.-]{1,60}$/i;      // <vendor>/<product>
const SKILL_NAME = /^[a-z0-9][a-z0-9-]{1,40}$/;
// memory files the user edits here: kept by install.sh; CLAUDE.md is shown only (install.sh rewrites it)
const MEMORY = {
  'notes.md': path.join(C, 'brain', 'notes.md'), 'environment.md': path.join(C, 'brain', 'environment.md'),
  'tool-map.md': path.join(C, 'brain', 'tool-map.md'), 'CLAUDE.md': path.join(C, 'CLAUDE.md'),
};
const writable = (p) => { try { fs.accessSync(p, fs.constants.W_OK); return true; } catch { return false; } };
const oneLine = (v, max) => String(v || '').replace(/\s+/g, ' ').trim().slice(0, max);

const read = (p, max = 200000) => { try { return fs.readFileSync(p, 'utf8').slice(0, max); } catch { return null; } };
const json = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; } };
const run = (cmd, args, timeout = 120000) => new Promise((resolve) => {
  execFile(cmd, args, { timeout, maxBuffer: 20 * 1024 * 1024, env: { ...process.env, PATH: `${HOME}/.local/bin:${process.env.PATH}` } },
    (err, stdout, stderr) => resolve({ ok: !err, out: `${stdout}${stderr}`.trim() }));
});

function frontmatter(text) {
  const m = /^---\n([\s\S]*?)\n---/.exec(text || '');
  const out = {};
  for (const line of (m ? m[1] : '').split('\n')) {
    const kv = /^([\w-]+):\s*(.*)$/.exec(line);
    if (!kv) continue;
    let v = kv[2];
    if (/^".*"$/.test(v)) { try { v = JSON.parse(v); } catch { v = v.slice(1, -1); } } else v = v.replace(/^'|'$/g, '');
    out[kv[1]] = v;
  }
  return out;
}

function skills() {
  const dir = path.join(C, 'skills');
  let names = [];
  try { names = fs.readdirSync(dir); } catch { return []; }
  return names.map((n) => {
    const text = read(path.join(dir, n, 'SKILL.md'), 60000) || '';
    const f = frontmatter(text);
    const mine = fs.existsSync(path.join(dir, n, '.user-skill'));
    return { dir: n, name: f.name || n, description: f.description || '', when: f.when_to_use || '', mine,
      body: mine ? text.replace(/^---\n[\s\S]*?\n---\n?/, '').trim() : undefined };
  }).filter((s) => s.description).sort((a, b) => a.name.localeCompare(b.name));
}

function agents() {
  const dir = path.join(C, 'agents');
  let names = [];
  try { names = fs.readdirSync(dir).filter((n) => n.endsWith('.md')); } catch { return []; }
  return names.map((n) => {
    const f = frontmatter(read(path.join(dir, n), 4000));
    const file = n.replace(/\.md$/, '');
    return { file, mine: isMine('agent', file), name: f.name || file, description: f.description || '', tools: f.tools || f.disallowedTools ? `${f.tools ? `tools: ${f.tools}` : `not: ${f.disallowedTools}`}` : 'all tools', model: f.model || '' };
  });
}

// the file behind a skill or agent name (null for anything else)
function defFile(kind, name) {
  if (!SKILL_NAME.test(String(name || ''))) return null;
  if (kind === 'skill') return path.join(C, 'skills', name, 'SKILL.md');
  if (kind === 'agent') return path.join(C, 'agents', `${name}.md`);
  return null;
}
// yours = made in the web UI (skills: a .user-skill file; agents: a line in agents/.user-agents); install.sh only
// rewrites the brain's own skills and agents, never these
const USER_AGENTS = path.join(C, 'agents', '.user-agents');
function isMine(kind, name) {
  if (kind === 'skill') return fs.existsSync(path.join(C, 'skills', String(name), '.user-skill'));
  return (read(USER_AGENTS) || '').split('\n').includes(String(name));
}
function markMine(kind, name) {
  if (kind === 'skill') fs.writeFileSync(path.join(C, 'skills', name, '.user-skill'), 'created in the web UI\n');
  else if (!isMine('agent', name)) fs.appendFileSync(USER_AGENTS, `${name}\n`);
}

function hooks() {
  const s = json(path.join(C, 'settings.json')) || {};
  const out = [];
  for (const [event, groups] of Object.entries(s.hooks || {})) {
    for (const g of groups || []) {
      for (const h of g.hooks || []) out.push({ event, matcher: g.matcher || '*', command: String(h.command || '').replace(HOME, '~') });
    }
  }
  return out;
}

function mcpServers() {
  const cfg = json(path.join(HOME, '.claude.json')) || {};
  return Object.entries(cfg.mcpServers || {}).map(([name, s]) => ({
    name, type: s.type || (s.url ? 'http' : 'stdio'),
    target: s.url || [s.command, ...(s.args || [])].join(' ').replace(new RegExp(HOME, 'g'), '~'),
  }));
}

function inbox() {
  const out = [];
  (function walk(d) {
    let entries = [];
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name !== 'manifest.json' && !e.name.startsWith('.')) {
        const st = fs.statSync(p);
        out.push({ path: path.relative(INBOX, p), size: st.size, mtime: st.mtimeMs });
      }
    }
  })(INBOX);
  return out.sort((a, b) => b.mtime - a.mtime).slice(0, 200);
}

async function overview() {
  const src = await run('python3', [path.join(LIB, 'search.py'), 'sources'], 60000);
  return {
    library: { version: read(path.join(LIB, 'VERSION'))?.trim() || null, sources: src.ok ? src.out : null },
    skills: skills(), agents: agents(), hooks: hooks(), mcp: mcpServers(), inbox: inbox(),
    // multi-user VM: environment.md / tool-map.md are shared and only root writes them; the library too
    memory: [['notes.md', true], ['environment.md', true], ['tool-map.md', true], ['CLAUDE.md', false]]
      .map(([name, editable]) => ({ name, editable: editable && writable(MEMORY[name]), text: read(MEMORY[name]) })).filter((m) => m.text !== null),
    canAddDocs: writable(LIB),
  };
}

function body(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (c) => { size += c.length; if (size > 52 * 1024 * 1024) { reject(new Error('too large')); req.destroy(); } else chunks.push(c); });
    req.on('end', () => { try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')); } catch (e) { reject(e); } });
  });
}

const routes = {
  'GET /overview': () => overview(),
  'GET /search': async (q) => {
    const query = (q.get('q') || '').slice(0, 300);
    if (!query.trim()) return { results: [] };
    const args = [path.join(LIB, 'search.py'), '--json', 'search', query, '--limit', '15'];
    if (/^[\w.-]{1,40}$/.test(q.get('vendor') || '')) args.push('--vendor', q.get('vendor'));
    const r = await run('python3', args, 60000);
    try { return JSON.parse(r.out); } catch { return { error: r.out.slice(0, 2000) }; }
  },
  'POST /add-url': async (_q, b) => {
    const urls = String(b.urls || '').split(/\s+/).filter((u) => /^https?:\/\/\S+$/.test(u)).slice(0, 20);
    if (!urls.length) return { ok: false, out: 'Give one or more http(s) urls' };
    const args = [...urls];
    if (b.to) { if (!DEST.test(b.to)) return { ok: false, out: 'Folder: <vendor>/<product>, e.g. cisco/mds' }; args.push('--to', b.to); }
    return run(ADD_DOCS, args, 600000);
  },
  'POST /upload': async (_q, b) => {
    const name = path.basename(String(b.name || '')).replace(/[^\w.-]+/g, '-');
    if (!/\.(pdf|html?|md|markdown|txt|adoc|rst)$/i.test(name)) return { ok: false, out: 'PDF, HTML, Markdown or text files only' };
    const to = b.to && DEST.test(b.to) ? b.to : 'local/uploads';
    const dir = path.join(INBOX, ...to.split('/'));
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, name), Buffer.from(String(b.data || ''), 'base64'));
    return { ok: true, saved: `${to}/${name}` };
  },
  'POST /index': () => run(ADD_DOCS, [], 600000),
  'POST /memory': async (_q, b) => {
    if (!['notes.md', 'environment.md', 'tool-map.md'].includes(b.name)) return { ok: false, out: 'That file is not editable here' };
    if (!writable(MEMORY[b.name])) return { ok: false, out: 'Shared file: only root changes it' };
    const text = String(b.text ?? '');
    if (text.length > 500000) return { ok: false, out: 'Too long' };
    const p = MEMORY[b.name];
    if (fs.existsSync(p)) fs.copyFileSync(p, `${p}.bak`);            // one step back, next to the file
    fs.writeFileSync(p, text.endsWith('\n') ? text : `${text}\n`);
    return { ok: true };
  },
  // your own skills (marked .user-skill; install.sh never touches them): create / update / delete
  'POST /skill': async (_q, b) => {
    const name = String(b.name || '').trim();
    const description = oneLine(b.description, 1000);
    if (!SKILL_NAME.test(name)) return { ok: false, out: 'Name: lower-case letters, digits and dashes, e.g. vm-patching' };
    if (!description) return { ok: false, out: 'A description is needed: it is how Claude knows when to use the skill' };
    const dir = path.join(C, 'skills', name);
    if (fs.existsSync(dir) && !fs.existsSync(path.join(dir, '.user-skill'))) return { ok: false, out: `"${name}" is a built-in skill` };
    fs.mkdirSync(dir, { recursive: true });
    const when = oneLine(b.when, 600);
    // JSON strings are valid YAML: a colon or quotes in the text cannot break the header
    fs.writeFileSync(path.join(dir, 'SKILL.md'), `---\nname: ${name}\ndescription: ${JSON.stringify(description)}\n`
      + `${when ? `when_to_use: ${JSON.stringify(when)}\n` : ''}---\n${String(b.body || '').trim()}\n`);
    fs.writeFileSync(path.join(dir, '.user-skill'), 'created in the web UI\n');
    return { ok: true };
  },
  'POST /skill-delete': async (_q, b) => {
    const dir = path.join(C, 'skills', String(b.name || ''));
    if (!SKILL_NAME.test(String(b.name || '')) || !fs.existsSync(path.join(dir, '.user-skill'))) return { ok: false, out: 'Only your own skills can be deleted' };
    fs.rmSync(dir, { recursive: true, force: true });
    return { ok: true };
  },
  // edit any skill or agent as its whole file (header + instructions). Built-in ones: brain/install.sh puts the
  // original back when re-run; the previous version is kept as <file>.bak
  'GET /file': async (q) => {
    const p = defFile(q.get('kind'), q.get('name'));
    if (!p) return { ok: false, out: 'Unknown skill or agent' };
    return { ok: true, text: read(p) ?? '', builtin: !isMine(q.get('kind'), q.get('name')) };
  },
  'POST /file': async (_q, b) => {
    const p = defFile(b.kind, b.name);
    if (!p) return { ok: false, out: 'Name: lower-case letters, digits and dashes, e.g. vm-patching' };
    const text = String(b.text ?? '');
    const f = frontmatter(text);
    if (!f.name || !f.description) return { ok: false, out: 'The file must start with a --- header holding name: and description:' };
    if (text.length > 300000) return { ok: false, out: 'Too long' };
    const isNew = !fs.existsSync(p);
    if (isNew && !b.create) return { ok: false, out: 'Not found' };
    if (!isNew && b.create) return { ok: false, out: `"${b.name}" already exists` };
    fs.mkdirSync(path.dirname(p), { recursive: true });
    if (!isNew) fs.copyFileSync(p, `${p}.bak`);
    fs.writeFileSync(p, text.endsWith('\n') ? text : `${text}\n`);
    if (isNew) markMine(b.kind, b.name);
    return { ok: true };
  },
  'POST /agent-delete': async (_q, b) => {
    const p = defFile('agent', b.name);
    if (!p || !isMine('agent', b.name)) return { ok: false, out: 'Only your own agents can be deleted' };
    fs.rmSync(p, { force: true });
    return { ok: true };
  },
  'GET /mcp-status': () => run('claude', ['mcp', 'list'], 90000),
};

const server = http.createServer(async (req, res) => {
  // only this user's UI may call (it sends the key it gave this process; other users on the VM cannot read it)
  if (process.env.PAAS_PLUGIN_KEY && req.headers['x-paas-key'] !== process.env.PAAS_PLUGIN_KEY) { res.writeHead(403); res.end('{"error":"forbidden"}'); return; }
  res.setHeader('Content-Type', 'application/json');
  const url = new URL(req.url, 'http://x');
  const fn = routes[`${req.method} ${url.pathname}`];
  if (!fn) { res.writeHead(404); res.end('{"error":"not found"}'); return; }
  try {
    const b = req.method === 'POST' ? await body(req) : {};
    res.end(JSON.stringify(await fn(url.searchParams, b)));
  } catch (e) {
    res.writeHead(500); res.end(JSON.stringify({ error: String(e.message || e) }));
  }
});
server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ ready: true, port: server.address().port })));
