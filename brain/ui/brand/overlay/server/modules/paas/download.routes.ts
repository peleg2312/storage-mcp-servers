import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import express from 'express';

/**
 * Peleg As A Service: download a file Claude made or named in the chat (Excel, PDF, CSV, charts, reports) straight
 * to the browser. Signed-in only (mounted behind authenticateToken). A relative path resolves against the project
 * folder the chat runs in (`base`); files must sit under the home folder or that project.
 */
export const paasRoutes = express.Router();

const real = (p: string): string | null => {
  try { return fs.realpathSync(p); } catch { return null; }
};

paasRoutes.get('/download', (req, res) => {
  const home = os.homedir();
  const base = real(String(req.query.base || home)) || home;
  const file = real(path.resolve(base, String(req.query.path || '').replace(/^~(?=\/|$)/, home)));
  if (!file || !fs.statSync(file).isFile()) {
    res.status(404).json({ error: 'File not found' });
    return;
  }
  const roots = [real(home) || home, base];
  if (!roots.some((r) => file === r || file.startsWith(r.endsWith(path.sep) ? r : r + path.sep))) {
    res.status(403).json({ error: 'Only files under the home folder or the project can be downloaded' });
    return;
  }
  res.download(file, path.basename(file));
});
