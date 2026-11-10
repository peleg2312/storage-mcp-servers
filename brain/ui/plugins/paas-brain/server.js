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
// without a team (or a team whose repository has no rules/ yet): the rule files beside the memory, in ~/.claude/brain
const OWN_RULES = ['persona.md', 'storage.md', 'coding.md'];
for (const n of OWN_RULES) MEMORY[n] = path.join(C, 'brain', n);
// a team's rules: every file in its repository's rules/ folder (main.md, persona.md, storage.md, coding.md and any other)
const RULE = /^rules\/((?:[\w][\w.-]{0,60}\/){0,3}[\w][\w.-]{0,100})$/;
const RULE_ORDER = ['main.md', 'persona.md', 'storage.md', 'coding.md'];
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
const run = (cmd, args, timeout = 120000, extraEnv = {}) => new Promise((resolve) => {
  execFile(cmd, args, { timeout, cwd: HOME || '/', maxBuffer: 20 * 1024 * 1024, env: { ...process.env, GIT_TERMINAL_PROMPT: '0', PATH: `${HOME}/.local/bin:${process.env.PATH}`, ...extraEnv } },
    (err, stdout, stderr) => resolve({ ok: !err, out: `${stdout}${stderr}`.trim() }));
});

// history of the memory files: ~/.claude/brain (or the active team's repository inside it) may be a git repository;
// never blocks a save. The repository is looked up per call: the team can change while the UI runs.
const TEAM_NAME = /^[a-z][a-z0-9_-]{0,31}$/;
const TEAM_BIN = [path.join(HOME, '.claude', 'tools', 'paas-team'), '/opt/paas/bin/paas-team', path.join(HOME, '.local', 'bin', 'paas-team')].find((p) => fs.existsSync(p));
// an external brain (paas-team add of another Claude Code brain): its record in the clone's .git, or null
function extRecord(team) {
  if (!TEAM_NAME.test(String(team || ''))) return null;
  const r = json(path.join(BRAIN, 'teams', team, '.git', 'paas-external.json'));
  return r && r.plugin && r.marketplace ? r : null;
}
function repoDir() {
  const team = (read(path.join(BRAIN, 'team'), 200) || '').trim();
  if (TEAM_NAME.test(team) && !extRecord(team)) {          // an external brain's clone is never written from here
    const d = path.join(BRAIN, 'teams', team);
    if (fs.existsSync(path.join(d, '.git'))) return d;
  }
  return fs.existsSync(path.join(BRAIN, '.git')) ? BRAIN : null;
}
// who commits from here: the person's own git identity when configured, else <login>@<host>, so the team repository's
// history says who wrote each note (the push may authenticate as the team's GitLab token through their credential helper)
let identEnv = null;
async function identity() {
  if (identEnv) return identEnv;
  const r = await run('git', ['config', '--get-regexp', '^user\\.(name|email)$'], 3000);
  const have = new Set(r.out.split('\n').map((l) => l.split(' ')[0]));
  const name = os.userInfo().username; const email = `${name}@${os.hostname()}`;
  identEnv = { ...(have.has('user.name') ? {} : { GIT_AUTHOR_NAME: name, GIT_COMMITTER_NAME: name }),
    ...(have.has('user.email') ? {} : { GIT_AUTHOR_EMAIL: email, GIT_COMMITTER_EMAIL: email }) };
  return identEnv;
}
const git = async (repo, args) => run('git', ['-C', repo, ...args], 5000, await identity());
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
// a file the UI is about to write must really lie inside the brain or the team repository: the memory files are symlinks
// into the team clone, and a teammate could commit a symlink that points elsewhere (writing through it would land there)
function inside(p, roots) {
  let real;
  try { real = fs.realpathSync(p); } catch { try { real = path.join(fs.realpathSync(path.dirname(p)), path.basename(p)); } catch { return false; } }
  return roots.filter(Boolean).some((r) => {
    let rr; try { rr = fs.realpathSync(r); } catch { return false; }
    const rel = path.relative(rr, real);
    return rel !== '' && !rel.startsWith('..') && !path.isAbsolute(rel);
  });
}
const OUTSIDE = { ok: false, out: 'That file points outside the brain and the team repository; not written' };
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
  if (!fs.existsSync(path.dirname(dst)) || !inside(dst, [repo])) return null;
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
function pluginTeam() {
  const team = (read(path.join(BRAIN, 'team'), 200) || '').trim();
  if (!TEAM_NAME.test(team)) return null;
  const ext = extRecord(team);
  if (ext) {                                                 // an external brain: its own plugin folder, read-only here
    const dir = path.resolve(BRAIN, 'teams', team, String(ext.dir || '.'));
    return dir.startsWith(path.join(BRAIN, 'teams', team)) && fs.existsSync(dir)
      ? { team, dir, external: true, plugin: ext.plugin, id: `${ext.plugin}@${ext.marketplace}` } : null;
  }
  const dir = path.join(BRAIN, 'teams', team, `paas-brain-${team}`);
  return fs.existsSync(dir) ? { team, dir } : null;
}
// ---- an external brain's own knowledge (its folders as its repository keeps them; never written on its main branch)
function extBrain() {
  const t = pluginTeam();
  if (!t || !t.external) return null;
  const rec = extRecord(t.team) || {};
  const repo = path.join(BRAIN, 'teams', t.team);
  const k = rec.knowledge || {};
  const rel = (x) => (typeof x === 'string' && x && !x.startsWith('.git') && !path.isAbsolute(x) && !x.split('/').includes('..') ? x : '');
  return { team: t.team, plugin: t.plugin, repo, title: rec.title || '', save: k.save === 'push' ? 'push' : 'merge-request', branch: rel(k.branch),
    folders: (k.folders || []).map(rel).filter(Boolean), inbox: rel(k.inbox), templates: rel(k.templates), index: rel(k.index),
    rules: (Array.isArray(rec.rules_files) ? rec.rules_files : rec.rules ? [rec.rules] : []).map(rel).filter((x) => x && x.endsWith('.md')) };
}
// a page path inside one of the brain's knowledge folders (or its inbox / templates / index): the real file, else null
function extFile(eb, rel, mustExist = true) {
  rel = String(rel || '');
  if (!/^[\w./ -]{1,300}\.md$/.test(rel) || rel.split('/').includes('..') || rel.startsWith('/')) return null;
  const roots = [...eb.folders, eb.inbox, eb.templates].filter(Boolean);
  if (!(roots.some((r) => rel === r || rel.startsWith(`${r}/`)) || (eb.index && rel === eb.index) || eb.rules.includes(rel))) return null;
  const p = path.join(eb.repo, rel);
  if (mustExist && !fs.existsSync(p)) return null;
  return inside(p, [eb.repo]) ? p : null;
}
function pageMeta(p, rel) {
  const text = read(p, 4000) || '';
  const f = frontmatter(text);
  const head = /^#\s+(.+)$/m.exec(text.replace(/^---\n[\s\S]*?\n---\n?/, ''));
  return { path: rel, title: String(f.title || (head ? head[1] : path.basename(rel, '.md'))).slice(0, 160),
    area: rel.split('/').length > 2 ? rel.split('/')[1] : '', mtime: fs.statSync(p).mtimeMs };
}
function extPages(eb, root, limit = 3000) {
  const out = [];
  (function walk(d) {
    if (out.length >= limit) return;
    let entries = [];
    try { entries = fs.readdirSync(path.join(eb.repo, d), { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (e.name.startsWith('.')) continue;
      const rel = `${d}/${e.name}`;
      if (e.isDirectory()) walk(rel);
      else if (e.name.endsWith('.md') && !/^(README|_template)/i.test(e.name) && out.length < limit) out.push(pageMeta(path.join(eb.repo, rel), rel));
    }
  })(root);
  return out;
}
function extOverview() {
  const eb = extBrain();
  if (!eb) return null;
  return { team: eb.team, plugin: eb.plugin, title: eb.title, save: eb.save, folders: eb.folders, inbox: eb.inbox, templates: eb.templates,
    index: eb.index && fs.existsSync(path.join(eb.repo, eb.index)) ? eb.index : '',
    pages: eb.folders.flatMap((f) => extPages(eb, f)), inboxPages: eb.inbox ? extPages(eb, eb.inbox, 500) : [],
    templatePages: eb.templates ? extPages(eb, eb.templates, 50) : [],
    rulesPages: eb.rules.filter((r) => fs.existsSync(path.join(eb.repo, r))).map((r) => pageMeta(path.join(eb.repo, r), r)) };
}
// a change to the brain's knowledge, its way: a branch from its main line and a GitLab merge request (GitLab's own push
// options open it, no glab needed), or a push to its main line only when its brain.json says "save": "push". Done in a
// separate worktree, so the clone the person works with is never touched.
async function extPropose(eb, rel, text, title) {
  const env = await identity();
  const g = (args, ms = 60000) => run('git', ['-C', eb.repo, ...args], ms, env);
  await g(['fetch', '-q', 'origin'], 60000);
  const head = (await g(['symbolic-ref', '--short', 'refs/remotes/origin/HEAD'], 5000)).out.trim();
  const main = eb.branch || (/^origin\/[\w./-]+$/.test(head) ? head.slice(7) : 'main');
  const slug = String(title).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'change';
  const d = new Date();
  const branch = `brain-tab/${d.toISOString().slice(0, 10)}-${slug}-${Math.random().toString(36).slice(2, 6)}`;
  const wt = path.join(eb.repo, '.git', 'paas-worktrees', branch.replace(/\//g, '_'));
  const add = await g(eb.save === 'push' ? ['worktree', 'add', '-q', '--detach', wt, `origin/${main}`] : ['worktree', 'add', '-q', '-b', branch, wt, `origin/${main}`]);
  if (!add.ok) return { ok: false, out: `Could not start the change: ${add.out.slice(-300)}` };
  try {
    const p = path.join(wt, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, text.endsWith('\n') ? text : `${text}\n`);
    const w = (args, ms = 60000) => run('git', ['-C', wt, ...args], ms, env);
    await w(['add', '--', rel]);
    const c = await w(['commit', '-q', '-m', String(title).slice(0, 200)]);
    if (!c.ok) return { ok: false, out: /nothing to commit/.test(c.out) ? 'Nothing changed' : c.out.slice(-300) };
    const push = eb.save === 'push'
      ? await w(['push', '-q', 'origin', `HEAD:${main}`], 120000)
      : await w(['push', '-u', 'origin', branch, '-o', 'merge_request.create', '-o', `merge_request.target=${main}`,
        '-o', `merge_request.title=${String(title).slice(0, 200)}`, '-o', 'merge_request.remove_source_branch'], 120000);
    if (!push.ok) return { ok: false, out: `Not pushed: ${push.out.slice(-400)}` };
    const url = (/https?:\/\/\S+\/merge_requests\/\d+/.exec(push.out) || /https?:\/\/\S+merge_requests\/new\S*/.exec(push.out) || [])[0] || '';
    return { ok: true, url, branch: eb.save === 'push' ? main : branch,
      out: eb.save === 'push' ? `Saved to ${main} of ${eb.team}` : url ? `Merge request: ${url}` : `Branch ${branch} pushed: open its merge request in GitLab` };
  } finally {
    await g(['worktree', 'remove', '--force', wt], 30000);
    if (eb.save !== 'push') await g(['branch', '-D', branch], 10000);
  }
}

// the clone's file for a team skill or agent (null: no plugin mode, bad name, or not in the team)
function teamFile(kind, name) {
  const t = pluginTeam();
  if (!t || !SKILL_NAME.test(String(name || ''))) return null;
  const f = kind === 'skill' ? path.join(t.dir, 'skills', name, 'SKILL.md') : kind === 'agent' ? path.join(t.dir, 'agents', `${name}.md`) : null;
  return f && fs.existsSync(f) ? { ...t, file: f } : null;
}
// the active team's rules/ folder in the person's clone (null: no team, an external brain, or an older repository)
function teamRulesDir() {
  const repo = repoDir();
  if (!repo || repo === BRAIN) return null;
  const d = path.join(repo, 'rules');
  try { return fs.lstatSync(d).isDirectory() ? d : null; } catch { return null; }
}
// every file in it (up to four levels, no hidden files, no links, no .bak), main / persona / storage / coding first
function ruleNames() {
  const d = teamRulesDir();
  if (!d) return [];
  const out = [];
  const walk = (dir, rel, depth) => {
    let names = [];
    try { names = fs.readdirSync(dir); } catch { return; }
    for (const n of names.sort()) {
      if (n.startsWith('.') || n.endsWith('.bak')) continue;
      const p = path.join(dir, n); let st;
      try { st = fs.lstatSync(p); } catch { continue; }
      if (st.isDirectory() && depth < 3) walk(p, rel ? `${rel}/${n}` : n, depth + 1);
      else if (st.isFile() && st.size < 500000) out.push(rel ? `${rel}/${n}` : n);
    }
  };
  walk(d, '', 0);
  const rank = (n) => { const k = RULE_ORDER.indexOf(n); return k < 0 ? RULE_ORDER.length : k; };
  return out.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
}
// the file behind rules/<name>, only inside the team's rules/ folder (never through a link out of it)
function rulePath(name) {
  const m = RULE.exec(String(name || ''));
  const d = teamRulesDir();
  if (!m || !d) return null;
  const p = path.join(d, ...m[1].split('/'));
  return inside(p, [d]) ? p : null;
}
// the memory tab's files: shared memory, then the rules (the team's rules/ folder, else your own), then CLAUDE.md
function memoryList() {
  const files = ['notes.md', 'environment.md', 'tool-map.md']
    .map((name) => ({ name, editable: writable(MEMORY[name]), text: read(MEMORY[name]) }));
  const rd = teamRulesDir();
  const rules = rd
    ? ruleNames().map((n) => { const p = path.join(rd, ...n.split('/')); return { name: `rules/${n}`, rules: 'team', editable: writable(p), text: read(p) }; })
    : repoDir() && repoDir() !== BRAIN                              // a team repository from before rules/: the plugin's copies
      ? ['main.md', ...OWN_RULES].map((name) => ({ name, rules: 'plugin', editable: false, text: read(path.join(C, 'brain', name)) }))
      : OWN_RULES.map((name) => ({ name, rules: 'own', editable: writable(MEMORY[name]), text: read(MEMORY[name]) }));
  const claude = { name: 'CLAUDE.md', editable: writable(MEMORY['CLAUDE.md']) || MULTI, text: read(MEMORY['CLAUDE.md']) ?? (MULTI ? '' : null) };
  return [...files, ...rules, claude].filter((m) => m.text !== null);
}
// the file behind a memory name or captures/<file>, and its repository and path inside it (null: outside it)
function memPath(name) {
  const rp = rulePath(name);
  if (rp) return { p: rp, ...locate(rp), cap: false };
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

// every other installed Claude Code plugin that is on (not the team plugins, listed through pluginTeam): Claude Code's own
// record (~/.claude/plugins/installed_plugins.json) and enabledPlugins in the user and managed settings, managed winning
function otherPlugins() {
  const rec = json(path.join(C, 'plugins', 'installed_plugins.json')) || {};
  const on = { ...((json(path.join(C, 'settings.json')) || {}).enabledPlugins || {}), ...((json(MANAGED) || {}).enabledPlugins || {}) };
  const out = [];
  const team = pluginTeam();                                 // an external brain is listed as the team, not twice
  for (const [id, v] of Object.entries(rec.plugins || {})) {
    const e = Array.isArray(v) ? (v.find((x) => x && x.scope === 'user') || v[0]) : v;
    const name = id.split('@')[0];
    if (!e || !e.installPath || on[id] === false || name.startsWith('paas-brain-') || id === team?.id || !fs.existsSync(e.installPath)) continue;
    out.push({ id, name, dir: e.installPath });
  }
  return out;
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
    const listed = new Set(out.map((s) => s.dir));          // a personal copy without a description must not hide the team's
    for (const n of tn) {
      if (!SKILL_NAME.test(n) || listed.has(n)) continue;
      const teamPath = path.join(t.dir, 'skills', n, 'SKILL.md');
      const f = frontmatter(read(teamPath, 60000));
      if (f.description) out.push({ dir: n, shared: false, name: f.name || n, description: f.description, when: f.when_to_use || '', mine: false, source: 'team', teamPath });
    }
  }
  for (const p of otherPlugins()) {                          // other plugins' skills: read-only here, /<plugin>:<skill> in a chat
    let pn = [];
    try { pn = fs.readdirSync(path.join(p.dir, 'skills')); } catch { /* no skills */ }
    for (const n of pn) {
      const f = frontmatter(read(path.join(p.dir, 'skills', n, 'SKILL.md'), 60000) || '');
      if (f.description) out.push({ dir: n, shared: false, name: `${p.name}:${f.name || n}`, description: f.description, when: f.when_to_use || '', mine: false, source: 'plugin', plugin: p.name });
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
    const listed = new Set(out.map((a) => a.file));          // a personal copy must not hide the team's agent
    for (const n of tn) {
      const file = n.replace(/\.md$/, '');
      if (!SKILL_NAME.test(file) || listed.has(file)) continue;
      const teamPath = path.join(t.dir, 'agents', n);
      const f = frontmatter(read(teamPath, 4000));
      out.push({ file, mine: false, source: 'team', shared: false, name: f.name || file, description: f.description || '', tools: info(f), model: f.model || '', teamPath });
    }
  }
  for (const p of otherPlugins()) {                          // other plugins' agents, read-only here
    let pn = [];
    try { pn = fs.readdirSync(path.join(p.dir, 'agents')).filter((n) => n.endsWith('.md')); } catch { /* no agents */ }
    for (const n of pn) {
      const f = frontmatter(read(path.join(p.dir, 'agents', n), 4000) || '');
      out.push({ file: n.replace(/\.md$/, ''), mine: false, source: 'plugin', plugin: p.name, shared: false, name: `${p.name}:${f.name || n.replace(/\.md$/, '')}`, description: f.description || '', tools: info(f), model: f.model || '' });
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
  // the active team's plugin brings its own hooks (from its git repository); while it is enabled the VM's shared copies
  // stand aside (brain/claude/hooks team_hooks_active), so the list says which ones really run
  const t = pluginTeam();
  const tid = t ? (t.id || `paas-brain-${t.team}@paas-brain-${t.team}`) : null;
  const teamOn = !!tid && ((json(path.join(C, 'settings.json')) || {}).enabledPlugins || {})[tid] === true;
  const files = [['shared', MANAGED], ['yours', path.join(C, 'settings.json')],
    ...(t ? [[`team ${t.external ? t.plugin : t.team.toUpperCase()}`, path.join(t.dir, 'hooks', 'hooks.json')]] : []),
    ...otherPlugins().map((pl) => [`plugin ${pl.name}`, path.join(pl.dir, 'hooks', 'hooks.json')])];   // other plugins' hooks too
  for (const [source, file] of files) {
    const s = json(file) || {};
    const fromPlugin = source.startsWith('plugin ') || source.startsWith('team ');
    // with a team on, the VM's own hooks do not run (they step aside for the team's from its git): not listed at all, except
    // the three learning hooks an external brain that learns into its own git keeps (ext_learn.py)
    const asides = source === 'shared' && teamOn && MANAGED_HOOKS_STEP_ASIDE;
    const learning = asides && t.external && !!(extRecord(t.team) || {}).learn;
    for (const [event, groups] of Object.entries(s.hooks || {})) {
      for (const g of groups || []) {
        for (const h of g.hooks || []) {
          const command = [h.command, ...(Array.isArray(h.args) ? h.args : [])].filter(Boolean).map(String).join(' ').replace(new RegExp(HOME, 'g'), '~');
          const id = (/([\w-]+)\.(?:py|sh|js)\b/.exec(command) || [])[1] || '';
          if (asides && !(learning && LEARN_HOOKS.has(id))) continue;
          const [title, about0, canToggle] = HOOK_INFO[id] || [command.length > 70 ? `${command.slice(0, 69)}…` : command, '', false];
          const about = asides ? `Keeps running for ${t.plugin}: saves what Claude learns into its own git (learning is on).${about0 ? ` ${about0}` : ''}` : about0;
          out.push({ id, title, about, canToggle: canToggle && !fromPlugin && !asides, on: fromPlugin || asides || !off.has(id), source, when: WHEN[event] || event, matcher: g.matcher || '*', command });
        }
      }
    }
  }
  return out;
}
// the VM's shared hooks step aside for an active team plugin (brain/claude/hooks, team_hooks_active); a VM whose hooks
// predate that rule does not, so the list only says so when the installed copy carries it
const LEARN_HOOKS = new Set(['session-start', 'notes-check', 'capture-nudge']);
const MANAGED_HOOKS_STEP_ASIDE = (() => { try { return fs.readFileSync('/opt/paas/hooks/block-write-tools.py', 'utf8').includes('team_hooks_active'); } catch { return false; } })();

// the servers this person's Claude connects: the active team plugin's (its .mcp.json, built from the team repository's
// mcp.json; Claude Code starts them while the plugin is enabled) and their own user-scope ones in ~/.claude.json
function mcpServers() {
  const row = (name, s, source) => ({
    name, source, type: s.type || (s.url ? 'http' : 'stdio'),
    target: s.url || [s.command, ...(s.args || [])].join(' ').replace(new RegExp(HOME, 'g'), '~'),
  });
  const out = [];
  const t = pluginTeam();
  if (t) {
    const pj = json(path.join(t.dir, '.mcp.json')) || {};
    for (const [name, s] of Object.entries(pj.mcpServers || pj)) if (s && typeof s === 'object') out.push(row(name, s, 'team'));
  }
  for (const p of otherPlugins()) {                          // other plugins' MCP servers
    const pj = json(path.join(p.dir, '.mcp.json')) || {};
    for (const [name, s] of Object.entries(pj.mcpServers || pj)) if (s && typeof s === 'object') out.push({ ...row(name, s, 'plugin'), plugin: p.name });
  }
  const cfg = json(path.join(HOME, '.claude.json')) || {};
  for (const [name, s] of Object.entries(cfg.mcpServers || {})) if (!out.some((m) => m.name === name)) out.push(row(name, s, 'mine'));
  return out;
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

// the active team's own library ("library" in its plugin's team.json: ~/.claude/brain/libraries/<name>/docs.db), or null for
// the general one: the Docs section shows and searches the library this person's Claude searches
function teamLibrary() {
  const t = pluginTeam();
  const name = t && String((t.external ? (extRecord(t.team) || {}).library : (json(path.join(t.dir, 'team.json')) || {}).library) || '');
  if (!name || !/^[a-z0-9][a-z0-9_-]{0,31}$/.test(name)) return null;
  const db = path.join(BRAIN, 'libraries', name, 'docs.db');
  if (t.external && !fs.existsSync(db)) return null;          // its docs not loaded by root yet: the general library stays
  return { name, db, built: fs.existsSync(db) ? fs.statSync(db).mtimeMs : null };
}

async function overview() {
  const tl = teamLibrary();
  const src = tl && !tl.built ? { ok: false } : await run('python3', [path.join(LIB, 'search.py'), ...(tl ? ['--db', tl.db] : []), 'sources'], 60000);
  return {
    library: tl ? { team: tl.name, built: tl.built, version: null, sources: src.ok ? src.out : null }
      : { version: read(path.join(LIB, 'VERSION'))?.trim() || null, sources: src.ok ? src.out : null },
    pluginTeam: pluginTeam()?.team || null,
    pluginName: pluginTeam() ? (pluginTeam().external ? pluginTeam().plugin : `paas-brain-${pluginTeam().team}`) : null,
    pluginExternal: !!pluginTeam()?.external,
    external: extOverview(),
    skills: skills(), agents: agents(), hooks: hooks(), mcp: mcpServers(), inbox: inbox(), captures: captures(),
    // multi-user VM: environment.md / tool-map.md are shared and only root writes them; the library too
    // CLAUDE.md is this account's own copy of the brain's rules, yours to change (a brain update replaces it)
    memory: memoryList(),
    canShare: !!MARKET_BIN && writable(MINE),
    canAddDocs: !teamLibrary() && writable(LIB),           // a team library is filled by root (paas-library), not from here
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
    const tl = teamLibrary();
    if (tl && !tl.built) return { error: `Your team's library "${tl.name}" is not built yet: root runs paas-library build ${tl.name}` };
    const args = [path.join(LIB, 'search.py'), ...(tl ? ['--db', tl.db] : []), '--json', 'search', query, '--limit', '15'];
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
      if (!inside(p, [BRAIN, repoDir()])) return OUTSIDE;
      if (fs.existsSync(p)) fs.copyFileSync(p, `${p}.bak`);
      fs.writeFileSync(p, t.endsWith('\n') ? t : `${t}\n`);
      await commitFile(p, `brain tab: ${b.name}`);
      return { ok: true };
    }
    if (RULE.test(String(b.name || ''))) {                           // a team rule: the team's own, changed by a person here
      const rp = rulePath(b.name);
      if (!rp || !fs.existsSync(rp)) return { ok: false, out: "That file is not in your team's rules/ folder" };
      if (!writable(rp)) return { ok: false, out: 'Not writable for you' };
      const t = String(b.text ?? '');
      if (t.length > 500000) return { ok: false, out: 'Too long' };
      fs.writeFileSync(rp, t.endsWith('\n') ? t : `${t}\n`);          // no .bak beside it: the team repository keeps every version
      await commitFile(rp, `brain tab: ${b.name}`);                    // committed and pushed: every member gets it at their next start
      return { ok: true };
    }
    if (!Object.hasOwn(MEMORY, b.name)) return { ok: false, out: 'That file is not editable here' };
    if (fs.existsSync(MEMORY[b.name]) && !writable(MEMORY[b.name])) return { ok: false, out: 'Shared file: only root changes it' };
    const text = String(b.text ?? '');
    if (text.length > 500000) return { ok: false, out: 'Too long' };
    const p = MEMORY[b.name];
    if (!inside(p, [BRAIN, repoDir()])) return OUTSIDE;
    if (fs.existsSync(p)) fs.copyFileSync(p, `${p}.bak`);            // one step back, next to the file
    fs.writeFileSync(p, text.endsWith('\n') ? text : `${text}\n`);
    await commitFile(p, `brain tab: ${b.name}`);
    return { ok: true };
  },
  'GET /history': async (q) => {
    const m = memPath(q.get('name'));
    if (!m || !m.rel || !m.repo) return { repo: false, entries: [] };
    const r = await git(m.repo, ['log', '--format=%h%x09%ct%x09%an%x09%s', '-n', '25', '--', m.rel]);   // who saved it: commits carry the person
    const entries = r.ok ? r.out.split('\n').filter(Boolean).map((l) => { const [sha, when, author, ...s] = l.split('\t'); return { sha, when: Number(when), author, subject: s.join('\t') }; }) : [];
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
      if (tf.external) return { ok: false, out: `"${b.name}" belongs to the external brain ${tf.team}: change it in its own repository` };
      const repo = repoDir();
      if (!repo || repo === BRAIN) return { ok: false, out: 'The team repository is not available' };
      if (!inside(tf.file, [repo])) return OUTSIDE;
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
    if (p && !fs.existsSync(p) && teamFile('agent', b.name)) return { ok: false, out: 'Team agents are removed in the team editor' };
    if (!p || !isMine('agent', b.name)) return { ok: false, out: 'Only your own agents can be deleted' };
    fs.rmSync(p, { force: true });
    return { ok: true };
  },
  'POST /share': async (_q, b) => {
    if (!MARKET_BIN || !['skill', 'agent', 'mcp'].includes(b.kind) || !/^[a-z0-9][a-z0-9_.-]{0,60}$/.test(String(b.name || ''))) return { ok: false, out: 'Cannot share that' };
    return new Promise((resolve) => execFile('python3', [MARKET_BIN, b.unshare ? 'unshare' : 'share', `${b.kind}/${b.name}`],
      { timeout: 60000, cwd: HOME || '/', env: { ...process.env, PAAS_DESCRIPTION: oneLine(b.description, 1000) } },
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
    const url = String(b.url || '');
    // no name given: the repository's own (".../redbull-brain.git" -> "redbull-brain")
    const name = String(b.name || '') || (url.replace(/\.git\/?$/, '').split(/[/:]/).pop() || '').toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^[^a-z]+/, '').slice(0, 32).replace(/-+$/, '');
    if (!TEAM_NAME.test(name)) return { ok: false, out: 'Name: lower-case letters, digits, dashes, starting with a letter' };
    if (url.length > 300 || /\s/.test(url) || !/^(https:\/\/|http:\/\/|ssh:\/\/|git@|\/)/.test(url)) return { ok: false, out: 'Give a git url (https://, ssh://, git@ or a folder path)' };
    const r = await run('python3', [TEAM_BIN, 'add', name, url], 180000);
    return { ...r, name };
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
        { timeout: 180000, cwd: HOME || '/', maxBuffer: 20 * 1024 * 1024, env: { ...process.env, PATH: `${HOME}/.local/bin:${process.env.PATH}` } },
        (err, stdout, stderr) => resolve({ ok: !err, out: `${stdout}${stderr}`.trim() }));
      child.stdin.on('error', () => { /* the child exited before reading: its exit code reports it */ });
      child.stdin.end(payload);
    });
  },
  // an external brain's settings (its server addresses, tokens): paas-team env <team> KEY=VALUE (KEY= removes one);
  // the values go on the command line of a local child process only and are never echoed back (names only)
  'POST /team-env': async (_q, b) => {
    if (!TEAM_BIN) return { ok: false, out: 'Teams are not installed on this VM' };
    const name = String(b.name || '');
    if (!TEAM_NAME.test(name) || !extRecord(name)) return { ok: false, out: 'Not an external brain' };
    const pairs = (Array.isArray(b.pairs) ? b.pairs : []).map(String).filter((x) => /^[A-Za-z_][A-Za-z0-9_]{0,63}=[^\n]{0,2000}$/.test(x)).slice(0, 40);
    if (!pairs.length) return { ok: false, out: 'Nothing to set: KEY=VALUE, one per line (KEY= removes it)' };
    return run('python3', [TEAM_BIN, 'env', name, ...pairs]);
  },
  // an external brain's knowledge: one page, read-only here (GET), and a proposed change (POST: branch + merge request)
  'GET /ext-page': async (q) => {
    const eb = extBrain();
    if (!eb) return { ok: false, out: 'No external brain active' };
    const p = extFile(eb, q.get('path'));
    return p ? { ok: true, path: q.get('path'), text: read(p) ?? '' } : { ok: false, out: 'Not one of its knowledge pages' };
  },
  'POST /ext-propose': async (_q, b) => {
    const eb = extBrain();
    if (!eb) return { ok: false, out: 'No external brain active' };
    const rel = String(b.path || '');
    if (!extFile(eb, rel, !b.create)) return { ok: false, out: 'Give a page inside its knowledge folders or inbox, ending in .md' };
    if (b.create && fs.existsSync(path.join(eb.repo, rel))) return { ok: false, out: 'That page already exists: open it and propose a change' };
    const text = String(b.text || '');
    if (!text.trim() || Buffer.byteLength(text) > 2 * 1024 * 1024) return { ok: false, out: 'The page is empty or too large' };
    const title = oneLine(b.title, 200) || `brain(${eb.team}): ${path.basename(rel, '.md')}`;
    return extPropose(eb, rel, text, title);
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
