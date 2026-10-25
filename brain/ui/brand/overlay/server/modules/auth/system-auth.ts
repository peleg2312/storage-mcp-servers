import pty from 'node-pty';

/**
 * Peleg As A Service: sign in with a VM account instead of a web-only one. The password is checked by the system
 * itself (`su <user>`, setuid, PAM: the same check as a console login), so it never lands in the UI's database.
 * Accounts allowed: PAAS_LOGIN_USERS (default "root"). No sign-up: accounts come from the VM.
 */
export function loginUsers(): string[] {
  return (process.env.PAAS_LOGIN_USERS || 'root').split(/[\s,]+/).filter(Boolean);
}

const failures = new Map<string, number[]>();
const WINDOW_MS = 10 * 60 * 1000;
const MAX_FAILURES = 5;

/** Five wrong passwords within ten minutes block that key (account + client address) for the rest of the window. */
export function isThrottled(username: string): boolean {
  const now = Date.now();
  const recent = (failures.get(username) || []).filter((t) => now - t < WINDOW_MS);
  failures.set(username, recent);
  return recent.length >= MAX_FAILURES;
}

export function recordFailure(username: string): void {
  failures.set(username, [...(failures.get(username) || []), Date.now()]);
}

export function checkSystemPassword(username: string, password: string): Promise<boolean> {
  if (!/^[a-z_][a-z0-9_.-]*$/.test(username) || /[\r\n]/.test(password) || password.length > 512) {
    return Promise.resolve(false);
  }
  return new Promise((resolve) => {
    // as root, su never asks for a password: drop to "nobody" first so the system really checks it
    const [cmd, args]: [string, string[]] = process.getuid?.() === 0
      ? ['runuser', ['-u', 'nobody', '--', 'su', username, '-c', 'exit 0']]
      : ['su', [username, '-c', 'exit 0']];
    const proc = pty.spawn(cmd, args, {
      name: 'dumb', cols: 80, rows: 24, env: { PATH: '/usr/sbin:/usr/bin:/sbin:/bin', LANG: 'C', LC_ALL: 'C' },
    });
    let sent = false;
    let done = false;
    const finish = (ok: boolean) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try { proc.kill(); } catch { /* already gone */ }
      resolve(ok);
    };
    const timer = setTimeout(() => finish(false), 15000);
    proc.onData((data) => {
      if (!sent && /password/i.test(data)) {
        sent = true;
        proc.write(`${password}\r`);
      }
    });
    // no password prompt at all (e.g. su without a tty check) never counts as a sign-in
    proc.onExit(({ exitCode }) => finish(sent && exitCode === 0));
  });
}
