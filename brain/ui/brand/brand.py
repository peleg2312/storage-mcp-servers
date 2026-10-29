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
# the read-only guard's "ask" (cluster changes, database writes) must reach the user, except in bypass (the user
# approved every change on the server; the guard's blocks on storage stay): the allowed-tools shortcut must not
# answer it. Auto and bypass run as themselves; only root's bypass is emulated in canUseTool (Claude Code refuses
# bypass as root, and the guard then sees "default" and asks, so the emulation answers that too)
P = "server/modules/providers/list/claude/claude-runtime.provider.js"
edit(P,
     ("function mapCliOptionsToSDK(options = {}) {",
      "// root's sessions in bypass mode: emulated in canUseTool (Claude Code refuses bypass as root)\n"
      "const PAAS_BYPASS = new WeakSet();\n\nfunction mapCliOptionsToSDK(options = {}) {"),
     ("  if (settings.skipPermissions && permissionMode !== 'plan') {\n    sdkOptions.permissionMode = 'bypassPermissions';\n  }\n",
      "  if (settings.skipPermissions && permissionMode !== 'plan') {\n    sdkOptions.permissionMode = 'bypassPermissions';\n  }\n"
      "  if (sdkOptions.permissionMode === 'bypassPermissions' && process.getuid?.() === 0) {\n"
      "    PAAS_BYPASS.add(sdkOptions);\n    sdkOptions.permissionMode = 'default';\n"
      "  } else if (sdkOptions.permissionMode === 'bypassPermissions') {\n"
      "    sdkOptions.allowDangerouslySkipPermissions = true;\n  }\n"),
     ("      const requiresInteraction = TOOLS_REQUIRING_INTERACTION.has(toolName);\n\n"
      "      if (!requiresInteraction) {\n"
      "        if (sdkOptions.permissionMode === 'bypassPermissions') {",
      "      const guardAsk = /^Read-only guard:/.test(String(context?.decisionReason || ''));\n"
      "      const bypass = PAAS_BYPASS.has(sdkOptions) || sdkOptions.permissionMode === 'bypassPermissions';\n"
      "      const requiresInteraction = TOOLS_REQUIRING_INTERACTION.has(toolName) || (guardAsk && !bypass);\n\n"
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
# the app opens straight into a new chat (like Claude desktop), so the header with Brain / Usage is always there;
# the sidebar "+" starts a new chat, the folder button next to it creates a project
edit("src/modules/project-workspace/WorkspaceStateView.tsx",
     ("import { useTranslation } from 'react-i18next';", "import { useEffect } from 'react';\nimport { useTranslation } from 'react-i18next';"),
     ("  const chats = (sidebarSharedProps?.projects || []).find((p) => /[\\/]chats$/.test(p.fullPath));\n",
      "  const chats = (sidebarSharedProps?.projects || []).find((p) => /[\\/]chats$/.test(p.fullPath));\n"
      "  useEffect(() => {\n"
      "    if (!isLoading && chats && window.location.pathname === '/') handleNewSession(chats);\n"
      "  }, [isLoading, chats, handleNewSession]);\n"))
for rel in ("src/modules/sidebar/SidebarContent.tsx", "src/modules/sidebar/SidebarHeader.tsx"):
    edit(rel, ("  onCreateProject: () => void;\n", "  onCreateProject: () => void;\n  onNewChat: () => void;\n"),
         ("  onCreateProject,\n", "  onCreateProject,\n  onNewChat,\n"))
edit("src/modules/sidebar/SidebarContent.tsx",
     ("        onCreateProject={onCreateProject}\n", "        onCreateProject={onCreateProject}\n        onNewChat={onNewChat}\n"))
edit("src/modules/sidebar/Sidebar.tsx",
     ("            onCreateProject={() => setShowNewProject(true)}\n",
      "            onCreateProject={() => setShowNewProject(true)}\n"
      "            onNewChat={() => {\n"
      "              const chats = projects.find((p) => /[\\/]chats$/.test(p.fullPath));\n"
      "              if (chats) onNewSession(chats); else { pendingChat.current = true; void refreshProjects(); }\n"
      "            }}\n"))
edit("src/modules/sidebar/SidebarHeader.tsx",
     ("              onClick={onCreateProject}\n              title={t('tooltips.createProject')}\n            >\n              <Plus className=\"h-3.5 w-3.5\" />\n",
      "              onClick={onCreateProject}\n              title={t('tooltips.createProject')}\n            >\n              <FolderPlus className=\"h-3.5 w-3.5\" />\n"
      "            </Button>\n"
      "            <Button\n"
      "              variant=\"ghost\"\n"
      "              size=\"sm\"\n"
      "              className=\"h-7 w-7 rounded-lg p-0 text-muted-foreground hover:bg-accent/80 hover:text-foreground\"\n"
      "              onClick={onNewChat}\n"
      "              title=\"New chat\"\n"
      "            >\n"
      "              <Plus className=\"h-3.5 w-3.5\" />\n"),
     ("              onClick={onCreateProject}\n            >\n              <FolderPlus className=\"h-4 w-4\" />\n            </button>\n",
      "              onClick={onNewChat}\n              title=\"New chat\"\n            >\n              <Plus className=\"h-4 w-4\" />\n            </button>\n"))
# simpler, offline-only UI: no settings for things the air-gapped VM cannot use (OpenAI voice, TaskMaster, browser
# automation, plugin installs from GitHub, web push, API tokens), no GitHub star badge / update check, a quieter
# new-chat screen and composer (model and mode stay in the composer)
edit("src/modules/settings/SettingsSidebar.tsx", *[(f"  {{ id: '{i}', labelKey: 'mainTabs.{k}', icon: {c} }},\n", "") for i, k, c in (
    ("api", "apiTokens", "Key"), ("voice", "voice", "Mic"), ("tasks", "tasks", "ListChecks"),
    ("browser", "browser", "MonitorPlay"), ("plugins", "plugins", "Puzzle"), ("notifications", "notifications", "Bell"))])
edit("src/modules/sidebar/SidebarHeader.tsx", ("        <GitHubStarBadge />\n", ""))
edit("src/shared/hooks/useVersionCheck.ts",
     ("    const checkVersion = async () => {\n      try {\n",
      "    const checkVersion = async () => {\n      return; // offline: no GitHub release check\n      try {\n"))
edit("src/modules/chat/transcript/ProviderSelectionEmptyState.tsx",
     ("className=\"group mx-auto max-w-xs cursor-pointer", "className=\"hidden group mx-auto max-w-xs cursor-pointer"),
     ("<p className=\"mt-4 text-center text-sm text-muted-foreground/70\">", "<p className=\"hidden\">"),
     ("<p className=\"mt-3 flex items-center justify-center gap-1.5 text-center text-xs text-muted-foreground/60\">", "<p className=\"hidden\">"))
edit("src/modules/chat/composer/ChatComposer.tsx",
     ("            <TokenUsageSummary usage={tokenBudget} onClick={onShowTokenUsage} />\n", ""),
     ("            <ScheduleMessagePopover\n              disabled={!input.trim()}\n              onSchedule={onScheduleMessage}\n            />\n", ""))
# projects can clone from the GitLab server; the GitHub token card is gone
edit("src/modules/project-creation-wizard/StepConfiguration.tsx",
     ("  const showGithubAuth = shouldShowGithubAuthentication(githubUrl);", "  const showGithubAuth = false && shouldShowGithubAuthentication(githubUrl);"),
     ("placeholder=\"https://github.com/username/repository\"", "placeholder=\"https://gitlab.example.local/group/repository.git\""))
strings("common.json", projectWizard__step2__githubUrl="Git URL (optional)",
        projectWizard__step2__githubHelp="Optional: a GitLab repository URL to clone into the workspace")
strings("settings.json", mainTabs__agents="Claude")
# Claude's reasoning is shown (summaries), not only a "Thinking" spinner: the API omits it unless asked
edit("server/modules/providers/list/claude/claude-runtime.provider.js",
     ("  sdkOptions.systemPrompt = {\n    type: 'preset',\n",
      "  // ponytail: Haiku has no adaptive thinking; other non-adaptive models would need { type: 'enabled' } here\n"
      "  if (!/haiku/i.test(sdkOptions.model)) sdkOptions.thinking = { type: 'adaptive', display: 'summarized' };\n\n"
      "  sdkOptions.systemPrompt = {\n    type: 'preset',\n"))
# fonts shipped with the app (the VM has no Google Fonts): Inter for UI and replies, Source Serif for headings
edit("index.html",
     ("    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />\n    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />\n"
      "    <link\n      href=\"https://fonts.googleapis.com/css2?family=Encode+Sans:wght@400;500;600;700&family=Merriweather:ital,wght@0,400;0,700;1,400;1,700&display=swap\"\n      rel=\"stylesheet\"\n    />\n",
      "    <link rel=\"preload\" href=\"/fonts/inter.woff2\" as=\"font\" type=\"font/woff2\" crossorigin />\n"))
edit("tailwind.config.js",
     ("sans: ['\"Encode Sans\"', ", "sans: ['Inter', "),
     ("serif: ['Merriweather', ", "serif: ['\"Source Serif\"', "))
edit("src/index.css", ('font-family: "Encode Sans", ', 'font-family: Inter, '))
edit("src/modules/chat/transcript/MessageComponent.tsx",
     ("max-w-none font-serif", "max-w-none paas-msg"), ("break-words font-serif text-sm", "break-words paas-msg"))
# the sidebar opens on the recent-conversations list (like Claude desktop); Projects is the second tab
edit("src/modules/sidebar/hooks/useSidebarController.ts",
     ("useState<SidebarSearchMode>('projects')", "useState<SidebarSearchMode>('conversations')"))
edit("src/modules/sidebar/SidebarModeTabs.tsx",
     ("    { mode: 'projects', label: t('search.modeProjects'), icon: Folder, showLabel: true },\n"
      "    { mode: 'conversations', label: t('search.modeConversations'), icon: MessageSquare, showLabel: true },\n",
      "    { mode: 'conversations', label: t('search.modeConversations'), icon: MessageSquare, showLabel: true },\n"
      "    { mode: 'projects', label: t('search.modeProjects'), icon: Folder, showLabel: true },\n"))
# Claude's reasoning is shown open above each reply (it can still be collapsed)
edit("src/modules/chat/transcript/MessageComponent.tsx",
     ('<Reasoning className="mb-3" defaultOpen={false}>', '<Reasoning className="mb-3" defaultOpen>'),
     ("<Reasoning defaultOpen={isExporting}>", "<Reasoning defaultOpen>"))
# no pulsing "active" dot on sessions merely updated in the last 10 minutes: it read as "running" when nothing ran
# (the dot stays for real background work and for sessions that need an answer)
edit("src/modules/sidebar/SidebarSessionItem.tsx",
     ("const showRecentIndicator = !showAttentionIndicator && !showBackgroundIndicator && !isProcessing && sessionView.isActive;",
      "const showRecentIndicator = false;"))
# offline VM: no "Pro" / hosted-service cards (the dead links themselves are hidden in paas.css)
edit("src/modules/settings/tabs/AboutTab.tsx", ("{!IS_PLATFORM && (", "{false && ("))
edit("src/modules/settings/PremiumFeatureCard.tsx",
     ("  const { t } = useTranslation('settings');\n  const resolvedCta", "  return null;\n  const { t } = useTranslation('settings');\n  const resolvedCta"))
edit("src/modules/mcp/McpServers.tsx",
     ("function TeamMcpFeatureCard() {\n", "function TeamMcpFeatureCard() {\n  return null;\n"))
# plain chats (~/chats) have no project to browse: only Chat and the brain's tabs there; projects keep all of them
edit("src/modules/project-workspace/WorkspaceHeader.tsx",
     ("                shouldShowBrowserTab={shouldShowBrowserTab}\n              />",
      "                shouldShowBrowserTab={shouldShowBrowserTab}\n                isChats={/[\\/]chats$/.test(selectedProject.fullPath)}\n              />"))
edit("src/modules/project-workspace/WorkspaceTabs.tsx",
     ("  shouldShowBrowserTab: boolean;\n};", "  shouldShowBrowserTab: boolean;\n  isChats?: boolean;\n};"),
     ("  shouldShowBrowserTab,\n}: WorkspaceTabsProps) {", "  shouldShowBrowserTab,\n  isChats,\n}: WorkspaceTabsProps) {"),
     ("    ...BASE_TABS,\n", "    ...(isChats ? BASE_TABS.slice(0, 1) : BASE_TABS),\n"))
# Conversations list: reloaded whenever the projects / sessions change (upstream loaded it only on opening the tab,
# so a new chat did not appear); the refresh button in the sidebar header reloads it too
edit("src/modules/sidebar/hooks/useSidebarController.ts",
     ("    reloadRecentConversations();\n  }, [debouncedSearchQuery, reloadRecentConversations, searchMode]);",
      "    reloadRecentConversations();\n  }, [debouncedSearchQuery, reloadRecentConversations, searchMode, projects]);"))
# Projects tab, calmer: Chats is listed under Conversations only; the star shows on hover (or when starred) and starred
# rows are not tinted yellow; the second line is "<n> sessions · ~/path"; a quiet "New chat" row instead of a big button
edit("src/modules/sidebar/SidebarProjectList.tsx",
     ("          : filteredProjects.map((project) => {", "          : filteredProjects.filter((p) => !/[\\/]chats$/.test(p.fullPath)).map((project) => {"))
edit("src/modules/sidebar/SidebarProjectItem.tsx",
     ("                  : 'opacity-40 hover:opacity-100 hover:bg-accent',", "                  : 'opacity-0 group-hover:opacity-50 hover:!opacity-100 hover:bg-accent',"),
     ("            isStarred &&\n              !isSelected &&\n              'bg-yellow-50/50 dark:bg-yellow-900/10 hover:bg-yellow-100/50 dark:hover:bg-yellow-900/20',\n", ""),
     ("                  <div className=\"text-xs text-muted-foreground\">\n                    {sessionCountDisplay}\n                    {project.fullPath !== project.displayName && (\n"
      "                      <span className=\"ml-1 opacity-60\" title={project.fullPath}>\n                        {' - '}\n"
      "                        {project.fullPath.length > 25 ? `...${project.fullPath.slice(-22)}` : project.fullPath}\n",
      "                  <div className=\"truncate text-xs text-muted-foreground\">\n                    {sessionCountDisplay}\n                    {project.fullPath !== project.displayName && (\n"
      "                      <span className=\"opacity-70\" title={project.fullPath}>\n                        {' · '}\n"
      "                        {project.fullPath.replace(/^\\/(home|Users)\\/[^/]+|^\\/root/, '~')}\n"))
edit("src/modules/sidebar/SidebarProjectSessions.tsx",
     ("        <Button\n          variant=\"default\"\n          size=\"sm\"\n          className=\"flex h-8 w-full justify-start gap-2 bg-primary text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90\"\n"
      "          onClick={() => onNewSession(project)}\n        >\n          <Plus className=\"h-3 w-3\" />\n          {t('sessions.newSession')}\n",
      "        <Button\n          variant=\"ghost\"\n          size=\"sm\"\n          className=\"flex h-8 w-full justify-start gap-2 text-xs font-medium text-muted-foreground hover:bg-accent/60 hover:text-foreground\"\n"
      "          onClick={() => onNewSession(project)}\n        >\n          <Plus className=\"h-3 w-3\" />\n          New chat\n"))
# no "Select" (bulk delete) row under each project: one less control; sessions are deleted from their own menu
edit("src/modules/sidebar/SidebarProjectSessions.tsx",
     ("{(isSelecting || (initialSessionsLoaded && selectableSessionIds.length > 0)) && (", "{isSelecting && ("))
# plugin servers listen on 127.0.0.1: on a VM shared by several Linux users they only answer this UI, which sends
# a key made at start (other users' processes cannot read it); our plugins refuse requests without it
edit("server/modules/plugins/plugin-process.service.ts",
     ("const runningPlugins = new Map();", "process.env.PAAS_PLUGIN_KEY ||= globalThis.crypto.randomUUID();\nconst runningPlugins = new Map();"),
     ("    PLUGIN_NAME: name,\n", "    PLUGIN_NAME: name,\n    PAAS_PLUGIN_KEY: process.env.PAAS_PLUGIN_KEY,\n"))
edit("server/modules/plugins/plugins.routes.ts",
     ("        'content-type': String(req.headers['content-type'] ?? 'application/json'),\n      };",
      "        'content-type': String(req.headers['content-type'] ?? 'application/json'),\n        'x-paas-key': String(process.env.PAAS_PLUGIN_KEY || ''),\n      };"))
# "+" pressed before the project list loaded: wait for the Chats space (never fall back to "new project", which asks
# for a folder)
edit("src/modules/sidebar/Sidebar.tsx",
     ("import { memo, useCallback, useEffect } from 'react';", "import { memo, useCallback, useEffect, useRef } from 'react';"),
     ("  const { t } = useTranslation(['sidebar', 'common']);\n",
      "  const { t } = useTranslation(['sidebar', 'common']);\n"
      "  const pendingChat = useRef(false);\n"
      "  useEffect(() => {\n"
      "    const chats = projects.find((p) => /[\\/]chats$/.test(p.fullPath));\n"
      "    if (pendingChat.current && chats) { pendingChat.current = false; onNewSession(chats); }\n"
      "  }, [projects, onNewSession]);\n"))
# the plugin tabs (Brain, Marketplace, Reports, ...) were fetched once at page load, before signing in, and stayed empty
# until a reload: fetch them again when the signed-in user changes
edit("src/modules/plugins/context/PluginsContext.tsx",
     ("import { api, readApiErrorMessage } from '@/shared/api';", "import { api, readApiErrorMessage } from '@/shared/api';\nimport { useAuth } from '@/modules/auth';"),
     ("  useEffect(() => {\n    void refreshPlugins();\n  }, [refreshPlugins]);",
      "  const { user } = useAuth();\n  useEffect(() => {\n    if (user) void refreshPlugins();\n  }, [refreshPlugins, user]);"))
# Sign out (with who is signed in) under Settings: ends the gate session too (multi-user VM), then the sign-in page
edit("src/modules/sidebar/SidebarFooter.tsx",
     ("import { Settings, ArrowUpCircle, Bug, AlertTriangle } from 'lucide-react';",
      "import { Settings, ArrowUpCircle, Bug, AlertTriangle, LogOut } from 'lucide-react';\nimport { useAuth } from '@/modules/auth';"),
     ("}: SidebarFooterProps) {\n  return (\n",
      "}: SidebarFooterProps) {\n"
      "  const { user, logout } = useAuth();\n"
      "  const signOut = async () => {\n"
      "    const token = localStorage.getItem('auth-token');\n"
      "    await fetch('/api/auth/logout', { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {} }).catch(() => undefined);\n"
      "    logout();\n"
      "    window.location.href = '/';\n"
      "  };\n"
      "  const signOutRow = (\n"
      "    <button className=\"flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground\" onClick={signOut}>\n"
      "      <LogOut className=\"h-3.5 w-3.5\" />\n"
      "      <span className=\"text-sm\">Sign out</span>\n"
      "      {user?.username && <span className=\"ml-auto truncate text-xs text-muted-foreground/70\">{user.username}</span>}\n"
      "    </button>\n"
      "  );\n"
      "  return (\n"),
     ("      {/* Desktop version brand line (OSS mode only) */}",
      "      <div className=\"hidden px-2 pb-1.5 md:block\">{signOutRow}</div>\n\n      {/* Desktop version brand line (OSS mode only) */}"),
     ("          <span className=\"text-sm font-normal text-foreground\">{t('actions.settings')}</span>\n        </button>\n      </div>\n    </div>\n  );\n}",
      "          <span className=\"text-sm font-normal text-foreground\">{t('actions.settings')}</span>\n        </button>\n      </div>\n      <div className=\"px-3 pb-3 md:hidden\">{signOutRow}</div>\n    </div>\n  );\n}"))
# root's own home is a normal place for its chats and projects (upstream refused every path under /root, so root's
# Chats space was never registered: no tab bar, and "+" had nowhere to go); other users cannot write there anyway
edit("server/shared/utils.ts", ("  '/boot',\n  '/root',\n  '/lib',", "  '/boot',\n  '/lib',"))
exec(open(os.path.join(HERE, "chat.py"), encoding="utf-8").read())    # chat fixes, same edit()
print(f"branded {SRC} as {NAME}")
