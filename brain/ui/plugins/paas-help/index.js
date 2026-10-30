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

// Help tab: how to use this UI - chats, commands, modes, every tab, the terminal, the safety rules, common fixes.
// Plain content, searchable; nothing is sent anywhere.
const k = (s) => `<kbd>${s}</kbd>`;
const tab = (s) => `<span class="tb">${s}</span>`;

const SECTIONS = [
  { id: 'start', title: 'Start here', body: `
    <p>This is Claude, your assistant for storage and development work. Ask in plain words, it looks things up,
    checks your systems when you ask it to, and writes reports, scripts and code for you.</p>
    <div class="grid">
      <div class="card"><h3>Knows your environment</h3><p>Reads PowerMax, ONTAP, PowerFlex, MDS, UCS and VMware, and searches the vendor docs and KBs.</p></div>
      <div class="card"><h3>Never changes storage</h3><p>It only reads your systems. When something needs changing, it gives you the exact steps to run.</p></div>
      <div class="card"><h3>Yours</h3><p>Your chats, files, reports and notes are your own. Nobody else sees them.</p></div>
    </div>
    <h3>Try this first</h3>
    <ol><li>Press <b>New chat</b> in the left menu (${k('☰')} on a phone) and ask something, e.g. "which hosts have only one path?".</li>
    <li>Type ${k('/')} in the message box to see every command.</li>
    <li>Ask for "an Excel of all LUNs over 2 TB" and find it in ${tab('Reports')}.</li>
    <li>Writing code? Create a <b>project</b> and set your Git name once (see <i>Projects</i>).</li>
    <li>Open ${tab('Status')} to see what Claude can reach.</li></ol>` },

  { id: 'chatting', title: 'Writing to Claude', body: `
    <ul><li>${k('Enter')} sends, ${k('Shift')}+${k('Enter')} is a new line.</li>
    <li><b>📎</b> attaches files (logs, screenshots, exports, up to 50 MB). Type ${k('@')} to point at a file in your project.</li>
    <li>The answer appears <b>as it is written</b>. Steps Claude takes (searches, queries, commands) show as boxes: click one to see what it ran and what came back.</li>
    <li><b>Thinking</b> is folded away: click "Thinking" to read how it reasoned.</li>
    <li><b>Stop</b> (the square button) ends the answer. A note "No response requested" after it is normal.</li>
    <li>The chat follows the answer down. Scroll up to read and it stays where you are; scroll back down to follow again.</li>
    <li>Files Claude makes get a <b>↓ Download</b> button: one click and it is on your computer.</li></ul>
    <h3>Sending more while it is still answering</h3>
    <ul><li>Just send: your message waits in a <b>queue</b> above the box and goes out by itself when the answer ends.</li>
    <li><b>Edit</b> or <b>Delete</b> a queued message if you change your mind.</li>
    <li>Urgent? <b>Send now</b> stops the current answer and sends yours straight away.</li></ul>` },

  { id: 'asking', title: 'Getting good answers', body: `
    <ul><li><b>Name what you mean</b>: the array, SVM, volume, LUN ID / NAA / WWN, host or fabric. "Why is LUN 6000097... slow on esx12?" beats "a LUN is slow".</li>
    <li><b>Say whether to check live.</b> "What does this error mean?" is answered from the docs. "Check which volumes are over 90%" makes Claude look at the systems.</li>
    <li>Answers start with the short answer, then the evidence, the findings and the <b>sources</b>. If something could not be checked, it says so: it does not guess.</li>
    <li>Long lists or trends: ask for "a chart", "Excel" or "CSV".</li>
    <li>Need a change made? Claude writes the steps <b>for you to run</b>, with checks before and after and how to undo it.</li>
    <li>Tell it a fact once ("our prod SVMs start with svm_p") and it remembers it for next time.</li>
    <li><b>Paste a log line, alert or code</b> and ask "explain this": Claude looks it up in the vendor docs and answers with sources.</li>
    <li><b>Open a document</b>: "show me the start of the PowerMax SRDF guide". <b>Ask several things at once</b>: Claude searches for all of them together.</li></ul>
    <h3>Ideas</h3>
    <ul class="ex"><li>Which hosts have a single path to array 1234?</li><li>Trace this OpenShift PVC to its LUN, array and switch ports.</li>
    <li>What does EMS event wafl.vol.autoSize.fail mean and what do I do?</li><li>IOPS and latency per volume for this PowerFlex host.</li>
    <li>Is this LUN still used anywhere?</li><li>Build a FastAPI endpoint that lists storage groups, with tests.</li><li>Show me my app in the Browser tab.</li></ul>` },

  { id: 'commands', title: '/ commands', body: `
    <p>Type ${k('/')} in the message box (or press <b>/</b>). Keep typing to filter, ${k('↑')} ${k('↓')} and ${k('Enter')} to pick.</p>
    <h3>Ready-made routines</h3>
    <ul><li><code>/morning-check</code> the daily health round · <code>/capacity-report</code> capacity across arrays</li>
    <li><code>/trace-path</code> a host to its storage, end to end · <code>/identify-lun</code> what a NAA / WWN is and where it lives</li>
    <li><code>/zoning-audit</code>, <code>/fabric-health</code> the SAN fabrics · <code>/replication-check</code> SRDF / SnapMirror</li>
    <li><code>/explain-error</code> an error or alert, from the docs · <code>/change-review</code> a change plan checked before you run it</li>
    <li><code>/decommission-check</code> before anything is removed · <code>/report-export</code> Excel, CSV, charts</li></ul>
    <p>You rarely have to type them: Claude picks the right one from your question.</p>
    <h3>Handy commands</h3>
    <ul><li><code>/clear</code> empties this chat and moves it to the archive (you can restore it). <code>/new</code> starts a new chat and keeps this one.</li>
    <li><code>/compact</code> a long chat: Claude summarises it and carries on, quicker and cheaper.</li>
    <li><code>/context</code> how full the chat is · <code>/cost</code> what it has used so far.</li>
    <li><code>/review</code> looks over code changes in a project.</li></ul>` },

  { id: 'chats', title: 'Chats', body: `
    <ul><li><b>New chat</b> (the + at the top of the left menu): a fresh conversation, for questions and investigations.</li>
    <li>The list on the left: <b>Conversations</b>, <b>Projects</b>, or <b>Running sessions</b> (chats answering right now).</li>
    <li>Each chat's <b>⋯</b> menu: rename, archive or delete.</li>
    <li>Like a terminal better? Your chats are there too: <code>claude --resume</code> picks one up, and the other way round.</li></ul>` },

  { id: 'projects', title: 'Projects: code, files and Git', body: `
    <p>A <b>project</b> is a folder you work in with Claude: an API, a script collection, a Terraform repo. Its chats run in that folder,
    so Claude reads and edits the code there. A project also gets three more tabs: ${tab('Shell')}, ${tab('Files')} and ${tab('Source control')}.</p>
    <h3>Set up Git once</h3>
    <p>Before your first commit, tell Git who you are: <b>Settings → Git</b>, fill in your name and your GitLab e-mail, <b>Save</b>.
    (Or in ${tab('Shell')}: <code>git config --global user.name "Your Name"</code> and <code>git config --global user.email you@company.com</code>.)</p>
    <h3>Create a project</h3>
    <ol><li>Press the <b>folder</b> button at the top of the left menu.</li>
    <li><b>Existing workspace</b>: a folder you already have, e.g. <code>~/projects/storage-api</code>.
      <b>New workspace</b>: a new folder, empty or <b>cloned from a Git URL</b> (your GitLab repository).</li>
    <li>The repository needs a login? Clone it in a terminal first (<code>git clone https://gitlab.../group/repo.git</code>, it asks for your user and token), then add the folder as an existing workspace.</li></ol>
    <h3>${tab('Files')}</h3>
    <ul><li>The folder as a tree: search, open a file to read or edit it, save.</li>
    <li>Right-click (long-press on a phone): new file or folder, rename, delete, copy path, <b>Upload files</b>, <b>Download</b>.</li>
    <li>Simple, compact or detailed view (sizes, dates, permissions).</li></ul>
    <h3>${tab('Shell')}</h3>
    <p>A terminal in the project folder, as you: run tests, start your app (then see it in ${tab('Browser')}), use git or any tool.</p>
    <h3>${tab('Source control')}</h3>
    <ul><li><b>Changes</b>: every changed file with its diff; tick the files, write a message, <b>Commit</b>.</li>
    <li><b>Commits</b>: the history. <b>Compare</b>: two branches side by side. <b>Branches</b>: switch, create, delete.</li>
    <li><b>Fetch</b>, <b>Pull</b> and <b>Push</b> at the top, with how many commits are waiting each way.</li>
    <li>Not a Git folder yet? <b>Run git init</b> starts one.</li></ul>
    <p class="note">Or just ask in the project's chat: "commit this with a good message", "create a branch for the new endpoint", "what changed since yesterday?". Claude shows the diff and asks before it commits or pushes.</p>` },

  { id: 'modes', title: 'How much Claude may do on its own', body: `
    <p>Next to the send button: the <b>model</b> and the <b>approval mode</b>. ${k('Tab')} in the message box switches mode.</p>
    <table><tr><th>Mode</th><th>Claude does on its own</th><th>Good for</th></tr>
    <tr><td><b>Default</b></td><td>Reading and looking things up; asks before anything else</td><td>Everyday use</td></tr>
    <tr><td><b>Auto</b></td><td>Each step is checked and allowed or refused for you, no questions</td><td>Long investigations without clicking "allow"</td></tr>
    <tr><td><b>Accept edits</b></td><td>Edits and commands inside your project</td><td>Coding</td></tr>
    <tr><td><b>Plan</b></td><td>Nothing: it only plans</td><td>Thinking a change through first</td></tr>
    <tr><td><b>Bypass</b></td><td>Everything on the server with no questions: files, installs, service restarts, cluster changes (oc / kubectl / helm), database writes, terraform</td><td>When you trust the task and want no interruptions</td></tr></table>
    <p class="note">Whatever the mode, changes to storage arrays, SAN switches, UCS and VMware stay blocked: Claude gives you those steps to run yourself.
    In the other modes, when Claude asks to run something, read it, then <b>Allow</b> or <b>Deny</b> (and say why).</p>` },

  { id: 'reports', title: 'Reports', body: `
    <p>${tab('Reports')} holds everything Claude saved for you: Excel, CSV, charts, write-ups. Newest first.</p>
    <ul><li>Click a file to preview it, <b>Download</b> to keep it. Filter by name at the top.</li>
    <li>Scheduled runs are in the <code>scheduled</code> folder. Files over 25 MB are listed but not previewed.</li>
    <li>Ask for one in any chat: "export this as Excel", "chart the latency for the last week".</li></ul>` },

  { id: 'browser', title: 'Browser', body: `
    <p>${tab('Browser')} shows web pages from your own work inside this page:</p>
    <ul><li>An app you are building: type its port and path, e.g. <code>8000/docs</code>.</li>
    <li>Your files and reports: <code>~/storage-reports/</code>, an HTML report with its charts.</li>
    <li>The <b>Your apps</b> row lists ports listening on this VM. ↗ opens the page in its own browser tab.</li>
    <li>Or ask: "show it to me in the Browser tab".</li></ul>
    <p class="note">It shows your own apps and files only, not internet sites or other people's apps.</p>` },

  { id: 'chrome', title: 'Chrome on your PC (DevTools)', body: `
    <p>With the <b>chrome-devtools</b> plugin (Marketplace → Add), Claude drives a Chrome window on <b>your</b> Windows PC:
    opens your app, clicks, types, takes screenshots, reads the console and network, checks speed and accessibility.</p>
    <ol><li>Ask Claude "connect my Chrome" (or run <code>paas-chrome windows</code>): it gives you one PowerShell line.</li>
    <li>Paste it into PowerShell on your PC and sign in. A separate Chrome window opens (its own empty profile, not your everyday Chrome). Keep the PowerShell window open; close it to disconnect.</li>
    <li>Ask: "open my app on port 8000 in Chrome and check the console", "test the login form", "why is this page slow?".</li></ol>
    <p class="note">Several people on the same account: each chat uses its own PC. If more than one PC is connected, Claude asks which one is yours.
    Switch a chat to another PC in the <b>Browser</b> tab ("Chrome on your PC") or just tell Claude.
    Claude may open any site, except storage, switch, UCS and vCenter pages: those stay read-only.</p>` },

  { id: 'uiux', title: 'UI design (UI UX Pro Max)', body: `
    <p>The <b>ui-ux-pro-max</b> plugin (Marketplace → Add) helps Claude design and review pages.</p>
    <ul><li>Ask: "design a dashboard for storage capacity", "make this page look professional", "review this form's UX".</li>
    <li>Fonts are installed locally from your npm (<code>@fontsource/…</code>), nothing loads from the internet.</li>
    <li>AI image generation (logos from Gemini) is not available here: Claude draws logos and icons as SVG instead.</li></ul>` },

  { id: 'brain', title: 'Brain', body: `
    <p>${tab('Brain')} is what Claude knows and can use:</p>
    <ul><li><b>Search</b> the vendor docs and KBs yourself, or ask Claude in chat: it uses the same search.</li>
    <li><b>Add documents</b>: upload PDFs or pages, or paste links to your wiki. Claude can search them a few seconds later.</li>
    <li><b>Skills and agents</b>: read, adjust or create your own routines. <b>Share with everyone</b> offers one to your colleagues.</li>
    <li><b>Systems</b> Claude can query, with <b>Check connections</b>, and your <b>memory</b> (the facts it remembers for you).</li>
    <li><b>Hooks</b> (under MCP & hooks): small helpers around Claude's steps, like docs hints or the Python check. Switch any helper off or on for your own chats. The read-only guard always stays on.</li></ul>` },

  { id: 'schedule', title: 'Schedule', body: `
    <p>${tab('Schedule')} runs a question or routine for you, <b>daily</b>, on <b>weekdays</b> or <b>weekly</b>.</p>
    <ul><li>Example: every weekday at 07:30, "check capacity on all arrays and list volumes over 85%".</li>
    <li>Each run lands in ${tab('Reports')} and as a chat you can open and continue.</li>
    <li><b>Run now</b> tries it straight away. <b>Edit</b> or <b>Delete</b> it any time. <b>Pause</b>/<b>Resume</b> a job.</li>
    <li>Runs are unattended and cannot ask permission. Each run stops after 30 minutes or about $2 (sonnet model).</li></ul>` },

  { id: 'status', title: 'Status', body: `
    <p>${tab('Status')} has <b>Health</b>: is this VM in order (disk, memory, docs library, read-only guard, connections to your systems). And <b>Usage</b>: tokens and estimated cost (API prices, not a bill) per day, project and chat.</p>
    <p>Claude says a system is unavailable? Look here first.</p>` },

  { id: 'market', title: 'Marketplace', body: `
    <p>${tab('Marketplace')} is what colleagues share: routines, helper agents and connections to more systems.</p>
    <ul><li><b>Add</b> what you like, <b>Update</b> when there is a newer version, <b>Remove</b> it again.</li>
    <li><b>Create and share</b> your own. Everyone can read shared items, so keep passwords out of them.</li></ul>` },

  { id: 'account', title: 'Account and settings', body: `
    <ul><li>Sign in with your usual user name and password. A sign-in lasts 12 hours. Forgot the password? Ask your admin.</li>
    <li><b>Sign out</b>: bottom of the left menu, next to your name.</li>
    <li><b>Quick settings</b> (the ‹ handle on the right edge): dark mode, language, show or hide thinking, send with ${k('Ctrl')}+${k('Enter')}.</li>
    <li>You can use it from several browsers or your phone at once: it is the same chats everywhere.</li></ul>` },

  { id: 'terminal', title: 'In a terminal', body: `
    <ul><li><code>claude</code> starts the same Claude in a terminal; <code>claude --resume</code> lists your chats.</li>
    <li><code>paas-open 8000/docs</code> shows a page in the Browser tab.</li>
    <li><code>add-docs</code> adds your own documents to the docs Claude searches.</li></ul>` },

  { id: 'safety', title: 'What Claude will and will not do', body: `
    <ul><li><b>Storage, switches, UCS and VMware: read only, always.</b> For a change you get the steps to run yourself.</li>
    <li>Kubernetes / OpenShift changes, service restarts and database writes: it asks you first, except in <b>Bypass</b> mode.</li>
    <li>Your own code and apps: it builds, runs and tests them with you.</li>
    <li>Nothing is called "safe to delete" until <code>/decommission-check</code> passed every check.</li>
    <li>Passwords and tokens never go into notes, reports or shared items.</li></ul>` },

  { id: 'trouble', title: 'Something is wrong', body: `
    <dl>
    <dt>Signed out after wrong passwords</dt><dd>5 wrong passwords, or too many tries from one shared address, lock sign-in for 10 minutes. Wait, then try again.</dd>
    <dt>The answer seems stuck</dt><dd>Press <b>Stop</b> and send again. Still stuck: reload the page, your chat is kept.</dd>
    <dt>You are back at the sign-in page</dt><dd>The 12 hours ended. Sign in again: nothing is lost.</dd>
    <dt>"System unavailable"</dt><dd>Check ${tab('Status')}. If a system is red, tell your admin.</dd>
    <dt>The chat got slow or forgets things</dt><dd>Run <code>/compact</code>, or start a new chat for a new topic.</dd>
    <dt>Too many "allow?" questions</dt><dd>Switch to <b>Auto</b>, or <b>Bypass</b> for no questions at all. A blocked storage change cannot be allowed in any mode: run that step yourself.</dd>
    <dt>Browser tab: "Nothing of yours on port..."</dt><dd>The app is not running yet. Start it and press reload.</dd>
    </dl>
    <p>Anything else: ask Claude in a chat, e.g. "how do I schedule a daily report?"</p>` },
];

const CSS = `
.ph .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.ph nav a:focus-visible,.ph nav input:focus-visible{outline:2px solid hsl(var(--ring,var(--foreground)));outline-offset:1px}
.ph{font:14px/1.6 Inter,ui-sans-serif,system-ui,sans-serif;color:hsl(var(--foreground));height:100%;display:grid;grid-template-columns:230px 1fr;min-height:0}
.ph nav{border-right:1px solid hsl(var(--border));padding:20px 12px;overflow:auto}
.ph nav input{width:100%;box-sizing:border-box;background:hsl(var(--background));border:1px solid hsl(var(--border));border-radius:10px;padding:7px 11px;color:inherit;font:inherit;margin-bottom:12px}
.ph nav a{display:block;padding:5px 10px;border-radius:8px;color:hsl(var(--muted-foreground));text-decoration:none;font-size:13.5px}
.ph nav a[hidden]{display:none}
.ph nav a:hover{background:hsl(var(--accent)/.6);color:hsl(var(--foreground))}.ph nav a.on{background:hsl(var(--accent));color:hsl(var(--foreground));font-weight:600}
.ph main{overflow:auto;padding:28px 32px 60px;min-height:0}.ph .in{max-width:820px}
.ph h1{font-size:24px;margin:0 0 4px}.ph .sub{color:hsl(var(--muted-foreground));margin:0 0 22px}
.ph section{border:1px solid hsl(var(--border));background:hsl(var(--card));border-radius:14px;padding:20px 22px;margin-bottom:16px;scroll-margin-top:12px}
.ph ul{list-style:disc}.ph ol{list-style:decimal}.ph ul ul{list-style:circle}
.ph h2{font-size:17px;margin:0 0 10px}.ph h3{font-size:14px;margin:14px 0 6px}.ph p{margin:0 0 10px}.ph ul,.ph ol{margin:0 0 10px;padding-left:20px}.ph li{margin:3px 0}
.ph code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;background:hsl(var(--muted));border-radius:6px;padding:1px 6px}
.ph kbd{font:600 11.5px ui-monospace,SFMono-Regular,Menlo,monospace;border:1px solid hsl(var(--border));border-bottom-width:2px;border-radius:6px;padding:0 6px;background:hsl(var(--background))}
.ph .tb{font-weight:600;border-radius:6px;padding:0 6px;background:linear-gradient(90deg,#a78bfa33,#22d3ee33)}
.ph .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:12px 0}
.ph .card{border:1px solid hsl(var(--border));border-radius:12px;padding:12px 14px;background:hsl(var(--background))}.ph .card h3{margin:0 0 4px}.ph .card p{margin:0;font-size:13px;color:hsl(var(--muted-foreground))}
.ph table{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0 12px}.ph td,.ph th{border:1px solid hsl(var(--border));padding:6px 9px;text-align:left;vertical-align:top}.ph th{background:hsl(var(--muted)/.6)}
.ph .note{border-left:3px solid #a78bfa;padding:6px 12px;background:hsl(var(--muted)/.4);border-radius:0 8px 8px 0}
.ph dt{font-weight:600;margin-top:10px}.ph dd{margin:2px 0 0;color:hsl(var(--muted-foreground))}.ph .ex li{font-style:italic}
.ph .none{color:hsl(var(--muted-foreground));padding:30px 0}
@media (max-width:760px){.ph{grid-template-columns:1fr;grid-template-rows:auto 1fr}.ph nav{border-right:0;border-bottom:1px solid hsl(var(--border));padding:10px;display:flex;gap:6px;overflow-x:auto;flex-wrap:nowrap}
.ph nav input{min-width:150px;margin:0}.ph nav a{white-space:nowrap;padding:10px 12px}.ph main{padding:16px 14px 40px}.ph section{padding:16px}}`;

export function mount(container) {
  container.innerHTML = `<style>${PAAS_CSS}</style><style>${CSS}</style><div class="paas ph"><nav><input type="search" placeholder="Search help…" aria-label="Search help"><div class="sr" role="status" aria-live="polite"></div>
    ${SECTIONS.map((s) => `<a href="#" data-s="${s.id}">${s.title}</a>`).join('')}</nav>
    <main><div class="in"><h1>How to use Peleg As A Service</h1><p class="sub">What every part does and how to get the most out of it.</p>
    ${SECTIONS.map((s) => `<section id="ph-${s.id}"><h2>${s.title}</h2>${s.body}</section>`).join('')}
    <div class="none" role="status" hidden>Nothing matches. Try another word, or just ask Claude in a chat.</div></div></main></div>`;
  const main = container.querySelector('main');
  const links = [...container.querySelectorAll('nav a')];
  const secs = [...container.querySelectorAll('section')];
  const none = container.querySelector('.none');
  const live = container.querySelector('nav .sr');
  const mark = (id) => links.forEach((a) => a.classList.toggle('on', a.dataset.s === id));

  links.forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault();
    container.querySelector(`#ph-${a.dataset.s}`)?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    mark(a.dataset.s);
  }));
  main.addEventListener('scroll', () => {           // the section at the top is the one marked in the menu
    const top = main.getBoundingClientRect().top + 40;
    const cur = secs.filter((s) => !s.hidden && s.getBoundingClientRect().top <= top).pop() || secs.find((s) => !s.hidden);
    if (cur) mark(cur.id.slice(3));
  });
  container.querySelector('nav input').addEventListener('input', (e) => {
    const words = e.target.value.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    secs.forEach((s, i) => {
      const hit = words.every((w) => s.textContent.toLowerCase().includes(w));
      s.hidden = !hit; links[i].hidden = !hit; shown += hit;
    });
    none.hidden = shown > 0;
    live.textContent = words.length ? `${shown} section${shown === 1 ? '' : 's'} match` : '';
    main.scrollTop = 0;
  });
  mark(SECTIONS[0].id);
}

export function unmount(container) { container.innerHTML = ''; }
