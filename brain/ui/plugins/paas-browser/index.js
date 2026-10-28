// Browser tab: web apps running on this VM (by port) and files under the home folder, shown through the UI server's
// /preview route (signed-in only; only ports this account listens on). Claude opens pages here with `paas-open`.
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
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
.pb{font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));height:100%;display:flex;flex-direction:column;box-sizing:border-box;padding:12px 16px 16px;gap:10px}
.pb .bar{display:flex;gap:6px;align-items:center}
.pb input{flex:1;min-width:0;background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:10px;padding:7px 12px;color:inherit;font:13px ui-monospace,SFMono-Regular,Menlo,monospace}
.pb .ic{border:1px solid hsl(var(--border));background:none;color:inherit;border-radius:8px;width:32px;height:32px;cursor:pointer;font-size:15px;flex:none}
.pb .ic:hover{background:hsl(var(--accent))}
.pb .btn{border:0;border-radius:999px;padding:6px 16px;font:600 13px/1.4 Inter,ui-sans-serif,system-ui,sans-serif;cursor:pointer;color:#0b0d1a;background:linear-gradient(90deg,#a78bfa,#60a5fa,#22d3ee);white-space:nowrap}
.pb .chips{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px;color:hsl(var(--muted-foreground))}
.pb .chip{border:1px solid hsl(var(--border));background:hsl(var(--card));color:hsl(var(--foreground));border-radius:999px;padding:2px 10px;cursor:pointer;font:12px ui-monospace,SFMono-Regular,Menlo,monospace}
.pb .chip:hover{background:hsl(var(--accent))}
.pb .frame{flex:1;min-height:0;border:1px solid hsl(var(--border));border-radius:12px;overflow:hidden;background:#fff}
.pb iframe{width:100%;height:100%;border:0;display:block}
.pb .empty{padding:40px 24px;color:hsl(var(--muted-foreground));background:hsl(var(--card));height:100%;box-sizing:border-box}
.pb .empty{line-height:1.8;overflow:auto}.pb .empty code{background:hsl(var(--muted));border-radius:6px;padding:1px 6px}
@media (max-width:760px){.pb{padding:10px}}`;

export function mount(container) {
  container.innerHTML = `<style>${CSS}</style><div class="pb">
    <div class="bar"><button class="ic" data-b title="Back">←</button><button class="ic" data-f title="Forward">→</button>
      <button class="ic" data-r title="Reload">⟳</button>
      <input spellcheck="false" placeholder="8000/docs  ·  ~/storage-reports/…/report.html">
      <button class="btn" data-go>Open</button><button class="ic" data-w title="Open in a new browser tab">↗</button></div>
    <div class="chips"></div>
    <div class="frame"><div class="empty"><b>Shows web pages running on this VM</b>, inside the UI:<br>
      · apps <b>your account</b> runs: a FastAPI service (<code>8000/docs</code>), a React / Vite dev server, a dashboard you started<br>
      · files under your home folder: <code>~/storage-reports/</code> (HTML reports with their charts)<br><br>
      It does not open internet sites (the VM is offline), other people's apps, or the storage / vCenter web pages.<br><br>
      Type a port (<code>8000</code>) or a path (<code>~/</code>) above, or ask Claude: "show me the API docs in the Browser tab".</div></div></div>`;
  const input = container.querySelector('input');
  const frameBox = container.querySelector('.frame');
  const chips = container.querySelector('.chips');
  let frame = null;
  let stopped = false;

  function open(url) {
    const p = toPreview(url);
    if (!p) { input.setCustomValidity('Use a port (8000/docs) or a path under ~'); input.reportValidity(); return; }
    input.setCustomValidity('');
    if (!frame) {
      frameBox.innerHTML = '<iframe title="Browser"></iframe>';
      frame = frameBox.querySelector('iframe');
      frame.addEventListener('load', () => {     // same origin: follow the page's own navigation in the address bar
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
    const list = (d.ports || []).map((p) => `<button class="chip" data-u="${p}/">localhost:${p}</button>`).join('');
    chips.innerHTML = `Your apps: ${list || '<span>none listening</span>'}<button class="chip" data-u="~/storage-reports/">~/storage-reports</button>`;
    chips.querySelectorAll('[data-u]').forEach((b) => b.addEventListener('click', () => open(b.dataset.u)));
  }

  // paas-open (Claude or the person in a terminal) writes the page to open; take each one once
  async function poll() {
    if (stopped) return;
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
  container._paasStop = () => { stopped = true; };

  ports();
  const last = store.get(LAST);
  if (last) open(last);
  poll();
}

export function unmount(container) { container._paasStop?.(); container.innerHTML = ''; }
