// Schedule tab: jobs that run a prompt or skill at set times, their next run and run history (data: server.js).
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const when = (j) => (j.repeat === 'weekly' ? `Every ${DAYS[j.day]} at ${j.time}` : j.repeat === 'weekdays' ? `Weekdays at ${j.time}` : `Every day at ${j.time}`);
const fmt = (iso) => (iso ? new Date(iso).toLocaleString([], { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—');

const CSS = `
.sc{font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));padding:28px;max-width:1000px;margin:0 auto}
.sc h2{font-size:22px;font-weight:700;margin:0}.sc .sub{color:hsl(var(--muted-foreground));font-size:13px}
.sc .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;justify-content:space-between}
.sc .top{margin-bottom:20px}
.sc .go{border:0;border-radius:999px;padding:7px 18px;font:600 13px/1.4 inherit;cursor:pointer;color:#0b0d1a;background:linear-gradient(90deg,#a78bfa,#60a5fa,#22d3ee)}
.sc .ghost{border:1px solid hsl(var(--border));background:none;color:inherit;border-radius:999px;padding:5px 14px;font:500 12.5px/1.4 inherit;cursor:pointer}
.sc .ghost.danger{color:hsl(var(--destructive))}
.sc .card{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:14px;padding:16px 18px;margin-bottom:12px}
.sc .card.off{opacity:.6}
.sc .t{font-weight:600;font-size:15px}.sc .p{font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:hsl(var(--muted-foreground));margin-top:4px;white-space:pre-wrap;max-height:60px;overflow:hidden}
.sc .meta{display:flex;gap:18px;flex-wrap:wrap;margin-top:10px;font-size:13px}.sc .meta b{font-weight:600}
.sc .pill{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600;border-radius:999px;padding:1px 9px}
.sc .pill::before{content:'';width:7px;height:7px;border-radius:50%;background:currentColor}
.sc .ok{color:#16a34a;background:rgba(22,163,74,.12)}.sc .fail{color:#dc2626;background:rgba(220,38,38,.13)}.sc .run{color:#7c3aed;background:rgba(124,58,237,.13)}
.sc .acts{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}
.sc .form{display:grid;gap:14px;margin-top:12px}.sc label{display:block;font-weight:600;font-size:13px}.sc label .sub{font-weight:400;margin-left:6px;font-size:12px}
.sc input,.sc select,.sc textarea{width:100%;box-sizing:border-box;margin-top:4px;background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:10px;padding:8px 12px;color:inherit;font:inherit;font-weight:400}
.sc textarea{font:12.5px/1.55 ui-monospace,Menlo,monospace;min-height:110px}
.sc .three{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.sc table{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}.sc td{padding:6px;border-top:1px solid hsl(var(--border)/.6)}
.sc pre{white-space:pre-wrap;font:12.5px/1.55 ui-monospace,Menlo,monospace;background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:10px;padding:12px;max-height:420px;overflow:auto;margin-top:10px}
.sc .empty{padding:36px 16px;text-align:center;color:hsl(var(--muted-foreground))}
@media (max-width:640px){.sc{padding:16px}}`;

export function mount(container, api) {
  let jobs = [];
  let open = null;        // job id whose history is shown
  container.innerHTML = `<style>${CSS}</style><div class="sc"><div class="row top"><div><h2>Schedule</h2>
    <div class="sub">Run a question or a skill at set times on this VM. Each run is saved in Reports and appears under Conversations.</div></div>
    <button class="go new">+ New schedule</button></div><div class="body"><div class="empty">Loading…</div></div></div>`;
  const body = container.querySelector('.body');
  container.querySelector('.new').addEventListener('click', () => form({}));

  async function load() {
    try { jobs = (await api.rpc('GET', 'jobs')).jobs; } catch (e) { body.innerHTML = `<div class="empty">Could not load: ${esc(e.message || e)}</div>`; return; }
    list();
  }

  function list() {
    if (!jobs.length) {
      body.innerHTML = `<div class="empty">Nothing scheduled yet.<br>For example: <b>/morning-check</b> every weekday at 07:00, or <b>/capacity-report</b> every Monday.</div>`;
      return;
    }
    body.innerHTML = jobs.map((j) => {
      const last = j.runs?.[0];
      const status = j.running ? '<span class="pill run">Running</span>' : last ? `<span class="pill ${last.ok ? 'ok' : 'fail'}">${last.ok ? 'OK' : 'Failed'}</span>` : '<span class="sub">never ran</span>';
      return `<div class="card${j.enabled ? '' : ' off'}" data-id="${esc(j.id)}">
        <div class="row"><div class="t">${esc(j.name)}</div>${status}</div>
        <div class="p">${esc(j.prompt)}</div>
        <div class="meta"><span><b>${esc(when(j))}</b>${j.enabled ? '' : ' · paused'}</span><span>Next: ${esc(fmt(j.next))}</span>
          <span>Last: ${esc(fmt(last?.at))}</span><span class="sub">in ${esc(j.folder)}</span></div>
        <div class="acts"><button class="ghost" data-a="run">Run now</button><button class="ghost" data-a="toggle">${j.enabled ? 'Pause' : 'Resume'}</button>
          <button class="ghost" data-a="edit">Edit</button><button class="ghost" data-a="hist">${open === j.id ? 'Hide runs' : `Runs (${j.runs?.length || 0})`}</button>
          <button class="ghost danger" data-a="del">Delete</button></div>
        ${open === j.id ? `<table>${(j.runs || []).map((r) => `<tr><td>${esc(fmt(r.at))}</td><td>${r.ok ? '<span class="pill ok">OK</span>' : '<span class="pill fail">Failed</span>'}</td>
          <td class="sub">${esc(r.why)} · ${r.seconds} s</td><td><button class="ghost" data-rep="${esc(r.report)}">View</button></td></tr>`).join('') || '<tr><td class="sub">No runs yet</td></tr>'}</table><div class="rep"></div>` : ''}
      </div>`;
    }).join('');
    body.querySelectorAll('[data-a]').forEach((b) => b.addEventListener('click', () => act(b.closest('.card').dataset.id, b.dataset.a, b)));
    body.querySelectorAll('[data-rep]').forEach((b) => b.addEventListener('click', async () => {
      const r = await api.rpc('GET', `report?file=${encodeURIComponent(b.dataset.rep)}`).catch((x) => ({ out: String(x) }));
      b.closest('.card').querySelector('.rep').innerHTML = `<pre>${esc(r.ok ? r.text : r.out)}</pre>`;
    }));
  }

  async function act(id, a, btn) {
    const j = jobs.find((x) => x.id === id);
    if (a === 'edit') return form(j);
    if (a === 'hist') { open = open === id ? null : id; return list(); }
    if (a === 'del' && !window.confirm(`Delete the schedule "${j.name}"? Its reports stay in Reports.`)) return;
    btn.disabled = true;
    const r = a === 'run' ? await api.rpc('POST', 'run', { id })
      : a === 'del' ? await api.rpc('POST', 'job-delete', { id })
        : await api.rpc('POST', 'job', { ...j, enabled: !j.enabled });
    if (!r.ok) window.alert(r.out);
    await load();
  }

  function form(j) {
    body.innerHTML = `<div class="card"><div class="t">${j.id ? 'Edit schedule' : 'New schedule'}</div>
      <div class="form">
        <label>Name<input class="f-name" value="${esc(j.name || '')}" placeholder="Morning check"></label>
        <label>Prompt <span class="sub">what Claude should do: a question, or a skill like /morning-check</span>
          <textarea class="f-prompt" placeholder="/morning-check fabric A and B, all arrays">${esc(j.prompt || '')}</textarea></label>
        <div class="three">
          <label>Repeat<select class="f-repeat">${[['daily', 'Every day'], ['weekdays', 'Weekdays (Mon–Fri)'], ['weekly', 'Once a week']].map(([v, l]) => `<option value="${v}"${(j.repeat || 'weekdays') === v ? ' selected' : ''}>${l}</option>`).join('')}</select></label>
          <label class="day">Day<select class="f-day">${DAYS.map((d, i) => `<option value="${i}"${Number(j.day ?? 1) === i ? ' selected' : ''}>${d}</option>`).join('')}</select></label>
          <label>Time <span class="sub">VM clock</span><input class="f-time" type="time" value="${esc(j.time || '07:00')}"></label>
        </div>
        <label>Folder <span class="sub">~/chats for a plain chat, or a project folder</span><input class="f-folder" value="${esc(j.folder || '~/chats')}"></label>
        <div class="sub">Runs without anyone watching: anything that would ask for permission is skipped, so keep scheduled prompts to checks and reports.</div>
      </div>
      <div class="acts"><button class="go f-save">Save</button><button class="ghost f-cancel">Cancel</button><span class="sub f-st"></span></div></div>`;
    const v = (c) => body.querySelector(c).value;
    const dayVis = () => { body.querySelector('.day').style.display = v('.f-repeat') === 'weekly' ? '' : 'none'; };
    body.querySelector('.f-repeat').addEventListener('change', dayVis);
    dayVis();
    body.querySelector('.f-cancel').addEventListener('click', list);
    body.querySelector('.f-save').addEventListener('click', async (e) => {
      e.target.disabled = true;
      const r = await api.rpc('POST', 'job', { id: j.id, enabled: j.enabled !== false, name: v('.f-name'), prompt: v('.f-prompt'),
        repeat: v('.f-repeat'), day: Number(v('.f-day')), time: v('.f-time'), folder: v('.f-folder') }).catch((x) => ({ out: String(x) }));
      e.target.disabled = false;
      if (!r.ok) { body.querySelector('.f-st').textContent = r.out; return; }
      await load();
    });
  }

  load();
  const poll = setInterval(() => { if (!body.querySelector('.f-save') && jobs.some((j) => j.running)) load(); }, 10000);   // until running jobs finish
  container.addEventListener('paas-unmount', () => clearInterval(poll), { once: true });
}

export function unmount(container) {
  container.dispatchEvent(new Event('paas-unmount'));
  container.innerHTML = '';
}
