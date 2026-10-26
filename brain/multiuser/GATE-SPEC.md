# Sign-in gate for the multi-user web UI: specification

For the developer who builds it. Everything around the gate (user accounts, the marketplace, the per-user UI service,
the Users page for root) is built separately in this repo; this document is the contract between the two.

## 1. What it is for

The storage brain's web UI ("Peleg As A Service", a branded CloudCLI) runs on one offline RHEL 9 VM and is opened
from Windows PCs in Chrome. Several people use it. Each person must:

- open the **same address** (`https://<vm>:3001`) and see **one sign-in screen**;
- sign in with **their own Linux account** on the VM (username + password);
- then work only in **their own** UI: their chats, projects, files, notes, marketplace items, and a Claude that runs
  as their Linux account.

Root signs in the same way and additionally manages users (that part is a UI page, not the gate).

To get real separation, the UI runs **one instance per Linux user**, as that user, listening only on `127.0.0.1`.
The gate is the only thing on the network: it checks who you are and forwards your browser to your own instance.

```
 Chrome on Windows ──https──> gate :3001 (root) ──http 127.0.0.1──> paas-ui@peleg (runs as peleg)  :41001
                                                └─────────────────> paas-ui@dana  (runs as dana)   :41002
                                                └─────────────────> paas-ui@root  (runs as root)   :41000
```

## 2. Pieces that already exist (do not rebuild)

| Piece | Where | What the gate uses |
|---|---|---|
| The UI app (Node 22 + built CloudCLI) | `/opt/paas/ui/node/bin/node`, `/opt/paas/ui/app` | Started per user by systemd (below) |
| The UI's own sign-in, checking the Linux password with `su` | `brain/ui/brand/overlay/server/modules/auth/system-auth.ts` | Each instance accepts only its own user (`PAAS_LOGIN_USERS=<user>`). Reuse its `su` technique for the gate's own check |
| Instance login API | `POST /api/auth/login` `{"username","password"}` → `{"token": "<JWT>"}` (HTTP 200), 401 wrong password, 429 locked | The gate calls it to get the browser's token |
| Instance health | `GET /health` → 200 | The gate waits for it after starting an instance |
| Where the browser keeps its token | `localStorage["auth-token"]` | The gate's post-login page writes it there |
| WebSocket endpoints | `/ws` (chat), `/shell` (terminal), `/desktop-notifications` | Must be forwarded (HTTP Upgrade) |
| Plugin servers protected by a per-instance key | already in `brain/ui/brand/brand.py` | Nothing to do |
| TLS certificate | `install-ui.sh` makes a self-signed one; for the gate: `/etc/paas/tls/paas-ui.crt` + `.key` | HTTPS listener |

## 3. Per-user UI instances (systemd)

Template unit `/etc/systemd/system/paas-ui@.service` (the gate starts it; user creation also enables it):

```ini
[Unit]
Description=Peleg As A Service web UI for %i
After=network.target

[Service]
User=%i
EnvironmentFile=/etc/paas/users/%i.env
Environment=HOST=127.0.0.1 NODE_ENV=production
WorkingDirectory=/opt/paas/ui/app
ExecStart=/opt/paas/ui/node/bin/node /opt/paas/ui/app/dist-server/server/index.js
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`/etc/paas/users/<user>.env` (owner root, mode 0600; systemd reads it as root, the running process is only readable
by that user and root):

```
SERVER_PORT=41001
JWT_SECRET=<64 random hex chars, one per user>
PAAS_LOGIN_USERS=<user>
PATH=/opt/paas/ui/node/bin:/usr/local/bin:/usr/bin:/bin
```

Ports: `41000 + n`, unique per user, never reused while the file exists. The gate creates the file the first time an
allowed user signs in and it is missing.

## 4. Gate behaviour

### 4.1 Listener
- HTTPS on `0.0.0.0:3001` with the certificate above. Runs as root (it must start other users' services and check
  passwords). Its own systemd unit `paas-gate.service`, enabled at boot.
- Suggested implementation: Node 22 standard library only (`https`, `http`, `net`, `crypto`, `child_process`),
  run with `/opt/paas/ui/node/bin/node`; `node-pty` is available in `/opt/paas/ui/app/node_modules` for the `su`
  check. Another language is fine if it meets the same rules and needs nothing from the internet.

### 4.2 Who may sign in
- `root`, and members of the Linux group `paas-users` (`id -nG <user>`). Anyone else: same "wrong username or
  password" answer as a bad password (do not reveal which accounts exist).
- Username must match `^[a-z_][a-z0-9_.-]{0,31}$` before it is used anywhere.

### 4.3 Sign-in
- One sign-in page at `GET /` when there is no valid gate session, styled like the current UI sign-in (logo, title
  "Peleg As A Service", "Sign in with this VM's account"). No sign-up.
- `POST /paas-gate/login` with username + password:
  1. Rate limit: 5 failures within 10 minutes per `username|client IP` → HTTP 429 for the rest of the window.
  2. Check the password exactly like `system-auth.ts`: run `su <user> -c 'exit 0'` in a pseudo-terminal, answer the
     password prompt; because the gate is root, run it as `runuser -u nobody -- su <user> -c 'exit 0'` (root's `su`
     never asks). Success only if the prompt appeared **and** exit code is 0. 15 s timeout = failure.
  3. Make sure the user's instance runs: create `/etc/paas/users/<user>.env` if missing, `systemctl start
     paas-ui@<user>`, poll `http://127.0.0.1:<port>/health` up to 60 s.
  4. Get the browser token: `POST http://127.0.0.1:<port>/api/auth/login` with the same username + password
     (the instance re-checks it as its own user and returns `token`).
  5. Set the gate session cookie (4.4) and answer with a small HTML page that stores the token and opens the app:
     `localStorage.setItem('auth-token', <token as a JSON string>); location.replace('/');`
- Never write passwords anywhere: no logs, no files, no command-line arguments (only into the pty).

### 4.4 Gate session
- Cookie `paas_gate` = `<user>.<expiry unix seconds>.<HMAC-SHA256(user.expiry) hex>`, key from `/etc/paas/gate.key`
  (32 random bytes, created at install, root 0600).
- Attributes: `HttpOnly; Secure; SameSite=Strict; Path=/`. Lifetime 12 hours.
- Verify with a constant-time comparison; expired, malformed or unknown user = no session.

### 4.5 Forwarding
- Every request with a valid session goes to that user's instance (`127.0.0.1:<port>`), path and query unchanged;
  remove `Cookie: paas_gate=...` before forwarding; add `X-Forwarded-For` / `X-Forwarded-Proto: https`.
- WebSocket upgrades on `/ws`, `/shell`, `/desktop-notifications` (and any other upgrade) are forwarded the same way
  (raw TCP pipe after the upgrade).
- No valid session: `GET` of an HTML page → the sign-in page; anything else → 401 JSON `{"error":"Sign in"}`.
- The instance is stopped (crash, reboot): start it again as in 4.3 step 3 before forwarding.
- Large bodies (file uploads up to ~60 MB) and streamed responses (chat streaming, downloads) must pass through
  without buffering everything in memory.

### 4.6 Sign-out
- `POST /api/auth/logout` (the UI's own sign-out) and `GET /paas-gate/logout`: clear the cookie
  (`Max-Age=0`), forward the logout to the instance when there was a session, then show the sign-in page.

### 4.7 Root
- Root signs in like everyone and gets root's own instance. The Users page (built in the repo, runs inside root's
  instance) creates users with `useradd -m -G paas-users`, sets passwords, creates the `.env` file and enables
  `paas-ui@<user>`. The gate needs no admin screens.

## 5. Security requirements (must all hold)

1. The gate is the only listener reachable from the network; instances bind `127.0.0.1` only.
2. A signed-in user can never reach another user's instance: routing comes only from the verified cookie, never from
   a header, path or parameter the browser controls.
3. Passwords never leave memory except into the `su` pty and the local instance login call.
4. Same error text and similar timing for unknown user, not allowed user and wrong password.
5. Rate limit as in 4.3.1; the instance has its own limit too.
6. Gate key, `.env` files and TLS key: root only (0600).
7. No dependency fetched from the internet at install or run time.
8. Logs: sign-in success / failure with user, client IP and time; never the password or tokens.

## 6. Acceptance tests (Rocky Linux 9 container, x86_64)

Run alongside `brain/ui/test-ui.sh`. Users: `root`, `peleg` and `dana` in `paas-users`, `eve` not in it.

| # | Test | Expected |
|---|---|---|
| 1 | `GET https://127.0.0.1:3001/` without cookie | sign-in page (200) |
| 2 | peleg, wrong password | 401, no cookie |
| 3 | eve, right password | same 401 as test 2 |
| 4 | peleg, right password | 200, cookie set, page stores a token |
| 5 | with peleg's cookie + token: `GET /api/projects` | peleg's projects (from `/home/peleg`) |
| 6 | dana signs in in another client; both use the UI at once | each sees only their own projects |
| 7 | peleg's cookie with dana's token | 401 from peleg's instance |
| 8 | edited cookie (user changed to dana, old HMAC) | treated as signed out |
| 9 | WebSocket `/ws?token=…` with peleg's cookie | connects; chat works |
| 10 | Shell tab as peleg, run `id -un` | `peleg` |
| 11 | Claude run from peleg's UI, `ps -o user` of the claude process | `peleg` |
| 12 | 5 wrong passwords for peleg from one IP, then the right one | 429 |
| 13 | `curl http://<vm-ip>:41001/` from another host | connection refused |
| 14 | sign out | cookie cleared; `/api/projects` → 401 |
| 15 | `systemctl stop paas-ui@peleg`, then any request with peleg's cookie | instance restarted, request served |
| 16 | 50 MB file upload in the Files tab | succeeds |

## 7. Deliverables

- `brain/multiuser/gate.js` (or equivalent), `paas-gate.service`, `paas-ui@.service`.
- An install step (root): create `/etc/paas/{users,tls}`, `gate.key`, group `paas-users`, install and enable both
  units, open port 3001 in firewalld.
- The acceptance tests above as a script next to `brain/ui/test-ui.sh`.
