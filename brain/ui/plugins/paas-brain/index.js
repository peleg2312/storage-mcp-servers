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

// Brain tab: search and grow the offline docs library, and see what this Claude knows and can do
// (skills, agents, MCP servers, hooks, memory files). Data: server.js.

const CSS = `
.paas .hk{display:flex;gap:16px;align-items:center;justify-content:space-between;padding:12px 8px;margin:0 -8px;border-top:1px solid hsl(var(--border));border-radius:8px}.paas .hk:hover{background:hsl(var(--accent)/.5)}
.paas .hk-t{min-width:0}
.paas .sw{position:relative;width:40px;height:22px;flex:none;cursor:pointer}.paas .sw input{opacity:0;width:0;height:0;position:absolute}
.paas .sw:after{content:'';position:absolute;inset:-11px -4px}
.paas .sw span{position:absolute;inset:0;border-radius:999px;background:hsl(var(--muted));border:1px solid hsl(var(--border));transition:.15s}
.paas .sw span:before{content:'';position:absolute;width:16px;height:16px;left:2px;top:2px;border-radius:50%;background:hsl(var(--background));box-shadow:0 1px 2px hsl(var(--foreground)/.25);transition:.15s}
.paas .sw input:checked+span{background:var(--paas-gradient,hsl(var(--primary)));border-color:transparent}.paas .sw input:checked+span:before{transform:translateX(18px)}
.paas .sw input:focus-visible+span{outline:2px solid hsl(var(--ring));outline-offset:2px}
.paas .res{padding:12px 0;border-bottom:1px solid hsl(var(--border))}.paas .res:last-child{border:0}
.paas .res a{color:hsl(var(--primary));font-weight:600;text-decoration:none}.paas .res a:hover{text-decoration:underline}
.paas .snip{color:hsl(var(--muted-foreground));font-size:13px;margin-top:4px;white-space:pre-wrap}.paas .snip b{color:hsl(var(--foreground))}
.paas .counts{margin:0 0 16px;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}
.paas .counts .tile{padding:8px 12px;display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}.paas .counts .tile .k{font-size:11px;flex:1 1 100%}.paas .counts .tile .v{font-size:18px;line-height:1.3;margin:0}.paas .counts .tile .u{font-size:12px}
.paas .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-top:8px}
.paas .item .row:last-child{margin-top:auto}
.paas .item{border:1px solid hsl(var(--border));border-radius:12px;padding:16px;background:hsl(var(--card));display:flex;flex-direction:column;gap:8px;transition:border-color .15s}
.paas .item .t{font-size:14px;font-weight:600}.paas .item .d{color:hsl(var(--muted-foreground));font-size:13px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.paas .drop{border:2px dashed hsl(var(--border));border-radius:12px;padding:22px;text-align:center;color:hsl(var(--muted-foreground));cursor:pointer}
.paas .drop.over{border-color:hsl(var(--ring));background:hsl(var(--accent))}.paas .drop[aria-disabled=true]{opacity:.5;cursor:progress}
.paas .two{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.paas pre{white-space:pre-wrap;font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:10px;padding:12px;max-height:520px;overflow:auto;margin:10px 0 0}
.paas code{font:12px ui-monospace,Menlo,monospace;overflow-wrap:anywhere}
.paas .field textarea.mt{min-height:420px;font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
.paas .field textarea.mono{font:12.5px/1.55 ui-monospace,Menlo,monospace}
.paas .sticky{position:sticky;bottom:0;background:hsl(var(--background));padding:10px 0;margin-top:10px}
.paas .bad{color:hsl(var(--destructive))}
.paas .grow{flex:1 1 220px}
@media (max-width:640px){.paas{padding:16px}.paas .grid,.paas .two{grid-template-columns:1fr}.paas pre{max-height:none}}`;

const TABS = [['docs', 'Docs library'], ['skills', 'Skills'], ['agents', 'Agents'], ['mcp', 'MCP & hooks'], ['memory', 'Memory']];
const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
const field = (label, input, hint) => `<div class="field"><label>${label}${hint ? ` <span class="sub">${hint}</span>` : ''}</label>${input}</div>`;

export function mount(container, api) {
  let data = null;
  let dirty = false;
  const keys = TABS.map((t) => t[0]);
  const fromHash = () => { const k = location.hash.replace(/^#brain-/, ''); return keys.includes(k) ? k : null; };
  let tab = fromHash() || (() => { try { const k = sessionStorage.getItem('paas-brain-tab'); return keys.includes(k) ? k : 'docs'; } catch { return 'docs'; } })();
  container.innerHTML = `<style>${PAAS_CSS}${CSS}</style><div class="paas">${header('Brain', 'Loading…')}
    <div class="note"></div><div class="tiles counts" hidden></div>
    <div class="subtabs tabs" role="tablist" aria-label="Brain sections">${TABS.map(([k, l]) =>
      `<button role="tab" data-k="${k}" aria-selected="${k === tab}" tabindex="${k === tab ? 0 : -1}">${l}</button>`).join('')}</div>
    <div class="guard"></div><div class="pane" role="tabpanel">${skeleton('cards')}</div></div>`;
  const pane = container.querySelector('.pane');
  const tabBtns = [...container.querySelectorAll('.tabs button')];
  const sub = container.querySelector('.head .sub');
  const SUB = 'Search the docs library and see what this Claude knows and can do.';
  // one place for page-level messages (share, delete, hooks); clears itself after 5s
  const note = statusLine(container.querySelector('.note'));
  let noteTimer;
  const say = (ok, t) => { clearTimeout(noteTimer); (ok ? note.say : note.error)(t); noteTimer = setTimeout(() => note.say(''), 5000); };

  async function setTab(k, focus) {
    if (k === tab) return;
    if (dirty) {
      const g = container.querySelector('.guard');
      const b = el('<button class="btn ghost sm" type="button">Switch section</button>');
      g.append(b);
      const r = await confirmInline(b, { title: 'Discard unsaved changes?', text: 'What you typed here has not been saved.', confirmLabel: 'Discard', danger: true });
      g.innerHTML = '';
      if (!r.ok) { tabBtns.find((x) => x.dataset.k === tab)?.focus(); return; }
    }
    tab = k; dirty = false; teamSynced = false;
    tabBtns.forEach((x) => { const on = x.dataset.k === k; x.setAttribute('aria-selected', on); x.tabIndex = on ? 0 : -1; if (on && focus) x.focus(); });
    try { history.replaceState(null, '', `#brain-${k}`); sessionStorage.setItem('paas-brain-tab', k); } catch { /* storage or history blocked */ }
    render();
  }
  tabBtns.forEach((b) => b.addEventListener('click', () => setTab(b.dataset.k)));
  container.querySelector('.tabs').addEventListener('keydown', (e) => {
    const i = keys.indexOf(tab);
    const j = { ArrowRight: (i + 1) % keys.length, ArrowLeft: (i + keys.length - 1) % keys.length, Home: 0, End: keys.length - 1 }[e.key];
    if (j === undefined) return;
    e.preventDefault(); setTab(keys[j], true);
  });
  const onHash = () => { const k = fromHash(); if (k) setTab(k, false); };
  window.addEventListener('hashchange', onHash);
  container._brainCleanup = () => window.removeEventListener('hashchange', onHash);
  pane.addEventListener('input', (e) => { if (e.target.matches('.mt,.f-name,.f-desc,.f-when,.f-body')) dirty = true; });

  async function refresh() {
    try { data = await api.rpc('GET', 'overview'); } catch (e) {
      sub.textContent = SUB;
      pane.replaceChildren(errorBlock(e.message || String(e), () => { sub.textContent = 'Loading…'; pane.innerHTML = skeleton('cards'); refresh(); }));
      return;
    }
    const docs = ((data.library.sources || '').split('\n')[0].match(/([\d,]+) documents/) || [])[1];
    const cnt = container.querySelector('.counts');
    cnt.innerHTML = [['Skills', data.skills.length, `incl. ${data.skills.filter((x) => x.mine).length} yours`], ['Agents', data.agents.length, ''], ['MCP servers', data.mcp.length, ''], ['Hooks', data.hooks.length, `${data.hooks.filter((h) => h.on).length} on`]]
      .map(([k, v, u]) => `<div class="tile"><div class="k">${k}</div><div class="v">${esc(v)}</div>${u ? `<div class="u">${u}</div>` : ''}</div>`).join('');
    cnt.hidden = false;
    sub.textContent = data.library.version ? `Library ${data.library.version}${docs ? ` · ${docs} documents` : ''}` : 'Docs library not installed on this VM';
    render();
  }

  function render() {
    if (!data) return;
    dirty = false;
    if (tab === 'docs') return renderDocs();
    if (tab === 'skills') return renderSkills();
    if (tab === 'agents') return renderAgents();
    if (tab === 'memory') return renderMemory();
    renderMcp();
  }

  function renderMcp() {
    pane.innerHTML = `<div class="card"><h3>MCP servers</h3><div class="sub" style="margin-bottom:8px">${data.mcp.length} connected tool servers</div>${data.mcp.length
      ? `<div class="table-wrap"><table><tr><th>Name</th><th>Type</th><th>Runs</th><th><span class="sr">Actions</span></th></tr>${data.mcp.map((m) => `<tr><td><b>${esc(m.name)}</b></td><td>${esc(m.type)}</td><td><code>${esc(m.target)}</code></td>
        <td>${data.canShare ? `<button class="btn link sm" data-share="mcp:${esc(m.name)}:0">Share with everyone</button>` : ''}</td></tr>`).join('')}</table></div>`
      : emptyBlock('Ask your admin to connect a tool server, or add one from the Marketplace.', '', null, { icon: 'box', title: 'No MCP servers configured' }).outerHTML}
      <div class="row" style="margin-top:10px"><button class="btn ghost sm chk">${icon('play')} Check connections</button><span class="sub">runs <code>claude mcp list</code></span></div><pre class="st" role="status" style="display:none"></pre></div>
      <div class="card"><h3>Hooks</h3><div class="sub" style="margin-bottom:10px">Small helpers that run around Claude's steps. Switching one off applies to your chats only.</div>${data.hooks.length ? data.hooks.map((h) => `<div class="hk">
        <div class="hk-t"><b>${esc(h.title)}</b> <span class="badge">${h.source === 'shared' ? 'shared' : 'yours'}</span>
        <div class="sub">${esc(h.about || h.command)}</div><div class="sub">${esc(h.when)}${h.matcher !== '*' ? ` · <code>${esc(h.matcher)}</code>` : ''}</div></div>
        ${h.canToggle ? `<label class="sw"><input type="checkbox" role="switch" aria-label="${esc(h.title)}" data-hk="${esc(h.id)}" ${h.on ? 'checked' : ''}><span></span></label>`
          : `<span class="sub">${h.id === 'block-write-tools' ? 'Always on: keeps your storage read-only' : 'Set by root'}</span>`}</div>`).join('')
        : emptyBlock('Hooks are small helpers that run around Claude\'s steps.', '', null, { icon: 'play', title: 'No hooks set up' }).outerHTML}</div>`;
    wireShare(renderMcp);
    pane.querySelectorAll('[data-hk]').forEach((cb) => cb.addEventListener('change', async () => {
      cb.disabled = true;
      try { data.hooks = (await api.rpc('POST', 'hooks', { id: cb.dataset.hk, on: cb.checked })).hooks; } catch (e) { cb.checked = !cb.checked; say(false, `Could not change it: ${e.message || e}`); }
      renderMcp();
    }));
    pane.querySelector('.chk').addEventListener('click', async (e) => {
      const b = e.currentTarget; const pre = pane.querySelector('.st'); const done = busy(b, 'Checking…');
      pre.style.display = 'block'; pre.textContent = 'Checking every server (can take a minute)…';
      const r = await api.rpc('GET', 'mcp-status').catch((x) => ({ out: String(x) }));
      pre.textContent = r.out || '(no output)'; done();
    });
  }

  // Team card (top of Memory): which team profile this chat uses, switch it, sync its knowledge (GET/POST team, team-sync)
  let teamMsg = null;
  let teamSynced = false;                                   // the quiet background sync runs once per opening of Memory
  async function renderTeam(box) {
    const t = await api.rpc('GET', 'team').catch((e) => ({ installed: true, error: e.message || String(e) }));
    if (!box.isConnected) return;
    if (!t.installed) { box.innerHTML = '<div class="sub" style="margin-bottom:12px">Team profiles are not installed on this VM.</div>'; return; }
    const teams = [...(t.teams || [])].sort((a, b) => Number(!!b.local) - Number(!!a.local));
    const cur = teams.find((x) => x.name === t.active);
    box.innerHTML = `<div class="card"><h3>Team</h3>${t.error ? `<div class="sub bad" role="alert">${esc(t.error)}</div>` : `
      <div class="sub" style="margin-bottom:10px">${cur ? `<b>${esc(cur.title || cur.name)}</b> (${esc(cur.name)}) · ${esc(t.mode || 'files')} mode · ${esc(cur.skills ?? 0)} skills, ${esc(cur.agents ?? 0)} agents` : 'No team is active.'}</div>
      ${field('Team', `<select class="tsel" aria-label="Team"><option value="none" ${t.active ? '' : 'selected'}>No team (your own skills and rules)</option>${teams.map((x) => `<option value="${esc(x.name)}" ${x.name === t.active ? 'selected' : ''}>${esc(x.title || x.name)} (${esc(x.name)})${x.local ? '' : ' (not added yet)'}</option>`).join('')}</select>`)}
      <div class="row" style="margin-bottom:10px"><span class="sub grow">${cur ? (cur.remote ? `Git remote: <code>${esc(cur.remote)}</code>` : 'No git remote: the knowledge stays on this VM') : ''}</span>${cur?.remote ? '<button type="button" class="btn ghost sm tcp">Copy</button>' : ''}</div>
      <div class="row"><button type="button" class="btn tsw">Switch</button>${cur ? '<button type="button" class="btn ghost tsy">Sync knowledge</button><button type="button" class="btn ghost tdl">Download plugin (zip)</button>' : ''}<span class="stbox"></span><span class="opn"></span></div>
      <details class="tadd" style="margin-top:12px"><summary>Add a team from a git url</summary>
        ${field('Name', '<input class="ta-name" aria-label="Team name" placeholder="san" autocomplete="off" spellcheck="false">', 'lower-case letters, digits, dashes')}
        ${field('Git url', '<input class="ta-url" aria-label="Git url" placeholder="https://gitlab.example.com/team/brain.git" autocomplete="off" spellcheck="false">')}
        <div class="row"><button type="button" class="btn ta-go">Add</button></div></details>`}</div>`;
    if (t.error) return;
    const st = statusLine(box.querySelector('.stbox'));
    const lead = teamMsg ? `${teamMsg} ` : '';
    if (teamMsg) { st.say(teamMsg); teamMsg = null; }
    const sw = box.querySelector('.tsw');
    sw?.addEventListener('click', async () => {
      const name = box.querySelector('.tsel').value; const x = teams.find((y) => y.name === name) || { local: true };
      if (name === (t.active || 'none')) { st.say(name === 'none' ? 'Already using your own skills and rules.' : 'Already using this team.'); return; }
      const r0 = await confirmInline(sw, name === 'none'
        ? { title: 'Switch to no team?', text: 'Your next chat uses your own copies of the rules; the team\'s skills leave. Your own and marketplace skills stay.', confirmLabel: 'Switch' }
        : { title: `Switch to ${x.title || name}?`, text: `Your next Claude chat uses this team's rules and skills.${dirty ? ' Unsaved edits below are lost.' : ''}${x.local ? '' : ' It is added first, which can take a few seconds.'}`, confirmLabel: 'Switch' });
      if (!r0.ok) return;
      const done = busy(sw, x.local ? 'Switching…' : 'Adding…'); st.say('');
      const r = await api.rpc('POST', 'team', { name }).catch((e) => ({ out: String(e) }));
      done();
      if (!r.ok) { st.error(`Not switched: ${r.out || 'unknown error'}`); return; }
      teamMsg = name === 'none' ? 'Switched to no team. Start a new chat to use it.' : `Switched to ${x.title || name}. Start a new chat to use it.`;
      teamSynced = false;
      refresh();
    });
    box.querySelector('.tsy')?.addEventListener('click', async (e) => {
      const done = busy(e.currentTarget, 'Syncing…'); st.say('');
      const r = await api.rpc('POST', 'team-sync').catch((x) => ({ out: String(x) }));
      done();
      if (r.ok) st.say(r.out || 'Synced.'); else st.error(`Not synced: ${r.out || 'unknown error'}`);
    });
    box.querySelector('.tcp')?.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(cur.remote); st.say('Copied'); } catch { st.say('Could not copy: select the url and copy it by hand.'); }
    });
    box.querySelector('.tdl')?.addEventListener('click', async (e) => {
      const done = busy(e.currentTarget, 'Preparing…'); st.say('');
      const r = await api.rpc('POST', 'team-export', { name: cur.name }).catch((x) => ({ out: String(x) }));
      done();
      if (!r.ok) { st.error(`Not saved: ${r.out || 'unknown error'}`); return; }
      st.say(`Saved ${String(r.file || '').split('/').pop()} under Reports`);
      if (typeof api.openTab === 'function') {
        const o = el('<button type="button" class="btn link sm">Open Reports</button>');
        o.addEventListener('click', () => api.openTab?.('paas-reports'));
        box.querySelector('.opn').replaceChildren(o);
      }
    });
    box.querySelector('.ta-go')?.addEventListener('click', async (e) => {
      const name = box.querySelector('.ta-name').value.trim(); const url = box.querySelector('.ta-url').value.trim();
      if (!name || !url) { st.error('Give a name and a git url.'); return; }
      const done = busy(e.currentTarget, 'Cloning…'); st.say('');
      const r = await api.rpc('POST', 'team-add', { name, url }).catch((x) => ({ out: String(x) }));
      done();
      if (!r.ok) { st.error(`Not added: ${r.out || 'unknown error'}`); return; }
      teamMsg = `Added ${name}. Pick it in the list and press Switch.`;
      renderTeam(box);
    });
    if (t.active && !teamSynced) {                       // quiet background sync: no spinner, no dialog
      teamSynced = true;
      api.rpc('POST', 'team-sync').then((r) => {
        if (!box.isConnected) return;
        const line = String(r.out || '').split('\n').filter(Boolean).pop() || (r.ok ? 'in sync' : 'no answer');
        st.say(`${lead}Sync: ${line}`);
      }).catch((x) => { if (box.isConnected) st.say(`${lead}Sync: ${x.message || x}`); });
    }
  }

  // Memory: notes.md / environment.md / tool-map.md are yours (kept by every install); CLAUDE.md is your own copy too
  function renderMemory(i = 0, cap = null) {
    const m = cap || data.memory[i];
    if (!m) { pane.replaceChildren(emptyBlock('Claude creates them the first time it saves a note.', '', null, { icon: 'file', title: 'No memory files found' })); return; }
    dirty = false;
    pane.innerHTML = `${cap ? '' : '<div class="teambox"></div>'}<div class="seg" role="group" aria-label="Memory file">${data.memory.map((x, k) => `<button data-i="${k}" aria-pressed="${k === i}">${esc(x.name)}</button>`).join('')}</div>
      <div class="sub" style="margin:12px 0 8px">${m.editable
        ? `What Claude reads at the start of every session. Edit and save; the previous version is kept as a .bak file.${m.name === 'CLAUDE.md' ? ' A brain update replaces this file: keep lasting facts in notes.md.' : ''}`
        : 'Shared file: only root changes it.'}</div>
      ${m.editable ? `${field(`${esc(m.name)}`, `<textarea class="mt" spellcheck="false">${esc(m.text)}</textarea>`)}
        <div class="row sticky"><button class="btn save">Save</button><button class="btn ghost hist">History</button><span class="stbox"></span></div><div class="histbox"></div>` : `<pre>${esc(m.text)}</pre>`}
      ${cap ? '' : `<div class="sub" style="margin:18px 0 8px"><b>Captures</b>: what Claude wrote down for later curation (ask it to "curate the captures").</div>
      ${(data.captures || []).length ? data.captures.map((c, k) => `<div class="row"><span class="grow">${esc(c.name)} <span class="sub">${esc(new Date(c.mtime).toLocaleDateString())} ${esc(c.text.split('\n')[0].replace(/^#+\s*/, '').slice(0, 80))}</span></span>
        <button class="btn ghost sm" data-open="${k}">Open</button><button class="btn danger sm" data-drop="${k}">Discard</button></div>`).join('')
        : '<div class="sub">Nothing captured yet. Claude writes a capture when it solves something worth keeping.</div>'}`}`;
    if (!cap) renderTeam(pane.querySelector('.teambox'));
    pane.querySelectorAll('.seg button').forEach((b) => b.addEventListener('click', () => renderMemory(Number(b.dataset.i))));
    pane.querySelectorAll('[data-open]').forEach((b) => b.addEventListener('click', () => {
      const c = data.captures[Number(b.dataset.open)]; renderMemory(0, { name: `captures/${c.name}`, editable: true, text: c.text });
    }));
    pane.querySelectorAll('[data-drop]').forEach((b) => b.addEventListener('click', async () => {
      const c = data.captures[Number(b.dataset.drop)];
      const r0 = await confirmInline(b, { title: `Discard capture ${c.name}?`, text: 'It is deleted; Claude will not see it again.', confirmLabel: 'Discard', danger: true });
      if (!r0.ok) return;
      const r = await api.rpc('POST', 'memory', { name: `captures/${c.name}`, remove: true }).catch((x) => ({ out: String(x) }));
      if (!r.ok) { say(false, r.out || 'Could not discard it'); return; }
      data.captures.splice(Number(b.dataset.drop), 1); renderMemory(i);
    }));
    const box = pane.querySelector('.stbox');
    if (!box) return;
    const st = statusLine(box);
    pane.querySelector('.mt').addEventListener('input', () => st.say('Unsaved changes'));
    pane.querySelector('.hist').addEventListener('click', async () => {
      const hb = pane.querySelector('.histbox');
      const r = await api.rpc('GET', `history?name=${encodeURIComponent(m.name)}`).catch((x) => ({ error: String(x) }));
      if (r.error) { st.error(`No history: ${r.error}`); return; }
      if (!r.repo) { hb.innerHTML = '<div class="sub">No history: the brain is not a git repository yet (re-run install.sh on the VM).</div>'; return; }
      hb.innerHTML = r.entries.length ? r.entries.map((x, k) => { const d = new Date(x.when * 1000).toLocaleString();
        return `<div class="row"><span class="grow">${esc(d)} <span class="sub">${esc(x.subject)}</span></span><button class="btn ghost sm" data-sha="${k}">Restore</button></div>`; }).join('')
        : '<div class="sub">No changes recorded yet.</div>';
      hb.querySelectorAll('[data-sha]').forEach((b) => b.addEventListener('click', async () => {
        const x = r.entries[Number(b.dataset.sha)]; const d = new Date(x.when * 1000).toLocaleString();
        if (!(await confirmInline(b, { title: `Restore ${m.name} from ${d}?`, text: 'The current text is kept in history.', confirmLabel: 'Restore' })).ok) return;
        const q = await api.rpc('POST', 'restore', { name: m.name, sha: x.sha }).catch((e) => ({ out: String(e) }));
        if (!q.ok) { st.error(`Not restored: ${q.out || 'unknown error'}`); return; }
        m.text = q.text; pane.querySelector('.mt').value = q.text; dirty = false; hb.replaceChildren();
        const c = cap && data.captures.find((y) => `captures/${y.name}` === m.name); if (c) c.text = q.text;
        st.say('Restored');
      }));
    });
    pane.querySelector('.save').addEventListener('click', async (e) => {
      const text = pane.querySelector('.mt').value; const done = busy(e.currentTarget, 'Saving…');
      const r = await api.rpc('POST', 'memory', { name: m.name, text }).catch((x) => ({ out: String(x) }));
      done();
      if (r.ok) { m.text = text; if (cap) { const c = data.captures.find((x) => `captures/${x.name}` === m.name); if (c) c.text = text; } dirty = false; st.say(`Saved ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`); } else st.error(`Not saved: ${r.out || 'unknown error'}`);
    });
  }

  // a quiet tag for where a skill or agent came from (nothing for the brain's own); "mine" reads "yours" like the rest of this tab
  const srcTag = (x) => { const l = { team: ['team', 'Comes with the active team'], market: ['market', 'Added from the Market tab'], mine: ['yours', ''] }[x.source || (x.mine ? 'mine' : '')];
    return l ? ` <span class="tag"${l[1] ? ` title="${esc(l[1])}"` : ''}>${l[0]}</span>` : ''; };
  const actions = (kind, id, o) => `<button class="btn ghost sm" data-edit="${esc(id)}">${icon('edit')} Edit</button>${o.mine && data.canShare ? `<button class="btn link sm" data-share="${kind}:${esc(id)}:${o.shared ? 1 : 0}">${o.shared ? 'Unshare' : 'Share with everyone'}</button>` : ''}${o.mine ? `<button class="btn danger sm" data-del="${esc(id)}">${icon('trash')} Delete</button>` : ''}`;

  function wireDelete(kind, rpcName, back) {
    pane.querySelectorAll('[data-del]').forEach((b) => b.addEventListener('click', async () => {
      const name = b.dataset.del;
      const r0 = await confirmInline(b, { title: `Delete your ${kind} ${kind === 'skill' ? '/' : ''}${name}?`, text: 'Others who added it keep their copy.', confirmLabel: 'Delete', danger: true });
      if (!r0.ok) return;
      const r = await api.rpc('POST', rpcName, { name }).catch((x) => ({ out: String(x) }));
      if (!r.ok) { say(false, r.out || 'Could not delete it'); return; }
      say(true, `Deleted ${kind} ${name}`);
      await refresh(); back();
    }));
  }

  // Skills: edit any (whole file); create and delete yours (never touched by an install)
  function renderSkills(editing = null) {
    dirty = false;
    const mine = data.skills.filter((x) => x.mine);
    const ro = editing && editing.name ? 'readonly' : '';
    const form = editing ? `<div class="card"><h3>${editing.name ? `Edit /${esc(editing.name)}` : 'New skill'}</h3>
      <div class="sub" style="margin-bottom:10px">A skill is a playbook Claude loads by itself when your request matches its description.</div>
      ${field('Name', `<input class="f-name" placeholder="vm-patching" value="${esc(editing.name || '')}" ${ro}>`)}
      ${field('Description', `<input class="f-desc" placeholder="Monthly RHEL patching of the storage VMs: pre-checks, order, rollback" value="${esc(editing.description || '')}">`, 'what it does and when to use it')}
      ${field('Trigger phrases', `<input class="f-when" placeholder="&quot;patch the vms&quot;, &quot;monthly patching&quot;" value="${esc(editing.when || '')}">`, 'optional')}
      ${field('Instructions', `<textarea class="f-body mono" rows="10" placeholder="## Steps&#10;1. ...">${esc(editing.body || '')}</textarea>`, 'Markdown: steps, commands, checks, what to report')}
      <div class="row sticky"><button class="btn f-save">Save skill</button><button class="btn ghost f-cancel">Cancel</button><span class="f-stbox"></span></div></div>` : '';
    const card = (x) => `<div class="item"><div class="t">/${esc(x.name)}${srcTag(x)}</div>
      <div class="d" title="${esc(x.description)}">${esc(x.description)}</div><div class="row">${actions('skill', x.dir, x)}</div></div>`;
    pane.innerHTML = `<div class="row spread"><span class="sub">${data.skills.length} skills · ${mine.length} of them yours</span>
      ${editing ? '' : '<button class="btn new">New skill</button>'}</div>
      <div class="sub" style="margin-top:6px">Team skills come and go with the team; your own and marketplace skills stay. Add more in the Market tab.</div>${form}
      ${mine.length ? `<div class="sec-label">Your skills</div><div class="grid">${mine.map(card).join('')}</div><div class="sec-label">Built in</div>` : '<div style="height:12px"></div>'}
      <div class="grid">${data.skills.filter((x) => !x.mine).map(card).join('')}</div>`;
    pane.querySelector('.new')?.addEventListener('click', () => renderSkills({}));
    pane.querySelector('.f-cancel')?.addEventListener('click', () => renderSkills());
    const fst = pane.querySelector('.f-stbox') ? statusLine(pane.querySelector('.f-stbox')) : null;
    pane.querySelector('.f-save')?.addEventListener('click', async (e) => {
      const v = (c) => pane.querySelector(c).value; const done = busy(e.currentTarget, 'Saving…');
      const r = await api.rpc('POST', 'skill', { name: v('.f-name').trim(), description: v('.f-desc'), when: v('.f-when'), body: v('.f-body') }).catch((x) => ({ out: String(x) }));
      done();
      if (!r.ok) { fst.error(`Not saved: ${r.out || 'unknown error'}`); return; }
      await refresh(); renderSkills();
    });
    pane.querySelectorAll('[data-edit]').forEach((b) => b.addEventListener('click', () => editFile('skill', b.dataset.edit, false, renderSkills)));
    wireShare(renderSkills);
    wireDelete('skill', 'skill-delete', renderSkills);
  }

  // Agents: the brain's own and yours; edit any of them, add and delete yours
  function renderAgents() {
    dirty = false;
    const card = (a) => `<div class="item"><div class="t">${esc(a.name)}${srcTag(a)}</div><div class="d" title="${esc(a.description)}">${esc(a.description)}</div>
      ${tags([a.tools, a.model], 2)}
      <div class="row">${actions('agent', a.file, a)}</div></div>`;
    pane.innerHTML = `<div class="row spread"><span class="sub">${data.agents.length} agents: helpers Claude hands a task to (they run with their own instructions and tools)</span>
      <button class="btn new">New agent</button></div><div style="height:12px"></div>${data.agents.length ? `<div class="grid">${data.agents.map(card).join('')}</div>`
      : emptyBlock('Add a helper Claude can hand a task to: click New agent above.', '', null, { icon: 'box', title: 'No agents yet' }).outerHTML}`;
    pane.querySelector('.new').addEventListener('click', () => editFile('agent', '', true, renderAgents));
    pane.querySelectorAll('[data-edit]').forEach((b) => b.addEventListener('click', () => editFile('agent', b.dataset.edit, false, renderAgents)));
    wireShare(renderAgents);
    wireDelete('agent', 'agent-delete', renderAgents);
  }

  // asks for a short description inline (no browser prompt); resolves to the text or null when cancelled
  function askText(btn, label) {
    return new Promise((resolve) => {
      const box = el(`<div class="confirm" role="group" aria-label="Describe it">${field(esc(label), '<input class="d-in">')}
        <div class="row"><button type="button" class="btn ghost sm d-no">Cancel</button><button type="button" class="btn sm d-yes">Share</button></div></div>`);
      const done = (v) => { box.remove(); btn.hidden = false; btn.focus(); resolve(v); };
      box.addEventListener('keydown', (e) => { if (e.key === 'Escape') { e.stopPropagation(); done(null); } });
      box.querySelector('.d-no').addEventListener('click', () => done(null));
      box.querySelector('.d-yes').addEventListener('click', () => done(box.querySelector('.d-in').value));
      btn.hidden = true; btn.after(box); box.querySelector('.d-in').focus();
    });
  }

  // Share with everyone / Unshare (the marketplace: others see it with your name and can add it)
  function wireShare(rerender) {
    pane.querySelectorAll('[data-share]').forEach((b) => b.addEventListener('click', async () => {
      const [kind, name, on] = b.dataset.share.split(':');
      const unshare = on === '1';
      let description = '';
      if (kind === 'mcp' && !unshare) {
        description = await askText(b, `Describe ${name} for the marketplace (what it gives Claude)`);
        if (description === null) return;
      }
      if (unshare && !(await confirmInline(b, { title: `Take ${kind} ${name} out of the marketplace?`, text: 'People who added it keep their copy.', confirmLabel: 'Remove' })).ok) return;
      const done = busy(b, unshare ? 'Removing…' : 'Sharing…');
      const r = await api.rpc('POST', 'share', { kind, name, unshare, description }).catch((x) => ({ out: String(x) }));
      done();
      say(!!r.ok, r.ok ? (unshare ? `Removed ${name} from the marketplace` : `Shared ${name}`) : (r.out || 'Could not do that'));
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
      if (!r.ok) { say(false, r.out || 'Could not open it'); return; }
      ({ text, builtin } = r);
    }
    dirty = false;
    pane.innerHTML = `<div class="card"><h3>${create ? `New ${kind}` : `Edit ${kind === 'skill' ? '/' : ''}${esc(name)}`}</h3>
      <div class="sub" style="margin-bottom:10px">The header between the --- lines needs <code>name:</code> and <code>description:</code> (Claude picks it by the description); below it, the instructions in Markdown.</div>
      ${builtin ? '<div class="sub" style="margin-bottom:10px">Built in: re-running brain/install.sh puts the original back. Your previous version is kept as a .bak file.</div>' : ''}
      ${create ? field('Name', '<input class="f-name" placeholder="vm-patching">', 'lower-case letters, digits and dashes') : ''}
      ${field(create ? 'File' : esc(name), `<textarea class="mt" spellcheck="false">${esc(text)}</textarea>`)}
      <div class="row sticky"><button class="btn f-save">Save</button><button class="btn ghost f-cancel">Cancel</button><span class="f-stbox"></span></div></div>`;
    const ta = pane.querySelector('.mt');
    const fst = statusLine(pane.querySelector('.f-stbox'));
    pane.querySelector('.f-name')?.addEventListener('input', (e) => { ta.value = ta.value.replace(/^name: .*$/m, `name: ${e.target.value.trim() || 'my-agent'}`); });
    pane.querySelector('.f-cancel').addEventListener('click', () => back());
    pane.querySelector('.f-save').addEventListener('click', async (e) => {
      const n = create ? pane.querySelector('.f-name').value.trim() : name; const done = busy(e.currentTarget, 'Saving…');
      const r = await api.rpc('POST', 'file', { kind, name: n, text: ta.value, create }).catch((x) => ({ out: String(x) }));
      done();
      if (!r.ok) { fst.error(`Not saved: ${r.out || 'unknown error'}`); return; }
      await refresh(); back();
    });
  }

  function renderDocs() {
    pane.innerHTML = `
      <div class="card"><div class="row" style="align-items:flex-end"><div class="field grow" style="margin:0"><label for="bq">Search the docs</label><input id="bq" class="q" placeholder="An error, an event, an API, a task…"></div>
        <div class="field" style="margin:0;flex:0 1 180px"><label for="bv">Vendor <span class="sub">optional</span></label><input id="bv" class="v"></div>
        <button class="btn s">${icon('search')} Search</button></div><div class="out" aria-live="polite"></div></div>
      ${data.canAddDocs === false ? '<div class="card"><h3>Add documents</h3><div class="sub">The docs library is shared by everyone on this VM: root adds documents to it (root\'s Brain tab).</div></div>' : `<div class="two">
        <div class="card"><h3>Add pages or PDFs by URL</h3><div class="sub" style="margin-bottom:10px">Any URL this VM can reach. Claude can do it too: “add this to your docs: …”</div>
          ${field('Web addresses', '<textarea class="urls" rows="3" placeholder="https://wiki.corp/san/zoning-standard"></textarea>', 'one per line')}
          ${field('Put it under', '<input class="to" placeholder="cisco/mds">', 'vendor/product')}
          <div class="row"><button class="btn ghost add">Add</button></div><pre class="addout" role="status" style="display:none"></pre></div>
        <div class="card"><h3>Upload files</h3><div class="sub" style="margin-bottom:10px">PDF, HTML, Markdown or text, up to 35 MB each</div>
          <div class="drop" tabindex="0" role="button" aria-label="Choose files to upload">Drop files here or click to choose<input type="file" multiple hidden accept=".pdf,.html,.htm,.md,.markdown,.txt,.adoc,.rst"></div>
          <div style="height:12px"></div>${field('Put it under', '<input class="to2" placeholder="local/uploads">', 'vendor/product, default local/uploads')}
          <pre class="upout" role="status" style="display:none"></pre></div>
      </div>
      <div class="card"><h3>Your added documents</h3>${data.inbox.length ? `<div class="table-wrap"><table><tr><th>File</th><th class="n">Size</th><th class="n">Added</th></tr>${data.inbox.map((f) => `<tr><td><code>${esc(f.path)}</code></td><td class="n">${kb(f.size)}</td><td class="n">${new Date(f.mtime).toLocaleDateString()}</td></tr>`).join('')}</table></div>` : emptyBlock('Documents you add by URL or upload show up here.', '', null, { icon: 'file', title: 'None yet' }).outerHTML}</div>`}`;
    const q = pane.querySelector('.q');
    const out = pane.querySelector('.out');
    const sb = pane.querySelector('.s');
    const search = async () => {
      const term = q.value.trim();
      if (!term || sb.disabled) return;
      const done = busy(sb, 'Searching…');
      out.innerHTML = skeleton('list');
      const v = pane.querySelector('.v').value.trim();
      const r = await api.rpc('GET', `search?q=${encodeURIComponent(term)}${v ? `&vendor=${encodeURIComponent(v)}` : ''}`).catch((e) => ({ error: String(e) }));
      done();
      if (r.error) { out.innerHTML = `<pre class="bad">${esc(r.error)}</pre>`; return; }
      const res = r.results || [];
      out.innerHTML = res.length ? `<div class="sub" style="margin-top:12px">${res.length} result${res.length === 1 ? '' : 's'} for "${esc(term)}"</div>${res.map((x) => `<div class="res">
        ${x.url ? `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a>` : `<b>${esc(x.title)}</b>`}
        <div><span class="tag">${esc(x.vendor)}/${esc(x.product)}</span><span class="sub">${esc(x.section || '')}</span></div>
        <div class="snip">${esc((x.snippet || '').slice(0, 420)).replace(/«(.*?)»/g, '<b>$1</b>')}</div></div>`).join('')}`
        : `<div class="sub" style="margin-top:12px">Nothing found for "${esc(term)}". Try fewer words or a product name${data.canAddDocs === false ? '' : ', or add the document below'}.</div>`;
    };
    sb.addEventListener('click', search);
    q.addEventListener('keydown', (e) => { if (e.key === 'Enter') search(); });
    if (data.canAddDocs === false) return;

    pane.querySelector('.add').addEventListener('click', async (e) => {
      const pre = pane.querySelector('.addout'); const done = busy(e.currentTarget, 'Adding…');
      pre.style.display = 'block'; pre.className = 'addout'; pre.textContent = 'Fetching and indexing…';
      const r = await api.rpc('POST', 'add-url', { urls: pane.querySelector('.urls').value, to: pane.querySelector('.to').value.trim() }).catch((x) => ({ out: String(x) }));
      pre.textContent = r.ok ? r.out : `Failed: check the address is reachable from this VM.\n${r.out || ''}`;
      if (!r.ok) pre.classList.add('bad');
      done(); if (r.ok) refreshInbox();
    });

    const drop = pane.querySelector('.drop');
    const input = drop.querySelector('input');
    let working = false;
    const upload = async (files) => {
      if (working || !files.length) return;
      working = true; drop.setAttribute('aria-disabled', 'true');
      const pre = pane.querySelector('.upout');
      pre.style.display = 'block'; pre.textContent = '';
      let ok = 0; let fail = 0;
      try {
        for (const [i, f] of files.entries()) {
          const tag = `(${i + 1}/${files.length}) ${f.name}`;
          if (f.size > 35 * 1048576) { pre.textContent += `${tag}: too large (35 MB max)\n`; fail++; continue; }
          pre.textContent += `${tag}: uploading…\n`;
          const b64 = await new Promise((res) => { const rd = new FileReader(); rd.onload = () => res(String(rd.result).split(',')[1] || ''); rd.readAsDataURL(f); });
          const r = await api.rpc('POST', 'upload', { name: f.name, to: pane.querySelector('.to2').value.trim(), data: b64 }).catch((x) => ({ out: String(x) }));
          if (r.ok) ok++; else fail++;
          pre.textContent += r.ok ? `${tag}: saved ${r.saved}\n` : `${tag}: ${r.out}\n`;
        }
        pre.textContent += 'Indexing…\n';
        const r = await api.rpc('POST', 'index').catch((x) => ({ out: String(x) }));
        pre.textContent += `${ok} saved, ${fail} failed. ${r.out || ''}\n`;
      } finally { working = false; drop.removeAttribute('aria-disabled'); }
      refreshInbox();
    };
    drop.addEventListener('click', () => { if (!working) input.click(); });
    drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); drop.click(); } });
    input.addEventListener('change', () => upload([...input.files]));
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', (e) => { e.preventDefault(); drop.classList.remove('over'); upload([...e.dataTransfer.files]); });
  }

  async function refreshInbox() {
    const keep = pane.querySelector('.out')?.innerHTML;
    const up = pane.querySelector('.upout')?.textContent;
    await refresh();
    if (keep && pane.querySelector('.out')) pane.querySelector('.out').innerHTML = keep;
    if (up && pane.querySelector('.upout')) { const p = pane.querySelector('.upout'); p.style.display = 'block'; p.textContent = up; }
  }
  refresh();
}

export function unmount(container) { container._brainCleanup?.(); container.innerHTML = ''; }
