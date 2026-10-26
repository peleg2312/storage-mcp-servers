// Users tab (root only): the people on this VM, add / password / lock / remove (data: server.js -> paas-user).
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const CSS = `
.us{font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));padding:28px;max-width:1000px;margin:0 auto}
.us h2{font-size:22px;font-weight:700;margin:0}.us .sub{color:hsl(var(--muted-foreground));font-size:13px}
.us .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;justify-content:space-between}
.us .card{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:14px;padding:6px 18px;margin-top:18px}
.us table{width:100%;border-collapse:collapse;font-size:13.5px}.us td,.us th{padding:10px 6px;text-align:left;border-bottom:1px solid hsl(var(--border)/.6)}
.us tr:last-child td{border-bottom:0}.us th{color:hsl(var(--muted-foreground));font-weight:500;font-size:12px}
.us .pill{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600;border-radius:999px;padding:1px 9px}
.us .pill::before{content:'';width:7px;height:7px;border-radius:50%;background:currentColor}
.us .ok{color:#16a34a;background:rgba(22,163,74,.12)}.us .off{color:#6b7280;background:rgba(107,114,128,.14)}.us .bad{color:#dc2626;background:rgba(220,38,38,.13)}
.us .go{border:0;border-radius:999px;padding:7px 18px;font:600 13px/1.4 inherit;cursor:pointer;color:#0b0d1a;background:linear-gradient(90deg,#a78bfa,#60a5fa,#22d3ee)}
.us .ghost{border:1px solid hsl(var(--border));background:none;color:inherit;border-radius:999px;padding:4px 12px;font:500 12px/1.4 inherit;cursor:pointer;margin:2px}
.us .ghost.danger{color:hsl(var(--destructive))}
.us .form{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;padding:14px 0}
.us label{font-weight:600;font-size:13px}.us input{display:block;width:100%;box-sizing:border-box;margin-top:4px;background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:10px;padding:8px 12px;color:inherit;font:inherit;font-weight:400}
@media (max-width:640px){.us{padding:16px}}`;

export function mount(container, api) {
  container.innerHTML = `<style>${CSS}</style><div class="us"><div class="row"><div><h2>Users</h2>
    <div class="sub">Each person signs in with their own VM account and gets their own chats, files, notes and marketplace items. You (root) can see everything.</div></div>
    <button class="go add">+ Add person</button></div><div class="form-slot"></div><div class="card"><div class="list sub" style="padding:14px 0">Loading…</div></div></div>`;
  const list = container.querySelector('.list');
  const slot = container.querySelector('.form-slot');

  async function load() {
    const r = await api.rpc('GET', 'list').catch((e) => ({ out: String(e.message || e) }));
    if (!r.ok) { list.textContent = r.out; return; }
    list.className = 'list';
    list.innerHTML = `<table><tr><th>Name</th><th>Home</th><th>Status</th><th></th></tr>${r.users.map((u) => `<tr data-n="${esc(u.name)}">
      <td><b>${esc(u.name)}</b></td><td class="sub">${esc(u.home)}</td>
      <td>${u.locked ? '<span class="pill bad">Locked</span>' : u.running ? '<span class="pill ok">Active</span>' : '<span class="pill off">Stopped</span>'}</td>
      <td style="text-align:right">${u.name === 'root' ? '' : `<button class="ghost" data-a="passwd">Password</button>
        <button class="ghost" data-a="${u.locked ? 'unlock' : 'lock'}">${u.locked ? 'Unlock' : 'Lock'}</button>
        <button class="ghost danger" data-a="remove">Remove</button>`}</td></tr>`).join('')}</table>`;
    list.querySelectorAll('[data-a]').forEach((b) => b.addEventListener('click', () => act(b.closest('tr').dataset.n, b.dataset.a, b)));
  }

  function passwordForm(title, name, onSave) {
    slot.innerHTML = `<div class="card"><div class="row" style="padding-top:12px"><b>${esc(title)}</b></div><div class="form">
      <label>Name<input class="f-n" value="${esc(name || '')}" ${name ? 'readonly' : 'placeholder="dana"'} autocomplete="off"></label>
      <label>Password<input class="f-p" type="password" autocomplete="new-password"></label>
      <label>Again<input class="f-p2" type="password" autocomplete="new-password"></label></div>
      <div class="row" style="padding-bottom:14px;justify-content:flex-start"><button class="go f-s">Save</button><button class="ghost f-c">Cancel</button><span class="sub f-st"></span></div></div>`;
    slot.querySelector('.f-c').addEventListener('click', () => { slot.innerHTML = ''; });
    slot.querySelector('.f-s').addEventListener('click', async (e) => {
      const n = slot.querySelector('.f-n').value.trim();
      const p = slot.querySelector('.f-p').value;
      if (p !== slot.querySelector('.f-p2').value) { slot.querySelector('.f-st').textContent = 'The two passwords differ'; return; }
      e.target.disabled = true;
      const r = await onSave(n, p).catch((x) => ({ out: String(x.message || x) }));
      e.target.disabled = false;
      if (!r.ok) { slot.querySelector('.f-st').textContent = r.out; return; }
      slot.innerHTML = '';
      load();
    });
  }

  async function act(n, a, btn) {
    if (a === 'passwd') return passwordForm(`New password for ${n}`, n, (name, password) => api.rpc('POST', 'passwd', { name, password }));
    let deleteHome = false;
    if (a === 'remove') {
      if (!window.confirm(`Remove ${n}? Their account and web UI are removed.`)) return;
      deleteHome = window.confirm(`Also delete ${n}'s home folder (chats, files, notes)? Cancel keeps it.`);
    }
    btn.disabled = true;
    const r = await api.rpc('POST', a, { name: n, deleteHome }).catch((x) => ({ out: String(x.message || x) }));
    if (!r.ok) window.alert(r.out);
    load();
  }

  container.querySelector('.add').addEventListener('click', () => passwordForm('Add a person', '', (name, password) => api.rpc('POST', 'add', { name, password })));
  load();
}

export function unmount(container) { container.innerHTML = ''; }
