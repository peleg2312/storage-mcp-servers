// Marketplace tab: search the VM's skills, agents and MCP servers; add / remove / update them for yourself (data: server.js).
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const KIND = { skill: 'Skill', agent: 'Agent', mcp: 'MCP server', plugin: 'Plugin' };

const CSS = `
.mk{font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));padding:28px;max-width:1100px;margin:0 auto}
.mk h2{font-size:22px;font-weight:700;margin:0}.mk .sub{color:hsl(var(--muted-foreground));font-size:13px}
.mk .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;justify-content:space-between}
.mk .bar{margin:18px 0 14px}
.mk input.q{flex:1 1 280px;background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:10px;padding:8px 12px;color:inherit;font:inherit}
.mk .seg{display:inline-flex;border:1px solid hsl(var(--border));border-radius:10px;overflow:hidden}
.mk .seg button{padding:7px 14px;background:none;border:0;color:hsl(var(--muted-foreground));cursor:pointer;font:inherit}
.mk .seg button.on{background:hsl(var(--accent));color:hsl(var(--foreground));font-weight:600}
.mk .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.mk .item{border:1px solid hsl(var(--border));border-radius:12px;padding:12px 14px;background:hsl(var(--card));display:flex;flex-direction:column;gap:6px}
.mk .item.have{border-color:rgba(124,58,237,.45)}
.mk .t{font-weight:600}.mk .d{color:hsl(var(--muted-foreground));font-size:13px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.mk .tag{display:inline-block;font-size:11px;padding:1px 8px;border-radius:999px;background:hsl(var(--accent));color:hsl(var(--muted-foreground));margin-right:6px}
.mk .tag.have{background:rgba(124,58,237,.15);color:#7c3aed}.mk .tag.upd{background:rgba(217,119,6,.15);color:#d97706}
.mk .acts{display:flex;gap:6px;margin-top:auto;padding-top:4px;flex-wrap:wrap}
.mk .go{border:0;border-radius:999px;padding:5px 16px;font:600 12.5px/1.4 inherit;cursor:pointer;color:#0b0d1a;background:linear-gradient(90deg,#a78bfa,#60a5fa,#22d3ee)}
.mk .ghost{border:1px solid hsl(var(--border));background:none;color:inherit;border-radius:999px;padding:4px 14px;font:500 12.5px/1.4 inherit;cursor:pointer}
.mk button:disabled{opacity:.5;cursor:default}
.mk .setup{display:grid;gap:6px;margin-top:6px}.mk .setup input{background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:8px;padding:6px 10px;color:inherit;font:13px inherit}
.mk .empty{padding:36px;text-align:center;color:hsl(var(--muted-foreground))}
@media (max-width:640px){.mk{padding:16px}.mk .grid{grid-template-columns:1fr}}`;

export function mount(container, api) {
  let items = [];
  let root = false;
  let me = '';
  let kind = 'all';
  container.innerHTML = `<style>${CSS}</style><div class="mk"><div class="row"><div><h2>Marketplace</h2>
    <div class="sub">Skills, agents, MCP servers and plugins on this VM. Add what you need: it goes into your own Claude only.</div></div>
    <div style="display:flex;gap:8px"><button class="ghost upd-all" style="display:none">Update all</button><button class="go new">+ New</button></div></div>
    <div class="newform"></div>
    <div class="row bar"><input class="q" type="search" placeholder="Search: ontap, latency, zoning, capacity…">
    <div class="seg">${[['all', 'All'], ['skill', 'Skills'], ['agent', 'Agents'], ['mcp', 'MCP servers'], ['plugin', 'Plugins'], ['have', 'Added']].map(([v, l]) => `<button data-k="${v}" class="${v === kind ? 'on' : ''}">${l}</button>`).join('')}</div></div>
    <div class="grid"><div class="empty">Loading…</div></div></div>`;
  const grid = container.querySelector('.grid');
  const q = container.querySelector('.q');
  const updAll = container.querySelector('.upd-all');

  async function load() {
    const r = await api.rpc('GET', 'list').catch((e) => ({ ok: false, out: String(e.message || e) }));
    if (!r.ok) { grid.innerHTML = `<div class="empty">${esc(r.out)}</div>`; return; }
    items = r.items; root = r.root; me = r.me;
    const n = items.filter((i) => i.update).length;
    updAll.style.display = n ? '' : 'none';
    updAll.textContent = `Update all (${n})`;
    render();
  }

  function render() {
    const words = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    const shown = items.filter((i) => (kind === 'all' || (kind === 'have' ? i.added : i.kind === kind))
      && words.every((w) => `${i.name} ${i.description} ${KIND[i.kind]}`.toLowerCase().includes(w)));
    grid.innerHTML = shown.map((i) => `<div class="item${i.added ? ' have' : ''}" data-id="${esc(i.id)}">
      <div><span class="tag">${KIND[i.kind]}</span>${i.author ? `<span class="tag">by ${esc(i.author)}</span>` : ''}${i.added ? '<span class="tag have">added</span>' : ''}${i.added && i.kind === 'plugin' && !i.enabled ? '<span class="tag upd">off</span>' : ''}${i.update ? '<span class="tag upd">update</span>' : ''}${i.ready ? '' : '<span class="tag upd">not set up</span>'}</div>
      <div class="t">${i.kind === 'skill' ? '/' : ''}${esc(i.name)}</div><div class="d" title="${esc(i.description)}">${esc(i.description)}</div>
      <div class="acts">${i.added && i.kind === 'plugin' ? `<button class="ghost" data-a="toggle" data-on="${i.enabled ? 0 : 1}">${i.enabled ? 'Turn off' : 'Turn on'}</button>` : ''}${i.added ? `<button class="ghost" data-a="remove">Remove</button>${i.update ? '<button class="go" data-a="add">Update</button>' : ''}`
        : i.ready ? '<button class="go" data-a="add">Add</button>' : `<span class="sub">${root ? '' : 'Root sets its address first'}</span>`}
        ${root && i.kind === 'mcp' && !i.author ? '<button class="ghost" data-a="setup">Set up</button>' : ''}
        ${i.author && i.author === me ? '<button class="ghost" data-a="unshare">Unshare</button>' : ''}</div>
    </div>`).join('') || `<div class="empty">${items.length ? 'Nothing matches' : 'The marketplace is empty'}</div>`;
    grid.querySelectorAll('[data-a]').forEach((b) => b.addEventListener('click', () => act(b.closest('.item'), b.dataset.a, b)));
  }

  async function act(card, a, btn) {
    const id = card.dataset.id;
    if (a === 'setup') {
      if (card.querySelector('.setup')) return;
      card.insertAdjacentHTML('beforeend', `<div class="setup"><input class="u" placeholder="http://host:8000/mcp"><input class="tk" type="password" placeholder="Bearer token (optional)">
        <div class="acts"><button class="go s">Save</button><span class="sub st"></span></div></div>`);
      card.querySelector('.s').addEventListener('click', async () => {
        const r = await api.rpc('POST', 'setup-mcp', { name: id.split('/')[1], url: card.querySelector('.u').value.trim(), token: card.querySelector('.tk').value.trim() })
          .catch((e) => ({ out: String(e.message || e) }));
        if (!r.ok) { card.querySelector('.st').textContent = r.out; return; }
        load();
      });
      return;
    }
    if (a === 'unshare' && !window.confirm(`Take ${id} out of the marketplace? People who added it keep their copy.`)) return;
    btn.disabled = true;
    const r = await api.rpc('POST', a, { ids: [id], on: btn.dataset.on === '1' }).catch((e) => ({ out: String(e.message || e) }));
    if (!r.ok) window.alert(r.out);
    await load();
  }

  const slot = container.querySelector('.newform');
  function newForm() {
    slot.innerHTML = `<div class="item" style="margin:14px 0"><div class="t">New for everyone</div>
      <div class="sub">It is added to your own Claude and shared in the marketplace, where everyone can add it.</div>
      <div class="setup"><select class="nk"><option value="skill">Skill: a playbook Claude follows</option><option value="agent">Agent: a helper Claude hands tasks to</option><option value="mcp">MCP server: a live data source</option></select>
        <input class="nn" placeholder="name, e.g. vm-patching">
        <input class="nd" placeholder="Description: what it does and when to use it">
        <div class="f-skill"><input class="nw" placeholder="Trigger phrases (optional), e.g. &quot;patch the vms&quot;"></div>
        <div class="f-agent" style="display:none"><input class="nt" placeholder="Tools (optional), e.g. Read, Grep, Bash"><input class="nm" placeholder="Model (optional): sonnet, opus, haiku" style="margin-top:6px"></div>
        <div class="f-mcp" style="display:none"><input class="nu" placeholder="http://host:8000/mcp"><input class="ntk" type="password" placeholder="Bearer token (optional)" style="margin-top:6px"></div>
        <textarea class="nb" rows="7" placeholder="Instructions (Markdown): steps, commands, checks, what to report" style="background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:8px;padding:8px 10px;color:inherit;font:12.5px/1.5 ui-monospace,Menlo,monospace"></textarea></div>
      <div class="acts"><button class="go ns">Create and share</button><button class="ghost nc">Cancel</button><span class="sub nst"></span></div></div>`;
    const v = (c) => slot.querySelector(c).value;
    const kindVis = () => {
      const k = v('.nk');
      slot.querySelector('.f-skill').style.display = k === 'skill' ? '' : 'none';
      slot.querySelector('.f-agent').style.display = k === 'agent' ? '' : 'none';
      slot.querySelector('.f-mcp').style.display = k === 'mcp' ? '' : 'none';
      slot.querySelector('.nb').style.display = k === 'mcp' ? 'none' : '';
    };
    slot.querySelector('.nk').addEventListener('change', kindVis);
    slot.querySelector('.nc').addEventListener('click', () => { slot.innerHTML = ''; });
    slot.querySelector('.ns').addEventListener('click', async (e) => {
      e.target.disabled = true;
      const r = await api.rpc('POST', 'new', { kind: v('.nk'), name: v('.nn').trim(), description: v('.nd'), when: v('.nw'), tools: v('.nt'),
        model: v('.nm').trim(), url: v('.nu').trim(), token: v('.ntk').trim(), body: v('.nb') }).catch((x) => ({ out: String(x.message || x) }));
      e.target.disabled = false;
      if (!r.ok) { slot.querySelector('.nst').textContent = r.out; return; }
      slot.innerHTML = '';
      load();
    });
  }
  container.querySelector('.new').addEventListener('click', newForm);

  q.addEventListener('input', render);
  container.querySelectorAll('.seg button').forEach((b) => b.addEventListener('click', () => {
    kind = b.dataset.k;
    container.querySelectorAll('.seg button').forEach((x) => x.classList.toggle('on', x === b));
    render();
  }));
  updAll.addEventListener('click', async () => {
    updAll.disabled = true;
    const r = await api.rpc('POST', 'update', {}).catch((e) => ({ out: String(e.message || e) }));
    updAll.disabled = false;
    if (!r.ok) window.alert(r.out);
    load();
  });
  load();
}

export function unmount(container) { container.innerHTML = ''; }
