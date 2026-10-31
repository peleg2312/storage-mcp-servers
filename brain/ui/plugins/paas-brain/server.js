// Brain backend: the docs library (search, add by url / upload via add-docs), skills, agents, hooks, MCP servers
// and memory files of this VM's Claude Code. Local only; reachable through the UI's signed-in plugin proxy.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
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
const CAPTURES = path.join(C, 'brain', 'captures');
const CAPTURE = /^captures\/([\w][\w.-]{0,100}\.md)$/;     // a file directly in captures/, never a deeper path
const BRAIN = path.join(C, 'brain');
const MULTI = fs.existsSync('/opt/paas/marketplace');
const writable = (p) => { try { fs.accessSync(p, fs.constants.W_OK); return true; } catch { return false; } };
const MARKET = process.env.PAAS_MARKET || '/opt/paas/marketplace';
const ME = os.userInfo().username;
const MINE = path.join(MARKET, 'contrib', ME);
const MARKET_BIN = ['/opt/paas/bin/paas-market', '/usr/local/bin/paas-market'].find((p) => fs.existsSync(p));
const sharedNow = (kind, name) => fs.existsSync(path.join(MINE, `${kind}s`, kind === 'agent' ? `${name}.md` : name));
const oneLine = (v, max) => String(v || '').replace(/\s+/g, ' ').trim().slice(0, max);

const read = (p, max = 200000) => { try { return fs.readFileSync(p, 'utf8').slice(0, max); } catch { return null; } };
const json = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; } };
const run = (cmd, args, timeout = 120000) => new Promise((resolve) => {
  execFile(cmd, args, { timeout, maxBuffer: 20 * 1024 * 1024, env: { ...process.env, PATH: `${HOME}/.local/bin:${process.env.PATH}` } },
    (err, stdout, stderr) => resolve({ ok: !err, out: `${stdout}${stderr}`.trim() }));
});

// history of the memory files: ~/.claude/brain (or the active team's repository inside it) may be a git repository;
// never blocks a save. The repository is looked up per call: the team can change while the UI runs.
const TEAM_NAME = /^[a-z][a-z0-9_-]{0,31}$/;
const TEAM_BIN = [path.join(HOME, '.claude', 'tools', 'paas-team'), '/opt/paas/bin/paas-team', path.join(HOME, '.local', 'bin', 'paas-team')].find((p) => fs.existsSync(p));
function repoDir() {
  const team = (read(path.join(BRAIN, 'team'), 200) || '').trim();
  if (TEAM_NAME.test(team)) {
    const d = path.join(BRAIN, 'teams', team);
    if (fs.existsSync(path.join(d, '.git'))) return d;
  }
  return fs.existsSync(path.join(BRAIN, '.git')) ? BRAIN : null;
}
const git = (repo, args) => run('git', ['-C', repo, '-c', 'user.name=brain', '-c', 'user.email=brain@localhost', ...args], 5000);
// the repository holding file p and p's path inside it (null: no repository, or p lies outside it).
// Memory files are symlinks into a team repository, so compare real paths; a deleted file keeps its real directory.
function locate(p) {
  const repo = repoDir();
  if (!repo) return { repo: null, rel: null };
  if (repo === BRAIN) { const rel = path.relative(BRAIN, p); return { repo, rel: rel.startsWith('..') ? null : rel }; }
  try {
    let real;
    try { real = fs.realpathSync(p); } catch { real = path.join(fs.realpathSync(path.dirname(p)), path.basename(p)); }
    const rel = path.relative(fs.realpathSync(repo), real);
    return { repo, rel: rel.startsWith('..') || path.isAbsolute(rel) ? null : rel };
  } catch { return { repo, rel: null }; }
}
const commitFile = async (p, msg) => {
  const { repo, rel } = locate(p);
  if (!repo || !rel) return;
  await git(repo, ['add', '-A', '--', rel]);
  await git(repo, ['commit', '-q', '-m', msg]);
  // a repository with an upstream: the knowledge leaves the VM after every save; a failure is ignored, the next sync retries
  const up = await git(repo, ['rev-parse', '--abbrev-ref', '@{upstream}']);
  if (up.ok) await run('git', ['-C', repo, 'push', '-q'], 10000);
};
// A team skill or agent edited here changes for the whole team: the file goes into the team's repository too
// (its plugin folder), committed and pushed; teammates pick it up at their next sync. Returns the team name, or null.
async function teamWriteBack(kind, name, file) {
  const repo = repoDir();
  const team = (read(path.join(BRAIN, 'team'), 200) || '').trim();
  if (!repo || repo === BRAIN || !TEAM_NAME.test(team)) return null;
  const put = json(path.join(BRAIN, 'teams', '.installed.json')) || {};
  const list = kind === 'skill' ? put.skills : put.agents;
  if (!Array.isArray(list) || !list.includes(name)) return null;        // the person's own or a marketplace item: theirs alone
  const dst = kind === 'skill' ? path.join(repo, `paas-brain-${team}`, 'skills', name, 'SKILL.md') : path.join(repo, `paas-brain-${team}`, 'agents', `${name}.md`);
  if (!fs.existsSync(path.dirname(dst))) return null;
  fs.copyFileSync(file, dst);
  await teamCommit(repo, team, kind, name);
  return team;
}
// bump the plugin version (plugin-mode members get the copy), commit the plugin folder, push when there is an upstream
async function teamCommit(repo, team, kind, name) {
  if (TEAM_BIN) await run('python3', [TEAM_BIN, 'bump', team], 20000);
  await git(repo, ['add', '-A', '--', `paas-brain-${team}`]);
  await git(repo, ['commit', '-q', '-m', `brain tab: team ${kind} ${name}`]);
  const up = await git(repo, ['rev-parse', '--abbrev-ref', '@{upstream}']);
  if (up.ok) await run('git', ['-C', repo, 'push', '-q'], 10000);
}
// plugin mode: the active team's skills and agents are read in place from the clone, not copied into ~/.claude.
// "claude" on PATH is looked up once at startup; the team and its mode are read per call (they can change while the UI runs).
const HAS_CLAUDE = [...(process.env.PATH || '').split(path.delimiter), path.join(HOME, '.local', 'bin'), '/usr/local/bin', '/usr/bin']
  .some((d) => d && fs.existsSync(path.join(d, 'claude')));
function pluginTeam() {
  const team = (read(path.join(BRAIN, 'team'), 200) || '').trim();
  if (!TEAM_NAME.test(team)) return null;
  const mode = (read(path.join(BRAIN, 'team-mode'), 50) || '').trim();
  if (!(mode === 'plugin' || (!mode && HAS_CLAUDE))) return null;
  const dir = path.join(BRAIN, 'teams', team, `paas-brain-${team}`);
  return fs.existsSync(dir) ? { team, dir } : null;
}
// the clone's file for a team skill or agent (null: no plugin mode, bad name, or not in the team)
function teamFile(kind, name) {
  const t = pluginTeam();
  if (!t || !SKILL_NAME.test(String(name || ''))) return null;
  const f = kind === 'skill' ? path.join(t.dir, 'skills', name, 'SKILL.md') : kind === 'agent' ? path.join(t.dir, 'agents', `${name}.md`) : null;
  return f && fs.existsSync(f) ? { ...t, file: f } : null;
}
// the file behind a memory name or captures/<file>, and its repository and path inside it (null: outside it)
function memPath(name) {
  const cap = CAPTURE.exec(String(name || ''));
  const p = cap ? path.join(CAPTURES, cap[1]) : Object.hasOwn(MEMORY, name) ? MEMORY[name] : null;
  if (!p) return null;
  return { p, ...locate(p), cap: !!cap };
}

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

// where a skill or agent came from: yours, the marketplace, the active team, else the brain itself
const INSTALLED_TEAM = path.join(BRAIN, 'teams', '.installed.json');
function sourceOf(kind, id, mine) {
  if (mine) return 'mine';
  if ((json(path.join(C, 'paas-market.json')) || {}).installed?.[`${kind}/${id}`] !== undefined) return 'market';
  const list = (json(INSTALLED_TEAM) || {})[`${kind}s`];
  if (Array.isArray(list) && (list.includes(id) || list.includes(`${id}.md`))) return 'team';
  return 'brain';
}

function skills() {
  const dir = path.join(C, 'skills');
  let names = [];
  try { names = fs.readdirSync(dir); } catch { /* none of your own */ }
  const out = names.map((n) => {
    const text = read(path.join(dir, n, 'SKILL.md'), 60000) || '';
    const f = frontmatter(text);
    const mine = fs.existsSync(path.join(dir, n, '.user-skill'));
    return { dir: n, shared: sharedNow('skill', n), name: f.name || n, description: f.description || '', when: f.when_to_use || '', mine, source: sourceOf('skill', n, mine),
      body: mine ? text.replace(/^---\n[\s\S]*?\n---\n?/, '').trim() : undefined };
  }).filter((s) => s.description);
  const t = pluginTeam();                                    // plugin mode: the team's own skills, once per name
  if (t) {
    let tn = [];
    try { tn = fs.readdirSync(path.join(t.dir, 'skills')); } catch { /* no skills */ }
    for (const n of tn) {
      if (!SKILL_NAME.test(n) || names.includes(n)) continue;
      const teamPath = path.join(t.dir, 'skills', n, 'SKILL.md');
      const f = frontmatter(read(teamPath, 60000));
      if (f.description) out.push({ dir: n, shared: false, name: f.name || n, description: f.description, when: f.when_to_use || '', mine: false, source: 'team', teamPath });
    }
  }
  return out.sort((a, b) => a.name.localeCompare(b.name));
}

function agents() {
  const dir = path.join(C, 'agents');
  let names = [];
  try { names = fs.readdirSync(dir).filter((n) => n.endsWith('.md')); } catch { /* none of your own */ }
  const info = (f) => (f.tools || f.disallowedTools ? `${f.tools ? `tools: ${f.tools}` : `not: ${f.disallowedTools}`}` : 'all tools');
  const out = names.map((n) => {
    const f = frontmatter(read(path.join(dir, n), 4000));
    const file = n.replace(/\.md$/, '');
    return { file, mine: isMine('agent', file), source: sourceOf('agent', file, isMine('agent', file)), shared: sharedNow('agent', file), name: f.name || file, description: f.description || '', tools: info(f), model: f.model || '' };
  });
  const t = pluginTeam();                                    // plugin mode: the team's own agents, once per name
  if (t) {
    let tn = [];
    try { tn = fs.readdirSync(path.join(t.dir, 'agents')).filter((n) => n.endsWith('.md')); } catch { /* no agents */ }
    for (const n of tn) {
      const file = n.replace(/\.md$/, '');
      if (!SKILL_NAME.test(file) || names.includes(n)) continue;
      const teamPath = path.join(t.dir, 'agents', n);
      const f = frontmatter(read(teamPath, 4000));
      out.push({ file, mine: false, source: 'team', shared: false, name: f.name || file, description: f.description || '', tools: info(f), model: f.model || '', teamPath });
    }
  }
  return out;
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

// the brain's hooks, in plain words; the guard cannot be switched off, the helpers can (each person for themselves:
// a helper whose name is in ~/.claude/brain/hooks-off returns at once)
const HOOK_INFO = {
  'block-write-tools': ['Read-only guard', 'Blocks anything that would change storage, switches, UCS or VMware, and asks you before cluster changes, service restarts and database writes.', false],
  'docs-leads': ['Docs leads', 'Before each request, finds the docs that match your question and hands them to Claude.', true],
  'docs-hints': ['Docs hints', 'When a live result shows an alert, event or error code, adds what the docs say about it.', true],
  'py-lint': ['Python check', 'Checks every Python file Claude edits (ruff) and shows it the problems to fix.', true],
  'session-start': ['Chat start status', 'At the start of each chat, tells Claude what is available (docs library, guard, your notes).', true],
};
const HOOKS_OFF = path.join(C, 'brain', 'hooks-off');
const MANAGED = process.platform === 'darwin' ? '/Library/Application Support/ClaudeCode/managed-settings.json' : '/etc/claude-code/managed-settings.json';
const hooksOff = () => new Set((read(HOOKS_OFF) || '').split(/\s+/).filter(Boolean));
const WHEN = { PreToolUse: 'Before a tool runs', PostToolUse: 'After a tool runs', UserPromptSubmit: 'When you send a message', SessionStart: 'When a chat starts' };

function hooks() {
  const off = hooksOff();
  const out = [];
  for (const [source, file] of [['shared', MANAGED], ['yours', path.join(C, 'settings.json')]]) {
    const s = json(file) || {};
    for (const [event, groups] of Object.entries(s.hooks || {})) {
      for (const g of groups || []) {
        for (const h of g.hooks || []) {
          const command = String(h.command || '').replace(HOME, '~');
          const id = (/([\w-]+)\.py\b/.exec(command) || [])[1] || '';
          const [title, about, canToggle] = HOOK_INFO[id] || [command.length > 70 ? `${command.slice(0, 69)}…` : command, '', false];
          out.push({ id, title, about, canToggle, on: !off.has(id), source, when: WHEN[event] || event, matcher: g.matcher || '*', command });
        }
      }
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

// what Claude wrote down for later curation (brain-learn skill): newest first
function captures() {
  try {
    return fs.readdirSync(CAPTURES).filter((n) => CAPTURE.test(`captures/${n}`)).map((name) => {
      const p = path.join(CAPTURES, name);
      return { name, text: read(p) ?? '', mtime: fs.statSync(p).mtimeMs };
    }).sort((a, b) => b.mtime - a.mtime).slice(0, 50);
  } catch { return []; }
}

async function overview() {
  const src = await run('python3', [path.join(LIB, 'search.py'), 'sources'], 60000);
  return {
    library: { version: read(path.join(LIB, 'VERSION'))?.trim() || null, sources: src.ok ? src.out : null },
    pluginTeam: pluginTeam()?.team || null,
    skills: skills(), agents: agents(), hooks: hooks(), mcp: mcpServers(), inbox: inbox(), captures: captures(),
    // multi-user VM: environment.md / tool-map.md are shared and only root writes them; the library too
    // CLAUDE.md is this account's own copy of the brain's rules, yours to change (a brain update replaces it)
    memory: ['notes.md', 'environment.md', 'tool-map.md', 'CLAUDE.md']
      .map((name) => ({ name, editable: writable(MEMORY[name]) || (MULTI && name === 'CLAUDE.md'),
        text: read(MEMORY[name]) ?? (MULTI && name === 'CLAUDE.md' ? '' : null) })).filter((m) => m.text !== null),
    canShare: !!MARKET_BIN && writable(MINE),
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
    const cap = CAPTURE.exec(String(b.name || ''));
    if (cap) {                                                         // a capture: save, or discard with {remove:true}
      const p = path.join(CAPTURES, cap[1]);
      if (b.remove) { try { fs.unlinkSync(p); } catch { /* already gone */ } await commitFile(p, `brain tab: remove ${b.name}`); return { ok: true }; }
      const t = String(b.text ?? '');
      if (t.length > 500000) return { ok: false, out: 'Too long' };
      fs.mkdirSync(CAPTURES, { recursive: true });
      if (fs.existsSync(p)) fs.copyFileSync(p, `${p}.bak`);
      fs.writeFileSync(p, t.endsWith('\n') ? t : `${t}\n`);
      await commitFile(p, `brain tab: ${b.name}`);
      return { ok: true };
    }
    if (!Object.hasOwn(MEMORY, b.name)) return { ok: false, out: 'That file is not editable here' };
    if (fs.existsSync(MEMORY[b.name]) && !writable(MEMORY[b.name])) return { ok: false, out: 'Shared file: only root changes it' };
    const text = String(b.text ?? '');
    if (text.length > 500000) return { ok: false, out: 'Too long' };
    const p = MEMORY[b.name];
    if (fs.existsSync(p)) fs.copyFileSync(p, `${p}.bak`);            // one step back, next to the file
    fs.writeFileSync(p, text.endsWith('\n') ? text : `${text}\n`);
    await commitFile(p, `brain tab: ${b.name}`);
    return { ok: true };
  },
  'GET /history': async (q) => {
    const m = memPath(q.get('name'));
    if (!m || !m.rel || !m.repo) return { repo: false, entries: [] };
    const r = await git(m.repo, ['log', '--format=%h%x09%ct%x09%s', '-n', '25', '--', m.rel]);
    const entries = r.ok ? r.out.split('\n').filter(Boolean).map((l) => { const [sha, when, ...s] = l.split('\t'); return { sha, when: Number(when), subject: s.join('\t') }; }) : [];
    return { repo: true, entries };
  },
  'POST /restore': async (_q, b) => {
    const m = memPath(b.name);
    if (!m || !m.rel || !m.repo) return { ok: false, out: 'No history for that file' };
    if (!/^[0-9a-f]{7,40}$/.test(String(b.sha || ''))) return { ok: false, out: 'Bad version' };
    if (fs.existsSync(m.p) && !writable(m.p)) return { ok: false, out: 'Shared file: only root changes it' };
    const r = await git(m.repo, ['show', `${b.sha}:${m.rel.split(path.sep).join('/')}`]);
    if (!r.ok) return { ok: false, out: 'That version is not in the history' };
    if (fs.existsSync(m.p)) fs.copyFileSync(m.p, `${m.p}.bak`);
    fs.writeFileSync(m.p, r.out ? `${r.out}\n` : '');
    await commitFile(m.p, `brain tab: restore ${b.name} from ${b.sha}`);
    return { ok: true, text: read(m.p) ?? '' };
  },
  // your own skills (marked .user-skill; install.sh never touches them): create / update / delete
  'POST /skill': async (_q, b) => {
    const name = String(b.name || '').trim();
    const description = oneLine(b.description, 250);
    if (!SKILL_NAME.test(name)) return { ok: false, out: 'Name: lower-case letters, digits and dashes, e.g. vm-patching' };
    if (!description) return { ok: false, out: 'A description is needed: it is how Claude knows when to use the skill' };
    const dir = path.join(C, 'skills', name);
    if (fs.existsSync(dir) && !fs.existsSync(path.join(dir, '.user-skill'))) return { ok: false, out: `"${name}" is a built-in skill` };
    fs.mkdirSync(dir, { recursive: true });
    const when = oneLine(b.when, 200);
    // JSON strings are valid YAML: a colon or quotes in the text cannot break the header
    fs.writeFileSync(path.join(dir, 'SKILL.md'), `---\nname: ${name}\ndescription: ${JSON.stringify(description)}\n`
      + `${when ? `when_to_use: ${JSON.stringify(when)}\n` : ''}---\n${String(b.body || '').trim()}\n`);
    fs.writeFileSync(path.join(dir, '.user-skill'), 'created in the web UI\n');
    return { ok: true };
  },
  'POST /skill-delete': async (_q, b) => {
    if (teamFile('skill', b.name) && !fs.existsSync(path.join(C, 'skills', String(b.name), 'SKILL.md'))) return { ok: false, out: 'Team skills are removed in the team editor' };
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
    const tf = fs.existsSync(p) ? null : teamFile(q.get('kind'), q.get('name'));   // your ~/.claude copy wins
    if (tf) return { ok: true, text: read(tf.file) ?? '', builtin: false, team: tf.team };
    return { ok: true, text: read(p) ?? '', builtin: !isMine(q.get('kind'), q.get('name')) };
  },
  'POST /file': async (_q, b) => {
    const p = defFile(b.kind, b.name);
    if (!p) return { ok: false, out: 'Name: lower-case letters, digits and dashes, e.g. vm-patching' };
    const text = String(b.text ?? '');
    const f = frontmatter(text);
    if (!f.name || !f.description) return { ok: false, out: 'The file must start with a --- header holding name: and description:' };
    if ((f.description || '').length + (f.when_to_use || '').length > 450) return { ok: false, out: 'Keep the description under ~450 characters: it is shown to Claude on every turn; put details in the body.' };
    if (text.length > 300000) return { ok: false, out: 'Too long' };
    const tf = fs.existsSync(p) ? null : teamFile(b.kind, b.name);
    if (tf) {                                                          // plugin mode: write into the clone, push for the team
      if (b.create) return { ok: false, out: `"${b.name}" already exists` };
      const repo = repoDir();
      if (!repo || repo === BRAIN) return { ok: false, out: 'The team repository is not available' };
      fs.writeFileSync(tf.file, text.endsWith('\n') ? text : `${text}\n`);
      await teamCommit(repo, tf.team, b.kind, b.name);
      return { ok: true, team: tf.team };
    }
    const isNew = !fs.existsSync(p);
    if (isNew && !b.create) return { ok: false, out: 'Not found' };
    if (!isNew && b.create) return { ok: false, out: `"${b.name}" already exists` };
    fs.mkdirSync(path.dirname(p), { recursive: true });
    if (!isNew) fs.copyFileSync(p, `${p}.bak`);
    fs.writeFileSync(p, text.endsWith('\n') ? text : `${text}\n`);
    if (isNew) markMine(b.kind, b.name);
    const shared = await teamWriteBack(b.kind, b.name, p);
    return { ok: true, team: shared };
  },
  'POST /agent-delete': async (_q, b) => {
    const p = defFile('agent', b.name);
    if (p && !fs.existsSync(p) && teamFile('agent', b.name)) return { ok: false, out: 'Team skills are removed in the team editor' };
    if (!p || !isMine('agent', b.name)) return { ok: false, out: 'Only your own agents can be deleted' };
    fs.rmSync(p, { force: true });
    return { ok: true };
  },
  'POST /share': async (_q, b) => {
    if (!MARKET_BIN || !['skill', 'agent', 'mcp'].includes(b.kind) || !/^[a-z0-9][a-z0-9_.-]{0,60}$/.test(String(b.name || ''))) return { ok: false, out: 'Cannot share that' };
    return new Promise((resolve) => execFile('python3', [MARKET_BIN, b.unshare ? 'unshare' : 'share', `${b.kind}/${b.name}`],
      { timeout: 60000, env: { ...process.env, PAAS_DESCRIPTION: oneLine(b.description, 1000) } },
      (err, stdout, stderr) => resolve({ ok: !err, out: `${stdout}${stderr}`.trim() })));
  },
  // team profiles (paas-team): list, switch, sync the active team's knowledge with its git remote
  'GET /team': async () => {
    if (!TEAM_BIN) return { installed: false };
    const r = await run('python3', [TEAM_BIN, 'list', '--json']);
    try { return { installed: true, ...JSON.parse(r.out), installed_skills: json(INSTALLED_TEAM) || undefined }; } catch { return { installed: true, error: r.out.slice(0, 2000) || 'paas-team gave no answer' }; }
  },
  'POST /team': async (_q, b) => {
    if (!TEAM_BIN) return { ok: false, out: 'Teams are not installed on this VM' };
    if (b.name !== 'none' && !TEAM_NAME.test(String(b.name || ''))) return { ok: false, out: 'Bad team name' };
    return run('python3', [TEAM_BIN, 'use', b.name]);
  },
  'POST /team-add': async (_q, b) => {
    if (!TEAM_BIN) return { ok: false, out: 'Teams are not installed on this VM' };
    const name = String(b.name || ''); const url = String(b.url || '');
    if (!TEAM_NAME.test(name)) return { ok: false, out: 'Name: lower-case letters, digits, dashes, starting with a letter' };
    if (url.length > 300 || /\s/.test(url) || !/^(https:\/\/|http:\/\/|ssh:\/\/|git@|\/)/.test(url)) return { ok: false, out: 'Give a git url (https://, ssh://, git@ or a folder path)' };
    return run('python3', [TEAM_BIN, 'add', name, url], 180000);
  },
  'POST /team-export': async (_q, b) => {
    if (!TEAM_BIN) return { ok: false, out: 'Teams are not installed on this VM' };
    const args = [TEAM_BIN, 'export'];
    if (b.name) { if (!TEAM_NAME.test(String(b.name))) return { ok: false, out: 'Bad team name' }; args.push(b.name); }
    const r = await run('python3', args);
    return r.ok ? { ...r, file: r.out.split('\n')[0].trim() } : r;
  },
  // one team in full, for the editor
  'GET /team-show': async (q) => {
    if (!TEAM_BIN) return { ok: false, out: 'Teams are not installed on this VM' };
    const name = String(q.get('name') || '');
    if (!TEAM_NAME.test(name)) return { ok: false, out: 'Bad team name' };
    const r = await run('python3', [TEAM_BIN, 'show', name, '--json']);
    try { return { ok: true, ...JSON.parse(r.out) }; } catch { return { ok: false, out: r.out.slice(0, 2000) || 'paas-team gave no answer' }; }
  },
  // apply an edit: the change (it may hold a token) goes to paas-team on stdin only and is never logged
  'POST /team-edit': async (_q, b) => {
    if (!TEAM_BIN) return { ok: false, out: 'Teams are not installed on this VM' };
    const name = String(b.name || '');
    if (!TEAM_NAME.test(name)) return { ok: false, out: 'Bad team name' };
    if (!b.change || typeof b.change !== 'object' || Array.isArray(b.change)) return { ok: false, out: 'Nothing to save' };
    const payload = JSON.stringify(b.change);
    if (Buffer.byteLength(payload) > 2 * 1024 * 1024) return { ok: false, out: 'The change is too large (2 MB at most)' };
    return new Promise((resolve) => {
      const child = execFile('python3', [TEAM_BIN, 'edit', name],
        { timeout: 180000, maxBuffer: 20 * 1024 * 1024, env: { ...process.env, PATH: `${HOME}/.local/bin:${process.env.PATH}` } },
        (err, stdout, stderr) => resolve({ ok: !err, out: `${stdout}${stderr}`.trim() }));
      child.stdin.on('error', () => { /* the child exited before reading: its exit code reports it */ });
      child.stdin.end(payload);
    });
  },
  'POST /team-sync': async () => (TEAM_BIN ? run('python3', [TEAM_BIN, 'sync']) : { ok: false, out: 'Teams are not installed on this VM' }),
  'GET /mcp-status': () => run('claude', ['mcp', 'list'], 90000),
};

routes['POST /hooks'] = async (_q, b) => {
  const id = String(b.id || '');
  if (!HOOK_INFO[id]?.[2]) throw new Error('this hook cannot be switched off');
  const off = hooksOff();
  if (b.on) off.delete(id); else off.add(id);
  fs.writeFileSync(HOOKS_OFF, [...off].sort().join('\n') + (off.size ? '\n' : ''));
  return { hooks: hooks() };
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
