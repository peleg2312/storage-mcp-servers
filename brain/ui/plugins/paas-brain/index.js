// Brain tab: search and grow the offline docs library, and see what this Claude knows and can do
// (skills, agents, MCP servers, hooks, memory files). Data: server.js.
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

const CSS = `
.pb{font:14px/1.55 ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));padding:28px;max-width:1100px;margin:0 auto}
.pb h2{font-size:22px;font-weight:700;margin:0}
.pb .hk{display:flex;gap:14px;align-items:center;justify-content:space-between;padding:10px 0;border-top:1px solid hsl(var(--border)/.6)}
.pb .hk-t{min-width:0}.pb .hk .badge{font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;border-radius:6px;padding:1px 6px;background:hsl(var(--muted));color:hsl(var(--muted-foreground))}
.pb .sw{position:relative;width:40px;height:22px;flex:none;cursor:pointer}.pb .sw input{opacity:0;width:0;height:0;position:absolute}
.pb .sw span{position:absolute;inset:0;border-radius:999px;background:hsl(var(--muted));border:1px solid hsl(var(--border));transition:.15s}
.pb .sw span:before{content:'';position:absolute;width:16px;height:16px;left:2px;top:2px;border-radius:50%;background:hsl(var(--background));box-shadow:0 1px 2px #0003;transition:.15s}
.pb .sw input:checked+span{background:linear-gradient(90deg,#a78bfa,#60a5fa);border-color:transparent}.pb .sw input:checked+span:before{transform:translateX(18px);background:#fff}
.pb .sw input:focus-visible+span{outline:2px solid #a78bfa;outline-offset:2px}.pb .sub{color:hsl(var(--muted-foreground));font-size:13px}
.pb .head{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:18px}
.pb .tabs{display:flex;gap:4px;border-bottom:1px solid hsl(var(--border));margin-bottom:20px;overflow-x:auto}
.pb .tabs button{background:none;border:0;padding:9px 14px;color:hsl(var(--muted-foreground));cursor:pointer;font:inherit;border-bottom:2px solid transparent;white-space:nowrap}
.pb .tabs button.on{color:hsl(var(--foreground));border-image:linear-gradient(90deg,#a78bfa,#22d3ee) 1;border-bottom:2px solid;font-weight:600}
.pb .card{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:14px;padding:18px;margin-bottom:14px}
.pb .card h3{margin:0 0 10px;font-size:15px;font-weight:600}
.pb input,.pb textarea,.pb select{font:inherit;color:inherit;background:hsl(var(--background));border:1px solid hsl(var(--input));border-radius:10px;padding:9px 12px;outline:none}
.pb input:focus,.pb textarea:focus{border-color:hsl(var(--ring))}
.pb .search{display:flex;gap:8px}.pb .search input{flex:1;font-size:15px;padding:11px 14px}
.pb button.go{background-image:linear-gradient(120deg,#a78bfa,#60a5fa 55%,#22d3ee);color:#0b0d1a;border:0;border-radius:10px;padding:9px 16px;font:inherit;font-weight:600;cursor:pointer}
.pb button.go:disabled{opacity:.5;cursor:wait}
.pb button.ghost{background:none;border:1px solid hsl(var(--border));color:inherit;border-radius:10px;padding:8px 14px;font:inherit;cursor:pointer}
.pb .res{padding:12px 0;border-bottom:1px solid hsl(var(--border)/.6)}.pb .res:last-child{border:0}
.pb .res a{color:hsl(var(--primary));font-weight:600;text-decoration:none}.pb .res a:hover{text-decoration:underline}
.pb .tag{display:inline-block;font-size:11px;padding:1px 8px;border-radius:999px;background:hsl(var(--accent));color:hsl(var(--muted-foreground));margin-right:6px}
.pb .snip{color:hsl(var(--muted-foreground));font-size:13px;margin-top:4px;white-space:pre-wrap}
.pb .snip b{color:hsl(var(--foreground));font-weight:600}
.pb .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.pb .item{border:1px solid hsl(var(--border));border-radius:12px;padding:12px 14px;background:hsl(var(--card))}
.pb .item .t{font-weight:600}.pb .item .d{color:hsl(var(--muted-foreground));font-size:13px;margin-top:4px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.pb .drop{border:2px dashed hsl(var(--border));border-radius:14px;padding:22px;text-align:center;color:hsl(var(--muted-foreground));cursor:pointer}
.pb .drop.over{border-color:#a78bfa;background:hsl(var(--accent))}
.pb .two{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.pb pre{white-space:pre-wrap;font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:10px;padding:12px;max-height:520px;overflow:auto;margin:0}
.pb table{width:100%;border-collapse:collapse;font-size:13px}.pb td,.pb th{padding:7px 6px;text-align:left;border-bottom:1px solid hsl(var(--border)/.6);vertical-align:top}
.pb th{color:hsl(var(--muted-foreground));font-weight:500;font-size:12px}.pb code{font:12px ui-monospace,Menlo,monospace;word-break:break-all}
.pb .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px}
.pb.pb ::placeholder,.pb.pb textarea::placeholder,.pb.pb textarea::-webkit-input-placeholder,.pb.pb input::placeholder{color:hsl(var(--muted-foreground)/.6) !important;opacity:1 !important}
.pb .search{flex-wrap:wrap}.pb .search input.q{flex:1 1 260px}.pb .search input.v{flex:0 1 170px;max-width:none !important}
.pb .seg2{display:inline-flex;flex-wrap:wrap;border:1px solid hsl(var(--border));border-radius:10px;overflow:hidden}
.pb .seg2 button{padding:7px 14px;background:none;border:0;color:hsl(var(--muted-foreground));cursor:pointer;font:inherit}
.pb .seg2 button.on{background:hsl(var(--accent));color:hsl(var(--foreground));font-weight:600}
.pb textarea.mt{width:100%;min-height:420px;font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;resize:vertical}
.pb .form{display:grid;gap:14px;margin-top:14px}.pb .form label{display:block;font-weight:600;font-size:13px}.pb .form label .sub{font-weight:400;margin-left:6px;font-size:12px}.pb .form label input,.pb .form label textarea{display:block;margin-top:6px}
.pb .form input,.pb .form textarea{font-weight:400;width:100%}.pb .form textarea{font:12.5px/1.55 ui-monospace,Menlo,monospace}
.pb .grp{margin:18px 0 10px;font-size:13px;font-weight:600;color:hsl(var(--muted-foreground));text-transform:uppercase;letter-spacing:.08em}
.pb button.sm{padding:4px 12px;font-size:12px}.pb button.danger{color:hsl(var(--destructive))}
.pb input[readonly]{opacity:.7}
@media (max-width:640px){.pb{padding:16px}.pb .search input.v{flex:1 1 100%}.pb .grid,.pb .two{grid-template-columns:1fr}.pb pre{max-height:none}}`;

export function mount(container, api) {
  let data = null;
  let tab = 'docs';
  container.innerHTML = `<style>${CSS}</style><div class="pb"><div class="head"><div><h2>Brain</h2>
    <div class="sub lib">Loading…</div></div></div>
    <div class="tabs">${[['docs', 'Docs library'], ['skills', 'Skills'], ['agents', 'Agents'], ['mcp', 'MCP & hooks'], ['memory', 'Memory']]
      .map(([k, l]) => `<button data-k="${k}" class="${k === tab ? 'on' : ''}">${l}</button>`).join('')}</div><div class="pane"></div></div>`;
  const pane = container.querySelector('.pane');
  container.querySelectorAll('.tabs button').forEach((b) => b.addEventListener('click', () => {
    tab = b.dataset.k;
    container.querySelectorAll('.tabs button').forEach((x) => x.classList.toggle('on', x === b));
    render();
  }));

  async function refresh() {
    try { data = await api.rpc('GET', 'overview'); } catch (e) { pane.innerHTML = `<div class="sub">Could not load: ${esc(e.message || e)}</div>`; return; }
    const first = (data.library.sources || '').split('\n')[0];
    container.querySelector('.lib').textContent = data.library.version
      ? `Library ${data.library.version} · ${first.replace(/^library bundle \S+ indexed \S+: /, '')} · ${data.skills.length} skills · ${data.agents.length} agents · ${data.mcp.length} MCP servers`
      : 'Docs library not installed on this VM';
    render();
  }

  function render() {
    if (!data) return;
    if (tab === 'docs') return renderDocs();
    if (tab === 'skills') return renderSkills();
    if (tab === 'agents') return renderAgents();
    if (tab === 'mcp') {
      pane.innerHTML = `<div class="card"><h3>MCP servers</h3><table><tr><th>Name</th><th>Type</th><th>Runs</th><th></th></tr>${data.mcp.map((m) => `<tr><td><b>${esc(m.name)}</b></td><td>${esc(m.type)}</td><td><code>${esc(m.target)}</code></td>
        <td>${data.canShare ? `<button class="ghost sm" data-share="mcp:${esc(m.name)}:0">Share with everyone</button>` : ''}</td></tr>`).join('')}</table>
        <div class="row"><button class="ghost chk">Check connections</button><span class="sub">runs <code>claude mcp list</code></span></div><pre class="st" style="display:none;margin-top:10px"></pre></div>
        <div class="card"><h3>Hooks</h3><div class="sub" style="margin-bottom:10px">Small helpers that run around Claude's steps.
        Switching one off applies to your chats only.</div>${data.hooks.length ? data.hooks.map((h) => `<div class="hk">
          <div class="hk-t"><b>${esc(h.title)}</b> <span class="badge">${h.source === 'shared' ? 'shared' : 'yours'}</span>
          <div class="sub">${esc(h.about || h.command)}</div><div class="sub">${esc(h.when)}${h.matcher !== '*' ? ` · <code>${esc(h.matcher)}</code>` : ''}</div></div>
          ${h.canToggle ? `<label class="sw" title="${h.on ? 'On: click to switch off' : 'Off: click to switch on'}"><input type="checkbox" data-hk="${esc(h.id)}" ${h.on ? 'checked' : ''}><span></span></label>`
            : `<span class="sub" title="Keeps your storage safe">${h.id === 'block-write-tools' ? 'always on' : ''}</span>`}</div>`).join('')
          : '<div class="sub">No hooks set up.</div>'}</div>`;
      wireShare(() => { tab = 'mcp'; render(); });
      pane.querySelectorAll('[data-hk]').forEach((cb) => cb.addEventListener('change', async () => {
        cb.disabled = true;
        try { data.hooks = (await api.rpc('POST', 'hooks', { id: cb.dataset.hk, on: cb.checked })).hooks; } catch (e) { cb.checked = !cb.checked; alert(`Could not change it: ${e.message || e}`); }
        tab = 'mcp'; render();
      }));
      pane.querySelector('.chk').addEventListener('click', async (e) => {
        const pre = pane.querySelector('.st');
        e.target.disabled = true; pre.style.display = 'block'; pre.textContent = 'Checking every server (can take a minute)…';
        const r = await api.rpc('GET', 'mcp-status').catch((x) => ({ out: String(x) }));
        pre.textContent = r.out || '(no output)'; e.target.disabled = false;
      });
    }
    if (tab === 'memory') return renderMemory();
  }

  // Memory: notes.md / environment.md / tool-map.md are yours (kept by every install); CLAUDE.md is shown only
  function renderMemory(i = 0) {
    const m = data.memory[i];
    pane.innerHTML = `<div class="seg2">${data.memory.map((x, k) => `<button class="${k === i ? 'on' : ''}" data-i="${k}">${esc(x.name)}</button>`).join('')}</div>
      <div class="sub" style="margin:12px 0 8px">${m.editable
        ? 'What Claude reads at the start of every session. Edit and save; the previous version is kept as a .bak file.'
        : 'The brain\'s main instructions. Rewritten by every install, so it is read-only here: put your own facts in notes.md or environment.md.'}</div>
      ${m.editable ? `<textarea class="mt" spellcheck="false">${esc(m.text)}</textarea>
        <div class="row"><button class="go save">Save</button><span class="sub st"></span></div>` : `<pre>${esc(m.text)}</pre>`}`;
    pane.querySelectorAll('.seg2 button').forEach((b) => b.addEventListener('click', () => renderMemory(Number(b.dataset.i))));
    pane.querySelector('.save')?.addEventListener('click', async (e) => {
      const text = pane.querySelector('.mt').value;
      e.target.disabled = true;
      const r = await api.rpc('POST', 'memory', { name: m.name, text }).catch((x) => ({ out: String(x) }));
      e.target.disabled = false;
      pane.querySelector('.st').textContent = r.ok ? `Saved ${new Date().toLocaleTimeString()}` : r.out;
      if (r.ok) m.text = text;
    });
  }

  // Skills: edit any (whole file); create and delete yours (never touched by an install)
  function renderSkills(editing = null) {
    const mine = data.skills.filter((x) => x.mine);
    const form = editing ? `<div class="card"><h3>${editing.name ? `Edit /${esc(editing.name)}` : 'New skill'}</h3>
      <div class="sub">A skill is a playbook Claude loads by itself when your request matches its description.</div>
      <div class="form">
        <label>Name<input class="f-name" placeholder="vm-patching" value="${esc(editing.name || '')}" ${editing.name ? 'readonly' : ''}></label>
        <label>Description <span class="sub">what it does and when to use it</span><input class="f-desc" placeholder="Monthly RHEL patching of the storage VMs: pre-checks, order, rollback" value="${esc(editing.description || '')}"></label>
        <label>Trigger phrases <span class="sub">optional</span><input class="f-when" placeholder="&quot;patch the vms&quot;, &quot;monthly patching&quot;" value="${esc(editing.when || '')}"></label>
        <label>Instructions <span class="sub">Markdown: steps, commands, checks, what to report</span><textarea class="f-body" rows="10" placeholder="## Steps&#10;1. ...">${esc(editing.body || '')}</textarea></label>
      </div>
      <div class="row"><button class="go f-save">Save skill</button><button class="ghost f-cancel">Cancel</button><span class="sub f-st"></span></div></div>` : '';
    const card = (x) => `<div class="item" title="${esc(x.description)}"><div class="t">/${esc(x.name)}${x.mine ? ' <span class="tag">yours</span>' : ''}</div>
      <div class="d">${esc(x.description)}</div><div class="row"><button class="ghost sm" data-edit="${esc(x.dir)}">Edit</button>${x.mine && data.canShare ? `<button class="ghost sm" data-share="skill:${esc(x.dir)}:${x.shared ? 1 : 0}">${x.shared ? 'Unshare' : 'Share with everyone'}</button>` : ''}${x.mine ? `<button class="ghost sm danger" data-del="${esc(x.dir)}">Delete</button>` : ''}</div></div>`;
    pane.innerHTML = `<div class="row" style="margin:0 0 14px;justify-content:space-between"><span class="sub">${data.skills.length} skills · ${mine.length} of them yours</span>
      ${editing ? '' : '<button class="go new">+ New skill</button>'}</div>${form}
      ${mine.length ? `<h4 class="grp">Your skills</h4><div class="grid">${mine.map(card).join('')}</div><h4 class="grp">Built in</h4>` : ''}
      <div class="grid">${data.skills.filter((x) => !x.mine).map(card).join('')}</div>`;
    pane.querySelector('.new')?.addEventListener('click', () => renderSkills({}));
    pane.querySelector('.f-cancel')?.addEventListener('click', () => renderSkills());
    pane.querySelector('.f-save')?.addEventListener('click', async (e) => {
      const v = (c) => pane.querySelector(c).value;
      e.target.disabled = true;
      const r = await api.rpc('POST', 'skill', { name: v('.f-name').trim(), description: v('.f-desc'), when: v('.f-when'), body: v('.f-body') }).catch((x) => ({ out: String(x) }));
      e.target.disabled = false;
      if (!r.ok) { pane.querySelector('.f-st').textContent = r.out; return; }
      await refresh(); renderSkills();
    });
    pane.querySelectorAll('[data-edit]').forEach((b) => b.addEventListener('click', () => editFile('skill', b.dataset.edit, false, renderSkills)));
    wireShare(renderSkills);
    pane.querySelectorAll('[data-del]').forEach((b) => b.addEventListener('click', async () => {
      if (!window.confirm(`Delete your skill /${b.dataset.del}?`)) return;
      const r = await api.rpc('POST', 'skill-delete', { name: b.dataset.del }).catch((x) => ({ out: String(x) }));
      if (!r.ok) { window.alert(r.out); return; }
      await refresh(); renderSkills();
    }));
  }

  // Agents: the brain's own and yours; edit any of them, add and delete yours
  function renderAgents() {
    const card = (a) => `<div class="item"><div class="t">${esc(a.name)}${a.mine ? ' <span class="tag">yours</span>' : ''}</div><div class="d">${esc(a.description)}</div>
      <div class="row"><span class="tag">${esc(a.tools)}</span>${a.model ? `<span class="tag">${esc(a.model)}</span>` : ''}</div>
      <div class="row"><button class="ghost sm" data-edit="${esc(a.file)}">Edit</button>${a.mine && data.canShare ? `<button class="ghost sm" data-share="agent:${esc(a.file)}:${a.shared ? 1 : 0}">${a.shared ? 'Unshare' : 'Share with everyone'}</button>` : ''}${a.mine ? `<button class="ghost sm danger" data-del="${esc(a.file)}">Delete</button>` : ''}</div></div>`;
    pane.innerHTML = `<div class="row" style="margin:0 0 14px;justify-content:space-between"><span class="sub">${data.agents.length} agents: helpers Claude hands a task to (they run with their own instructions and tools)</span>
      <button class="go new">+ New agent</button></div><div class="grid">${data.agents.map(card).join('')}</div>`;
    pane.querySelector('.new').addEventListener('click', () => editFile('agent', '', true, renderAgents));
    pane.querySelectorAll('[data-edit]').forEach((b) => b.addEventListener('click', () => editFile('agent', b.dataset.edit, false, renderAgents)));
    wireShare(renderAgents);
    pane.querySelectorAll('[data-del]').forEach((b) => b.addEventListener('click', async () => {
      if (!window.confirm(`Delete your agent ${b.dataset.del}?`)) return;
      const r = await api.rpc('POST', 'agent-delete', { name: b.dataset.del }).catch((x) => ({ out: String(x) }));
      if (!r.ok) { window.alert(r.out); return; }
      await refresh(); renderAgents();
    }));
  }

  // Share with everyone / Unshare (the marketplace: others see it with your name and can add it)
  function wireShare(rerender) {
    pane.querySelectorAll('[data-share]').forEach((b) => b.addEventListener('click', async () => {
      const [kind, name, on] = b.dataset.share.split(':');
      const unshare = on === '1';
      let description = '';
      if (kind === 'mcp' && !unshare) {
        description = window.prompt(`Describe ${name} for the marketplace (what it gives Claude):`, '') ?? null;
        if (description === null) return;
      }
      if (unshare && !window.confirm(`Take ${kind} ${name} out of the marketplace? People who added it keep their copy.`)) return;
      b.disabled = true;
      const r = await api.rpc('POST', 'share', { kind, name, unshare, description }).catch((x) => ({ out: String(x) }));
      b.disabled = false;
      window.alert(r.out || (r.ok ? 'Done' : 'Failed'));
      await refresh(); rerender();
    }));
  }

  const AGENT_TEMPLATE = (name) => `---\nname: ${name || 'my-agent'}\ndescription: "What this agent does and when Claude should hand a task to it"\n`
    + 'tools: Read, Grep, Glob, Bash\nmodel: sonnet\n---\nYou are ... Your job: ...\n\n## Steps\n1. ...\n\n## Report\nReturn a short summary with ...\n';

  // the whole file of a skill or agent in an editor (header + instructions)
  async function editFile(kind, name, create, back) {
    let text = AGENT_TEMPLATE('');
    let builtin = false;
    if (!create) {
      const r = await api.rpc('GET', `file?kind=${kind}&name=${encodeURIComponent(name)}`).catch((x) => ({ out: String(x) }));
      if (!r.ok) { window.alert(r.out); return; }
      ({ text, builtin } = r);
    }
    pane.innerHTML = `<div class="card"><h3>${create ? `New ${kind}` : `Edit ${kind === 'skill' ? '/' : ''}${esc(name)}`}</h3>
      <div class="sub">The header between the --- lines needs <code>name:</code> and <code>description:</code> (Claude picks it by the description); below it, the instructions in Markdown.</div>
      ${builtin ? '<div class="sub" style="margin-top:6px;color:#d97706">Built in: re-running brain/install.sh puts the original back. Your previous version is kept as a .bak file.</div>' : ''}
      ${create ? '<div class="form"><label>Name <span class="sub">lower-case letters, digits and dashes</span><input class="f-name" placeholder="vm-patching"></label></div>' : ''}
      <textarea class="mt" spellcheck="false" style="margin-top:12px">${esc(text)}</textarea>
      <div class="row"><button class="go f-save">Save</button><button class="ghost f-cancel">Cancel</button><span class="sub f-st"></span></div></div>`;
    const ta = pane.querySelector('.mt');
    pane.querySelector('.f-name')?.addEventListener('input', (e) => { ta.value = ta.value.replace(/^name: .*$/m, `name: ${e.target.value.trim() || 'my-agent'}`); });
    pane.querySelector('.f-cancel').addEventListener('click', () => back());
    pane.querySelector('.f-save').addEventListener('click', async (e) => {
      const n = create ? pane.querySelector('.f-name').value.trim() : name;
      e.target.disabled = true;
      const r = await api.rpc('POST', 'file', { kind, name: n, text: ta.value, create }).catch((x) => ({ out: String(x) }));
      e.target.disabled = false;
      if (!r.ok) { pane.querySelector('.f-st').textContent = r.out; return; }
      await refresh(); back();
    });
  }

  function renderDocs() {
    pane.innerHTML = `
      <div class="card"><div class="search"><input class="q" placeholder="Search the docs: an error, an event, an API, a task…" />
        <input class="v" placeholder="vendor (optional)" style="max-width:170px" /><button class="go s">Search</button></div><div class="out"></div></div>
      ${data.canAddDocs === false ? '<div class="card"><h3>Add documents</h3><div class="sub">The docs library is shared by everyone on this VM: root adds documents to it (root\'s Brain tab).</div></div>' : `<div class="two">
        <div class="card"><h3>Add pages or PDFs by URL</h3><div class="sub">Any URL this VM can reach. Claude can do it too: “add this to your docs: …”</div>
          <textarea class="urls" rows="3" style="width:100%;margin-top:10px" placeholder="https://wiki.corp/san/zoning-standard"></textarea>
          <div class="row"><input class="to" placeholder="vendor/product, e.g. cisco/mds" style="flex:1" /><button class="go add">Add</button></div><pre class="addout" style="display:none;margin-top:10px"></pre></div>
        <div class="card"><h3>Upload files</h3><div class="sub">PDF, HTML, Markdown or text, up to 35 MB each</div>
          <div class="drop" style="margin-top:10px">Drop files here or click to choose<input type="file" multiple hidden accept=".pdf,.html,.htm,.md,.markdown,.txt,.adoc,.rst" /></div>
          <div class="row"><input class="to2" placeholder="vendor/product (default local/uploads)" style="flex:1" /></div><pre class="upout" style="display:none;margin-top:10px"></pre></div>
      </div>
      <div class="card"><h3>Your added documents</h3>${data.inbox.length ? `<table><tr><th>File</th><th>Size</th><th>Added</th></tr>${data.inbox.map((f) => `<tr><td><code>${esc(f.path)}</code></td><td>${kb(f.size)}</td><td>${new Date(f.mtime).toLocaleDateString()}</td></tr>`).join('')}</table>` : '<div class="sub">None yet</div>'}</div>`}`;
    const q = pane.querySelector('.q');
    const out = pane.querySelector('.out');
    const search = async () => {
      if (!q.value.trim()) return;
      out.innerHTML = '<div class="sub" style="margin-top:12px">Searching…</div>';
      const v = pane.querySelector('.v').value.trim();
      const r = await api.rpc('GET', `search?q=${encodeURIComponent(q.value)}${v ? `&vendor=${encodeURIComponent(v)}` : ''}`).catch((e) => ({ error: String(e) }));
      if (r.error) { out.innerHTML = `<pre style="margin-top:12px">${esc(r.error)}</pre>`; return; }
      out.innerHTML = (r.results || []).map((x) => `<div class="res">
        ${x.url ? `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a>` : `<b>${esc(x.title)}</b>`}
        <div><span class="tag">${esc(x.vendor)}/${esc(x.product)}</span><span class="sub">${esc(x.section || '')}</span></div>
        <div class="snip">${esc((x.snippet || '').slice(0, 420)).replace(/«(.*?)»/g, '<b>$1</b>')}</div></div>`).join('') || '<div class="sub" style="margin-top:12px">No matches: try other words</div>';
    };
    pane.querySelector('.s').addEventListener('click', search);
    q.addEventListener('keydown', (e) => { if (e.key === 'Enter') search(); });
    if (data.canAddDocs === false) return;

    pane.querySelector('.add').addEventListener('click', async (e) => {
      const pre = pane.querySelector('.addout');
      e.target.disabled = true; pre.style.display = 'block'; pre.textContent = 'Fetching and indexing…';
      const r = await api.rpc('POST', 'add-url', { urls: pane.querySelector('.urls').value, to: pane.querySelector('.to').value.trim() }).catch((x) => ({ out: String(x) }));
      pre.textContent = r.out; e.target.disabled = false; if (r.ok) refreshInbox();
    });

    const drop = pane.querySelector('.drop');
    const input = drop.querySelector('input');
    const upload = async (files) => {
      const pre = pane.querySelector('.upout');
      pre.style.display = 'block'; pre.textContent = '';
      for (const f of files) {
        if (f.size > 35 * 1048576) { pre.textContent += `${f.name}: too large (35 MB max)\n`; continue; }
        pre.textContent += `uploading ${f.name}…\n`;
        const b64 = await new Promise((res) => { const rd = new FileReader(); rd.onload = () => res(String(rd.result).split(',')[1] || ''); rd.readAsDataURL(f); });
        const r = await api.rpc('POST', 'upload', { name: f.name, to: pane.querySelector('.to2').value.trim(), data: b64 }).catch((x) => ({ out: String(x) }));
        pre.textContent += r.ok ? `saved ${r.saved}\n` : `${f.name}: ${r.out}\n`;
      }
      pre.textContent += 'indexing…\n';
      const r = await api.rpc('POST', 'index').catch((x) => ({ out: String(x) }));
      pre.textContent += `${r.out}\n`; refreshInbox();
    };
    drop.addEventListener('click', () => input.click());
    input.addEventListener('change', () => upload([...input.files]));
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', (e) => { e.preventDefault(); drop.classList.remove('over'); upload([...e.dataTransfer.files]); });
  }

  async function refreshInbox() {
    const keep = pane.querySelector('.out')?.innerHTML;
    await refresh();
    if (keep && pane.querySelector('.out')) pane.querySelector('.out').innerHTML = keep;
  }
  refresh();
}

export function unmount(container) { container.innerHTML = ''; }
