// Help tab: how to use this UI - chats, commands, modes, every tab, the terminal, the safety rules, common fixes.
// Plain content, searchable; nothing is sent anywhere.
const k = (s) => `<kbd>${s}</kbd>`;
const tab = (s) => `<span class="tb">${s}</span>`;

const SECTIONS = [
  { id: 'start', title: 'Start here', body: `
    <p>This is Claude, your assistant for storage and development work. Ask in plain words, it looks things up,
    checks your systems when you ask it to, and writes reports, scripts and code for you.</p>
    <div class="grid">
      <div class="card"><h4>Knows your environment</h4><p>Reads PowerMax, ONTAP, PowerFlex, MDS, UCS and VMware, and searches the vendor docs and KBs.</p></div>
      <div class="card"><h4>Never changes storage</h4><p>It only reads your systems. When something needs changing, it gives you the exact steps to run.</p></div>
      <div class="card"><h4>Yours</h4><p>Your chats, files, reports and notes are your own. Nobody else sees them.</p></div>
    </div>
    <h4>Try this first</h4>
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
    <h4>Sending more while it is still answering</h4>
    <ul><li>Just send: your message waits in a <b>queue</b> above the box and goes out by itself when the answer ends.</li>
    <li><b>Edit</b> or <b>Delete</b> a queued message if you change your mind.</li>
    <li>Urgent? <b>Send now</b> stops the current answer and sends yours straight away.</li></ul>` },

  { id: 'asking', title: 'Getting good answers', body: `
    <ul><li><b>Name what you mean</b>: the array, SVM, volume, LUN ID / NAA / WWN, host or fabric. "Why is LUN 6000097... slow on esx12?" beats "a LUN is slow".</li>
    <li><b>Say whether to check live.</b> "What does this error mean?" is answered from the docs. "Check which volumes are over 90%" makes Claude look at the systems.</li>
    <li>Answers start with the short answer, then the evidence, the findings and the <b>sources</b>. If something could not be checked, it says so: it does not guess.</li>
    <li>Long lists or trends: ask for "a chart", "Excel" or "CSV".</li>
    <li>Need a change made? Claude writes the steps <b>for you to run</b>, with checks before and after and how to undo it.</li>
    <li>Tell it a fact once ("our prod SVMs start with svm_p") and it remembers it for next time.</li></ul>
    <h4>Ideas</h4>
    <ul class="ex"><li>Which hosts have a single path to array 1234?</li><li>Trace this OpenShift PVC to its LUN, array and switch ports.</li>
    <li>What does EMS event wafl.vol.autoSize.fail mean and what do I do?</li><li>IOPS and latency per volume for this PowerFlex host.</li>
    <li>Is this LUN still used anywhere?</li><li>Build a FastAPI endpoint that lists storage groups, with tests.</li><li>Show me my app in the Browser tab.</li></ul>` },

  { id: 'commands', title: '/ commands', body: `
    <p>Type ${k('/')} in the message box (or press <b>/</b>). Keep typing to filter, ${k('↑')} ${k('↓')} and ${k('Enter')} to pick.</p>
    <h4>Ready-made routines</h4>
    <ul><li><code>/morning-check</code> the daily health round · <code>/capacity-report</code> capacity across arrays</li>
    <li><code>/trace-path</code> a host to its storage, end to end · <code>/identify-lun</code> what a NAA / WWN is and where it lives</li>
    <li><code>/zoning-audit</code>, <code>/fabric-health</code> the SAN fabrics · <code>/replication-check</code> SRDF / SnapMirror</li>
    <li><code>/explain-error</code> an error or alert, from the docs · <code>/change-review</code> a change plan checked before you run it</li>
    <li><code>/decommission-check</code> before anything is removed · <code>/report-export</code> Excel, CSV, charts</li></ul>
    <p>You rarely have to type them: Claude picks the right one from your question.</p>
    <h4>Handy commands</h4>
    <ul><li><code>/compact</code> a long chat: Claude summarises it and carries on, quicker and cheaper.</li>
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
    <h4>Set up Git once</h4>
    <p>Before your first commit, tell Git who you are: <b>Settings → Git</b>, fill in your name and your GitLab e-mail, <b>Save</b>.
    (Or in ${tab('Shell')}: <code>git config --global user.name "Your Name"</code> and <code>git config --global user.email you@company.com</code>.)</p>
    <h4>Create a project</h4>
    <ol><li>Press the <b>folder</b> button at the top of the left menu.</li>
    <li><b>Existing workspace</b>: a folder you already have, e.g. <code>~/projects/storage-api</code>.
      <b>New workspace</b>: a new folder, empty or <b>cloned from a Git URL</b> (your GitLab repository).</li>
    <li>The repository needs a login? Clone it in a terminal first (<code>git clone https://gitlab.../group/repo.git</code>, it asks for your user and token), then add the folder as an existing workspace.</li></ol>
    <h4>${tab('Files')}</h4>
    <ul><li>The folder as a tree: search, open a file to read or edit it, save.</li>
    <li>Right-click (long-press on a phone): new file or folder, rename, delete, copy path, <b>Upload files</b>, <b>Download</b>.</li>
    <li>Simple, compact or detailed view (sizes, dates, permissions).</li></ul>
    <h4>${tab('Shell')}</h4>
    <p>A terminal in the project folder, as you: run tests, start your app (then see it in ${tab('Browser')}), use git or any tool.</p>
    <h4>${tab('Source control')}</h4>
    <ul><li><b>Changes</b>: every changed file with its diff; tick the files, write a message, <b>Commit</b>.</li>
    <li><b>Commits</b>: the history. <b>Compare</b>: two branches side by side. <b>Branches</b>: switch, create, delete.</li>
    <li><b>Fetch</b>, <b>Pull</b> and <b>Push</b> at the top, with how many commits are waiting each way.</li>
    <li>Not a Git folder yet? <b>Run git init</b> starts one.</li></ul>
    <p class="note">Or just ask in the project's chat: "commit this with a good message", "create a branch for the new endpoint", "what changed since yesterday?". Claude shows the diff and asks before it commits or pushes.</p>` },

  { id: 'modes', title: 'How much Claude may do on its own', body: `
    <p>Next to the send button: the <b>model</b> and the <b>approval mode</b>. ${k('Tab')} in the message box switches mode.</p>
    <table><tr><th>Mode</th><th>Claude does on its own</th><th>Good for</th></tr>
    <tr><td><b>Default</b></td><td>Reading and looking things up; asks before anything else</td><td>Everyday use</td></tr>
    <tr><td><b>Auto</b></td><td>Each step is checked and allowed or refused for you</td><td>Long investigations without clicking "allow"</td></tr>
    <tr><td><b>Accept edits</b></td><td>Edits and commands inside your project</td><td>Coding</td></tr>
    <tr><td><b>Plan</b></td><td>Nothing: it only plans</td><td>Thinking a change through first</td></tr>
    <tr><td><b>Bypass</b></td><td>Everything</td><td>Best avoided</td></tr></table>
    <p class="note">Whatever the mode, changes to storage, switches, UCS and VMware stay blocked. When Claude asks to run something, read it, then <b>Allow</b> or <b>Deny</b> (and say why).</p>` },

  { id: 'reports', title: 'Reports', body: `
    <p>${tab('Reports')} holds everything Claude saved for you: Excel, CSV, charts, write-ups. Newest first.</p>
    <ul><li>Click a file to preview it, <b>Download</b> to keep it. Filter by name at the top.</li>
    <li>Ask for one in any chat: "export this as Excel", "chart the latency for the last week".</li></ul>` },

  { id: 'browser', title: 'Browser', body: `
    <p>${tab('Browser')} shows web pages from your own work inside this page:</p>
    <ul><li>An app you are building: type its port and path, e.g. <code>8000/docs</code>.</li>
    <li>Your files and reports: <code>~/storage-reports/</code>, an HTML report with its charts.</li>
    <li>Buttons at the top list the apps you have running. ↗ opens the page in its own browser tab.</li>
    <li>Or ask: "show it to me in the Browser tab".</li></ul>
    <p class="note">It shows your own apps and files only, not internet sites or other people's apps.</p>` },

  { id: 'brain', title: 'Brain', body: `
    <p>${tab('Brain')} is what Claude knows and can use:</p>
    <ul><li><b>Search</b> the vendor docs and KBs yourself.</li>
    <li><b>Add documents</b>: upload PDFs or pages, or paste links to your wiki. Claude can search them a few seconds later.</li>
    <li><b>Skills and agents</b>: read, adjust or create your own routines. <b>Share with everyone</b> offers one to your colleagues.</li>
    <li><b>Systems</b> Claude can query, with <b>Check connections</b>, and your <b>memory</b> (the facts it remembers for you).</li></ul>` },

  { id: 'schedule', title: 'Schedule', body: `
    <p>${tab('Schedule')} runs a question or routine for you, <b>daily</b>, on <b>weekdays</b> or <b>weekly</b>.</p>
    <ul><li>Example: every weekday at 07:30, "check capacity on all arrays and list volumes over 85%".</li>
    <li>Each run lands in ${tab('Reports')} and as a chat you can open and continue.</li>
    <li><b>Run now</b> tries it straight away. <b>Edit</b> or <b>Delete</b> it any time.</li></ul>` },

  { id: 'status', title: 'Status', body: `
    <p>${tab('Status')} shows what Claude can reach right now (each storage system and the docs) and what your chats have used (per day, project and chat).</p>
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
    <li>Kubernetes / OpenShift changes and service restarts: it asks you first.</li>
    <li>Your own code and apps: it builds, runs and tests them with you.</li>
    <li>Nothing is called "safe to delete" until <code>/decommission-check</code> passed every check.</li>
    <li>Passwords and tokens never go into notes, reports or shared items.</li></ul>` },

  { id: 'trouble', title: 'Something is wrong', body: `
    <dl>
    <dt>The answer seems stuck</dt><dd>Press <b>Stop</b> and send again. Still stuck: reload the page, your chat is kept.</dd>
    <dt>You are back at the sign-in page</dt><dd>The 12 hours ended. Sign in again: nothing is lost.</dd>
    <dt>"System unavailable"</dt><dd>Check ${tab('Status')}. If a system is red, tell your admin.</dd>
    <dt>The chat got slow or forgets things</dt><dd>Run <code>/compact</code>, or start a new chat for a new topic.</dd>
    <dt>Too many "allow?" questions</dt><dd>Switch to <b>Auto</b> mode. A blocked storage change cannot be allowed: run that step yourself.</dd>
    <dt>Browser tab: "Nothing of yours on port..."</dt><dd>The app is not running yet. Start it and press reload.</dd>
    </dl>
    <p>Anything else: ask Claude in a chat, e.g. "how do I schedule a daily report?"</p>` },
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
    <main><div class="in"><h1>How to use Peleg As A Service</h1><p class="sub">What every part does and how to get the most out of it.</p>
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
