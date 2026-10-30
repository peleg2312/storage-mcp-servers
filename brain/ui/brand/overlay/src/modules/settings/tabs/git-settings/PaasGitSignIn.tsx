import { useEffect, useState } from 'react';
import { Check, Eye, EyeOff, KeyRound, Trash2 } from 'lucide-react';

import { authenticatedFetch } from '@/shared/api';
import { Button, Input } from '@/shared/ui';
import SettingsCard from '@/modules/settings/SettingsCard';
import SettingsSection from '@/modules/settings/SettingsSection';

type Cred = { host: string; username: string };

/**
 * Peleg As A Service: sign in to a git server with a username and a token or password (name and email alone
 * cannot push). Kept by git itself for this VM account (~/.git-credentials); the secret is never shown again.
 */
export default function PaasGitSignIn() {
  const [creds, setCreds] = useState<Cred[]>([]);
  const [url, setUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);

  const load = async () => {
    try {
      const r = await authenticatedFetch('/api/paas/git-credentials');
      if (r.ok) setCreds(((await r.json()) as { credentials: Cred[] }).credentials);
    } catch { /* offline: the list stays empty */ }
  };
  useEffect(() => { void load(); }, []);

  const save = async () => {
    setBusy(true); setStatus(null);
    try {
      const r = await authenticatedFetch('/api/paas/git-credentials', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url, username, password }),
      });
      const body = (await r.json()) as { credentials?: Cred[]; error?: string };
      if (!r.ok) { setStatus({ ok: false, text: body.error || 'Not saved' }); return; }
      setCreds(body.credentials || []); setPassword(''); setUrl(''); setUsername('');
      setStatus({ ok: true, text: 'Signed in: pushes and pulls to that server work from this account now' });
    } catch (e) { setStatus({ ok: false, text: (e as Error).message }); } finally { setBusy(false); }
  };

  const remove = async (c: Cred) => {
    const r = await authenticatedFetch('/api/paas/git-credentials', {
      method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(c),
    });
    if (r.ok) setCreds(((await r.json()) as { credentials: Cred[] }).credentials);
  };

  return (
    <SettingsSection
      title="Git server sign-in"
      description="Pushing and pulling needs more than a name: sign in to your git server (GitLab, Bitbucket, GitHub, ...) with a username and a token or password. Kept by git for this VM account only."
    >
      <SettingsCard className="p-4">
        {creds.length > 0 && (
          <ul className="mb-4 divide-y divide-border rounded-lg border border-border">
            {creds.map((c) => (
              <li key={`${c.host}/${c.username}`} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <span className="flex min-w-0 items-center gap-2">
                  <KeyRound className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate"><span className="text-foreground">{c.host}</span><span className="text-muted-foreground"> · {c.username}</span></span>
                </span>
                <Button variant="ghost" size="sm" className="h-8 text-muted-foreground hover:text-red-600" onClick={() => remove(c)} aria-label={`Forget ${c.host}`}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </li>
            ))}
          </ul>
        )}
        <div className="space-y-3">
          <div>
            <label htmlFor="paas-git-url" className="mb-2 block text-sm font-medium text-foreground">Server</label>
            <Input id="paas-git-url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://git.example.com" autoComplete="off" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="paas-git-user" className="mb-2 block text-sm font-medium text-foreground">Username</label>
              <Input id="paas-git-user" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" />
            </div>
            <div>
              <label htmlFor="paas-git-token" className="mb-2 block text-sm font-medium text-foreground">Token or password</label>
              <div className="relative">
                <Input id="paas-git-token" type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" className="pr-10" />
                <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide' : 'Show'} className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground">
                  {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">A personal access token is safer than the account password.</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={save} disabled={busy || !url.trim() || !username.trim() || !password}>{busy ? 'Signing in…' : 'Sign in'}</Button>
            {status && (
              <span className={`flex items-center gap-1 text-sm ${status.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`} role="status">
                {status.ok && <Check className="h-4 w-4" />}{status.text}
              </span>
            )}
          </div>
        </div>
      </SettingsCard>
    </SettingsSection>
  );
}
