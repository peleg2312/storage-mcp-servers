#!/usr/bin/env node
// Chrome DevTools for Claude on this server, driving the Chrome of the person in the chat on their own Windows PC.
// Each PC runs one PowerShell line (`paas-chrome windows` prints it): Chrome with its own empty profile and a debugging
// port, plus an SSH tunnel that brings that port to this server on 127.0.0.1:93xx and registers it in ~/.paas-chrome
// as "<PC> <Windows user>". Several people may use the same Linux account from different PCs, so each chat picks its
// PC: one PC connected = that one; more = Claude asks and calls use_browser. Pages: only this server's own (its names
// and addresses, localhost, plus /etc/paas/chrome-allowed-hosts and ~/.paas-chrome/allowed-hosts), never the storage,
// switch or vCenter web pages.
//   paas-chrome.mjs [mcp]          the MCP server (wraps chrome-devtools-mcp)
//   paas-chrome.mjs windows        the PowerShell line for a Windows PC
//   paas-chrome.mjs list           the PCs connected right now
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SERVER = path.join(HERE, 'server', 'build', 'src', 'bin', 'chrome-devtools-mcp.js');
const DIR = path.join(os.homedir(), '.paas-chrome');
const FIRST_PORT = 9300;
const SERVER_ARGS = ['--no-usage-statistics', '--no-performance-crux', '--redactNetworkHeaders'];
const OUR_TOOLS = [
  { name: 'list_my_browsers', description: 'The Chrome browsers connected to this server right now: one per PC (PC name, Windows user, port), and which one this chat uses. Call it when a Chrome tool says it does not know which PC to use.', inputSchema: { type: 'object', properties: {} } },
  { name: 'use_browser', description: 'Use the Chrome of this PC for the rest of this chat. Ask the person which PC they are on when more than one is connected.', inputSchema: { type: 'object', properties: { pc: { type: 'string', description: 'PC name or port from list_my_browsers' } }, required: ['pc'] } },
];

// ---- connected PCs ------------------------------------------------------------------------------------------------
function alive(port) {
  return new Promise((resolve) => {
    const req = http.get({ host: '127.0.0.1', port, path: '/json/version', timeout: 1500 }, (res) => {
      let body = '';
      res.on('data', (d) => { body += d; });
      res.on('end', () => { try { resolve(JSON.parse(body).Browser || 'Chrome'); } catch { resolve(null); } });
    });
    req.on('error', () => resolve(null));
    req.on('timeout', () => { req.destroy(); resolve(null); });
  });
}

async function browsers() {
  let names = [];
  try { names = fs.readdirSync(DIR).filter((n) => /^\d{4,5}$/.test(n)); } catch { /* none yet */ }
  const out = [];
  for (const n of names) {
    const port = Number(n);
    const [pc = '?', user = ''] = (fs.readFileSync(path.join(DIR, n), 'utf8').trim().split(/\s+/));
    const version = await alive(port);
    if (version) out.push({ port, pc, user, version });
  }
  return out.sort((a, b) => a.port - b.port);
}

// ---- which pages Chrome may open ------------------------------------------------------------------------------------
function allowedHosts() {
  const hosts = new Set(['localhost', '127.0.0.1', '::1', '[::1]', os.hostname().toLowerCase(), os.hostname().split('.')[0].toLowerCase()]);
  try { for (const n of execFileSync('hostname', ['-A'], { encoding: 'utf8' }).split(/\s+/)) if (n) hosts.add(n.toLowerCase()); } catch { /* not on every system */ }
  for (const list of Object.values(os.networkInterfaces())) for (const a of list || []) hosts.add(a.address.toLowerCase());
  for (const f of ['/etc/paas/chrome-allowed-hosts', path.join(DIR, 'allowed-hosts')]) {
    try { for (const line of fs.readFileSync(f, 'utf8').split('\n')) { const h = line.replace(/#.*/, '').trim().toLowerCase(); if (h) hosts.add(h); } } catch { /* optional */ }
  }
  return hosts;
}

/** null when Chrome may open url, else why not */
function refuseUrl(url) {
  if (!url || url === 'about:blank') return null;
  let u;
  try { u = new URL(url); } catch { return `"${url}" is not a full address (http://host:port/path)`; }
  if (!/^https?:$/.test(u.protocol)) return `${u.protocol} pages cannot be opened here`;
  const host = u.hostname.toLowerCase().replace(/^\[|\]$/g, '');
  const ok = allowedHosts();
  if (ok.has(host) || ok.has(`[${host}]`) || [...ok].some((h) => h.startsWith('*.') && host.endsWith(h.slice(1)))) return null;
  return `${host} is not one of this server's own addresses. Chrome here opens only the apps on this server `
    + `(${[...ok].filter((h) => !h.includes(':')).slice(0, 6).join(', ')} ...), never storage, switch or vCenter pages. `
    + 'Root can add a host to /etc/paas/chrome-allowed-hosts (or you to ~/.paas-chrome/allowed-hosts).';
}

// ---- the MCP server: chrome-devtools-mcp behind a switch -----------------------------------------------------------
function mcp() {
  const send = (m) => process.stdout.write(`${JSON.stringify(m)}\n`);
  const reply = (id, text, isError = false) => send({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text }], ...(isError ? { isError: true } : {}) } });
  let child = null;
  let childPort = 0;
  let chosen = 0;                       // the port this chat uses
  let initMsg = null;
  let initializedMsg = null;
  let internal = 0;
  const waiting = new Map();            // our own request ids sent to the child -> resolve
  const listIds = new Set();            // client tools/list ids: add our two tools to the answer

  function start(port) {
    if (child) child.kill();
    childPort = port;
    child = spawn(process.execPath, [SERVER, '--browserUrl', `http://127.0.0.1:${port || 1}`, ...SERVER_ARGS], { stdio: ['pipe', 'pipe', 'inherit'] });
    readline.createInterface({ input: child.stdout }).on('line', (line) => {
      let m;
      try { m = JSON.parse(line); } catch { return; }
      if (m.id !== undefined && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); return; }
      if (m.id !== undefined && listIds.has(m.id) && m.result?.tools) { listIds.delete(m.id); m.result.tools.push(...OUR_TOOLS); }
      send(m);
    });
  }

  async function switchTo(port) {
    start(port);
    if (!initMsg) return;
    const id = `paas-${++internal}`;
    await new Promise((resolve) => { waiting.set(id, resolve); child.stdin.write(`${JSON.stringify({ ...initMsg, id })}\n`); });
    if (initializedMsg) child.stdin.write(`${JSON.stringify(initializedMsg)}\n`);
  }

  async function ensureBrowser() {   // null when connected, else what to tell Claude
    if (!chosen) {
      const list = await browsers();
      if (list.length === 0) return 'No Chrome is connected to this server. Ask the person to run the Chrome line on their Windows PC (the command paas-chrome windows prints it; the connect-chrome skill explains), then try again.';
      if (list.length > 1) return `Several PCs are connected (${list.map((b) => `${b.pc} (${b.user}, port ${b.port})`).join('; ')}). Ask the person which PC they are on, then call use_browser.`;
      chosen = list[0].port;
    } else if (!(await alive(chosen))) {
      return `The Chrome on port ${chosen} is no longer connected (its PowerShell window was closed?). Ask the person to run the Chrome line again, then call list_my_browsers.`;
    }
    if (childPort !== chosen) await switchTo(chosen);
    return null;
  }

  async function handle(m) {
    if (m.method === 'initialize') { initMsg = m; if (!child) start(0); child.stdin.write(`${JSON.stringify(m)}\n`); return; }
    if (m.method === 'notifications/initialized') { initializedMsg = m; child?.stdin.write(`${JSON.stringify(m)}\n`); return; }
    if (m.method === 'tools/list') listIds.add(m.id);
    if (m.method === 'tools/call') {
      const { name, arguments: args = {} } = m.params || {};
      if (name === 'list_my_browsers') {
        const list = await browsers();
        return reply(m.id, list.length ? list.map((b) => `${b.port === chosen ? '* ' : '  '}${b.pc} (${b.user}) port ${b.port}, ${b.version}`).join('\n')
          + (chosen ? '\n(* = this chat)' : '\nNone chosen yet: one PC = used automatically, several = call use_browser.')
          : 'No Chrome connected. The person runs the Chrome line on their Windows PC first.');
      }
      if (name === 'use_browser') {
        const want = String(args.pc || '').trim().toLowerCase();
        const b = (await browsers()).find((x) => String(x.port) === want || x.pc.toLowerCase() === want);
        if (!b) return reply(m.id, `No connected PC "${args.pc}". Call list_my_browsers.`, true);
        chosen = b.port;
        await switchTo(chosen);
        return reply(m.id, `This chat now uses the Chrome of ${b.pc} (${b.user}), port ${b.port}.`);
      }
      const why = refuseUrl(args.url);
      if (why) return reply(m.id, `Not opened: ${why}`, true);
      const missing = await ensureBrowser();
      if (missing) return reply(m.id, missing, true);
    }
    if (!child) start(0);
    child.stdin.write(`${JSON.stringify(m)}\n`);
  }

  let queue = Promise.resolve();         // one message at a time: a switch finishes before the next call goes out
  readline.createInterface({ input: process.stdin }).on('line', (line) => {
    let m;
    try { m = JSON.parse(line); } catch { return; }
    queue = queue.then(() => handle(m)).catch((e) => { if (m.id !== undefined) reply(m.id, `Chrome connector error: ${e.message || e}`, true); });
  }).on('close', () => { child?.kill(); process.exit(0); });
}

// ---- the line each Windows PC runs ---------------------------------------------------------------------------------
function windows() {
  let host = os.hostname();
  try { host = execFileSync('hostname', ['-f'], { encoding: 'utf8' }).trim() || host; } catch { /* keep os.hostname */ }
  const user = os.userInfo().username;
  // ponytail: the port comes from a hash of PC + Windows user; two PCs with the same hash: the second gets "remote port
  // forwarding failed" and sets $p by hand (any free 9300-9399)
  const ps = '$s="$env:COMPUTERNAME$env:USERNAME"; $h=0; foreach($ch in $s.ToCharArray()){ $h=($h*31+[int]$ch)%100 }; '
    + `$p=${FIRST_PORT}+$h; `
    + '$c="$env:ProgramFiles\\Google\\Chrome\\Application\\chrome.exe"; if(!(Test-Path $c)){ $c="${env:ProgramFiles(x86)}\\Google\\Chrome\\Application\\chrome.exe" }; '
    + 'Start-Process $c "--remote-debugging-port=$p --user-data-dir=`\"$env:LOCALAPPDATA\\paas-chrome`\" --no-first-run about:blank"; '
    + `ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -R "\${p}:127.0.0.1:\${p}" ${user}@${host} `
    + '"mkdir -p ~/.paas-chrome; echo $env:COMPUTERNAME $env:USERNAME > ~/.paas-chrome/$p; trap \'rm -f ~/.paas-chrome/$p\' EXIT HUP INT TERM; '
    + 'echo Chrome of $env:COMPUTERNAME connected on port $p - keep this window open, close it to disconnect; while sleep 60; do :; done"';
  console.log('Run this in PowerShell on your Windows PC (Chrome opens with its own empty profile; keep the window open):\n');
  console.log(ps);
}

const cmd = process.argv[2] || 'mcp';
if (cmd === 'mcp') mcp();
else if (cmd === 'windows') windows();
else if (cmd === 'list') browsers().then((l) => { console.log(l.length ? l.map((b) => `${b.pc} (${b.user}) port ${b.port}, ${b.version}`).join('\n') : 'No Chrome connected.'); });
else { console.error('usage: paas-chrome.mjs [mcp | windows | list]'); process.exit(1); }
