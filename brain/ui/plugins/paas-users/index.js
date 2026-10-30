// >>> paas shared (generated from ../shared.js; edit that file and run sync-shared.py)
// Shared UI helpers for the tab plugins. Tabs are loaded through a Blob URL and cannot import siblings,
// so sync-shared.py pastes this block at the top of every index.js. Use: root element gets class "paas".
const PAAS_CSS = `
.paas{font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));padding:28px;max-width:1000px;margin:0 auto;box-sizing:border-box}
.paas *,.paas *::before,.paas *::after{box-sizing:border-box}
.paas h2{font-size:22px;font-weight:700;margin:0}
.paas h3{font-size:15px;font-weight:600;margin:0}
.paas .sub{color:hsl(var(--muted-foreground));font-size:13px}
.paas .head{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin-bottom:18px}
.paas .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.paas .spread{justify-content:space-between}
.paas .card{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:12px;padding:16px 18px;margin-top:16px}
.paas .btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:36px;padding:0 18px;border:0;border-radius:999px;font:600 13px/1.4 inherit;cursor:pointer;color:hsl(var(--primary-foreground));background:var(--paas-gradient,hsl(var(--primary)))}
.paas .btn.ghost{background:none;color:inherit;border:1px solid hsl(var(--border));font-weight:500}
.paas .btn.ghost:hover:not(:disabled){background:hsl(var(--accent))}
.paas .btn.danger{background:none;color:hsl(var(--destructive));border:1px solid hsl(var(--destructive))}
.paas .btn.danger.solid{background:hsl(var(--destructive));color:hsl(var(--background))}
.paas .btn.sm{min-height:30px;padding:0 12px;font-size:12px}
.paas .btn:disabled,.paas .btn[aria-busy=true]{opacity:.55;cursor:not-allowed}
.paas .btn[aria-busy=true]{cursor:progress}
.paas .btn svg,.paas .ico{width:16px;height:16px;flex:none;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.paas .field{display:flex;flex-direction:column;gap:4px;margin:0 0 12px}
.paas .field>label{font-weight:600;font-size:13px}
.paas .field input,.paas .field select,.paas .field textarea{width:100%;min-height:36px;padding:7px 12px;border:1px solid hsl(var(--input));border-radius:10px;background:hsl(var(--background));color:inherit;font:inherit}
.paas .field textarea{min-height:90px;resize:vertical}
.paas .field .hint{font-size:12px;color:hsl(var(--muted-foreground))}
.paas .field.invalid input,.paas .field.invalid select,.paas .field.invalid textarea{border-color:hsl(var(--destructive))}
.paas .field .error{font-size:12px;color:hsl(var(--destructive))}
.paas .tag,.paas .badge{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:500;border-radius:999px;padding:1px 9px;color:inherit;background:color-mix(in srgb,currentColor 10%,transparent);border:1px solid color-mix(in srgb,currentColor 25%,transparent)}
.paas .pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;border-radius:999px;padding:1px 10px;color:hsl(var(--foreground));background:hsl(var(--muted))}
.paas .pill::before{content:'';width:8px;height:8px;border-radius:50%;background:currentColor}
.paas .pill.ok::before{background:hsl(var(--primary))}
.paas .pill.warn{border:1px dashed hsl(var(--muted-foreground))}.paas .pill.warn::before{background:hsl(var(--muted-foreground));border-radius:2px}
.paas .pill.fail{color:hsl(var(--destructive));background:color-mix(in srgb,hsl(var(--destructive)) 12%,transparent)}.paas .pill.fail::before{border-radius:0;clip-path:polygon(50% 0,100% 100%,0 100%)}
.paas .table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
.paas table{width:100%;border-collapse:collapse;font-size:13.5px}
.paas th,.paas td{padding:10px 8px;text-align:left;border-bottom:1px solid hsl(var(--border)/.6);vertical-align:middle}
.paas th{color:hsl(var(--muted-foreground));font-weight:500;font-size:12px;white-space:nowrap}
.paas tr:last-child td{border-bottom:0}
.paas .seg,.paas .subtabs{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 24px),transparent);mask-image:linear-gradient(90deg,#000 calc(100% - 24px),transparent);padding-right:24px}
.paas .seg::-webkit-scrollbar,.paas .subtabs::-webkit-scrollbar{display:none}
.paas .seg{border:1px solid hsl(var(--border));border-radius:999px;padding:3px;width:max-content;max-width:100%}
.paas .seg button,.paas .subtabs button{flex:none;min-height:32px;padding:0 14px;border:0;border-radius:999px;background:none;color:hsl(var(--muted-foreground));font:500 13px/1.4 inherit;cursor:pointer;white-space:nowrap}
.paas .seg button[aria-pressed=true],.paas .seg button[aria-selected=true],.paas .subtabs button[aria-selected=true]{background:hsl(var(--accent));color:hsl(var(--foreground))}
.paas .live{min-height:20px;font-size:13px;color:hsl(var(--muted-foreground))}
.paas .live.err,.paas .alert{color:hsl(var(--destructive))}
.paas .alert{border:1px solid hsl(var(--destructive));border-radius:12px;padding:14px 16px;margin-top:16px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between}
.paas .empty{border:1px dashed hsl(var(--border));border-radius:12px;padding:28px 16px;margin-top:16px;text-align:center;color:hsl(var(--muted-foreground));display:flex;flex-direction:column;gap:12px;align-items:center}
.paas .confirm{border:1px solid hsl(var(--border));border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:8px;background:hsl(var(--card))}
.paas .confirm.danger{border-color:hsl(var(--destructive))}
.paas .confirm label{display:flex;gap:8px;align-items:flex-start;font-size:13px}
.paas .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.paas :focus-visible{outline:2px solid hsl(var(--ring));outline-offset:2px}
@media (pointer:coarse){.paas .btn,.paas .btn.sm,.paas .seg button,.paas .subtabs button,.paas .field input,.paas .field select{min-height:44px}.paas .confirm input[type=checkbox]{width:24px;height:24px}}
@media (max-width:640px){.paas{padding:16px}}
@media (prefers-reduced-motion:reduce){.paas *{animation:none!important;transition:none!important;scroll-behavior:auto!important}}`;

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmtSize = (n) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : n >= 1024 ? `${(n / 1024).toFixed(0)} KB` : `${n} B`);
const fmtTime = (ms) => new Date(ms).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });

// el('<div>..</div>') -> first element (html is trusted markup; pass user text through esc)
const el = (html) => { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstElementChild; };

const ICONS = {
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  warning: '<path d="M12 3 2 21h20L12 3zM12 10v5M12 18h.01"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
  external: '<path d="M14 4h6v6M20 4 10 14M18 14v6H4V6h6"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  unlock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7-2.6"/>',
  key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M16 7l3 3"/>',
  play: '<path d="M7 4v16l13-8z"/>',
  pause: '<path d="M8 4v16M16 4v16"/>',
  edit: '<path d="M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-5-5"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
};
// icon('trash') -> inline SVG markup, decorative (put the words next to it)
const icon = (name) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name] || ''}</svg>`;

// header('Reports', 'Files your agents made') -> markup; add buttons into .head after it if needed
const header = (title, subtitle) => `<div class="head"><div><h2>${esc(title)}</h2>${subtitle ? `<div class="sub">${esc(subtitle)}</div>` : ''}</div></div>`;

// errorBlock(message, onRetry) -> element: plain-words error with Try again
function errorBlock(message, onRetry) {
  const b = el(`<div class="alert" role="alert"><span>The UI server did not answer (${esc(message)})</span></div>`);
  if (onRetry) {
    const r = el(`<button type="button" class="btn ghost">${icon('refresh')}Try again</button>`);
    r.addEventListener('click', onRetry);
    b.append(r);
  }
  return b;
}

// emptyBlock('No reports yet', 'Refresh', fn) -> element; button only when both label and handler are given
function emptyBlock(text, actionLabel, onAction) {
  const b = el(`<div class="empty"><span>${esc(text)}</span></div>`);
  if (actionLabel && onAction) {
    const a = el(`<button type="button" class="btn ghost">${esc(actionLabel)}</button>`);
    a.addEventListener('click', onAction);
    b.append(a);
  }
  return b;
}

// statusLine(container) -> {say(text), error(text)}; two live regions that stay in the page (polite status, assertive alert)
function statusLine(container) {
  const s = el('<div class="live" role="status" aria-live="polite"></div>');
  const a = el('<div class="live err" role="alert" aria-live="assertive"></div>');
  container.append(s, a);
  return { say: (t) => { a.textContent = ''; s.textContent = t || ''; }, error: (t) => { s.textContent = ''; a.textContent = t || ''; } };
}

// confirmInline(button, {title, text, confirmLabel, danger, checkbox}) -> Promise<{ok, checked}>
// hides the button and shows the question in its place; Cancel has focus, Escape cancels; checkbox is a label string, unchecked at start
function confirmInline(button, o = {}) {
  return new Promise((resolve) => {
    const box = el(`<div class="confirm${o.danger ? ' danger' : ''}" role="group" aria-label="${esc(o.title || 'Confirm')}">
      ${o.title ? `<b>${esc(o.title)}</b>` : ''}${o.text ? `<span class="sub">${esc(o.text)}</span>` : ''}
      ${o.checkbox ? `<label><input type="checkbox"> <span>${esc(o.checkbox)}</span></label>` : ''}
      <div class="row"><button type="button" class="btn ghost sm c-no">Cancel</button>
      <button type="button" class="btn sm c-yes${o.danger ? ' danger solid' : ''}">${esc(o.confirmLabel || 'Confirm')}</button></div></div>`);
    const done = (ok) => {
      const checked = !!box.querySelector('input')?.checked;
      box.remove(); button.hidden = false; button.focus(); resolve({ ok, checked });
    };
    box.addEventListener('keydown', (e) => { if (e.key === 'Escape') { e.stopPropagation(); done(false); } });
    box.querySelector('.c-no').addEventListener('click', () => done(false));
    box.querySelector('.c-yes').addEventListener('click', () => done(true));
    button.hidden = true;
    button.after(box);
    box.querySelector('.c-no').focus();
  });
}

// const restore = busy(btn, 'Saving...'); try { await work } finally { restore() }
function busy(button, label) {
  const html = button.innerHTML;
  button.disabled = true; button.setAttribute('aria-busy', 'true');
  if (label) button.textContent = label;
  return () => { button.disabled = false; button.removeAttribute('aria-busy'); button.innerHTML = html; };
}
// <<< paas shared

// Users tab (root only): the people on this VM, add / password / lock / remove (data: server.js -> paas-user).

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
