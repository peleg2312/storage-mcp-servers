#!/usr/bin/env python3
"""Peleg As A Service branding on a CloudCLI checkout (siteboon/claudecodeui, AGPL-3.0): name, logo, colours.

    python3 brand.py <claudecodeui checkout>

Every edit checks that the upstream text is still there, so an upstream change fails here loudly instead of
silently half-branding the UI. The "open source" links to upstream stay (AGPL attribution).
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1]
NAME = "Peleg As A Service"


def edit(rel, *pairs):
    p = os.path.join(SRC, rel)
    s = open(p, encoding="utf-8").read()
    for old, new in pairs:
        if old not in s:
            sys.exit(f"brand: '{old[:60]}' not found in {rel} (upstream changed: update brand.py)")
        s = s.replace(old, new)
    open(p, "w", encoding="utf-8").write(s)


def strings(rel, **keys):
    p = os.path.join(SRC, "src/modules/i18n/locales/en", rel)
    data = json.load(open(p, encoding="utf-8"))
    for dotted, value in keys.items():
        node = data
        *path, last = dotted.split("__")
        for k in path:
            node = node[k]
        if last not in node:
            sys.exit(f"brand: {dotted} not in {rel}")
        node[last] = value
    json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


# logo + favicon (the PNG sizes are rendered from it by the bundle script)
for name in ("logo.svg", "favicon.svg"):
    shutil.copy(os.path.join(HERE, "logo.svg"), os.path.join(SRC, "public", name))
# new files (system login, Claude-desktop touches): overlay/<path> -> <checkout>/<path>
for root, _, files in os.walk(os.path.join(HERE, "overlay")):
    for fn in files:
        rel = os.path.relpath(os.path.join(root, fn), os.path.join(HERE, "overlay"))
        os.makedirs(os.path.dirname(os.path.join(SRC, rel)), exist_ok=True)
        shutil.copy(os.path.join(root, fn), os.path.join(SRC, rel))
with open(os.path.join(SRC, "src/index.css"), "a", encoding="utf-8") as f:
    f.write("\n" + open(os.path.join(HERE, "paas.css"), encoding="utf-8").read())

edit("index.html", ("<title>CloudCLI UI</title>", f"<title>{NAME}</title>"))
m = json.load(open(os.path.join(SRC, "public/manifest.json")))
m.update(name=NAME, short_name="PaaS", description=f"{NAME}: the storage & platform brain", theme_color="#0d0f1c",
         background_color="#0d0f1c")
json.dump(m, open(os.path.join(SRC, "public/manifest.json"), "w"), indent=2)
edit("src/modules/chat/utils/pageTitleNotification.ts", ("'CloudCLI UI'", f"'{NAME}'"))

strings("sidebar.json", app__title=NAME, app__subtitle="Storage & platform brain")
edit("src/modules/i18n/locales/en/common.json", ('"Loading CloudCLI"', f'"Loading {NAME}"'))
strings("auth.json", login__title=NAME, register__title=NAME, register__description="First start: create your login (one account, kept on this VM)")

# sidebar: gradient logo tile + gradient wordmark
edit("src/modules/sidebar/SidebarHeader.tsx",
     ('<div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-primary/90 shadow-sm">\n'
      '        <svg className="h-3.5 w-3.5 text-primary-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      'strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">\n'
      '          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />\n'
      '        </svg>\n'
      '      </div>',
      '<img src="/logo.svg" alt="" className="h-7 w-7 flex-shrink-0 rounded-lg shadow-sm shadow-primary/30" />'),
     ('className="truncate text-sm font-bold tracking-tight text-foreground"',
      'className="paas-wordmark truncate text-sm font-bold tracking-tight text-foreground"'))

# login / setup card: the logo itself (already a gradient tile), gradient title, banner-like glow behind
edit("src/modules/auth/AuthScreenLayout.tsx",
     ('<div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/80 '
      'shadow-lg shadow-primary/25 ring-1 ring-inset ring-white/20">\n'
      '                  <img src="/logo.svg" alt="CloudCLI" className="h-9 w-9" />\n'
      '                </div>',
      f'<img src="/logo.svg" alt="{NAME}" className="h-16 w-16 rounded-2xl shadow-lg shadow-primary/30" />'),
     ('<div aria-hidden className="pointer-events-none fixed inset-0">',
      '<div aria-hidden className="paas-login-glow pointer-events-none fixed inset-0">'),
     ('className="font-serif text-3xl font-bold tracking-tight text-foreground">{title}</h1>',
      'className="paas-wordmark text-3xl font-bold tracking-tight text-foreground">{title}</h1>'))
edit("src/modules/auth/AuthLoadingScreen.tsx",
     ('<div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/80 '
      'shadow-lg shadow-primary/25 ring-1 ring-inset ring-white/20">\n'
      '            <img src="/logo.svg" alt="CloudCLI" className="h-9 w-9" />\n'
      '          </div>',
      f'<img src="/logo.svg" alt="{NAME}" className="h-16 w-16 rounded-2xl shadow-lg shadow-primary/30" />'),
     ('className="mb-4 text-2xl font-bold tracking-tight text-foreground"',
      'className="paas-wordmark mb-4 text-2xl font-bold tracking-tight text-foreground"'),
     ("          CloudCLI\n", f"          {NAME}\n"))
edit("src/modules/sidebar/SidebarFooter.tsx", ("CloudCLI v{currentVersion}", "PaaS · CloudCLI v{currentVersion}"))
edit("src/shared/utils.ts", ("const DEFAULT_PAGE_TITLE = 'CloudCLI UI';", f"const DEFAULT_PAGE_TITLE = '{NAME}';"))
# offline VM: no GitHub stars badge (it calls api.github.com), no Discord / issue links; the repo link stays (AGPL)
edit("src/modules/sidebar/GitHubStarBadge.tsx", ("  if (IS_PLATFORM || isDismissed) return null;", "  return null;"))
# sign in with the VM's own account (PAAS_LOGIN_USERS, default root), checked by the system; no sign-up page
edit("server/modules/auth/auth.service.ts",
     ("import { AppError } from '@/shared/utils.js';",
      "import { AppError } from '@/shared/utils.js';\n\nimport { checkSystemPassword, isThrottled, loginUsers, recordFailure } from './system-auth.js';"),
     ("        needsSetup: !dependencies.users.hasUsers(),", "        needsSetup: false,"),
     ("      dependencies.transaction.begin();\n",
      "      throw new AppError('Sign-up is disabled: sign in with this VM\\'s account', {\n"
      "        code: 'AUTH_SIGNUP_DISABLED', statusCode: 403 });\n"
      "      dependencies.transaction.begin();\n"),
     ("      const user = dependencies.users.getUserByUsername(username);\n"
      "      const validPassword = user\n"
      "        ? await dependencies.comparePassword(password, user.password_hash)\n"
      "        : false;\n"
      "      if (!user || !validPassword) {",
      "      const lockKey = `${username}|${String(clientAddress ?? '')}`;   // per person: one typo-prone colleague cannot lock the team out\n"
      "      if (isThrottled(lockKey)) {\n"
      "        throw new AppError('Too many failed sign-ins: try again in 10 minutes', {\n"
      "          code: 'AUTH_THROTTLED', statusCode: 429 });\n"
      "      }\n"
      "      const validPassword = loginUsers().includes(username) && await checkSystemPassword(username, password);\n"
      "      if (!validPassword) recordFailure(lockKey);\n"
      "      // the VM account gets a row on first sign-in (the stored hash is random: the password always comes from the VM)\n"
      "      const user = validPassword\n"
      "        ? dependencies.users.getUserByUsername(username)\n"
      "          ?? dependencies.users.createUser(username, await dependencies.hashPassword(crypto.randomUUID() + crypto.randomUUID()))\n"
      "        : undefined;\n"
      "      if (!user || !validPassword) {"))
edit("server/modules/auth/auth.service.ts",
     ("    async login(usernameInput: unknown, passwordInput: unknown) {",
      "    async login(usernameInput: unknown, passwordInput: unknown, clientAddress?: string) {"))
edit("server/modules/auth/auth.routes.ts",
     ("      res.json(await service.login(body.username, body.password));",
      "      res.json(await service.login(body.username, body.password, req.ip));"))
strings("auth.json", login__description="Sign in with this VM's account",
        login__footerText="Runs on this VM · read-only toward infrastructure",
        login__placeholders__username="root", login__placeholders__password="The VM's root password")

# HTTPS when PAAS_TLS_CERT / PAAS_TLS_KEY are set (install-ui.sh makes a certificate): the password is not sent in clear
edit("server/index.ts",
     ("import http from 'http';", "import http from 'http';\nimport https from 'https';\nimport { readFileSync } from 'fs';"),
     ("const server = http.createServer(app);",
      "const server = process.env.PAAS_TLS_CERT && process.env.PAAS_TLS_KEY\n"
      "  ? https.createServer({ cert: readFileSync(process.env.PAAS_TLS_CERT), key: readFileSync(process.env.PAAS_TLS_KEY) }, app)\n"
      "  : http.createServer(app);"))
# Claude-desktop feel: a new chat opens on the logo and a time-of-day greeting instead of a provider picker heading
edit("src/modules/chat/transcript/ProviderSelectionEmptyState.tsx",
     ('<h2 className="text-lg font-semibold tracking-tight text-foreground sm:text-xl">\n'
      '              {t("providerSelection.title")}\n'
      '            </h2>',
      '<img src="/logo.svg" alt="" className="mx-auto mb-5 h-12 w-12 rounded-xl shadow-lg shadow-primary/30" />\n'
      '            <h2 className="font-serif text-3xl tracking-tight text-foreground sm:text-4xl">\n'
      '              {(() => { const h = new Date().getHours(); return h < 5 ? "Working late" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"; })()}\n'
      '            </h2>'))
strings("chat.json", providerSelection__description="What are we working on today?")
# upstream: any 401 before signing in (plugin / task polling) showed "Your session expired" on the sign-in page
edit("src/shared/api.ts", ("    if (response.status === 401 && response.headers.get('X-Auth-Error')) {",
                           "    if (response.status === 401 && response.headers.get('X-Auth-Error') && localStorage.getItem('auth-token')) {"))
# files Claude names in the chat (Excel, PDF, CSV, charts...) get a Download chip; served by /api/paas/download
edit("server/index.ts",
     ("import { taskmasterRoutes } from './modules/taskmaster/index.js';",
      "import { taskmasterRoutes } from './modules/taskmaster/index.js';\nimport { paasRoutes } from './modules/paas/download.routes.js';"),
     ("app.use('/api/file-tree', authenticateToken, fileTreeRoutes);",
      "app.use('/api/file-tree', authenticateToken, fileTreeRoutes);\napp.use('/api/paas', authenticateToken, paasRoutes);"))
edit("src/modules/chat/transcript/Markdown.tsx",
     ("import { usePaletteOps } from '@/modules/command-palette';",
      "import { usePaletteOps } from '@/modules/command-palette';\n"
      "import { useMarkdownWorkspaceProjectId } from '@/modules/chat/context/MarkdownWorkspaceContext';\n"
      "import { PAAS_DOWNLOADABLE, downloadChatFile } from '@/modules/chat/transcript/paasDownload';"),
     ("  const { openFileInEditor, openDirectory } = usePaletteOps();\n",
      "  const { openFileInEditor, openDirectory } = usePaletteOps();\n  const paasProjectId = useMarkdownWorkspaceProjectId();\n"),
     ("          return (\n            <a\n              href={href || fileRef}",
      "          return (\n            <>\n            <a\n              href={href || fileRef}"),
     ("              {linkChildren}\n            </a>\n          );\n        }\n",
      "              {linkChildren}\n            </a>\n"
      "            {PAAS_DOWNLOADABLE.test(stripLineSuffix(fileRef.trim())) && (\n"
      "              <button type=\"button\" className=\"paas-dl\" title=\"Download to this computer\"\n"
      "                onClick={(event) => { event.preventDefault(); void downloadChatFile(fileRef, paasProjectId); }}>\n"
      "                ↓ Download\n"
      "              </button>\n"
      "            )}\n"
      "            </>\n          );\n        }\n"),
     ("    [openFileInEditor, openDirectory],\n", "    [openFileInEditor, openDirectory, paasProjectId],\n"))
# the read-only guard's "ask" (cluster changes, database writes) must reach the user in every permission mode: the
# allowed-tools shortcut must not answer it, "bypass" is emulated in canUseTool (all else allowed) and the classifier
# mode runs as default (the SDK documents neither for a hook's ask)
P = "server/modules/providers/list/claude/claude-runtime.provider.js"
edit(P,
     ("function mapCliOptionsToSDK(options = {}) {",
      "// sessions started in bypass mode: emulated in canUseTool so the read-only guard's asks still reach the user\n"
      "const PAAS_BYPASS = new WeakSet();\n\nfunction mapCliOptionsToSDK(options = {}) {"),
     ("  if (settings.skipPermissions && permissionMode !== 'plan') {\n    sdkOptions.permissionMode = 'bypassPermissions';\n  }\n",
      "  if (settings.skipPermissions && permissionMode !== 'plan') {\n    sdkOptions.permissionMode = 'bypassPermissions';\n  }\n"
      "  if (sdkOptions.permissionMode === 'bypassPermissions') PAAS_BYPASS.add(sdkOptions);\n"
      "  if (sdkOptions.permissionMode === 'bypassPermissions' || sdkOptions.permissionMode === 'auto') {\n"
      "    sdkOptions.permissionMode = 'default';\n  }\n"),
     ("      const requiresInteraction = TOOLS_REQUIRING_INTERACTION.has(toolName);\n\n"
      "      if (!requiresInteraction) {\n"
      "        if (sdkOptions.permissionMode === 'bypassPermissions') {",
      "      const guardAsk = /^Read-only guard:/.test(String(context?.decisionReason || ''));\n"
      "      const requiresInteraction = TOOLS_REQUIRING_INTERACTION.has(toolName) || guardAsk;\n\n"
      "      if (!requiresInteraction) {\n"
      "        if (PAAS_BYPASS.has(sdkOptions)) {"))
# prompt bar like Claude desktop: a clear "/" commands button instead of a speech bubble with a count badge
edit("src/modules/chat/composer/ChatComposer.tsx",
     ("import { PaperclipIcon, MessageSquareIcon, XIcon, Loader2, ArrowUpIcon, PencilIcon } from 'lucide-react';",
      "import { PaperclipIcon, XIcon, Loader2, ArrowUpIcon, PencilIcon } from 'lucide-react';"),
     ("              <MessageSquareIcon />\n"
      "              {slashCommandsCount > 0 && (\n"
      "                <span\n"
      "                  className=\"absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground\"\n"
      "                >\n"
      "                  {slashCommandsCount}\n"
      "                </span>\n"
      "              )}\n",
      "              <span className=\"text-[15px] font-semibold leading-none\" data-count={slashCommandsCount}>/</span>\n"))
edit("src/modules/chat/transcript/MessageComponent.tsx",
     ('rounded-full bg-blue-600 text-sm text-white sm:flex">', 'rounded-full paas-avatar text-sm font-semibold sm:flex">'))
# only Claude on this VM: no Cursor / Codex / OpenCode tabs and pickers
edit("src/modules/settings/tabs/agents-settings/AgentsSettingsTab.tsx",
     ("    return ['claude', 'cursor', 'codex', 'opencode'];", "    return ['claude'];"))
edit("src/modules/chat/transcript/ProviderSelectionEmptyState.tsx",
     ('  { id: "codex", name: "OpenAI" },\n  { id: "cursor", name: "Cursor" },\n  { id: "opencode", name: "OpenCode" },\n', ""))
edit("src/modules/chat/modals/ModelLibraryPanel.tsx",
     ("  { id: 'codex', label: 'Codex' },\n  { id: 'cursor', label: 'Cursor' },\n  { id: 'opencode', label: 'OpenCode' },\n", ""))
edit("src/shared/selectedProvider.ts",
     ("const PROVIDERS: LLMProvider[] = ['claude', 'cursor', 'codex', 'opencode'];", "const PROVIDERS: LLMProvider[] = ['claude'];"))
# upstream: settings finish loading over several renders, so opening the dialog "saved" and said so
edit("src/modules/settings/hooks/useSettingsController.ts",
     ("  const isInitialLoadRef = useRef(true);\n",
      "  const isInitialLoadRef = useRef(true);\n  const openedAtRef = useRef(Date.now());\n"),
     ("      isInitialLoadRef.current = false;\n      return;\n    }\n",
      "      isInitialLoadRef.current = false;\n      return;\n    }\n"
      "    if (Date.now() - openedAtRef.current < 1500) {\n      return;\n    }\n"),
     ("      isInitialLoadRef.current = true;\n    }\n  }, [isOpen]);",
      "      isInitialLoadRef.current = true;\n      openedAtRef.current = Date.now();\n    }\n  }, [isOpen]);"))
# the first screen after signing in (no project picked yet): the same welcome as a new chat, not a bare folder icon
edit("src/modules/project-workspace/WorkspaceStateView.tsx",
     ("import { Folder } from 'lucide-react';\n", ""),
     ('            <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted/50">\n'
      '              <Folder className="h-7 w-7 text-muted-foreground" />\n'
      '            </div>\n'
      '            <h2 className="mb-2 text-xl font-semibold text-foreground">{t(\'mainContent.chooseProject\')}</h2>',
      '            <img src="/logo.svg" alt="" className="mx-auto mb-5 h-12 w-12 rounded-xl shadow-lg shadow-primary/30" />\n'
      '            <h2 className="mb-2 font-serif text-3xl tracking-tight text-foreground">\n'
      '              {(() => { const h = new Date().getHours(); return h < 5 ? "Working late" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"; })()}\n'
      '            </h2>'))
strings("common.json", mainContent__selectProjectDescription="Start a plain chat, or pick a project on the left to work in its folder (code, git, files).",
        mainContent__createProjectDesktop="the folder button at the top of the sidebar adds a project",
        mainContent__createProjectMobile="tap the menu button above to see your projects")
# no first-run git setup screen: it rewrote the VM's global git identity for everyone on the shared login
# (set it once in a terminal: git config --global user.name / user.email, with the GitLab email)
edit("server/modules/user/user.module.ts",
     ("    hasCompletedOnboarding: (userId) => userDb.hasCompletedOnboarding(userId),",
      "    hasCompletedOnboarding: () => true,"))
# plain chats without picking a folder: ~/chats is registered as the "Chats" project at start, and the welcome
# screen has a New chat button into it (projects stay for code work)
edit("server/index.ts",
     ("import { readFileSync } from 'fs';", "import { readFileSync, mkdirSync } from 'fs';\nimport { createProject } from './modules/projects/index.js';"),
     ("        server.listen(SERVER_PORT, HOST, async () => {\n",
      "        server.listen(SERVER_PORT, HOST, async () => {\n"
      "            try {\n"
      "                const chatsDir = path.join(os.homedir(), 'chats');\n"
      "                mkdirSync(chatsDir, { recursive: true });\n"
      "                await createProject({ projectPath: chatsDir, customName: 'Chats' });\n"
      "            } catch { /* already registered */ }\n"))
edit("src/modules/project-workspace/WorkspaceStateView.tsx",
     ("import MobileMenuButton from '@/modules/project-workspace/MobileMenuButton';",
      "import MobileMenuButton from '@/modules/project-workspace/MobileMenuButton';\n"
      "import { useProjectCommandState, useProjectSidebarState } from '@/modules/project-workspace/context/ProjectsStateContext';"),
     ("  const isLoading = mode === 'loading';\n",
      "  const isLoading = mode === 'loading';\n"
      "  const { handleNewSession } = useProjectCommandState();\n"
      "  const { sidebarSharedProps } = useProjectSidebarState();\n"
      "  const chats = (sidebarSharedProps?.projects || []).find((p) => /[\\/]chats$/.test(p.fullPath));\n"),
     ("            <p className=\"mb-5 text-sm leading-relaxed text-muted-foreground\">{t('mainContent.selectProjectDescription')}</p>\n",
      "            {chats && (\n"
      "              <button type=\"button\" onClick={() => handleNewSession(chats)} className=\"paas-newchat mb-4\">New chat</button>\n"
      "            )}\n"
      "            <p className=\"mb-5 text-sm leading-relaxed text-muted-foreground\">{t('mainContent.selectProjectDescription')}</p>\n"))
print(f"branded {SRC} as {NAME}")
