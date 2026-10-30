import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import express from 'express';

/**
 * Peleg As A Service: sign in to a git server (GitLab, Bitbucket, GitHub, ...) with a username and a token or
 * password, so pushes and pulls from this account work without asking. Stored by git itself (`git credential
 * approve` with the "store" helper: ~/.git-credentials, mode 600, this VM account only); listed without the secret.
 * Signed-in only (mounted behind authenticateToken).
 */
export const paasGitCredentials = express.Router();

const FILE = path.join(os.homedir(), '.git-credentials');

const git = (args: string[], input = ''): Promise<void> => new Promise((resolve, reject) => {
  const p = spawn('git', args, { env: { ...process.env, GIT_TERMINAL_PROMPT: '0' } });
  let err = '';
  p.stderr.on('data', (d) => { err += d; });
  p.on('error', reject);
  p.on('close', (code) => (code === 0 ? resolve() : reject(new Error(err.trim() || `git ${args[0]} failed`))));
  p.stdin.end(input);
});

const list = () => {
  let text = '';
  try { text = fs.readFileSync(FILE, 'utf8'); } catch { return []; }
  return text.split('\n').flatMap((line) => {
    try {
      const u = new URL(line.trim());
      return line.trim() && u.username ? [{ host: u.host, username: decodeURIComponent(u.username) }] : [];
    } catch { return []; }
  });
};

paasGitCredentials.get('/git-credentials', (_req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.json({ credentials: list() });
});

paasGitCredentials.post('/git-credentials', async (req, res) => {
  const { url, username, password } = (req.body ?? {}) as Record<string, unknown>;
  let u: URL;
  try { u = new URL(String(url || '').trim()); } catch { res.status(400).json({ error: 'Enter the server address, e.g. https://git.example.com' }); return; }
  if (!/^https?:$/.test(u.protocol)) { res.status(400).json({ error: 'Only http(s) servers: for ssh use a key' }); return; }
  const user = String(username || '').trim();
  const secret = String(password || '');
  if (!user || !secret || /[\r\n]/.test(user + secret) || secret.length > 4096) { res.status(400).json({ error: 'Username and token (or password) are needed' }); return; }
  try {
    await git(['config', '--global', 'credential.helper', 'store']);
    await git(['credential', 'approve'], `protocol=${u.protocol.slice(0, -1)}\nhost=${u.host}\nusername=${user}\npassword=${secret}\n\n`);
    res.json({ ok: true, credentials: list() });
  } catch (e) { res.status(500).json({ error: (e as Error).message }); }
});

paasGitCredentials.delete('/git-credentials', async (req, res) => {
  const { host, username } = (req.body ?? {}) as Record<string, unknown>;
  const h = String(host || '').trim();
  const user = String(username || '').trim();
  if (!h || !user || /[\s]/.test(h + user)) { res.status(400).json({ error: 'host and username are needed' }); return; }
  try {
    for (const protocol of ['https', 'http']) await git(['credential', 'reject'], `protocol=${protocol}\nhost=${h}\nusername=${user}\n\n`);
    res.json({ ok: true, credentials: list() });
  } catch (e) { res.status(500).json({ error: (e as Error).message }); }
});
