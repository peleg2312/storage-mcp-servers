// Reports tab: the files Claude saved in ~/storage-reports, newest first, with preview and download (data: server.js).
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmtSize = (n) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : n >= 1024 ? `${(n / 1024).toFixed(0)} KB` : `${n} B`);
const fmtTime = (ms) => new Date(ms).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
const ext = (p) => (p.match(/\.([a-z0-9]+)$/i)?.[1] || '').toLowerCase();
const MIME = { csv: 'text/csv', md: 'text/markdown', html: 'text/html', htm: 'text/html', json: 'application/json', svg: 'image/svg+xml',
  png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', pdf: 'application/pdf',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' };

// one CSV line -> cells (quoted cells may hold commas and doubled quotes)
function cells(line, sep) {
  const out = []; let cur = ''; let q = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (q) { if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; } else if (c === '"') q = false; else cur += c; }
    else if (c === '"') q = true; else if (c === sep) { out.push(cur); cur = ''; } else cur += c;
  }
  out.push(cur);
  return out;
}

const CSS = `
.pr{font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));padding:28px;max-width:1200px;margin:0 auto;height:100%;box-sizing:border-box;display:flex;flex-direction:column}
.pr h2{font-size:22px;font-weight:700;margin:0}.pr .sub{color:hsl(var(--muted-foreground));font-size:13px}
.pr .row{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin-bottom:16px}
.pr input{background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:10px;padding:7px 12px;color:inherit;font:inherit;min-width:220px}
.pr .split{display:grid;grid-template-columns:minmax(260px,360px) 1fr;gap:16px;flex:1;min-height:0}
.pr .list,.pr .view{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:14px;overflow:auto;min-height:0}
.pr .item{display:block;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid hsl(var(--border)/.6);padding:10px 14px;color:inherit;font:inherit;cursor:pointer}
.pr .item:hover{background:hsl(var(--accent)/.5)}.pr .item.on{background:hsl(var(--accent))}
.pr .item .n{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pr .badge{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;border-radius:6px;padding:1px 6px;margin-right:6px;background:hsl(var(--muted));color:hsl(var(--muted-foreground))}
.pr .vh{display:flex;gap:10px;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid hsl(var(--border));position:sticky;top:0;background:hsl(var(--card))}
.pr .vh .n{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pr .btn{border:0;border-radius:999px;padding:6px 16px;font:600 13px/1.4 Inter,ui-sans-serif,system-ui,sans-serif;cursor:pointer;color:#0b0d1a;background:linear-gradient(90deg,#a78bfa,#60a5fa,#22d3ee);white-space:nowrap}
.pr .btn.ghost{background:none;color:hsl(var(--foreground));border:1px solid hsl(var(--border))}
.pr .body{padding:16px}
.pr pre{margin:0;white-space:pre-wrap;word-break:break-word;font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
.pr table{border-collapse:collapse;font-size:12.5px}.pr td,.pr th{border:1px solid hsl(var(--border)/.7);padding:4px 8px;white-space:nowrap}
.pr th{background:hsl(var(--muted)/.6);position:sticky;top:0}
.pr iframe{width:100%;height:70vh;border:0;background:#fff;border-radius:8px}
.pr img{max-width:100%;border-radius:8px;background:#fff}
.pr .empty{padding:40px 20px;text-align:center;color:hsl(var(--muted-foreground))}
@media (max-width:760px){.pr{padding:16px}.pr .split{grid-template-columns:1fr}.pr .list{max-height:40vh}}`;

export function mount(container, api) {
  let files = [];
  let selected = null;
  container.innerHTML = `<style>${CSS}</style><div class="pr"><div class="row"><div><h2>Reports</h2>
    <div class="sub">Files Claude saved in <code>~/storage-reports</code>: ask it to "export this as CSV / Excel / HTML"</div></div>
    <div style="display:flex;gap:8px"><input type="search" placeholder="Filter by name…"><button class="btn ghost" data-r>Refresh</button></div></div>
    <div class="split"><div class="list"><div class="empty">Loading…</div></div><div class="view"><div class="empty">Pick a file to preview it</div></div></div></div>`;
  const listEl = container.querySelector('.list');
  const viewEl = container.querySelector('.view');
  const filter = container.querySelector('input');

  function renderList() {
    const q = filter.value.trim().toLowerCase();
    const shown = files.filter((f) => f.path.toLowerCase().includes(q));
    listEl.innerHTML = shown.map((f) => `<button class="item${f.path === selected ? ' on' : ''}" data-p="${esc(f.path)}">
      <div class="n" title="${esc(f.path)}">${esc(f.path)}</div>
      <div class="sub"><span class="badge">${esc(ext(f.path) || 'file')}</span>${fmtSize(f.size)} · ${fmtTime(f.mtime)}</div></button>`).join('')
      || `<div class="empty">${files.length ? 'No file matches' : 'No reports yet. Ask Claude to save one, e.g. "export the LUN list as Excel".'}</div>`;
    listEl.querySelectorAll('.item').forEach((b) => b.addEventListener('click', () => open(b.dataset.p)));
  }

  async function load() {
    try {
      const d = await api.rpc('GET', 'list');
      files = d.files;
    } catch (e) {
      listEl.innerHTML = `<div class="empty">Could not list reports: ${esc(e.message || e)}</div>`;
      return;
    }
    renderList();
  }

  const blobOf = (d) => {
    const type = MIME[ext(d.name)] || 'application/octet-stream';
    if (d.encoding === 'utf8') return new Blob([d.data], { type });
    const bin = atob(d.data);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new Blob([bytes], { type });
  };

  async function open(p) {
    selected = p;
    renderList();
    viewEl.innerHTML = '<div class="empty">Loading…</div>';
    let d;
    try { d = await api.rpc('GET', `file?path=${encodeURIComponent(p)}`); } catch (e) {
      viewEl.innerHTML = `<div class="empty">Could not open ${esc(p)}: ${esc(e.message || e)}</div>`;
      return;
    }
    const e = ext(d.name);
    let body;
    if (e === 'csv' || e === 'tsv') {
      const rows = d.data.split(/\r?\n/).filter(Boolean).slice(0, 501).map((l) => cells(l, e === 'tsv' ? '\t' : ','));
      body = `<table>${rows.map((r, i) => `<tr>${r.map((c) => (i ? `<td>${esc(c)}</td>` : `<th>${esc(c)}</th>`)).join('')}</tr>`).join('')}</table>
        ${rows.length > 500 ? '<div class="sub" style="margin-top:8px">First 500 rows shown; download for all of it</div>' : ''}`;
    } else if (e === 'html' || e === 'htm') {
      body = `<iframe sandbox="" srcdoc="${esc(d.data)}"></iframe>`;
    } else if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(e)) {
      body = `<img alt="${esc(d.name)}" src="${URL.createObjectURL(blobOf(d))}">`;
    } else if (d.encoding === 'utf8') {
      body = `<pre>${esc(d.data.length > 400000 ? `${d.data.slice(0, 400000)}\n…` : d.data)}</pre>`;
    } else {
      body = `<div class="empty">No preview for .${esc(e)} files: download it to open it</div>`;
    }
    viewEl.innerHTML = `<div class="vh"><div class="n" title="${esc(p)}">${esc(p)}</div><button class="btn" data-dl>Download</button></div><div class="body">${body}</div>`;
    viewEl.querySelector('[data-dl]').addEventListener('click', () => {
      const url = URL.createObjectURL(blobOf(d));
      const a = document.createElement('a');
      a.href = url; a.download = d.name;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    });
  }

  filter.addEventListener('input', renderList);
  container.querySelector('[data-r]').addEventListener('click', load);
  load();
}

export function unmount(container) { container.innerHTML = ''; }
