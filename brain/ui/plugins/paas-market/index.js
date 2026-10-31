// >>> paas shared (generated from ../shared.js; edit that file and run sync-shared.py)
// Shared UI helpers for the tab plugins. Tabs are loaded through a Blob URL and cannot import siblings,
// so sync-shared.py pastes this block at the top of every index.js. Use: root element gets class "paas".
const PAAS_CSS = `
.paas{font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));padding:16px 28px 40px;max-width:1120px;margin:0 auto;box-sizing:border-box}
.paas *,.paas *::before,.paas *::after{box-sizing:border-box}
.paas h2{font-size:18px;font-weight:600;line-height:1.3;margin:0}
.paas h3{font-size:14px;font-weight:600;margin:0}
.paas .sub{color:hsl(var(--muted-foreground));font-size:13px}
.paas .head{display:flex;gap:8px 16px;flex-wrap:wrap;align-items:center;justify-content:space-between;padding:0 0 10px;margin-bottom:16px;border-bottom:1px solid hsl(var(--border))}
.paas .head>div:first-child{min-width:0;flex:1 1 320px;display:flex;gap:4px 12px;flex-wrap:wrap;align-items:baseline}.paas .head .sub{margin-top:0;max-width:70ch}
.paas .head .actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.paas .row{display:flex;gap:8px 12px;flex-wrap:wrap;align-items:center}
.paas .spread{display:flex;gap:8px 12px;flex-wrap:wrap;align-items:center;justify-content:space-between}
.paas .card{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:12px;padding:16px 20px;margin-top:16px;transition:border-color .15s}
.paas .card[data-id]:hover,.paas .grid .item:hover{border-color:hsl(var(--primary))}
.paas .grid .item.have{border-color:hsl(var(--primary));box-shadow:0 0 0 3px hsl(var(--ring)/.2)}
.paas .sec-label{margin:24px 0 8px;font:600 12px/1.4 inherit;color:hsl(var(--muted-foreground));text-transform:uppercase;letter-spacing:.08em}
.paas .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:36px;padding:0 16px;border:1px solid transparent;border-radius:10px;font:600 13px/1.4 inherit;cursor:pointer;color:hsl(222 47% 11%);background:var(--paas-gradient,hsl(var(--primary)));transition:opacity .15s,background-color .15s,border-color .15s}
.paas .btn:hover:not(:disabled){opacity:.92}
.paas .btn.ghost{background:none;color:hsl(var(--foreground));border-color:hsl(var(--border));font-weight:500}
.paas .btn.ghost:hover:not(:disabled){background:hsl(var(--accent));opacity:1}
.paas .btn.link{background:none;border-color:transparent;color:hsl(var(--primary));font-weight:500;padding:0 8px}
.paas .btn.link:hover:not(:disabled){background:hsl(var(--accent));opacity:1}
.paas .btn.danger{background:none;color:hsl(var(--destructive));border-color:hsl(var(--destructive))}
.paas .btn.danger.solid{background:hsl(var(--destructive));color:hsl(var(--background))}
.paas .btn.sm{min-height:30px;padding:0 12px;font-size:12px}
.paas .btn.link.sm{padding:0 8px}
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
.paas .tag,.paas .badge{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:500;line-height:18px;border-radius:999px;padding:0 8px;color:hsl(var(--muted-foreground));background:none;border:1px solid hsl(var(--border));white-space:nowrap}
.paas .tags{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.paas .pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;line-height:20px;border-radius:999px;padding:0 10px;color:hsl(var(--foreground));background:hsl(var(--muted))}
.paas .pill::before{content:'';width:8px;height:8px;border-radius:50%;background:currentColor;flex:none}
.paas .pill.ok::before{background:hsl(var(--primary))}
.paas .pill.warn{border:1px dashed hsl(var(--muted-foreground))}.paas .pill.warn::before{background:hsl(var(--muted-foreground));border-radius:2px}
.paas .pill.fail{color:hsl(var(--destructive));background:color-mix(in srgb,hsl(var(--destructive)) 12%,transparent)}.paas .pill.fail::before{border-radius:0;clip-path:polygon(50% 0,100% 100%,0 100%)}
.paas .table-wrap{overflow:auto;max-height:min(60vh,560px);-webkit-overflow-scrolling:touch}
.paas table{width:100%;border-collapse:collapse;font-size:14px}
.paas th,.paas td{padding:10px 12px;text-align:left;border-bottom:1px solid hsl(var(--border));vertical-align:middle}
.paas th{position:sticky;top:0;z-index:1;background:hsl(var(--card));color:hsl(var(--muted-foreground));font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.06em;white-space:nowrap}
.paas tr:last-child td{border-bottom:0}
.paas th.n,.paas td.n{text-align:right;font-variant-numeric:tabular-nums}
.paas .seg{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;border:1px solid hsl(var(--border));border-radius:10px;padding:3px;width:max-content;max-width:100%}
.paas .seg::-webkit-scrollbar,.paas .subtabs::-webkit-scrollbar{display:none}
.paas .seg button{flex:none;min-height:30px;padding:0 14px;border:0;border-radius:8px;background:none;color:hsl(var(--muted-foreground));font:500 13px/1.4 inherit;cursor:pointer;white-space:nowrap}
.paas .seg button:hover{color:hsl(var(--foreground))}
.paas .seg button[aria-pressed=true],.paas .seg button[aria-selected=true]{background:hsl(var(--accent));color:hsl(var(--foreground))}
.paas .subtabs{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;border-bottom:1px solid hsl(var(--border));margin-bottom:16px}
.paas .subtabs button{position:relative;flex:none;min-height:40px;padding:0 14px;border:0;background:none;color:hsl(var(--muted-foreground));font:500 14px/1.4 inherit;cursor:pointer;white-space:nowrap}
.paas .subtabs button:hover{color:hsl(var(--foreground))}
.paas .subtabs button[aria-selected=true]{color:hsl(var(--foreground));font-weight:600}
.paas .subtabs button[aria-selected=true]::after{content:'';position:absolute;left:10px;right:10px;bottom:-1px;height:2px;border-radius:2px;background:var(--paas-gradient,hsl(var(--primary)))}
.paas .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:16px}
.paas .tile{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:12px;padding:16px;min-width:0}
.paas .tile .k{font-size:12px;font-weight:500;color:hsl(var(--muted-foreground));text-transform:uppercase;letter-spacing:.06em}
.paas .tile .v{font-size:28px;line-height:1.2;font-weight:600;margin-top:4px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.paas .tile .v.sm{font-size:18px;line-height:1.5}
.paas .tile .v small,.paas .tile .u{font-size:13px;font-weight:400;color:hsl(var(--muted-foreground))}
.paas .tile .sub{margin-top:2px}
.paas .gauge{height:4px;border-radius:4px;background:hsl(var(--muted));margin-top:12px;overflow:hidden}
.paas .gauge i{display:block;height:100%;border-radius:4px;background:var(--paas-gradient,hsl(var(--primary)))}
.paas .gauge.warn i{background:hsl(var(--foreground)/.55)}.paas .gauge.fail i{background:hsl(var(--destructive))}
.paas .live{min-height:20px;font-size:13px;color:hsl(var(--muted-foreground))}
.paas .live:empty{min-height:0}
.paas .live.err,.paas .alert{color:hsl(var(--destructive))}
.paas .alert{border:1px solid hsl(var(--destructive));border-radius:12px;padding:14px 16px;margin-top:16px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between}
.paas .empty{padding:48px 16px;margin-top:16px;text-align:center;color:hsl(var(--muted-foreground));display:flex;flex-direction:column;gap:8px;align-items:center;max-width:46ch;margin-inline:auto}
.paas .empty .ei{width:48px;height:48px;border-radius:50%;background:hsl(var(--muted));color:hsl(var(--muted-foreground));display:grid;place-items:center;margin-bottom:4px}
.paas .empty .ei svg{width:22px;height:22px}
.paas .empty .et{font-size:15px;font-weight:600;color:hsl(var(--foreground))}
.paas .empty .btn{margin-top:8px}
.paas .skel{display:flex;flex-direction:column;gap:12px;margin-top:16px}
.paas .skel i{display:block;border-radius:8px;background:linear-gradient(90deg,hsl(var(--muted)) 25%,hsl(var(--muted-foreground)/.18) 50%,hsl(var(--muted)) 75%);background-size:200% 100%;animation:paas-shimmer 1.4s linear infinite}
.paas .skel .sk-card{border:1px solid hsl(var(--border));border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:10px;background:hsl(var(--card))}
.paas .skel .sk-card i:nth-child(1){height:14px;width:34%}.paas .skel .sk-card i:nth-child(2){height:12px;width:82%}.paas .skel .sk-card i:nth-child(3){height:12px;width:56%}
.paas .skel .sk-row{height:36px}.paas .skel .sk-head{height:14px;width:100%;opacity:.7}
@keyframes paas-shimmer{from{background-position:200% 0}to{background-position:-200% 0}}
.paas .confirm{border:1px solid hsl(var(--border));border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:8px;background:hsl(var(--card))}
.paas .confirm.danger{border-color:hsl(var(--destructive))}
.paas .confirm label{display:flex;gap:8px;align-items:flex-start;font-size:13px}
.paas .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.paas :focus-visible{outline:2px solid hsl(var(--ring));outline-offset:2px}
@media (pointer:coarse){.paas .btn,.paas .btn.sm,.paas .seg button,.paas .subtabs button,.paas .field input,.paas .field select{min-height:44px}.paas .confirm input[type=checkbox]{width:24px;height:24px}}
@media (max-width:640px){.paas{padding:16px 16px 32px}.paas .tiles{grid-template-columns:1fr 1fr;gap:10px}.paas .tile .v{font-size:24px}}
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
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
  file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 14 0M16 4.5a3.5 3.5 0 0 1 0 7M22 20a7 7 0 0 0-4-6.3"/>',
  box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
};
// icon('trash') -> inline SVG markup, decorative (put the words next to it)
const icon = (name) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name] || ''}</svg>`;

// header('Reports', 'Files your agents made', '<button class="btn">..</button>') -> markup: title + subtitle left, actions (optional) right, hairline under
const header = (title, subtitle, actions) => `<div class="head"><div><h2>${esc(title)}</h2>${subtitle ? `<div class="sub">${esc(subtitle)}</div>` : ''}</div>${actions ? `<div class="actions">${actions}</div>` : ''}</div>`;

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

// skeleton('cards'|'table'|'list') -> markup: shimmering blocks shaped like the content (static under reduced motion)
function skeleton(kind = 'cards') {
  const rows = (n, c) => Array.from({ length: n }, () => `<i class="${c}"></i>`).join('');
  const body = kind === 'table' ? `<i class="sk-head"></i>${rows(5, 'sk-row')}`
    : kind === 'list' ? rows(6, 'sk-row') : Array.from({ length: 3 }, () => '<div class="sk-card"><i></i><i></i><i></i></div>').join('');
  return `<div class="skel" role="status" aria-busy="true"><span class="sr">Loading</span>${body}</div>`;
}

// tags(['a', ['b', 'tooltip'], 'c'], 2) -> markup: at most max quiet outline tags, then a "+n" with the rest in its tooltip
const tags = (list, max = 2) => {
  const l = list.filter(Boolean).map((t) => (Array.isArray(t) ? t : [t, '']));
  const one = ([t, tip]) => `<span class="tag"${tip ? ` title="${esc(tip)}"` : ''}>${esc(t)}</span>`;
  return `<span class="tags">${l.slice(0, max).map(one).join('')}${l.length > max ? `<span class="tag" title="${esc(l.slice(max).map((x) => x[0]).join(', '))}">+${l.length - max}</span>` : ''}</span>`;
};

// emptyBlock('One line of help', 'Refresh', fn, {icon:'inbox', title:'No reports yet'}) -> element; button only when both label and handler are given
function emptyBlock(text, actionLabel, onAction, o = {}) {
  const b = el(`<div class="empty"><span class="ei">${icon(o.icon || 'inbox')}</span>${o.title ? `<span class="et">${esc(o.title)}</span>` : ''}<span>${esc(text)}</span></div>`);
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
const MODES = [['shared', 'One token for everyone'], ['personal', 'Each person their own'], ['none', 'No token']];
const TYPES = [['skill', 'Skill', 'A playbook Claude follows'], ['agent', 'Agent', 'A helper Claude hands tasks to'], ['mcp', 'MCP server', 'A live data source']];
const ACT_TEXT = { add: ['Adding...', 'Added'], remove: ['Removing...', 'Removed'], update: ['Updating...', 'Updated'], unshare: ['Working...', 'Unshared'], toggle: ['Working...', 'Done'] };

// tab-specific rules only; the rest comes from PAAS_CSS
const CSS = `
.mk .bar{margin:0 0 14px}
.mk .bar .field{flex:1 1 280px;margin:0}
.mk .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.mk .item{border:1px solid hsl(var(--border));border-radius:12px;padding:16px;background:hsl(var(--card));display:flex;flex-direction:column;gap:8px;transition:border-color .15s}
.mk .t{font-size:14px;font-weight:600}.mk .d{color:hsl(var(--muted-foreground));font-size:13px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.mk .acts{display:flex;gap:8px;margin-top:auto;padding-top:4px;flex-wrap:wrap;align-items:center}
.mk .setup{display:grid;gap:6px;margin-top:6px}
.mk .nf{margin:0 0 14px;gap:14px}
.mk .types{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.mk .types button{text-align:left;border:1px solid hsl(var(--border));border-radius:10px;background:hsl(var(--background));color:inherit;padding:10px 12px;cursor:pointer;font:inherit;min-height:44px}
.mk .types button b{display:block;font-size:13.5px}.mk .types button span{color:hsl(var(--muted-foreground));font-size:12px}
.mk .types button[aria-pressed=true]{border-color:hsl(var(--primary));background:hsl(var(--accent));box-shadow:0 0 0 1px hsl(var(--primary))}
.mk .types button[aria-pressed=true] b::before{content:'\\2713  '}
.mk .fields{display:grid;grid-template-columns:1fr 2fr;gap:0 12px}
.mk .fields .wide{grid-column:1/-1}
.mk .grp{margin:0 0 12px;padding:0;border:0;min-width:0}
.mk .grp>legend{font-weight:600;font-size:13px;padding:0;margin-bottom:4px}
.mk textarea.mono{font:12.5px/1.55 ui-monospace,Menlo,monospace;min-height:150px}
.mk .tm{display:flex;gap:6px;flex-wrap:wrap}
.mk .tm button{border:1px solid hsl(var(--border));background:hsl(var(--background));color:inherit;border-radius:8px;padding:5px 10px;font:500 13px/1.4 inherit;cursor:pointer;min-height:36px}
.mk .tm button[aria-checked=true]{border-color:hsl(var(--primary));background:hsl(var(--accent))}
.mk .tm button[aria-checked=true]::before{content:'\\2713  '}
.mk .sec{margin-bottom:10px}.mk .sec>.sh{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid hsl(var(--border));color:inherit;font:inherit;padding:10px 2px;cursor:pointer;min-height:44px}
.mk .sec>.sh b{font-size:14px}.mk .sec>.sh .car{display:inline-flex;transition:transform .15s;color:hsl(var(--muted-foreground))}
.mk .sec.open>.sh .car{transform:rotate(90deg)}.mk .sec>.grid{margin-top:12px}.mk .sec:not(.open)>.grid{display:none}
.mk .viewer{width:100%;font:12.5px/1.55 ui-monospace,Menlo,monospace;min-height:260px;background:hsl(var(--background));color:inherit;border:1px solid hsl(var(--input));border-radius:10px;padding:8px 12px}
@media (pointer:coarse){.mk .tm button{min-height:44px}.mk .acts{gap:10px}}
@media (max-width:640px){.mk .grid,.mk .fields,.mk .types{grid-template-columns:1fr}}`;

const TEAM_NOTE = "Team plugins carry the team's skills, agents and MCP servers; turning one on switches your team (Brain tab shows the details).";
let seq = 0;
// label + control with a real for/id pair; extra is the hint text
const field = (label, control, cls = '', hint = '') => { const id = `mk${++seq}`; return `<div class="field ${cls}"><label for="${id}">${label}</label>${control.replace(/^<(\w+)/, `<$1 id="${id}"`)}${hint ? `<span class="hint" id="${id}h">${hint}</span>` : ''}</div>`; };
const tmHtml = (cls, label) => `<div class="grp ${cls.includes('wide') ? 'wide' : ''}"><div class="sub" style="font-weight:600;margin-bottom:4px" id="${cls}l">${label}</div><div class="tm ${cls}" role="radiogroup" aria-labelledby="${cls}l">${MODES.map(([m, l]) => `<button type="button" role="radio" aria-checked="false" data-m="${m}">${l}</button>`).join('')}</div></div>`;
const setRadio = (root, m) => root.querySelectorAll('button[data-m]').forEach((x) => x.setAttribute('aria-checked', String(x.dataset.m === m)));
const msgOf = (e) => ({ ok: false, out: String(e.message || e) });
const goTo = (n, block) => n.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block });

export function mount(container, api) {
  let items = [];
  let root = false;
  let me = '';
  let kind = 'all';
  container.innerHTML = `<style>${PAAS_CSS}${CSS}</style><div class="paas mk">${header('Marketplace', 'Skills, agents, MCP servers and plugins on this VM. Add what you need: it goes into your own Claude only.', '<span class="slot"></span>')}
    <div class="stwrap"></div>
    <div class="newform"></div>
    <div class="row bar"><div class="field"><label for="mkq">Search the marketplace</label><input id="mkq" class="q" type="search" placeholder="Search: ontap, latency, zoning, capacity..."></div>
    <div class="seg" role="group" aria-label="Show">${[['all', 'All'], ['skill', 'Skills'], ['agent', 'Agents'], ['mcp', 'MCP servers'], ['plugin', 'Plugins'], ['have', 'Mine']].map(([v, l]) => `<button type="button" data-k="${v}" aria-pressed="${v === kind}">${l}</button>`).join('')}</div></div>
    <div class="groups">${skeleton('cards')}</div></div>`;
  container.querySelector('.actions').insertAdjacentHTML('beforeend', `<button type="button" class="btn ghost upd-all" style="display:none">Update all</button><button type="button" class="btn new">${icon('plus')} New</button>`);
  const st = statusLine(container.querySelector('.stwrap'));
  const grid = container.querySelector('.groups');
  const slot = container.querySelector('.newform');
  const opened = new Set(['']);
  const q = container.querySelector('.q');
  const updAll = container.querySelector('.upd-all');

  async function load() {
    const r = await api.rpc('GET', 'list').catch(msgOf);
    if (!r.ok) { grid.replaceChildren(errorBlock(r.out, load)); return; }
    items = r.items; root = r.root; me = r.me;
    const n = items.filter((i) => i.update).length;
    updAll.style.display = n ? '' : 'none';
    updAll.textContent = `Update all (${n})`;
    render();
  }

  function render() {
    const words = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    const shown0 = items.filter((i) => (kind === 'all' || (kind === 'have' ? i.added || i.team || (i.author && i.author === me) : i.kind === kind))
      && words.every((w) => `${i.name} ${i.description} ${KIND[i.kind]} ${i.source_title || ''}`.toLowerCase().includes(w)));
    const card = (i) => { const mine = i.author && i.author === me; const teamItem = !!i.team && i.kind !== 'plugin'; const teamPlug = !!i.team && i.kind === 'plugin'; return `<div class="item${i.added || i.team || mine ? ' have' : ''}" data-id="${esc(i.id)}">
      ${tags([KIND[i.kind], mine ? 'yours' : i.author ? `by ${i.author}` : '', teamItem ? ['from your team', `Comes with the ${i.team} team plugin`] : teamPlug ? [`team ${i.team}`, 'Your team profile: switching it changes rules, skills, agents and MCP servers'] : i.added ? 'added' : '', i.update && !teamItem ? ['update available', 'A newer version is available'] : '', i.added && i.kind === 'plugin' && !i.enabled ? ['off', 'Added but switched off'] : '', i.ready ? '' : i.kind === 'plugin' ? ['needs internet', 'This VM is offline, so plugins cannot be fetched'] : ['waiting for admin', 'An admin has to enter the server address first'], i.token_mode === 'personal' ? ['asks for your token', 'Each person uses their own token'] : '', i.risky ? ['can run commands', i.risky] : ''], 3)}
      <div class="t">${i.kind === 'skill' ? '/' : ''}${esc(i.name.split('@')[0])}</div><div class="d" title="${esc(i.description)}">${esc(i.description)}</div>
      <div class="acts">${mine ? '<button type="button" class="btn ghost sm" data-a="edit">Edit</button><button type="button" class="btn ghost sm" data-a="unshare">Unshare</button>'
        : `${i.added && i.kind === 'plugin' ? `<button type="button" class="btn ghost sm" data-a="toggle" data-on="${i.enabled ? 0 : 1}">${i.enabled ? 'Turn off' : 'Turn on'}</button>` : ''}${i.added && !i.team ? `<button type="button" class="btn ghost danger sm" data-a="remove">Remove</button>${i.update ? '<button type="button" class="btn sm" data-a="add">Update</button>' : ''}`
        : i.added ? '' : i.ready ? '<button type="button" class="btn sm" data-a="add">Add</button>' : `<span class="sub">${i.kind === 'plugin' ? 'Needs internet (this VM is offline)' : root ? '' : 'Ask root to set it up'}</span>`}
        ${root && i.kind === 'mcp' && !i.author && !i.local ? '<button type="button" class="btn link sm" data-a="setup">Set up</button>' : ''}
        ${i.kind !== 'plugin' ? '<button type="button" class="btn link sm" data-a="view">View</button>' : ''}`}</div>
    </div>`; };
    const secs = [...new Set(['', ...items.map((i) => i.source || '')])];
    const title = (s) => (s ? (items.find((i) => i.source === s) || {}).source_title || s : 'This VM');
    grid.innerHTML = secs.map((s) => {
      const shown = shown0.filter((i) => (i.source || '') === s);
      const total = items.filter((i) => (i.source || '') === s).length;
      if (!shown.length && (words.length || kind !== 'all') && s) return '';
      const open = opened.has(s) || (words.length && shown.length);
      const added = shown.filter((i) => i.added).length;
      return `<div class="sec${open ? ' open' : ''}" data-s="${esc(s)}"><button type="button" class="sh" aria-expanded="${!!open}"><span class="car" aria-hidden="true">${icon('chevron')}</span><b>${esc(title(s))}</b>
        <span class="sub">${shown.length === total ? total : `${shown.length} of ${total}`} items${added ? ` · ${added} added` : ''}${s ? ` · ${esc(s)}` : ''}</span></button>
        <div class="grid">${shown.some((i) => i.team && i.kind === 'plugin') ? `<div class="sub" style="grid-column:1/-1">${esc(TEAM_NOTE)}</div>` : ''}${shown.map(card).join('') || `<div class="sub" style="padding:8px 0">${total ? 'Nothing matches' : 'The marketplace is empty'}</div>`}</div></div>`;
    }).join('') || emptyBlock('Try fewer words, or pick All above.', '', null, { icon: 'search', title: 'Nothing matches' }).outerHTML;
    grid.querySelectorAll('.sec>.sh').forEach((h) => h.addEventListener('click', () => {
      const sec = h.parentElement; const s = sec.dataset.s;
      const o = sec.classList.toggle('open');
      if (o) opened.add(s); else opened.delete(s);
      h.setAttribute('aria-expanded', String(o));
    }));
    grid.querySelectorAll('[data-a]').forEach((b) => b.addEventListener('click', () => act(b.closest('.item'), b.dataset.a, b)));
  }

  // reload the list but keep the page where it was
  async function reload() { const y = window.scrollY; await load(); window.scrollTo(0, y); }

  async function act(card, a, btn) {
    const id = card.dataset.id;
    const it = items.find((x) => x.id === id) || {};
    const short = id.split('/').pop();
    if (a === 'setup') {
      if (card.querySelector('.setup')) return;
      let mode = it.token_mode === 'none' || it.token_mode === 'personal' ? it.token_mode : 'shared';
      card.insertAdjacentHTML('beforeend', `<div class="setup">${field('Address', `<input class="u" autocomplete="off" placeholder="http://host:8000/mcp" value="${esc(it.url || '')}">`)}
        ${tmHtml('tm', 'Token')}
        ${field('Token (shared by everyone)', '<input class="tk" type="password" autocomplete="new-password">', 'tkf')}
        <div class="acts"><button type="button" class="btn sm s">Save</button><button type="button" class="btn ghost sm cx">Cancel</button><span class="sub st" role="alert"></span></div></div>`);
      const box = card.querySelector('.setup');
      const tk = card.querySelector('.tk');
      const pick = () => { setRadio(box, mode); box.querySelector('.tkf').style.display = mode === 'shared' ? '' : 'none'; };
      box.querySelectorAll('.tm button').forEach((x) => x.addEventListener('click', () => { mode = x.dataset.m; pick(); }));
      pick();
      const save = async () => {
        const sb = box.querySelector('.s');
        if (sb.disabled) return;
        const done = busy(sb, 'Saving...');
        const r = await api.rpc('POST', 'setup-mcp', { name: id.split('/')[1], url: box.querySelector('.u').value.trim(), mode, token: mode === 'shared' ? tk.value.trim() : '' }).catch(msgOf);
        done();
        if (!r.ok) { box.querySelector('.st').textContent = r.out; return; }
        st.say(`Saved the address for ${short}.`);
        reload();
      };
      box.querySelector('.s').addEventListener('click', save);
      box.querySelector('.cx').addEventListener('click', () => { box.remove(); btn.focus(); });
      box.querySelectorAll('input').forEach((i) => i.addEventListener('keydown', (e) => { if (e.key === 'Enter') save(); }));
      box.querySelector('.u').focus();
      return;
    }
    if (a === 'add' && it.token_mode === 'personal' && !it.added) {
      if (card.querySelector('.setup')) return;
      card.insertAdjacentHTML('beforeend', `<div class="setup">${field('Your token (optional)', '<input class="ptk" type="password" autocomplete="new-password">', '', 'Only you use it.')}
        <div class="acts"><button type="button" class="btn sm pa">Add</button><button type="button" class="btn ghost sm cx">Cancel</button><span class="sub st" role="alert"></span></div></div>`);
      const box = card.querySelector('.setup');
      const add = async () => {
        const pb = box.querySelector('.pa');
        if (pb.disabled) return;
        const done = busy(pb, 'Adding...');
        const r = await api.rpc('POST', 'add', { ids: [id], token: box.querySelector('.ptk').value.trim() }).catch(msgOf);
        done();
        if (!r.ok) { box.querySelector('.st').textContent = r.out; return; }
        st.say(`Added ${short}. Start a new chat to use it.`);
        reload();
      };
      box.querySelector('.pa').addEventListener('click', add);
      box.querySelector('.cx').addEventListener('click', () => { box.remove(); btn.focus(); });
      box.querySelector('.ptk').addEventListener('keydown', (e) => { if (e.key === 'Enter') add(); });
      box.querySelector('.ptk').focus();
      return;
    }
    if (a === 'edit') { editForm(id); return; }
    if (a === 'view') {
      const done = busy(btn, 'Opening...');
      const v = await api.rpc('POST', 'view', { id }).catch(msgOf);
      done();
      const risk = it.risky ? `<div class="sub">Runs commands or uses tools without asking (${esc(it.risky)}): read it before you add it.</div>` : '';
      slot.innerHTML = `<div class="card nf"><div><h3>${esc(id)}${it.author ? ` <span class="sub">shared by ${esc(it.author)}</span>` : ''}</h3>${risk}</div>
        ${v.ok ? '<textarea class="viewer" rows="18" readonly spellcheck="false" aria-label="File contents"></textarea>' : `<div class="alert" role="alert">${esc(v.out || 'Could not read it')}</div>`}
        <div class="acts"><button type="button" class="btn ghost sm ec">Close</button></div></div>`;
      if (v.ok) slot.querySelector('.viewer').value = v.out;
      const close = () => { slot.innerHTML = ''; goTo(card, 'nearest'); btn.focus(); };
      slot.querySelector('.ec').addEventListener('click', close);
      slot.onkeydown = (e) => { if (e.key === 'Escape') close(); };
      goTo(slot, 'start');
      slot.querySelector('.ec').focus();
      return;
    }
    // confirmations (inline, no native dialogs)
    let ask = null;
    if (a === 'remove' && it.kind === 'mcp' && it.token_mode === 'personal') ask = { title: `Remove ${short}?`, text: 'Your copy and your token are deleted. You can add it again, but you will need to enter the token again.', confirmLabel: 'Remove', danger: true };
    else if (a === 'add' && it.author && it.author !== me) ask = { title: `Add ${short}?`, text: `Shared by ${it.author}${it.risky ? `. It runs commands or uses tools without asking (${it.risky})` : ''}. It works with your permissions.`, confirmLabel: 'Add' };
    else if (a === 'unshare') ask = { title: `Take ${short} out of the marketplace?`, text: 'People who added it keep their copy.', confirmLabel: 'Unshare', danger: true };
    if (ask && !(await confirmInline(btn, ask)).ok) return;
    const [doing, did] = ACT_TEXT[a] || ACT_TEXT.toggle;
    const upd = a === 'add' && btn.textContent.trim() === 'Update';
    const done = busy(btn, upd ? 'Updating...' : doing);
    const r = await api.rpc('POST', a, { ids: [id], on: btn.dataset.on === '1' }).catch(msgOf);
    done();
    if (!r.ok) { st.error(r.out); return; }
    st.say(a === 'toggle' ? `Turned ${btn.dataset.on === '1' ? 'on' : 'off'} ${short}.` : `${upd ? 'Updated' : did} ${short}.${a === 'add' ? ' Start a new chat to use it.' : ''}`);
    await reload();
  }

  function newForm() {
    slot.innerHTML = `<div class="card nf"><div><h3>New for everyone</h3>
      <div class="sub">Added to your own Claude and shared in the marketplace, where everyone can add it.</div></div>
      <div class="types" role="group" aria-label="What are you creating">${TYPES.map(([k, t, d]) => `<button type="button" data-t="${k}" aria-pressed="${k === 'skill'}"><b>${t}</b><span>${d}</span></button>`).join('')}</div>
      <div class="fields">
        ${field('Name', '<input class="nn" autocomplete="off" placeholder="e.g. vm-patching">', '', 'Lower-case letters, digits and dashes.')}
        ${field('Description', '<input class="nd" autocomplete="off" placeholder="What it does and when to use it">')}
        ${field('Trigger phrases (optional)', '<input class="nw" autocomplete="off" placeholder="e.g. patch the vms, vm patching">', 'wide f-skill')}
        ${field('Tools (optional)', '<input class="nt" autocomplete="off" placeholder="e.g. Read, Grep, Bash">', 'f-agent')}
        ${field('Model (optional)', '<input class="nm" autocomplete="off" placeholder="sonnet, opus or haiku">', 'f-agent', 'Default: same as yours.')}
        ${field('Address', '<input class="nu" autocomplete="off" placeholder="http://host:8000/mcp">', 'f-mcp')}
        <div class="wide f-mcp">${tmHtml('ntm', 'Token')}</div>
        ${field('<span class="ntl">The token everyone uses</span>', '<input class="ntk" type="password" autocomplete="new-password">', 'wide f-mcp f-tok')}
        ${field('Instructions (Markdown)', '<textarea class="nb mono" rows="8" placeholder="Steps, commands, checks, what to report"></textarea>', 'wide f-body')}
      </div>
      <div class="acts"><button type="button" class="btn ns">Create and share</button><button type="button" class="btn ghost nc">Cancel</button><span class="sub nst" role="alert"></span></div></div>`;
    let nk = 'skill';
    let ntm = 'shared';
    const tokLabel = { shared: 'The token everyone uses', personal: 'Your own token (optional, only you use it)' };
    const tmVis = () => {
      setRadio(slot.querySelector('.ntm'), ntm);
      slot.querySelector('.f-tok').style.display = nk === 'mcp' && ntm !== 'none' ? '' : 'none';
      slot.querySelector('.ntl').textContent = tokLabel[ntm] || '';
    };
    const v = (c) => slot.querySelector(c).value;
    const kindVis = () => {
      const show = { skill: ['f-skill', 'f-body'], agent: ['f-agent', 'f-body'], mcp: ['f-mcp'] }[nk];
      slot.querySelectorAll('.f-skill,.f-agent,.f-mcp,.f-body').forEach((n) => { n.style.display = show.some((c) => n.classList.contains(c)) ? '' : 'none'; });
      slot.querySelectorAll('.types button').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.t === nk)));
    };
    slot.querySelectorAll('.types button').forEach((x) => x.addEventListener('click', () => { nk = x.dataset.t; kindVis(); tmVis(); }));
    slot.querySelectorAll('.ntm button').forEach((x) => x.addEventListener('click', () => { ntm = x.dataset.m; tmVis(); }));
    kindVis();
    tmVis();
    slot.querySelector('.nn').focus();
    const close = () => { slot.innerHTML = ''; slot.onkeydown = null; container.querySelector('.new').focus(); };
    slot.querySelector('.nc').addEventListener('click', close);
    const create = async () => {
      const nb = slot.querySelector('.ns');
      if (nb.disabled) return;
      const done = busy(nb, 'Creating...');
      const r = await api.rpc('POST', 'new', { kind: nk, name: v('.nn').trim(), description: v('.nd'), when: v('.nw'), tools: v('.nt'),
        model: v('.nm').trim(), url: v('.nu').trim(), token: ntm === 'none' ? '' : v('.ntk').trim(), token_mode: ntm, body: v('.nb') }).catch(msgOf);
      done();
      if (!r.ok) { slot.querySelector('.nst').textContent = r.out; return; }
      const nm = v('.nn').trim();
      close();
      st.say(`Created and shared ${nm}. Start a new chat to use it.`);
      reload();
    };
    slot.querySelector('.ns').addEventListener('click', create);
    slot.onkeydown = (e) => {
      if (e.key === 'Escape') close();
      else if (e.key === 'Enter' && e.target.matches('input')) { e.preventDefault(); create(); }
    };
  }

  async function editForm(id) {
    const r = await api.rpc('POST', 'show', { id }).catch(msgOf);
    if (!r.ok) { st.error(r.out); return; }
    const mcp = id.startsWith('mcp/');
    const m = mcp ? JSON.parse(r.out) : null;
    slot.innerHTML = `<div class="card nf"><div><h3>Edit ${esc(id.replace('skill/', '/').replace(/^(agent|mcp)\//, ''))}</h3>
      <div class="sub">Saved to your own Claude and to the marketplace. People who added it see an update.</div></div>
      <div class="fields">${mcp ? `
        ${field('Description', `<input class="ed" value="${esc(m.description)}">`, 'wide')}
        ${field('Address', `<input class="eu" autocomplete="off" value="${esc(m.url)}">`)}
        <div class="wide">${tmHtml('etm', 'Token')}</div>
        ${field('Token', '<input class="et" type="password" autocomplete="new-password">', 'e-tok', m.has_token ? 'Leave blank to keep the current one.' : 'Optional.')}`
        : field('The file: header (name, description) between the --- lines, then the instructions', '<textarea class="ex mono" rows="18" spellcheck="false"></textarea>', 'wide')}
      </div>
      <div class="acts"><button type="button" class="btn es">Save</button><button type="button" class="btn ghost ec">Cancel</button><span class="sub nst" role="alert"></span></div></div>`;
    if (!mcp) slot.querySelector('.ex').value = r.out;
    let etm = mcp ? m.token_mode : '';
    const etmVis = () => {
      if (!mcp) return;
      setRadio(slot.querySelector('.etm'), etm);
      slot.querySelector('.e-tok').style.display = etm === 'none' ? 'none' : '';
    };
    slot.querySelectorAll('.etm button').forEach((x) => x.addEventListener('click', () => { etm = x.dataset.m; etmVis(); }));
    etmVis();
    goTo(slot, 'start');
    const close = () => { slot.innerHTML = ''; slot.onkeydown = null; };
    slot.querySelector('.ec').addEventListener('click', close);
    slot.onkeydown = (e) => { if (e.key === 'Escape') close(); };
    slot.querySelector('.es').addEventListener('click', async (e) => {
      const done = busy(e.currentTarget, 'Saving...');
      const v = (c) => slot.querySelector(c).value;
      const body = mcp ? { id, description: v('.ed'), url: v('.eu').trim(), token: etm === 'none' ? '' : v('.et').trim(), token_mode: etm } : { id, text: v('.ex') };
      const s = await api.rpc('POST', 'edit', body).catch(msgOf);
      done();
      if (!s.ok) { slot.querySelector('.nst').textContent = s.out; return; }
      close();
      st.say(`Saved ${id.split('/').pop()}.`);
      reload();
    });
  }
  container.querySelector('.new').addEventListener('click', newForm);

  // do not rebuild the list under an open setup form
  q.addEventListener('input', () => { if (!grid.querySelector('.setup')) render(); });
  container.querySelectorAll('.seg button').forEach((b) => b.addEventListener('click', () => {
    kind = b.dataset.k;
    container.querySelectorAll('.seg button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    render();
  }));
  updAll.addEventListener('click', async () => {
    const done = busy(updAll, 'Updating...');
    const r = await api.rpc('POST', 'update', {}).catch(msgOf);
    done();
    if (!r.ok) { st.error(r.out); return; }
    st.say('Updated everything that had a newer version.');
    reload();
  });
  load();
}

export function unmount(container) { container.innerHTML = ''; }
