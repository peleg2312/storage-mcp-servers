// Help tab: how to use this UI - chats, commands, modes, every tab, the terminal, the safety rules, common fixes.
// Plain content, searchable; nothing is sent anywhere.
const k = (s) => `<kbd>${s}</kbd>`;
const tab = (s) => `<span class="tb">${s}</span>`;

const SECTIONS = [
  { id: 'start', title: 'Start here', body: `
    <p><b>Peleg As A Service</b> is Claude Code, running on this VM, in your browser. It is the same Claude as the
    <code>claude</code> command in a terminal on the VM: same skills, same docs library, same MCP servers, same memory.</p>
    <div class="grid">
      <div class="card"><h4>Runs as you</h4><p>Everything Claude does (files, commands, apps) runs as your own Linux account on the VM. Your chats, files and settings are yours.</p></div>
      <div class="card"><h4>Offline</h4><p>The VM has no internet. Vendor knowledge comes from the offline docs library (NetApp, Dell, Cisco, Python...).</p></div>
      <div class="card"><h4>Read-only to storage</h4><p>Claude reads PowerMax, ONTAP, PowerFlex, MDS, UCS and VMware but never changes them. It gives you the commands to run yourself.</p></div>
    </div>
    <h4>Your first five minutes</h4>
    <ol><li>Press <b>New chat</b> in the left menu (${k('☰')} on a phone) and ask a question.</li>
    <li>Type ${k('/')} in the message box to see every command.</li>
    <li>Open ${tab('Status')} to check the MCP servers are connected.</li>
    <li>Open ${tab('Brain')} to search the docs library.</li>
    <li>Ask for a report ("export the LUN list as Excel") and find it in ${tab('Reports')}.</li></ol>` },

  { id: 'signin', title: 'Signing in and out', body: `
    <ul><li>Sign in with your <b>VM account</b> (Linux user name and password). The UI keeps no passwords of its own.
      New accounts and password resets: ask root (${tab('Users')} tab, or <code>paas-user</code> on the VM).</li>
    <li>A sign-in lasts <b>12 hours</b> from when you signed in, then you are asked again. A reply still running keeps going on the VM: sign in again and it is in the chat.</li>
    <li><b>5 wrong passwords</b> in 10 minutes block sign-in for a few minutes.</li>
    <li><b>Sign out</b>: left menu, bottom, next to your name. It signs out this browser only.</li>
    <li>You can be signed in from several browsers at once. They all see the same chats and files.</li></ul>` },

  { id: 'chats', title: 'Chats and projects', body: `
    <h4>The left menu</h4>
    <ul><li><b>New chat</b>: a plain chat. It runs in your <code>~/chats</code> folder (the <b>Chats</b> space).</li>
    <li><b>Conversations / Projects / Running sessions</b>: switch how the list is grouped. Running sessions are chats replying right now.</li>
    <li><b>Create new project</b> (the folder button): work in a folder of your code. Pick a folder on the VM, or give a GitLab URL to clone.</li>
    <li>Each chat's <b>⋯</b> menu: rename, archive or delete it. ${k('Ctrl')}+${k('R')} refreshes the list.</li></ul>
    <h4>Inside a project</h4>
    <p>Besides ${tab('Chat')}, a project has ${tab('Shell')} (a terminal in that folder, as you), ${tab('Files')} (browse and edit its files)
    and ${tab('Source control')} (git status, diffs, commits). The Chats space has only the chat.</p>
    <h4>Same chats in the terminal</h4>
    <p>Every chat started here also shows in <code>claude --resume</code> on the VM (as your account), and you can continue it there, and the other way round.</p>` },

  { id: 'chatting', title: 'Writing to Claude', body: `
    <ul><li>${k('Enter')} sends, ${k('Shift')}+${k('Enter')} is a new line. Prefer ${k('Ctrl')}+${k('Enter')} to send? Turn it on in quick settings.</li>
    <li><b>📎</b> attaches files (up to 50 MB). Type ${k('@')} to point Claude at a file of the project.</li>
    <li>The reply appears <b>as it is written</b>. Tool calls (commands, searches, MCP calls) show as boxes: click one to see what ran and what came back.</li>
    <li><b>Thinking</b> is collapsed: click "Thinking" to read it. Hide it completely with <i>Show thinking</i> in quick settings.</li>
    <li><b>Stop</b> (the square button while it replies) ends the reply. "No response requested" after a stop is normal.</li>
    <li>The chat follows the reply to the bottom. Scroll up to read and it stays put; scroll back down to follow again.</li>
    <li>A file Claude made or named gets a <b>↓ Download</b> button next to it: it lands on your PC.</li></ul>
    <h4>While Claude is still replying</h4>
    <ul><li>Send another message: it waits in a <b>queue</b> above the box and goes out by itself when the reply ends.</li>
    <li>Change your mind: <b>Edit</b> or <b>Delete</b> the queued message.</li>
    <li>It cannot wait? <b>Send now</b> stops the running reply and sends it at once.</li></ul>` },

  { id: 'commands', title: '/ commands', body: `
    <p>Type ${k('/')} in the message box (or press the <b>/</b> button) for the menu. Keep typing to filter, ${k('↑')} ${k('↓')} and ${k('Enter')} to pick.</p>
    <ul><li><b>Built-in</b>: the UI's own commands (help, clear, model...).</li>
    <li><b>Claude Code</b> (violet): the same commands as in the terminal. The useful ones:
      <ul><li><code>/compact</code> a long chat: Claude summarises it and keeps going, faster and cheaper.</li>
      <li><code>/context</code> how full the chat's memory is.</li>
      <li><code>/cost</code> what this chat has used.</li>
      <li><code>/review</code>, <code>/security-review</code> look over code changes in a project.</li></ul></li>
    <li><b>Skills</b>: the brain's own recipes. You rarely need to type them, Claude picks the right one from your question, but they are handy to start a routine:
      <ul><li><code>/morning-check</code> the daily health round; <code>/capacity-report</code> capacity across arrays</li>
      <li><code>/trace-path</code> a host to its LUN end to end; <code>/identify-lun</code> what a NAA / WWN is</li>
      <li><code>/zoning-audit</code>, <code>/fabric-health</code> the MDS fabrics; <code>/replication-check</code> SRDF / SnapMirror</li>
      <li><code>/explain-error</code> an error or alert from the docs; <code>/change-review</code> a change plan checked before you run it</li>
      <li><code>/decommission-check</code> before anything is removed; <code>/report-export</code> Excel / CSV / charts</li></ul></li></ul>` },

  { id: 'modes', title: 'Model and approval mode', body: `
    <p>Under the message box: the <b>model</b> menu (and how hard it thinks) and the <b>approval mode</b>. ${k('Tab')} in the message box switches mode.</p>
    <table><tr><th>Mode</th><th>What Claude may do without asking</th><th>Use it for</th></tr>
    <tr><td><b>Default</b></td><td>Safe reading commands; asks before anything else</td><td>Everyday work (recommended)</td></tr>
    <tr><td><b>Auto</b></td><td>A checker approves or refuses each step</td><td>Long investigations without clicking "allow"</td></tr>
    <tr><td><b>Accept edits</b></td><td>Edits and commands inside the project folder</td><td>Coding in your own project</td></tr>
    <tr><td><b>Plan</b></td><td>Nothing: it only plans</td><td>Thinking a change through first</td></tr>
    <tr><td><b>Bypass</b></td><td>Everything</td><td>Avoid</td></tr></table>
    <p class="note">In every mode the <b>read-only guard</b> still blocks anything that would change storage, switches, UCS or VMware.
    When it asks you to allow something, read the command first: <b>Allow</b> once, or <b>Deny</b> and tell it why.</p>` },

  { id: 'asking', title: 'Getting good answers', body: `
    <ul><li><b>Name the object</b>: the array, SVM, volume, NAA / WWN, host, fabric. "Why is LUN 60000970... slow on host esx12?" beats "LUN slow".</li>
    <li><b>Say if you want a live check.</b> "What does this error mean" gets an answer from the docs. "Check which volumes are over 90%" makes Claude query the systems.</li>
    <li>Answers come as: the answer first, an evidence table, findings, then <b>sources</b> (which tool or document said it). Nothing is invented: if a source was not checked, it says so.</li>
    <li>Big lists and trends: ask for "a chart", "Excel" or "CSV". They go to ${tab('Reports')}.</li>
    <li>Changes to storage: Claude writes the steps <b>for you to run</b>, with checks before and after and a way back.</li>
    <li>Tell it facts once ("our prod SVMs start with svm_p"): it keeps them in your notes for next time.</li></ul>
    <h4>Examples</h4>
    <ul class="ex"><li>Which hosts have a single path to array 1234?</li><li>Map this OpenShift PVC to its LUN, array and switch ports.</li>
    <li>Explain EMS event wafl.vol.autoSize.fail and what to do.</li><li>Per-volume IOPS and latency for SDC 4a3b...</li>
    <li>Build a FastAPI endpoint that lists PowerMax storage groups, with tests.</li><li>Show me the API docs in the Browser tab.</li></ul>` },

  { id: 'brain', title: 'Brain tab', body: `
    <p>${tab('Brain')} is everything Claude knows and can use:</p>
    <ul><li><b>Search</b> the offline docs library the way Claude does, and open the documents.</li>
    <li><b>Add documents</b>: upload PDFs, HTML or text, or give URLs the VM can reach (intranet wiki). They are searchable in seconds and survive library updates.</li>
    <li><b>Skills and agents</b>: read, edit or create your own. <b>Share with everyone</b> puts one in the Marketplace.</li>
    <li><b>MCP servers</b>: the systems Claude can query (powermax, ontap, powerflex, harvest, mds, ucsc, Aria, kuparashit, docs). <b>Check connections</b> tests them.</li>
    <li><b>Hooks</b> (the read-only guard and the docs helpers) and <b>memory</b> (your notes).</li></ul>` },

  { id: 'browser', title: 'Browser tab', body: `
    <p>${tab('Browser')} shows web pages that run <b>on this VM under your account</b>, inside the UI:</p>
    <ul><li>Your apps by port: <code>8000/docs</code> (a FastAPI service), <code>5173</code> (a Vite / React dev server), a dashboard you started.</li>
    <li>Files under your home folder: <code>~/storage-reports/</code>, an HTML report with its charts.</li>
    <li>The buttons above the page list the apps you have running. ↗ opens the page in its own browser tab.</li>
    <li>Ask Claude "show it in the Browser tab": it runs <code>paas-open</code> and the tab switches to the page.</li></ul>
    <p class="note">Not shown: internet sites (the VM is offline), other people's apps, system services, hidden files (<code>~/.ssh</code>).
    FastAPI's <code>/docs</code> page needs internet for its look, so it can appear blank: the API itself works.</p>` },

  { id: 'reports', title: 'Reports tab', body: `
    <p>${tab('Reports')} lists what Claude saved in <code>~/storage-reports</code>, newest first: Excel, CSV, HTML charts, Markdown, PDFs.</p>
    <ul><li>Click a file to preview it (tables, charts, text). <b>Download</b> saves it to your PC.</li>
    <li>Filter by name at the top. <b>Refresh</b> after Claude saves something new.</li></ul>` },

  { id: 'schedule', title: 'Schedule tab', body: `
    <p>${tab('Schedule')} runs a prompt or skill by itself: <b>daily</b>, on <b>weekdays</b> or <b>weekly</b>, at a time of the <b>VM clock</b>.</p>
    <ul><li>Example: every weekday 07:30, "check capacity on all arrays, list volumes over 85%".</li>
    <li>Each run is saved as a report (${tab('Reports')}) and as a chat you can open and continue.</li>
    <li><b>Run now</b> tests it at once. <b>Edit</b>, <b>Delete</b>, and the status (Running / Failed) per job.</li>
    <li>Runs use the same read-only rules as your chats.</li></ul>` },

  { id: 'status', title: 'Status tab', body: `
    <p>${tab('Status')} is the health check and the bill:</p>
    <ul><li><b>Health</b>: each MCP server (connected or not), the docs library, the read-only guard, disk and memory of the VM.</li>
    <li><b>Usage</b>: tokens and estimated cost per day, per project, per model, and the most expensive chats.</li></ul>
    <p>Claude says a system is "unavailable"? Look here first.</p>` },

  { id: 'market', title: 'Marketplace tab', body: `
    <p>${tab('Marketplace')} is what people on this VM share: skills, agents and MCP servers.</p>
    <ul><li><b>Add</b> one to your own Claude, <b>Update</b> (or <b>Update all</b>) when a newer version is shared, <b>Remove</b> it again.</li>
    <li><b>Create and share</b> your own; <b>Unshare</b> takes it back. Shared things are read by everyone, so no passwords in them.</li>
    <li>Some MCP servers need <b>Set up</b> first (an address or the token everyone uses).</li>
    <li>In a terminal: <code>paas-market</code> does the same.</li></ul>` },

  { id: 'users', title: 'Users tab (root)', body: `
    <p>Only root sees ${tab('Users')}: add people to this VM, reset passwords, lock or remove accounts.</p>
    <ul><li>Each person gets their own Linux account, home, chats and UI. Locked = cannot sign in (their UI stops).</li>
    <li>Remove keeps the home folder unless you ask to delete it.</li>
    <li>The same on the VM: <code>paas-user add | passwd | lock | unlock | remove | list</code>.</li></ul>` },

  { id: 'settings', title: 'Settings', body: `
    <ul><li><b>Quick settings</b> (the ‹ handle on the right edge): dark mode, language, show raw tool parameters, show thinking, send with ${k('Ctrl')}+${k('Enter')}.
      Its <b>Commands</b> tab lists the / commands too.</li>
    <li><b>Settings</b> (left menu, bottom): appearance, models and your account.</li></ul>` },

  { id: 'terminal', title: 'On the VM terminal', body: `
    <ul><li><code>claude</code> starts the same brain in a terminal (with the Peleg As A Service banner). <code>claude --resume</code> lists your chats, UI ones included.</li>
    <li><code>paas-open 8000/docs</code> or <code>paas-open ~/storage-reports/x.html</code> shows a page in the Browser tab.</li>
    <li><code>add-docs</code> adds the files in <code>~/.claude/brain/inbox/</code> to the docs library.</li>
    <li><code>paas-market</code> manages marketplace items; root: <code>paas-user</code> manages people.</li></ul>` },

  { id: 'safety', title: 'Safety and limits', body: `
    <ul><li><b>Storage, switches, UCS, VMware: read-only, always.</b> A guard blocks any tool or command that would change them, in every mode. Claude gives you the change steps to run yourself.</li>
    <li><code>oc</code>, <code>kubectl</code>, <code>helm</code>, <code>curl</code>, <code>systemctl</code> changes: Claude asks you first.</li>
    <li>Your own code, apps and services on the VM: normal work, Claude may build and run them.</li>
    <li>Nothing leaves the VM except what goes to Claude's model service. No passwords or tokens go into notes, reports or the marketplace.</li>
    <li>Nothing is "safe to delete" until the <code>/decommission-check</code> passed every check.</li></ul>` },

  { id: 'trouble', title: 'Something is wrong', body: `
    <dl>
    <dt>The reply seems stuck</dt><dd>Press <b>Stop</b>, then send again. Still stuck: reload the page (your chat is kept).</dd>
    <dt>"Signed out" or a sign-in page</dt><dd>The 12 hours ended, or you signed out. Sign in again: nothing is lost.</dd>
    <dt>A system is unavailable</dt><dd>${tab('Status')} → MCP servers. A red one is down or unreachable: tell the VM admin.</dd>
    <dt>The chat got slow or forgets things</dt><dd>Run <code>/compact</code>, or start a new chat for a new topic.</dd>
    <dt>Claude keeps asking to allow things</dt><dd>Use <b>Auto</b> mode for long investigations. A denial from the read-only guard cannot be allowed: run that step yourself.</dd>
    <dt>A UI chat is missing in <code>claude --resume</code></dt><dd>Older chats are fixed when root installs an update (or runs <code>paas-user provision --all</code>). A chat open at that moment is fixed the next time.</dd>
    <dt>Browser tab: "Nothing of yours on port..."</dt><dd>Your app is not running (or runs as another account). Start it, then reload.</dd>
    <dt>No / commands from Claude Code in the menu</dt><dd>Open a chat first (the list is read for the chat's folder), then type / again.</dd>
    </dl>` },
];

const CSS = `
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
.ph h2{font-size:17px;margin:0 0 10px}.ph h4{font-size:14px;margin:14px 0 6px}.ph p{margin:0 0 10px}.ph ul,.ph ol{margin:0 0 10px;padding-left:20px}.ph li{margin:3px 0}
.ph code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;background:hsl(var(--muted));border-radius:6px;padding:1px 6px}
.ph kbd{font:600 11.5px ui-monospace,SFMono-Regular,Menlo,monospace;border:1px solid hsl(var(--border));border-bottom-width:2px;border-radius:6px;padding:0 6px;background:hsl(var(--background))}
.ph .tb{font-weight:600;border-radius:6px;padding:0 6px;background:linear-gradient(90deg,#a78bfa33,#22d3ee33)}
.ph .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:12px 0}
.ph .card{border:1px solid hsl(var(--border));border-radius:12px;padding:12px 14px;background:hsl(var(--background))}.ph .card h4{margin:0 0 4px}.ph .card p{margin:0;font-size:13px;color:hsl(var(--muted-foreground))}
.ph table{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0 12px}.ph td,.ph th{border:1px solid hsl(var(--border));padding:6px 9px;text-align:left;vertical-align:top}.ph th{background:hsl(var(--muted)/.6)}
.ph .note{border-left:3px solid #a78bfa;padding:6px 12px;background:hsl(var(--muted)/.4);border-radius:0 8px 8px 0}
.ph dt{font-weight:600;margin-top:10px}.ph dd{margin:2px 0 0;color:hsl(var(--muted-foreground))}.ph .ex li{font-style:italic}
.ph .none{color:hsl(var(--muted-foreground));padding:30px 0}
@media (max-width:760px){.ph{grid-template-columns:1fr;grid-template-rows:auto 1fr}.ph nav{border-right:0;border-bottom:1px solid hsl(var(--border));padding:10px;display:flex;gap:6px;overflow-x:auto;flex-wrap:nowrap}
.ph nav input{min-width:150px;margin:0}.ph nav a{white-space:nowrap}.ph main{padding:16px 14px 40px}.ph section{padding:16px}}`;

export function mount(container) {
  container.innerHTML = `<style>${CSS}</style><div class="ph"><nav><input type="search" placeholder="Search help…" aria-label="Search help">
    ${SECTIONS.map((s) => `<a href="#" data-s="${s.id}">${s.title}</a>`).join('')}</nav>
    <main><div class="in"><h1>How to use Peleg As A Service</h1><p class="sub">Everything in this UI, what it is for and how to use it.</p>
    ${SECTIONS.map((s) => `<section id="ph-${s.id}"><h2>${s.title}</h2>${s.body}</section>`).join('')}
    <div class="none" hidden>Nothing matches. Try another word, or just ask Claude in a chat.</div></div></main></div>`;
  const main = container.querySelector('main');
  const links = [...container.querySelectorAll('nav a')];
  const secs = [...container.querySelectorAll('section')];
  const none = container.querySelector('.none');
  const mark = (id) => links.forEach((a) => a.classList.toggle('on', a.dataset.s === id));

  links.forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault();
    container.querySelector(`#ph-${a.dataset.s}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    main.scrollTop = 0;
  });
  mark(SECTIONS[0].id);
}

export function unmount(container) { container.innerHTML = ''; }
