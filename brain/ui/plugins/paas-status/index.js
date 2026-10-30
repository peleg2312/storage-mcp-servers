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

// Status tab: Health (machine, brain checks, MCP servers) and Usage (tokens, estimated cost); data: server.js.
const gb = (n) => `${(n / 1073741824).toFixed(1)} GB`;
const dur = (s) => (s >= 86400 ? `${Math.floor(s / 86400)} d ${Math.floor((s % 86400) / 3600)} h` : `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min`);
const LABEL = { ok: 'OK', warn: 'Check', fail: 'Problem' };
const HINT = { ok: 'Working', warn: 'Worth a look, not broken', fail: 'Needs fixing' };

// Tab-specific rules only; the common look is PAAS_CSS.
const CSS = `
.paas .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:16px}
.paas .tile{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:12px;padding:14px 16px}
.paas .tile .k{font-size:12px;color:hsl(var(--muted-foreground));text-transform:uppercase;letter-spacing:.06em}
.paas .tile .v{font-size:22px;font-weight:700;margin-top:2px;font-variant-numeric:tabular-nums}
.paas .gauge{height:5px;border-radius:5px;background:hsl(var(--muted));margin-top:8px;overflow:hidden}
.paas .gauge i{display:block;height:100%;border-radius:5px;background:hsl(var(--primary))}
.paas .gauge.warn i{background:#b45309}.paas .gauge.fail i{background:hsl(var(--destructive))}
.paas td.g{color:hsl(var(--muted-foreground));width:150px}.paas td.s{width:100px;white-space:nowrap}
.paas .fix{margin-top:4px;font-size:13px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.paas .fix code{background:hsl(var(--muted));border-radius:6px;padding:1px 6px;font-size:12px}
.paas .busy{opacity:.6;transition:opacity .15s}
.paas .chart{position:relative;height:200px;display:flex;align-items:flex-end;gap:3px;border-bottom:1px solid hsl(var(--border));overflow-x:auto}
.paas .bar{flex:1;min-width:2px;border-radius:4px 4px 0 0;background:hsl(var(--primary));opacity:.85}
.paas .hit{flex:1;min-width:4px;height:100%;display:flex;align-items:flex-end;cursor:pointer}
.paas .hit:hover .bar,.paas .hit:focus-visible .bar{opacity:1}
.paas .hit:focus-visible{outline:2px solid hsl(var(--ring));outline-offset:-2px}
.paas .axis{display:flex;justify-content:space-between;color:hsl(var(--muted-foreground));font-size:12px;margin-top:6px}
.paas .tip{position:absolute;pointer-events:none;background:hsl(var(--popover));color:hsl(var(--popover-foreground));border:1px solid hsl(var(--border));border-radius:8px;padding:6px 10px;font-size:12px;white-space:nowrap;box-shadow:0 8px 24px rgba(0,0,0,.25);display:none;z-index:5}
.paas .grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr));gap:16px}
.paas td.n,.paas th.n{text-align:right;font-variant-numeric:tabular-nums}
.paas .meter{height:4px;border-radius:4px;background:hsl(var(--primary));margin-top:4px}
.paas .name{max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.paas .sw{display:flex;justify-content:center;margin-bottom:18px}
@media (max-width:640px){.paas td.g{width:auto}.paas .tiles{grid-template-columns:1fr 1fr;gap:10px}.paas .name{max-width:150px}}`;

const pill = (s) => `<span class="pill ${s}" title="${HINT[s]}">${LABEL[s]}</span>`;
const fmtTok = (n) => (n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : `${n}`);
const fmtUsd = (n) => (n >= 100 ? `$${n.toFixed(0)}` : `$${n.toFixed(2)}`);
const shortPath = (p) => esc(String(p || '').replace(/^\/home\/[^/]+|^\/Users\/[^/]+|^\/root/, '~'));
const mcpErr = (m) => (/ENOENT/.test(m) ? 'Claude is not installed for this user: ask your admin.'
  : /timed out|ETIMEDOUT|killed/i.test(m) ? 'Checking the servers took too long. Press "Run again" to try once more.'
  : m ? `Could not check MCP servers: ${m}` : 'No MCP servers are set up yet.');
const copy = async (text, st) => {
  try { await navigator.clipboard.writeText(text); st.say('Copied.'); } catch { st.error('Could not copy. Select the command and copy it by hand.'); }
};

function mountHealth(container, api) {
  container.innerHTML = `${header('Health', 'Brain health on this VM: the checks of /brain-health that need no AI, live')}
    <div class="top" style="min-height:80px"><div class="sub">Checking…</div></div>
    <div class="card"><h3>MCP servers</h3><div class="mcp sub">Starting each server to test it (up to a minute)…</div></div>`;
  const head = container.querySelector('.head');
  const btn = el(`<button type="button" class="btn">${icon('refresh')}Run again</button>`);
  head.append(btn);
  const st = statusLine(container);
  const top = container.querySelector('.top');
  const mcpEl = container.querySelector('.mcp');
  let shown = false;   // a finished MCP table is on screen: keep it (dimmed) while re-testing

  async function loadStatus() {
    let d;
    try { d = await api.rpc('GET', 'status'); } catch (e) { console.error(e); top.replaceChildren(errorBlock(e.message || e, loadStatus)); return; }
    const m = d.machine;
    const used = 1 - m.mem.free / m.mem.total;
    const lvl = used > 0.95 ? 'fail' : used > 0.85 ? 'warn' : '';
    const rank = (c) => (c.status === 'fail' ? 0 : c.status === 'warn' ? 1 : 2);
    const groups = [...new Set(d.checks.map((c) => c.group))]
      .map((g) => d.checks.filter((c) => c.group === g).sort((a, b) => rank(a) - rank(b)))
      .sort((a, b) => rank(a[0]) - rank(b[0]));
    const bad = d.checks.filter((c) => c.status !== 'ok');
    const summary = bad.length
      ? `<span class="pill ${bad.some((c) => c.status === 'fail') ? 'fail' : 'warn'}">${bad.length} need${bad.length === 1 ? 's' : ''} attention</span>`
      : '<span class="pill ok">All good</span>';
    const fixOf = (c) => (c.fix ? `<div class="fix"><span>How to fix: ${esc(c.fix)}</span>${c.cmd ? `<code>${esc(c.cmd)}</code><button type="button" class="btn ghost sm" data-copy="${esc(c.cmd)}">${icon('copy')}Copy command</button>` : ''}</div>` : '');
    top.innerHTML = `
      <div class="tiles">
        <div class="tile"><div class="k">Host</div><div class="v" style="font-size:17px">${esc(m.host)}</div><div class="sub">${esc(m.os)}</div></div>
        <div class="tile"><div class="k">Memory</div><div class="v">${(used * 100).toFixed(0)}%${lvl ? ` <span class="sub">${lvl === 'fail' ? 'Critical' : 'High'}</span>` : ''}</div><div class="sub">${gb(m.mem.total - m.mem.free)} of ${gb(m.mem.total)}</div><div class="gauge ${lvl}"><i style="width:${used * 100}%"></i></div></div>
        <div class="tile"><div class="k">Load (1 min)</div><div class="v">${m.load[0].toFixed(2)}</div><div class="sub">${m.cpus} CPUs, ${m.load[0] / m.cpus > 1 ? 'busy' : 'ok'} (fine while load stays below this)</div></div>
        <div class="tile"><div class="k">Up</div><div class="v" style="font-size:19px">${dur(m.uptime)}</div><div class="sub">since last restart</div></div>
      </div>
      <div class="card"><div class="row"><h3>Brain checks</h3>${summary}</div><div class="table-wrap"><table>
        ${groups.map((g) => g.map((c, i) => `<tr><td class="g">${i ? '' : esc(c.group)}</td><td>${esc(c.name)}<div class="sub">${esc(c.detail)}</div>${fixOf(c)}</td><td class="s">${pill(c.status)}</td></tr>`).join('')).join('')}
      </table></div><div class="sub" style="margin-top:8px">Updated ${new Date().toLocaleTimeString()}</div></div>`;
    top.querySelectorAll('[data-copy]').forEach((b) => b.addEventListener('click', () => copy(b.dataset.copy, st)));
  }

  async function loadMcp(fresh) {
    if (shown) mcpEl.classList.add('busy');
    else { mcpEl.className = 'mcp sub'; mcpEl.textContent = 'Starting each server to test it (up to a minute)…'; }
    let d;
    try { d = await api.rpc('GET', `mcp${fresh ? '?fresh=1' : ''}`); } catch (e) { console.error(e); shown = false; mcpEl.className = 'mcp sub'; mcpEl.textContent = mcpErr(String(e.message || e)); return; }
    if (!d.servers.length) { shown = false; mcpEl.className = 'mcp sub'; mcpEl.textContent = mcpErr(d.error === 'no MCP servers configured' ? '' : d.error); return; }
    shown = true;
    mcpEl.className = 'mcp';
    mcpEl.innerHTML = `<div class="table-wrap"><table>${d.servers.map((s) => `<tr><td>${esc(s.name)}<div class="sub">${esc(s.detail)}${/auth/i.test(s.detail) ? ' Needs sign-in: authorize it in Claude.' : ''}</div></td><td class="s">${pill(s.status)}</td></tr>`).join('')}</table></div>
      <div class="sub" style="margin:8px 0 2px">Checked ${new Date(d.at).toLocaleTimeString()}</div>`;
  }

  btn.addEventListener('click', async () => {
    if (btn.disabled) return;
    const restore = busy(btn, 'Checking…');
    top.classList.add('busy');
    try { await Promise.allSettled([loadStatus(), loadMcp(true)]); } finally { top.classList.remove('busy'); restore(); }
  });
  loadStatus();
  loadMcp(false);
}

function mountUsage(container, api) {
  let days = 30;
  container.innerHTML = `${header('Usage', 'Tokens and estimated cost of every Claude Code session on this VM. Estimated at API list prices; on a subscription you are not billed per token, so it shows relative use.')}
    <div class="body"><div class="sub">Reading session logs…</div></div>`;
  const seg = el(`<div class="seg" role="group" aria-label="Range">${[7, 30, 90].map((d) => `<button type="button" data-d="${d}" aria-pressed="${d === days}">${d} days</button>`).join('')}</div>`);
  container.querySelector('.head').append(seg);
  const body = container.querySelector('.body');
  seg.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {
    days = Number(b.dataset.d);
    seg.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    load();
  }));

  const table = (rows, label, nameFn) => {
    const max = Math.max(...rows.map((r) => r.cost), 1e-9);
    return `<div class="table-wrap"><table><tr><th>${label}</th><th class="n">Tokens</th><th class="n">Cost (est.)</th></tr>${rows.map((r) => `
      <tr><td><div class="name" title="${esc(r.key)}">${nameFn(r)}</div><div class="meter" style="width:${(r.cost / max) * 100}%"></div></td>
      <td class="n">${fmtTok(r.tokens)}</td><td class="n">${fmtUsd(r.cost)}</td></tr>`).join('') || '<tr><td colspan="3" class="sub">Nothing yet</td></tr>'}</table></div>`;
  };

  async function load() {
    let d;
    try { d = await api.rpc('GET', `summary?days=${days}`); } catch (e) { console.error(e); body.replaceChildren(errorBlock(e.message || e, load)); return; }
    const t = d.total;
    const max = Math.max(...d.days.map((x) => x.cost), 1e-9);
    body.innerHTML = `
      <div class="tiles">
        <div class="tile"><div class="k">Estimated cost</div><div class="v">${fmtUsd(t.cost)}</div><div class="sub">Estimate from token counts, not a bill</div></div>
        <div class="tile"><div class="k">Written by Claude (tokens)</div><div class="v">${fmtTok(t.output)}</div><div class="sub">Text Claude wrote</div></div>
        <div class="tile"><div class="k">Read by Claude (tokens, incl. cached)</div><div class="v">${fmtTok(t.input + t.cacheRead + t.cacheWrite)}</div><div class="sub">Text sent to Claude, incl. re-used context</div></div>
        <div class="tile"><div class="k">Chats · answers</div><div class="v">${d.sessions} · ${t.messages}</div><div class="sub">Sessions started · Claude replies</div></div>
      </div>
      <div class="card"><h3>Estimated cost per day <span class="sub" style="font-weight:400">· peak ${fmtUsd(max)}</span></h3>
        <div class="chart" role="group" aria-label="Estimated cost per day">${d.days.map((x) => {
    const t2 = `${x.key}: ${fmtUsd(x.cost)} · ${fmtTok(x.tokens)} tokens · ${x.messages} replies`;
    return `<div class="hit" tabindex="0" role="img" aria-label="${esc(t2)}" data-t="${esc(t2)}"><div class="bar" style="height:${x.cost ? Math.max((x.cost / max) * 100, 1.5) : 0}%"></div></div>`;
  }).join('')}<div class="tip"></div></div>
        <div class="axis"><span>${esc(d.days[0].key)}</span><span>$0 to ${fmtUsd(max)}</span><span>${esc(d.days[d.days.length - 1].key)}</span></div></div>
      <div class="grid2">
        <div class="card"><h3>By project</h3>${table(d.projects, 'Project', (r) => shortPath(r.key))}</div>
        <div class="card"><h3>By model</h3>${table(d.models, 'Model', (r) => esc(String(r.key).replace(/^claude-/, '')))}</div>
      </div>
      <div class="card"><h3>Most expensive sessions</h3>${table(d.topSessions, 'Session', (r) => `${shortPath(r.project)} <span class="sub">${esc(r.session.slice(0, 8))}</span>`)}</div>`;
    const chart = body.querySelector('.chart');
    const tip = chart.querySelector('.tip');
    const hide = () => { tip.style.display = 'none'; };
    chart.querySelectorAll('.hit').forEach((h) => {
      const show = () => {
        tip.textContent = h.dataset.t; tip.style.display = 'block';
        const left = h.offsetLeft + h.offsetWidth / 2 - tip.offsetWidth / 2;
        tip.style.left = `${Math.min(Math.max(left, 0), chart.clientWidth - tip.offsetWidth)}px`; tip.style.top = '-8px';
      };
      ['mouseenter', 'focus', 'click'].forEach((ev) => h.addEventListener(ev, show));
      ['mouseleave', 'blur'].forEach((ev) => h.addEventListener(ev, hide));
    });
  }
  load();
}

export function mount(container, api) {
  let view = 'health';
  try { if (localStorage.getItem('paas-status.view') === 'usage') view = 'usage'; } catch { /* storage blocked */ }
  container.innerHTML = `<style>${PAAS_CSS}${CSS}</style><div class="paas"><div class="sw"><div class="seg" role="group" aria-label="View">
    <button type="button" data-v="health">Health</button><button type="button" data-v="usage">Usage</button></div></div><div class="pane"></div></div>`;
  const pane = container.querySelector('.pane');
  const btns = container.querySelectorAll('.sw button');
  const show = (v) => {
    btns.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === v)));
    try { localStorage.setItem('paas-status.view', v); } catch { /* storage blocked */ }
    (v === 'usage' ? mountUsage : mountHealth)(pane, api);
  };
  btns.forEach((b) => b.addEventListener('click', () => show(b.dataset.v)));
  show(view);
}

export function unmount(container) { container.innerHTML = ''; }
