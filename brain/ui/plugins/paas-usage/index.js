// Usage tab: tokens and estimated cost per day, model, project and session (data: server.js).
const fmtTok = (n) => (n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : `${n}`);
const fmtUsd = (n) => (n >= 100 ? `$${n.toFixed(0)}` : `$${n.toFixed(2)}`);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const shortPath = (p) => esc(String(p || '').replace(/^\/home\/[^/]+|^\/Users\/[^/]+|^\/root/, '~'));

const CSS = `
.pu{font:14px/1.5 ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));padding:28px;max-width:1100px;margin:0 auto}
@media (max-width:640px){.pu{padding:16px}.pu .tiles{grid-template-columns:1fr 1fr;gap:10px}.pu .tile{padding:12px}.pu .tile .v{font-size:20px}.pu .grid2{grid-template-columns:1fr}.pu .name{max-width:150px}}
.pu h2{font-size:22px;font-weight:700;margin:0}.pu .sub{color:hsl(var(--muted-foreground));font-size:13px}
.pu .row{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin-bottom:20px}
.pu .seg{display:inline-flex;border:1px solid hsl(var(--border));border-radius:10px;overflow:hidden}
.pu .seg button{padding:6px 14px;background:none;border:0;color:hsl(var(--muted-foreground));cursor:pointer;font:inherit}
.pu .seg button.on{background:hsl(var(--accent));color:hsl(var(--foreground));font-weight:600}
.pu .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px}
.pu .tile{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:14px;padding:16px}
.pu .tile .k{font-size:12px;color:hsl(var(--muted-foreground));text-transform:uppercase;letter-spacing:.08em}
.pu .tile .v{font-size:28px;font-weight:700;margin-top:4px;font-variant-numeric:tabular-nums}
.pu .card{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:14px;padding:18px;margin-bottom:16px}
.pu .card h3{margin:0 0 12px;font-size:15px;font-weight:600}
.pu .chart{position:relative;height:200px;display:flex;align-items:flex-end;gap:3px;border-bottom:1px solid hsl(var(--border))}
.pu .bar{flex:1;min-width:2px;border-radius:4px 4px 0 0;background:linear-gradient(180deg,#a78bfa,#60a5fa);opacity:.9;position:relative}
.pu .bar:hover{opacity:1;outline:2px solid hsl(var(--card))}
.pu .hit{flex:1;height:100%;display:flex;align-items:flex-end;cursor:default}
.pu .axis{display:flex;justify-content:space-between;color:hsl(var(--muted-foreground));font-size:11px;margin-top:6px}
.pu .tip{position:absolute;pointer-events:none;background:hsl(var(--popover));color:hsl(var(--popover-foreground));border:1px solid hsl(var(--border));border-radius:8px;padding:6px 10px;font-size:12px;white-space:nowrap;box-shadow:0 8px 24px rgba(0,0,0,.25);display:none;z-index:5}
.pu .grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.pu table{width:100%;border-collapse:collapse;font-size:13px}
.pu td,.pu th{padding:7px 6px;text-align:left;border-bottom:1px solid hsl(var(--border)/.6)}
.pu th{color:hsl(var(--muted-foreground));font-weight:500;font-size:12px}
.pu td.n,.pu th.n{text-align:right;font-variant-numeric:tabular-nums}
.pu .meter{height:4px;border-radius:4px;background:linear-gradient(90deg,#a78bfa,#22d3ee);margin-top:4px}
.pu .name{max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pu .note{color:hsl(var(--muted-foreground));font-size:12px;margin-top:8px}`;

export function mount(container, api) {
  let days = 30;
  container.innerHTML = `<style>${CSS}</style><div class="pu"><div class="row"><div><h2>Usage</h2>
    <div class="sub">Tokens and estimated cost of every Claude Code session on this VM</div></div>
    <div class="seg">${[7, 30, 90].map((d) => `<button data-d="${d}" class="${d === days ? 'on' : ''}">${d} days</button>`).join('')}</div></div>
    <div class="body"><div class="sub">Reading session logs…</div></div></div>`;
  const body = container.querySelector('.body');
  container.querySelectorAll('.seg button').forEach((b) => b.addEventListener('click', () => {
    days = Number(b.dataset.d);
    container.querySelectorAll('.seg button').forEach((x) => x.classList.toggle('on', x === b));
    load();
  }));

  const table = (rows, label, nameFn) => {
    const max = Math.max(...rows.map((r) => r.cost), 1e-9);
    return `<table><tr><th>${label}</th><th class="n">Tokens</th><th class="n">Est. cost</th></tr>${rows.map((r) => `
      <tr><td><div class="name" title="${esc(r.key)}">${nameFn(r)}</div><div class="meter" style="width:${(r.cost / max) * 100}%"></div></td>
      <td class="n">${fmtTok(r.tokens)}</td><td class="n">${fmtUsd(r.cost)}</td></tr>`).join('') || '<tr><td colspan="3" class="sub">Nothing yet</td></tr>'}</table>`;
  };

  async function load() {
    let d;
    try { d = await api.rpc('GET', `summary?days=${days}`); } catch (e) { body.innerHTML = `<div class="sub">Could not read usage: ${esc(e.message || e)}</div>`; return; }
    const t = d.total;
    const max = Math.max(...d.days.map((x) => x.cost), 1e-9);
    body.innerHTML = `
      <div class="tiles">
        <div class="tile"><div class="k">Est. cost</div><div class="v">${fmtUsd(t.cost)}</div></div>
        <div class="tile"><div class="k">Output tokens</div><div class="v">${fmtTok(t.output)}</div></div>
        <div class="tile"><div class="k">Input + cache</div><div class="v">${fmtTok(t.input + t.cacheRead + t.cacheWrite)}</div></div>
        <div class="tile"><div class="k">Sessions · replies</div><div class="v">${d.sessions} · ${t.messages}</div></div>
      </div>
      <div class="card"><h3>Estimated cost per day <span class="sub" style="font-weight:400">· peak ${fmtUsd(max)}</span></h3><div class="chart">${d.days.map((x) => `
        <div class="hit" data-t="${esc(x.key)}: ${fmtUsd(x.cost)} · ${fmtTok(x.tokens)} tokens · ${x.messages} replies">
        <div class="bar" style="height:${x.cost ? Math.max((x.cost / max) * 100, 1.5) : 0}%"></div></div>`).join('')}
        <div class="tip"></div></div>
        <div class="axis"><span>${esc(d.days[0].key)}</span><span>${esc(d.days[d.days.length - 1].key)}</span></div></div>
      <div class="grid2">
        <div class="card"><h3>By project</h3>${table(d.projects, 'Project', (r) => shortPath(r.key))}</div>
        <div class="card"><h3>By model</h3>${table(d.models, 'Model', (r) => esc(r.key))}</div>
      </div>
      <div class="card"><h3>Most expensive sessions</h3>${table(d.topSessions, 'Session', (r) => `${shortPath(r.project)} <span class="sub">${esc(r.session.slice(0, 8))}</span>`)}</div>
      <div class="note">Estimated at Anthropic API list prices (cache writes and reads included). On a Claude subscription you are not billed per token; the numbers show relative usage.</div>`;
    const chart = body.querySelector('.chart');
    const tip = chart.querySelector('.tip');
    chart.querySelectorAll('.hit').forEach((h) => {
      h.addEventListener('mouseenter', () => {
        tip.textContent = h.dataset.t; tip.style.display = 'block';
        const left = h.offsetLeft + h.offsetWidth / 2 - tip.offsetWidth / 2;
        tip.style.left = `${Math.min(Math.max(left, 0), chart.clientWidth - tip.offsetWidth)}px`; tip.style.top = '-8px';
      });
      h.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
    });
  }
  load();
}

export function unmount(container) { container.innerHTML = ''; }
