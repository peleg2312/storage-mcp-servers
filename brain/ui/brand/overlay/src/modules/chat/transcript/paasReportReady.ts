import { createElement as h, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';

import { authenticatedFetch } from '@/shared/api';
import { useMarkdownWorkspaceProjectId } from '@/modules/chat/context/MarkdownWorkspaceContext';
import { PAAS_DOWNLOADABLE, downloadChatFile } from '@/modules/chat/transcript/paasDownload';

/**
 * "Report ready" feedback: a card under a reply that names a file Claude made, a browser notification when the reply
 * finishes in a hidden tab, and a 'new' dot on the Reports tab until it is opened. Plain DOM + localStorage, no store.
 */
const NEW_KEY = 'paas-reports-new';     // { "<path>": count }
const NOTIFY_KEY = 'paas-notify';       // '1' on, '0' off (permission itself lives in the browser)
const NEW_EVENT = 'paas-reports-new';
const REPORTS_TAB = 'plugin:paas-reports';

const store = {
  get(key: string): string | null { try { return localStorage.getItem(key); } catch { return null; } },
  set(key: string, value: string): void { try { localStorage.setItem(key, value); } catch { /* storage may be blocked */ } },
};

const EXTENSIONS = PAAS_DOWNLOADABLE.source.match(/\((.*)\)/)?.[1] ?? 'xlsx|csv|pdf';
const FILE_RE = new RegExp(`[~/]?[\\w@%+.~/-]*[\\w@%+-]\\.(?:${EXTENSIONS})(?![\\w/])`, 'gi');
const MADE_RE = /\b(creat|wrote|written|writing|sav|export|generat|made|built|produc|ready|here'?s|attach)/i;
const READ_RE = /\b(read|reading|open(ed)?|look(ed)?|check(ed)?|found|exists?|existing|loaded|parsed|from)\b/i;

/** Files this reply hands over: under storage-reports, or a project file the sentence says was made (not just read). */
export function reportFiles(text: string): string[] {
  const plain = text.replace(/https?:\/\/\S+/g, ' ');
  const found = new Set<string>();
  for (const m of plain.matchAll(FILE_RE)) {
    const ref = m[0].replace(/^\.\//, '');
    const lineStart = plain.lastIndexOf('\n', m.index) + 1;
    const before = plain.slice(Math.max(lineStart, (m.index ?? 0) - 100), m.index);
    const inReports = /(^|\/)storage-reports\//.test(ref);
    const projectFile = !/^[~/]/.test(ref) && MADE_RE.test(before) && !READ_RE.test(before);
    if (inReports || projectFile) found.add(ref);
  }
  return [...found];
}

function bumpNew(paths: string[]): void {
  let counts: Record<string, number> = {};
  try { counts = JSON.parse(store.get(NEW_KEY) || '{}'); } catch { /* start fresh */ }
  for (const p of paths) counts[p] = (counts[p] || 0) + 1;
  store.set(NEW_KEY, JSON.stringify(counts));
  window.dispatchEvent(new Event(NEW_EVENT));
}

const subscribe = (cb: () => void) => {
  window.addEventListener(NEW_EVENT, cb);
  window.addEventListener('storage', cb);
  return () => { window.removeEventListener(NEW_EVENT, cb); window.removeEventListener('storage', cb); };
};

/** The 'new' dot inside a tab button; clears itself while the Reports tab is the open one. */
export function PaasNewDot(props: { tabId: string; active: boolean }) {
  const raw = useSyncExternalStore(subscribe, () => store.get(NEW_KEY) || '{}', () => '{}');
  const isReports = props.tabId === REPORTS_TAB;
  useEffect(() => {
    if (isReports && props.active && raw !== '{}') { store.set(NEW_KEY, '{}'); window.dispatchEvent(new Event(NEW_EVENT)); }
  }, [isReports, props.active, raw]);
  if (!isReports || props.active || raw === '{}') return null;
  return h('span', { className: 'paas-newdot', role: 'img', 'aria-label': 'New report' });
}

const canNotify = () => typeof Notification !== 'undefined' && Notification.permission === 'granted' && store.get(NOTIFY_KEY) !== '0';

function notify(files: string[]): void {
  if (!document.hidden || !canNotify()) return;
  try {
    const name = (files[0].split('/').pop() || files[0]);
    const n = new Notification(`Report ready: ${name}`, { body: files.length > 1 ? `and ${files.length - 1} more` : undefined, tag: 'paas-report' });
    n.onclick = () => { window.focus(); n.close(); };
  } catch { /* some mobile browsers only allow service-worker notifications */ }
}

/** Quick-settings row: ask for permission once, only when the person turns it on. */
export function PaasNotifySwitch() {
  const supported = typeof Notification !== 'undefined';
  const [on, setOn] = useState(canNotify());
  const [note, setNote] = useState('');
  if (!supported) return null;
  const toggle = async () => {
    setNote('');
    if (on) { store.set(NOTIFY_KEY, '0'); setOn(false); return; }
    let permission = Notification.permission;
    if (permission === 'default') permission = await Notification.requestPermission();
    if (permission === 'granted') { store.set(NOTIFY_KEY, '1'); setOn(true); }
    else setNote('Notifications are blocked. Allow them for this site in the browser settings.');
  };
  return h('div', { className: 'paas-notify' },
    h('button', { type: 'button', role: 'switch', 'aria-checked': on, className: 'paas-switch', onClick: () => { void toggle(); } },
      h('span', { className: 'paas-switch-label' }, 'Notify me when a report is ready'),
      h('span', { className: 'paas-switch-track', 'aria-hidden': 'true' }, h('span', { className: 'paas-switch-knob' }))),
    note ? h('p', { role: 'status', className: 'paas-dl-note' }, note) : null);
}

const formatSize = (n: number) => (n < 1024 ? `${n} B` : n < 1048576 ? `${Math.round(n / 1024)} KB` : `${(n / 1048576).toFixed(1)} MB`);

const icon = () => h('svg', { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': 'true' },
  h('path', { d: 'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z' }), h('path', { d: 'M14 3v5h5' }), h('path', { d: 'M9 14l2 2 4-4' }));

function openReports(): boolean {
  const tab = document.querySelector<HTMLButtonElement>('[role="tab"][aria-label="Reports"]');
  tab?.click();
  return Boolean(tab);
}

/** Under an assistant reply: the card once the reply is complete, plus the notification and the new-dot bump. */
export function PaasReportReady(props: { content: string; isStreaming: boolean }) {
  const projectId = useMarkdownWorkspaceProjectId();
  const files = useMemo(() => (props.isStreaming ? [] : reportFiles(props.content)), [props.content, props.isStreaming]);
  const wasStreaming = useRef(props.isStreaming);
  const [sizes, setSizes] = useState<Record<string, number>>({});
  const [note, setNote] = useState('');

  useEffect(() => {
    // only a reply seen finishing counts; history loaded from disk never notifies
    if (wasStreaming.current && !props.isStreaming && files.length) { bumpNew(files); notify(files); }
    wasStreaming.current = props.isStreaming;
  }, [props.isStreaming, files]);

  useEffect(() => {
    let alive = true;
    for (const f of files) {
      if (!/^(\/|~)/.test(f)) continue;   // project-relative files go through the project route: no size
      authenticatedFetch(`/api/paas/download?path=${encodeURIComponent(f)}`, { method: 'HEAD' })
        .then((r) => { const n = Number(r.headers.get('content-length')); if (alive && r.ok && n) setSizes((s) => ({ ...s, [f]: n })); })
        .catch(() => { /* size is optional */ });
    }
    return () => { alive = false; };
  }, [files]);

  if (!files.length) return null;
  return h('div', { className: 'paas-rr', role: 'group', 'aria-label': 'Report ready' },
    files.map((f) => {
      const name = f.split('/').pop() || f;
      return h('div', { key: f, className: 'paas-rr-row' },
        h('span', { className: 'paas-rr-icon' }, icon()),
        h('span', { className: 'paas-rr-text' },
          h('span', { className: 'paas-rr-title' }, 'Report ready'),
          h('span', { className: 'paas-rr-name', title: f }, name, sizes[f] ? ` · ${formatSize(sizes[f])}` : '')),
        h('span', { className: 'paas-rr-actions' },
          h('button', { type: 'button', className: 'paas-rr-btn primary', 'aria-label': `Download ${name}`,
            onClick: (e: { currentTarget: HTMLButtonElement }) => { void downloadChatFile(f, projectId, e.currentTarget); } }, '↓ Download'),
          h('button', { type: 'button', className: 'paas-rr-btn',
            onClick: () => { setNote(openReports() ? '' : 'The Reports tab is not available here.'); } }, 'Open in Reports')));
    }),
    note ? h('p', { role: 'status', className: 'paas-dl-note' }, note) : null);
}
