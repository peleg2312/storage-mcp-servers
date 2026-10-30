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

// Browser tab: web apps running on this VM (by port) and files under the home folder, shown through the UI server's
// /preview route (signed-in only; only ports this account listens on). Claude opens pages here with `paas-open`.
const SEEN = 'paas-browser-seen';
const LAST = 'paas-browser-last';
const store = {
  get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* private window */ } },
};

// what the person types -> /preview/... ("8000/docs", ":8000", "localhost:8000/x", "~/storage-reports/a.html")
export function toPreview(s) {
  s = s.trim();
  if (!s) return null;
  if (s.startsWith('/preview/')) return s;
  const m = /^(?:https?:\/\/)?(?:(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]):|:)?(\d{1,5})(\/.*)?$/.exec(s);
  if (m) return `/preview/${m[1]}${m[2] || '/'}`;
  if (s.startsWith('~')) return `/preview/~/${s.replace(/^~\/?/, '')}`;
  return null;
}
// and back, for the address bar
const toShort = (p) => (p.startsWith('/preview/~/') ? `~/${p.slice(11)}` : p.replace(/^\/preview\/(\d+)/, 'localhost:$1'));

const CSS = `
.paas.pb{max-width:none;margin:0;height:100%;display:flex;flex-direction:column;padding:12px 16px 16px;gap:10px}
.pb .bar{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.pb .bar label{font-weight:600;font-size:13px;flex:none}
.pb .bar input{flex:1;min-width:0;min-height:36px;background:hsl(var(--background));border:1px solid hsl(var(--input));border-radius:10px;padding:7px 12px;color:inherit;font:13px ui-monospace,SFMono-Regular,Menlo,monospace}
.pb .ic{width:36px;height:36px;padding:0;flex:none}
.pb .ic:disabled{opacity:.4;cursor:default}
.pb [data-b] svg{transform:scaleX(-1)}
.pb .chips{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13px;color:hsl(var(--muted-foreground))}
.pb .chip{min-height:32px;padding:4px 12px;font:12px ui-monospace,SFMono-Regular,Menlo,monospace}
.pb .st{margin:0}
.pb .frame{flex:1;min-height:200px;border:1px solid hsl(var(--border));border-radius:12px;overflow:hidden;background:hsl(var(--card))}
.pb iframe{width:100%;height:100%;border:0;display:block}
.pb .intro{padding:40px 24px;color:hsl(var(--muted-foreground));height:100%;line-height:1.8;overflow:auto}
.pb .intro code{background:hsl(var(--muted));border-radius:6px;padding:1px 6px}
.pb .cr{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:13px;border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:12px;padding:7px 10px}
.pb .cr[hidden],.pb .howto[hidden]{display:none}
.pb .cr .dot{width:8px;height:8px;border-radius:50%;background:hsl(var(--muted-foreground));flex:none}
.pb .cr .dot.on{background:hsl(var(--primary));box-shadow:0 0 0 3px hsl(var(--primary)/.25)}
.pb .cr b{font-weight:600}
.pb .cr select{min-height:36px;background:hsl(var(--background));border:1px solid hsl(var(--input));border-radius:8px;padding:4px 8px;color:inherit;font:inherit;max-width:260px}
.pb .cr [data-connect]{margin-left:auto}
.pb .howto{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:12px;padding:14px 16px;font-size:13px;line-height:1.6}
.pb .howto ol{margin:6px 0 10px;padding-left:20px;list-style:decimal}
.pb .howto pre{margin:0;white-space:pre-wrap;word-break:break-all;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;background:hsl(var(--muted));border-radius:8px;padding:10px 12px;max-height:120px;overflow:auto}
@media (pointer:coarse){.pb .ic{width:44px;height:44px}.pb .bar input,.pb .cr select,.pb .chip{min-height:44px}}
@media (max-width:760px){.paas.pb{padding:10px}.pb .cr select{max-width:100%}}
@media (max-width:560px){.pb .bar input{flex:1 1 100%;order:-1}.pb .bar label{order:-2;flex:1 1 100%}}`;

// Chrome DevTools plugin: which PC's Chrome this chat drives, a switch between the connected PCs, how to connect one
function chromeBar(box, howto, api, status) {
  let stopped = false;
  let data = null;
  const session = () => api?.context?.session?.id || '';
  function render() {
    if (!data || !data.installed) { box.hidden = true; howto.hidden = true; return; }
    box.hidden = false;
    const pcs = data.pcs || [];
    const cur = pcs.find((p) => p.port === data.chosen);
    const label = (p) => `${p.pc}${p.user ? ` (${p.user})` : ''}`;
    let line;
    if (data.error) line = `<span class="sub">Chrome: ${esc(data.error)}</span>`;
    else if (!pcs.length) line = '<span class="dot"></span><span><b>Chrome on your PC:</b> <span class="sub">no PC connected</span></span>';
    else if (!session()) line = `<span class="dot on"></span><span><b>Chrome on your PC:</b> ${pcs.length} connected <span class="sub">· open a chat to choose its PC</span></span>`;
    else {
      line = `<span class="dot ${cur ? 'on' : ''}"></span><label for="pb-pc"><b>Chrome on your PC:</b></label>
        <select id="pb-pc">${cur ? '' : `<option value="">${pcs.length > 1 ? 'Choose your PC…' : 'Not chosen yet'}</option>`}
        ${pcs.map((p) => `<option value="${p.port}" ${p.port === data.chosen ? 'selected' : ''}>${esc(label(p))}</option>`).join('')}</select>
        ${pcs.length === 1 && !cur ? '<span class="sub">(used automatically)</span>' : ''}`;
    }
    box.innerHTML = `${line}<button class="btn ghost sm" data-connect aria-expanded="${!howto.hidden}">${howto.hidden ? 'Connect a PC' : 'Close'}</button>`;
    box.querySelector('select')?.addEventListener('change', async (e) => {
      const pc = e.target.value;
      if (!pc) return;
      e.target.disabled = true;
      try {
        const r = await fetch('/preview/_chrome', { method: 'POST', credentials: 'same-origin', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ session: session(), pc }) });
        if (!r.ok) throw new Error((await r.json()).error || r.status);
        data.chosen = Number(pc);
      } catch (err) { status.error(`Could not switch PC: ${err.message || err}`); }
      render();
    });
    box.querySelector('[data-connect]').addEventListener('click', () => { howto.hidden = !howto.hidden; render(); });
    howto.innerHTML = `<b>Connect the Chrome on your Windows PC</b>
      <ol><li>Copy the line below and paste it into <b>PowerShell</b> on your PC.</li>
      <li>Sign in with your server password. A separate Chrome window opens (its own empty profile, not your everyday Chrome).</li>
      <li>Keep that PowerShell window open while you work; close it to disconnect. Your PC then appears above.</li></ol>
      <pre>${esc(data.line || '')}</pre><div class="row"><button class="btn ghost sm" data-copy>Copy</button>
      <span class="sub">Claude may open any site in that Chrome, except storage, switch, UCS and vCenter pages.</span></div>`;
    howto.querySelector('[data-copy]').addEventListener('click', async (e) => {
      try { await navigator.clipboard.writeText(data.line || ''); status.say('Command copied: paste it into PowerShell'); } catch {
        const range = document.createRange(); range.selectNodeContents(howto.querySelector('pre'));
        const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range); status.say('Select the command and copy it (Ctrl+C or Cmd+C)');
      }
    });
  }
  async function refresh() {
    if (document.hidden) return;
    try { data = await (await fetch(`/preview/_chrome?session=${encodeURIComponent(session())}`, { credentials: 'same-origin', cache: 'no-store' })).json(); } catch { /* signed out: keep the last view */ }
    if (!stopped && !box.querySelector('select:focus')) render();
  }
  let timer = 0;
  const tick = () => refresh().finally(() => { if (!stopped) timer = setTimeout(tick, 5000); });
  const off = api?.onContextChange?.(() => { refresh(); });
  tick();
  return () => { stopped = true; clearTimeout(timer); off?.(); };
}

export function mount(container, api) {
  container.innerHTML = `<style>${PAAS_CSS}${CSS}</style><div class="paas pb">
    <div class="bar"><button class="btn ghost ic" data-b disabled title="Back" aria-label="Back">${icon('chevron')}</button><button class="btn ghost ic" data-f disabled title="Forward" aria-label="Forward">${icon('chevron')}</button>
      <button class="btn ghost ic" data-r disabled title="Reload" aria-label="Reload">${icon('refresh')}</button>
      <label for="pb-addr">Address</label>
      <input id="pb-addr" type="text" inputmode="url" enterkeyhint="go" autocapitalize="off" autocomplete="off" spellcheck="false" placeholder="8000/docs  ·  ~/storage-reports/…/report.html">
      <button class="btn" data-go>Open</button><button class="btn ghost ic" data-w title="Open in a new browser tab" aria-label="Open in a new browser tab">${icon('external')}</button></div>
    <div class="stwrap"></div>
    <div class="chips" role="group" aria-label="Your apps"></div>
    <div class="cr" hidden></div><div class="howto" hidden></div>
    <div class="frame"><div class="intro"><b>Your own pages, inside the UI:</b><br>
      · apps you run: a FastAPI service (<code>8000/docs</code>), a React / Vite dev server, a dashboard you started<br>
      · files under your home folder: <code>~/storage-reports/</code> (HTML reports with their charts)<br><br>
      Type a port (<code>8000</code>) or a path (<code>~/</code>) above, or ask Claude: "show me the API docs in the Browser tab".<br><br>
      Want Claude to click through your app in a real Chrome? Use <b>Connect a PC</b> above (chrome-devtools plugin).</div></div></div>`;
  const input = container.querySelector('#pb-addr');
  const status = statusLine(container.querySelector('.stwrap'));
  const nav = ['[data-b]', '[data-f]', '[data-r]'].map((q) => container.querySelector(q));
  const frameBox = container.querySelector('.frame');
  const chips = container.querySelector('.chips');
  let frame = null;
  let stopped = false;

  function open(url) {
    const p = toPreview(url);
    if (!p) { status.error('Type a port such as 8000/docs, or a path such as ~/storage-reports/'); return; }
    status.say(`Opening ${toShort(p)}…`);
    if (!frame) {
      frameBox.innerHTML = '<iframe title="Browser"></iframe>';
      frame = frameBox.querySelector('iframe');
      nav.forEach((b) => { b.disabled = false; });
      frame.addEventListener('load', () => {     // same origin: follow the page's own navigation in the address bar
        status.say('');
        try {
          const l = frame.contentWindow.location;
          if (l.pathname.startsWith('/preview/')) { input.value = toShort(l.pathname + l.search + l.hash); store.set(LAST, l.pathname + l.search + l.hash); }
        } catch { /* left /preview: nothing to show */ }
      });
    }
    frame.src = p;
    input.value = toShort(p);
    store.set(LAST, p);
  }

  async function ports() {
    let d = {};
    try { d = await (await fetch('/preview/_ports', { credentials: 'same-origin' })).json(); } catch { /* signed out */ }
    const list = (d.ports || []).map((p) => `<button class="btn ghost chip" data-u="${p}/">App on port ${p}</button>`).join('');
    chips.innerHTML = `<span>Your apps:</span> ${list || '<span>No app is running yet. Start one in the Shell tab, then press Reload.</span>'}<button class="btn ghost chip" data-u="~/storage-reports/">~/storage-reports</button>`;
    chips.querySelectorAll('[data-u]').forEach((b) => b.addEventListener('click', () => open(b.dataset.u)));
  }

  // paas-open (Claude or the person in a terminal) writes the page to open; take each one once
  let ticks = 0;
  async function poll() {
    if (stopped) return;
    if (document.hidden) { setTimeout(poll, 5000); return; }
    if (++ticks % 8 === 0) ports();
    try {
      const d = await (await fetch('/preview/_open', { credentials: 'same-origin', cache: 'no-store' })).json();
      if (d.url && d.ts > Number(store.get(SEEN) || 0)) { store.set(SEEN, String(d.ts)); open(d.url); }
    } catch { /* signed out or offline: try again */ }
    setTimeout(poll, 2000);
  }

  const go = () => open(input.value);
  container.querySelector('[data-go]').addEventListener('click', go);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
  container.querySelector('[data-b]').addEventListener('click', () => frame?.contentWindow.history.back());
  container.querySelector('[data-f]').addEventListener('click', () => frame?.contentWindow.history.forward());
  container.querySelector('[data-r]').addEventListener('click', () => { if (frame) frame.contentWindow.location.reload(); ports(); });
  container.querySelector('[data-w]').addEventListener('click', () => { const p = toPreview(input.value); if (p) window.open(p, '_blank', 'noopener'); });
  const stopChrome = chromeBar(container.querySelector('.cr'), container.querySelector('.howto'), api, status);
  container._paasStop = () => { stopped = true; stopChrome(); };

  ports();
  const last = store.get(LAST);
  if (last) open(last);
  poll();
}

export function unmount(container) { container._paasStop?.(); container.innerHTML = ''; }
