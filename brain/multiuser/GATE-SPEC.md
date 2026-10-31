# Sign-in gate for the multi-user web UI: specification

The contract of `gate.js`. Accounts, the marketplace, the per-user UI service and the Users page are separate (`paas-user`).

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

## 3. Per-user UI instances

One systemd unit per user: `paas-ui@.service` (the file next to this one). Its settings are
`/etc/paas/users/<user>.env` (root, 0600), written by `write_env` in `paas-user` (the gate's `createEnv` writes the same
file for a first sign-in): port, `JWT_SECRET`, `PAAS_LOGIN_USERS=<user>`, `CLAUDE_CLI_PATH`, `PATH`. Ports are
one above the highest in use, never reused while the file exists. Instance API the gate relies on:
`POST /api/auth/login` (200 + `token`, 401, 429) and `GET /health`.

### 3.1 Idle stop
Every instance costs RAM, so the gate stops the ones nobody uses. It records per user the time of the last forwarded
request and the number of open upgraded (WebSocket) connections. Every 60 s it stops (`systemctl stop paas-ui@<user>`,
logged) each user whose instance runs, who has no open WebSocket, whose last request is older than `GATE_IDLE_MINUTES`
(environment of the gate, default 120, `0` = never stop) and who has no running `claude` process
(`pgrep -u <user> -x claude`; if pgrep itself fails the user counts as busy). An instance already running when the gate
starts gets its clock started then. The decision is the pure function `idleUsers(now, lastSeen, sockets, running, idleMs)`.
A stopped instance needs no sign-in again: the next request with a live cookie starts it (4.5). `node gate.js --self-test`
checks the decision and the allowed-groups parser without touching `/etc/paas`.

## 4. Gate behaviour

### 4.1 Listener
- HTTPS on `0.0.0.0:3001` with the certificate above. Runs as root (it must start other users' services and check
  passwords). Its own systemd unit `paas-gate.service`, enabled at boot.
- Suggested implementation: Node 22 standard library only (`https`, `http`, `net`, `crypto`, `child_process`),
  run with `/opt/paas/ui/node/bin/node`; `node-pty` is available in `/opt/paas/ui/app/node_modules` for the `su`
  check. Another language is fine if it meets the same rules and needs nothing from the internet.

### 4.2 Who may sign in
- `root`, and members of any group listed in `/etc/paas/allowed-groups` (`id -nG <user>`; one group name per line,
  `#` comments; `paas-users` when the file is missing or empty; read at startup and again at most every 60 s). Anyone
  else: same "wrong username or password" answer as a bad password (do not reveal which accounts exist).
- Accounts may come from Active Directory through sssd: `id` sees their groups, so an AD group in the file works like
  a local one. People need no `paas-user add` first (4.3 step 3).
- The submitted username is lower-cased first (sssd with `case_sensitive = false` resolves it) and must match
  `^[a-z_][a-z0-9_.-]{0,63}$` before it is used anywhere. Same error and same timing as for any wrong password.

### 4.3 Sign-in
- One sign-in page at `GET /` when there is no valid gate session, styled like the current UI sign-in (logo, title
  "Peleg As A Service", "Sign in with this VM's account"). No sign-up.
- `POST /paas-gate/login` with username + password:
  1. Rate limit: 5 failures within 10 minutes per `username|client IP`, 30 per client IP, 4 password checks at once
     per client IP → HTTP 429. A request body not complete after 10 s is dropped.
  2. Check the password exactly like `system-auth.ts`: run `su <user> -c 'exit 0'` in a pseudo-terminal, answer the
     password prompt; because the gate is root, run it as `runuser -u nobody -- su <user> -c 'exit 0'` (root's `su`
     never asks). Success only if the prompt appeared **and** exit code is 0. 15 s timeout = failure.
  3. Provision on first use: when `/etc/paas/users/<user>.env` did not exist yet (first sign-in) or the home has no
     `.claude/brain`, run `/opt/paas/bin/paas-user provision <user>` (60 s timeout; a failure is logged, never fatal).
     It makes the home when sssd has not (`mkhomedir_helper`), links the brain, installs the UI plugins and default
     marketplace items, and picks the team: `/etc/paas/team-groups` (lines `<team> <group>`, `#` comments) maps AD
     groups to teams; a person with no team yet gets the team of the first group they belong to (`paas-team use`).
     Then make sure the user's instance runs: create `/etc/paas/users/<user>.env` if missing, `systemctl start
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
- Verify with a constant-time comparison; expired, malformed or unknown user = no session. A user with
  `/etc/paas/users/<user>.locked` (made by `paas-user lock`) has no session either.

### 4.5 Forwarding
- Every request with a valid session goes to that user's instance (`127.0.0.1:<port>`), path and query unchanged;
  remove `Cookie: paas_gate=...` before forwarding; add `X-Forwarded-For` / `X-Forwarded-Proto: https`.
- WebSocket upgrades on `/ws`, `/shell`, `/desktop-notifications` (and any other upgrade) are forwarded the same way
  (raw TCP pipe after the upgrade).
- No valid session: `GET` of an HTML page → the sign-in page; anything else → 401 JSON `{"error":"Sign in"}`.
- The instance is stopped (crash, reboot): start it again as in 4.3 step 3 before forwarding (not for a locked user).
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
| 17 | dana signs in, `paas-user lock dana`, then a request with her cookie | 401, `paas-ui@dana` not restarted |
| 18 | `GATE_IDLE_MINUTES=1`, peleg signs in, no request and no `claude` for over 1 minute (plus the 60 s sweep); then any request with his cookie | `paas-ui@peleg` stopped (gate log), then restarted and the request served |
| 19 | a member of an AD group in `allowed-groups`, never created with `paas-user add`, signs in | 200; `.env` made, home exists with `.claude/brain`, team from `team-groups` set |
| 20 | peleg keeps a WebSocket open (or a `claude` process runs as him) past the timeout | `paas-ui@peleg` is not stopped; after the socket closes it is stopped once idle again |
| 21 | a second group added to `/etc/paas/allowed-groups` (wait 60 s or restart the gate) | its members sign in; non-members still get the same 401 as test 3 |
