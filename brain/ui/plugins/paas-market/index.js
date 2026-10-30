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

// Marketplace tab: search the VM's skills, agents and MCP servers; add / remove / update them for yourself (data: server.js).
// Other marketplaces root added (paas-market source add) are their own sections, closed until clicked.
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
.mk .nf{margin:14px 0;padding:18px 20px;gap:14px}
.mk .types{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.mk .types button{text-align:left;border:1px solid hsl(var(--border));border-radius:10px;background:hsl(var(--background));color:inherit;padding:10px 12px;cursor:pointer;font:inherit}
.mk .types button b{display:block;font-size:13.5px}.mk .types button span{color:hsl(var(--muted-foreground));font-size:12px}
.mk .types button.on{border-color:#8b5cf6;background:rgba(124,58,237,.12);box-shadow:0 0 0 1px #8b5cf6}
.mk .fields{display:grid;grid-template-columns:1fr 2fr;gap:12px}
.mk label,.mk .lbl{display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:600;color:hsl(var(--muted-foreground))}
.mk label.wide,.mk .lbl.wide{grid-column:1/-1}
.mk .nf input,.mk .nf textarea{background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:8px;padding:8px 11px;color:hsl(var(--foreground));font:400 13.5px/1.45 Inter,ui-sans-serif,system-ui,sans-serif;width:100%;box-sizing:border-box}
.mk .nf input::placeholder,.mk .nf textarea::placeholder{color:hsl(var(--muted-foreground));opacity:.6}
.mk .nf textarea{font:12.5px/1.55 ui-monospace,Menlo,monospace;resize:vertical;min-height:150px}
.mk .nf input:focus,.mk .nf textarea:focus{outline:none;border-color:#8b5cf6;box-shadow:0 0 0 3px rgba(124,58,237,.2)}
.mk .nf .acts{padding-top:0}.mk .nst{color:#f87171}
.mk .tm{display:flex;gap:6px;flex-wrap:wrap}.mk .tm button{border:1px solid hsl(var(--border));background:hsl(var(--background));color:inherit;border-radius:8px;padding:5px 10px;font:500 12.5px/1.4 inherit;cursor:pointer}
.mk .tm button.on{border-color:#8b5cf6;background:rgba(124,58,237,.12)}
.mk .sec{margin-bottom:10px}.mk .sec>.sh{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid hsl(var(--border));color:inherit;font:inherit;padding:10px 2px;cursor:pointer}
.mk .sec>.sh b{font-size:15px}.mk .sec>.sh .car{display:inline-block;transition:transform .15s;color:hsl(var(--muted-foreground))}
.mk .sec.open>.sh .car{transform:rotate(90deg)}.mk .sec>.grid{margin-top:12px}.mk .sec:not(.open)>.grid{display:none}
.mk .empty{padding:36px;text-align:center;color:hsl(var(--muted-foreground))}
@media (max-width:640px){.mk{padding:16px}.mk .grid,.mk .fields,.mk .types{grid-template-columns:1fr}}`;

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
    <div class="groups"><div class="empty">Loading…</div></div></div>`;
  const grid = container.querySelector('.groups');
  // sections: this VM's marketplace open; each other marketplace (paas-market source add) closed until clicked
  const opened = new Set(['']);
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
    const shown0 = items.filter((i) => (kind === 'all' || (kind === 'have' ? i.added || (i.author && i.author === me) : i.kind === kind))
      && words.every((w) => `${i.name} ${i.description} ${KIND[i.kind]} ${i.source_title || ''}`.toLowerCase().includes(w)));
    const card = (i) => { const mine = i.author && i.author === me; return `<div class="item${i.added || mine ? ' have' : ''}" data-id="${esc(i.id)}">
      <div><span class="tag">${KIND[i.kind]}</span>${mine ? '<span class="tag have">yours</span>' : i.author ? `<span class="tag">by ${esc(i.author)}</span>` : ''}${i.added ? '<span class="tag have">added</span>' : ''}${i.added && i.kind === 'plugin' && !i.enabled ? '<span class="tag upd">off</span>' : ''}${i.update ? '<span class="tag upd">update</span>' : ''}${i.ready ? '' : `<span class="tag upd">${i.kind === 'plugin' ? 'internet only' : 'not set up'}</span>`}${i.token_mode === 'personal' ? '<span class="tag">own token</span>' : ''}${i.risky ? `<span class="tag upd" title="${esc(i.risky)}">runs commands</span>` : ''}</div>
      <div class="t">${i.kind === 'skill' ? '/' : ''}${esc(i.name.split('@')[0])}</div><div class="d" title="${esc(i.description)}">${esc(i.description)}</div>
      <div class="acts">${mine ? '<button class="ghost" data-a="edit">Edit</button><button class="ghost" data-a="unshare">Unshare</button>'
        : `${i.added && i.kind === 'plugin' ? `<button class="ghost" data-a="toggle" data-on="${i.enabled ? 0 : 1}">${i.enabled ? 'Turn off' : 'Turn on'}</button>` : ''}${i.added ? `<button class="ghost" data-a="remove">Remove</button>${i.update ? '<button class="go" data-a="add">Update</button>' : ''}`
        : i.ready ? '<button class="go" data-a="add">Add</button>' : `<span class="sub">${i.kind === 'plugin' ? 'Needs the internet' : root ? '' : 'Root sets its address first'}</span>`}
        ${root && i.kind === 'mcp' && !i.author && !i.local ? '<button class="ghost" data-a="setup">Set up</button>' : ''}
        ${i.kind !== 'plugin' ? '<button class="ghost" data-a="view">View</button>' : ''}`}</div>
    </div>`; };
    const secs = [...new Set(['', ...items.map((i) => i.source || '')])];
    const title = (s) => (s ? (items.find((i) => i.source === s) || {}).source_title || s : 'This VM');
    grid.innerHTML = secs.map((s) => {
      const shown = shown0.filter((i) => (i.source || '') === s);
      const total = items.filter((i) => (i.source || '') === s).length;
      if (!shown.length && (words.length || kind !== 'all') && s) return '';
      const open = opened.has(s) || (words.length && shown.length);
      const added = shown.filter((i) => i.added).length;
      return `<div class="sec${open ? ' open' : ''}" data-s="${esc(s)}"><button class="sh"><span class="car">▸</span><b>${esc(title(s))}</b>
        <span class="sub">${shown.length === total ? total : `${shown.length} of ${total}`} items${added ? ` · ${added} added` : ''}${s ? ` · ${esc(s)}` : ''}</span></button>
        <div class="grid">${shown.map(card).join('') || `<div class="empty">${total ? 'Nothing matches' : 'The marketplace is empty'}</div>`}</div></div>`;
    }).join('') || '<div class="empty">Nothing matches</div>';
    grid.querySelectorAll('.sec>.sh').forEach((h) => h.addEventListener('click', () => {
      const sec = h.parentElement; const s = sec.dataset.s;
      if (sec.classList.toggle('open')) opened.add(s); else opened.delete(s);
    }));
    grid.querySelectorAll('[data-a]').forEach((b) => b.addEventListener('click', () => act(b.closest('.item'), b.dataset.a, b)));
  }

  async function act(card, a, btn) {
    const id = card.dataset.id;
    const it = items.find((x) => x.id === id) || {};
    if (a === 'setup') {
      if (card.querySelector('.setup')) return;
      let mode = it.token_mode === 'none' || it.token_mode === 'personal' ? it.token_mode : 'shared';
      card.insertAdjacentHTML('beforeend', `<div class="setup"><input class="u" placeholder="http://host:8000/mcp" value="${esc(it.url || '')}">
        <div class="tm">${[['shared', 'One token for everyone'], ['personal', 'Each person their own'], ['none', 'No token']].map(([m, l]) => `<button type="button" data-m="${m}">${l}</button>`).join('')}</div>
        <input class="tk" type="password" placeholder="The token everyone uses">
        <div class="acts"><button class="go s">Save</button><span class="sub st"></span></div></div>`);
      const tk = card.querySelector('.tk');
      const pick = () => { card.querySelectorAll('.tm button').forEach((x) => x.classList.toggle('on', x.dataset.m === mode)); tk.style.display = mode === 'shared' ? '' : 'none'; };
      card.querySelectorAll('.tm button').forEach((x) => x.addEventListener('click', () => { mode = x.dataset.m; pick(); }));
      pick();
      card.querySelector('.s').addEventListener('click', async () => {
        const r = await api.rpc('POST', 'setup-mcp', { name: id.split('/')[1], url: card.querySelector('.u').value.trim(), mode, token: mode === 'shared' ? tk.value.trim() : '' })
          .catch((e) => ({ out: String(e.message || e) }));
        if (!r.ok) { card.querySelector('.st').textContent = r.out; return; }
        load();
      });
      return;
    }
    if (a === 'add' && it.token_mode === 'personal' && !it.added) {
      if (card.querySelector('.setup')) return;
      card.insertAdjacentHTML('beforeend', `<div class="setup"><input class="ptk" type="password" placeholder="Your own token (optional)">
        <div class="acts"><button class="go pa">Add</button><span class="sub st"></span></div></div>`);
      card.querySelector('.ptk').focus();
      card.querySelector('.pa').addEventListener('click', async (e) => {
        e.target.disabled = true;
        const r = await api.rpc('POST', 'add', { ids: [id], token: card.querySelector('.ptk').value.trim() }).catch((x) => ({ out: String(x.message || x) }));
        e.target.disabled = false;
        if (!r.ok) { card.querySelector('.st').textContent = r.out; return; }
        load();
      });
      return;
    }
    if (a === 'edit') { editForm(id); return; }
    if (a === 'view') {
      const v = await api.rpc('POST', 'view', { id }).catch((e) => ({ out: String(e.message || e) }));
      slot.innerHTML = `<div class="item nf"><div><div class="t">${esc(id)}${it.author ? ` <span class="sub">shared by ${esc(it.author)}</span>` : ''}</div>
        ${it.risky ? `<div class="sub" style="color:#d97706">Runs commands or uses tools without asking (${esc(it.risky)}): read it before you add it.</div>` : ''}</div>
        <textarea class="ex" rows="18" readonly spellcheck="false"></textarea><div class="acts"><button class="ghost ec">Close</button></div></div>`;
      slot.querySelector('.ex').value = v.ok ? v.out : v.out || 'Could not read it';
      slot.querySelector('.ec').addEventListener('click', () => { slot.innerHTML = ''; });
      slot.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    if (a === 'add' && it.author && it.author !== me && !window.confirm(`${id} was shared by ${it.author}${it.risky ? ` and runs commands or uses tools without asking (${it.risky})` : ''}. It works with your permissions. Add it?`)) return;
    if (a === 'unshare' && !window.confirm(`Take ${id} out of the marketplace? People who added it keep their copy.`)) return;
    btn.disabled = true;
    const r = await api.rpc('POST', a, { ids: [id], on: btn.dataset.on === '1' }).catch((e) => ({ out: String(e.message || e) }));
    if (!r.ok) window.alert(r.out);
    await load();
  }

  const slot = container.querySelector('.newform');
  function newForm() {
    slot.innerHTML = `<div class="item nf"><div><div class="t">New for everyone</div>
      <div class="sub">Added to your own Claude and shared in the marketplace, where everyone can add it.</div></div>
      <div class="types">${[['skill', 'Skill', 'A playbook Claude follows'], ['agent', 'Agent', 'A helper Claude hands tasks to'], ['mcp', 'MCP server', 'A live data source']]
        .map(([k, t, d]) => `<button type="button" data-t="${k}" class="${k === 'skill' ? 'on' : ''}"><b>${t}</b><span>${d}</span></button>`).join('')}</div>
      <div class="fields">
        <label>Name<input class="nn" placeholder="e.g. vm-patching"></label>
        <label>Description<input class="nd" placeholder="What it does and when to use it"></label>
        <label class="wide f-skill"><span>Trigger phrases <i style="font-weight:400">(optional)</i></span><input class="nw" placeholder="e.g. patch the vms, vm patching"></label>
        <label class="f-agent"><span>Tools <i style="font-weight:400">(optional)</i></span><input class="nt" placeholder="e.g. Read, Grep, Bash"></label>
        <label class="f-agent"><span>Model <i style="font-weight:400">(optional)</i></span><input class="nm" placeholder="sonnet, opus or haiku (default: same as yours)"></label>
        <label class="f-mcp">Address<input class="nu" placeholder="http://host:8000/mcp"></label>
        <div class="lbl wide f-mcp">Token<div class="tm ntm">${[['shared', 'One token for everyone'], ['personal', 'Each person their own'], ['none', 'No token']].map(([m, l]) => `<button type="button" data-m="${m}">${l}</button>`).join('')}</div></div>
        <label class="wide f-mcp f-tok"><span class="ntl">The token everyone uses</span><input class="ntk" type="password"></label>
        <label class="wide f-body">Instructions (Markdown)<textarea class="nb" rows="8" placeholder="Steps, commands, checks, what to report"></textarea></label>
      </div>
      <div class="acts"><button class="go ns">Create and share</button><button class="ghost nc">Cancel</button><span class="sub nst"></span></div></div>`;
    let nk = 'skill';
    let ntm = 'shared';
    const tokLabel = { shared: 'The token everyone uses', personal: 'Your own token (optional, only you use it)' };
    const tmVis = () => {
      slot.querySelectorAll('.ntm button').forEach((x) => x.classList.toggle('on', x.dataset.m === ntm));
      slot.querySelector('.f-tok').style.display = nk === 'mcp' && ntm !== 'none' ? '' : 'none';
      slot.querySelector('.ntl').textContent = tokLabel[ntm] || '';
    };
    const v = (c) => slot.querySelector(c).value;
    const kindVis = () => {
      const show = { skill: ['f-skill', 'f-body'], agent: ['f-agent', 'f-body'], mcp: ['f-mcp'] }[nk];
      slot.querySelectorAll('.f-skill,.f-agent,.f-mcp,.f-body').forEach((el) => { el.style.display = show.some((c) => el.classList.contains(c)) ? '' : 'none'; });
      slot.querySelectorAll('.types button').forEach((x) => x.classList.toggle('on', x.dataset.t === nk));
    };
    slot.querySelectorAll('.types button').forEach((x) => x.addEventListener('click', () => { nk = x.dataset.t; kindVis(); tmVis(); }));
    slot.querySelectorAll('.ntm button').forEach((x) => x.addEventListener('click', () => { ntm = x.dataset.m; tmVis(); }));
    kindVis();
    tmVis();
    slot.querySelector('.nn').focus();
    slot.querySelector('.nc').addEventListener('click', () => { slot.innerHTML = ''; });
    slot.querySelector('.ns').addEventListener('click', async (e) => {
      e.target.disabled = true;
      const r = await api.rpc('POST', 'new', { kind: nk, name: v('.nn').trim(), description: v('.nd'), when: v('.nw'), tools: v('.nt'),
        model: v('.nm').trim(), url: v('.nu').trim(), token: ntm === 'none' ? '' : v('.ntk').trim(), token_mode: ntm, body: v('.nb') }).catch((x) => ({ out: String(x.message || x) }));
      e.target.disabled = false;
      if (!r.ok) { slot.querySelector('.nst').textContent = r.out; return; }
      slot.innerHTML = '';
      load();
    });
  }
  async function editForm(id) {
    const r = await api.rpc('POST', 'show', { id }).catch((e) => ({ out: String(e.message || e) }));
    if (!r.ok) { window.alert(r.out); return; }
    const mcp = id.startsWith('mcp/');
    const m = mcp ? JSON.parse(r.out) : null;
    slot.innerHTML = `<div class="item nf"><div><div class="t">Edit ${esc(id.replace('skill/', '/').replace(/^(agent|mcp)\//, ''))}</div>
      <div class="sub">Saved to your own Claude and to the marketplace. People who added it see an update.</div></div>
      <div class="fields">${mcp ? `
        <label class="wide">Description<input class="ed" value="${esc(m.description)}"></label>
        <label>Address<input class="eu" value="${esc(m.url)}"></label>
        <div class="lbl wide">Token<div class="tm etm">${[['shared', 'One token for everyone'], ['personal', 'Each person their own'], ['none', 'No token']].map(([m, l]) => `<button type="button" data-m="${m}">${l}</button>`).join('')}</div></div>
        <label class="e-tok"><span>Token <i style="font-weight:400">(${m.has_token ? 'blank keeps the current one' : 'optional'})</i></span><input class="et" type="password"></label>`
        : '<label class="wide">The file: header (name, description) between the --- lines, then the instructions<textarea class="ex" rows="18" spellcheck="false"></textarea></label>'}
      </div>
      <div class="acts"><button class="go es">Save</button><button class="ghost ec">Cancel</button><span class="sub nst"></span></div></div>`;
    if (!mcp) slot.querySelector('.ex').value = r.out;
    let etm = mcp ? m.token_mode : '';
    const etmVis = () => {
      slot.querySelectorAll('.etm button').forEach((x) => x.classList.toggle('on', x.dataset.m === etm));
      const t = slot.querySelector('.e-tok'); if (t) t.style.display = etm === 'none' ? 'none' : '';
    };
    slot.querySelectorAll('.etm button').forEach((x) => x.addEventListener('click', () => { etm = x.dataset.m; etmVis(); }));
    etmVis();
    slot.scrollIntoView({ behavior: 'smooth', block: 'start' });
    slot.querySelector('.ec').addEventListener('click', () => { slot.innerHTML = ''; });
    slot.querySelector('.es').addEventListener('click', async (e) => {
      e.target.disabled = true;
      const v = (c) => slot.querySelector(c).value;
      const body = mcp ? { id, description: v('.ed'), url: v('.eu').trim(), token: etm === 'none' ? '' : v('.et').trim(), token_mode: etm } : { id, text: v('.ex') };
      const s = await api.rpc('POST', 'edit', body).catch((x) => ({ out: String(x.message || x) }));
      e.target.disabled = false;
      if (!s.ok) { slot.querySelector('.nst').textContent = s.out; return; }
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
