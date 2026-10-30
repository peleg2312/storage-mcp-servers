"""Chat fixes on top of the branding (run by brand.py with its edit()): follow the transcript while it streams,
thinking starts collapsed, "Send now" on a queued message, and Claude Code's own slash commands in the / menu."""

# --- auto-scroll: follow a message that grows in place (streamed text, tool output), not only new rows; and only the
# person scrolling (wheel, touch, keys, scrollbar) stops following: a fast stream or a re-render that moved the view
# used to count as "scrolled up" and the chat stopped following
edit("src/modules/chat/hooks/useChatSessionState.ts",
     ("    const nearBottom = isNearBottom();\n    setIsUserScrolledUp(!nearBottom);\n",
      "    const nearBottom = isNearBottom();\n"
      "    if (nearBottom || Date.now() - userScrollAtRef.current < 1000) setIsUserScrolledUp(!nearBottom);\n"),
     ("  const handleScroll = useCallback(async () => {\n",
      "  const userScrollAtRef = useRef(0);\n  const handleScroll = useCallback(async () => {\n"),
     ("  const wasChatActiveRef = useRef(isActive);\n",
      "  useEffect(() => {\n"
      "    if (!isActive || typeof MutationObserver === 'undefined') return;\n"
      "    let el: HTMLDivElement | null = null;\n"
      "    let frame = 0;\n"
      "    const follow = () => {\n"
      "      if (frame) return;\n"
      "      frame = requestAnimationFrame(() => {\n"
      "        frame = 0;\n"
      "        if (!isUserScrolledUpRef.current && !pendingScrollRestoreRef.current && !searchScrollActiveRef.current\n"
      "            && !isLoadingMoreRef.current) scrollToBottom();\n"
      "      });\n"
      "    };\n"
      "    const observer = new MutationObserver(follow);\n"
      "    const intent = () => { userScrollAtRef.current = Date.now(); };\n"
      "    const kinds = ['wheel', 'touchmove', 'mousedown', 'keydown'];\n"
      "    const attach = () => {\n"   # the pane is mounted again after a reload / session load: follow the live one
      "      const c = scrollContainerRef.current;\n"
      "      if (c === el) return;\n"
      "      observer.disconnect();\n"
      "      if (el) kinds.forEach((k) => el?.removeEventListener(k, intent));\n"
      "      el = c;\n"
      "      if (!el) return;\n"
      "      observer.observe(el, { childList: true, subtree: true, characterData: true });\n"
      "      kinds.forEach((k) => el?.addEventListener(k, intent, { passive: true }));\n"
      "      follow();\n"
      "    };\n"
      "    attach();\n"
      "    const timer = setInterval(attach, 500);\n"
      "    return () => {\n"
      "      clearInterval(timer);\n"
      "      observer.disconnect();\n"
      "      if (el) kinds.forEach((k) => el?.removeEventListener(k, intent));\n"
      "      if (frame) cancelAnimationFrame(frame);\n"
      "    };\n"
      "  }, [isActive, scrollToBottom]);\n\n"
      "  const wasChatActiveRef = useRef(isActive);\n"))

# --- thinking: collapsed ("Thought for 4s"), one click to read it
edit("src/modules/chat/transcript/MessageComponent.tsx",
     ("<Reasoning defaultOpen>", "<Reasoning defaultOpen={false}>"),
     ('<Reasoning className="mb-3" defaultOpen>', '<Reasoning className="mb-3" defaultOpen={false}>'))

# --- queued message: "Send now" stops the running turn and sends it at once
edit("src/modules/chat/hooks/useChatComposerState.ts",
     ("  const handleGrantToolPermission = useCallback(",
      "  // The message leaves the server's queue at once (its dispatcher must not send it as well), is held here until the\n"
      "  // answer has stopped, then sent. If the answer does not stop within 10 s the text goes back into the box.\n"
      "  const sendNowRef = useRef<QueuedDraft | null>(null);\n"
      "  const sendNowTimerRef = useRef<number | null>(null);\n"
      "  const sendQueuedDraftNow = useCallback(() => {\n"
      "    if (!queuedDraft) return;\n"
      "    if (queuedDraftSessionRef.current) clearQueuedMessage(queuedDraftSessionRef.current);\n"
      "    sendNowRef.current = queuedDraft;\n"
      "    setQueuedDraft(null);\n"
      "    if (sendNowTimerRef.current) window.clearTimeout(sendNowTimerRef.current);\n"
      "    sendNowTimerRef.current = window.setTimeout(() => {\n"
      "      const draft = sendNowRef.current;\n"
      "      sendNowRef.current = null;\n"
      "      if (!draft) return;\n"
      "      setInput(draft.content);\n"
      "      inputValueRef.current = draft.content;\n"
      "      setAttachedFiles(draft.attachments);\n"
      "      paasNotice('Could not stop the answer. Your message is back in the box: send it again when ready.');\n"
      "    }, 10000);\n"
      "    handleAbortSession();\n"
      "  }, [handleAbortSession, queuedDraft]);\n"
      "  useEffect(() => {\n"
      "    if (isLoading || !sendNowRef.current) return;\n"
      "    const draft = sendNowRef.current;\n"
      "    sendNowRef.current = null;\n"
      "    if (sendNowTimerRef.current) window.clearTimeout(sendNowTimerRef.current);\n"
      "    void handleSubmitRef.current?.(createFakeSubmitEvent(), draft);\n"
      "  }, [isLoading, queuedDraft]);\n\n"
      "  const handleGrantToolPermission = useCallback("),
     ("import { useSlashCommands } from '@/modules/chat/hooks/useSlashCommands';",
      "import { useSlashCommands } from '@/modules/chat/hooks/useSlashCommands';\n"
      "import { paasNotice } from '@/modules/chat/composer/PaasNotice';"),
     ("    deleteQueuedDraft,\n", "    deleteQueuedDraft,\n    sendQueuedDraftNow,\n"))
edit("src/modules/chat/ChatInterface.tsx",
     ("    deleteQueuedDraft,\n", "    deleteQueuedDraft,\n    sendQueuedDraftNow,\n"),
     ("          onDeleteQueuedDraft={deleteQueuedDraft}",
      "          onDeleteQueuedDraft={deleteQueuedDraft}\n          onSendQueuedDraftNow={sendQueuedDraftNow}"))
edit("src/modules/chat/composer/ChatComposer.tsx",
     ("  onDeleteQueuedDraft: () => void;", "  onDeleteQueuedDraft: () => void;\n  onSendQueuedDraftNow: () => void;"),
     ("  onDeleteQueuedDraft,\n", "  onDeleteQueuedDraft,\n  onSendQueuedDraftNow,\n"),
     ("          onDelete={onDeleteQueuedDraft}", "          onDelete={onDeleteQueuedDraft}\n          onSendNow={onSendQueuedDraftNow}"),
     ("import CommandMenu from '@/modules/chat/composer/CommandMenu';",
      "import CommandMenu from '@/modules/chat/composer/CommandMenu';\nimport PaasNotice from '@/modules/chat/composer/PaasNotice';"),
     ("        <CommandMenu\n          commands={filteredCommands}", "        <PaasNotice />\n\n        <CommandMenu\n          commands={filteredCommands}"))
edit("src/modules/chat/composer/QueuedMessageCard.tsx",
     ("  onDelete: () => void;\n};", "  onDelete: () => void;\n  onSendNow?: () => void;\n};"),
     ("  onDelete,\n}: QueuedMessageCardProps)", "  onDelete,\n  onSendNow,\n}: QueuedMessageCardProps)"),
     ("        <div className=\"flex shrink-0 items-center gap-0.5\">\n",
      "        <div className=\"flex shrink-0 items-center gap-0.5\">\n"
      "          {onSendNow && (\n"
      "            <button\n"
      "              type=\"button\"\n"
      "              onClick={onSendNow}\n"
      "              title=\"Stop the running answer and send this message now\"\n"
      "              aria-label=\"Stop the running answer and send this message now\"\n"
      "              className=\"mr-2 min-h-[36px] rounded-md bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-primary/20 md:min-h-0\"\n"
      "            >\n"
      "              Stop and send\n"
      "            </button>\n"
      "          )}\n"))

# --- slash commands: everything Claude Code offers in that folder (/compact, /context, /init, /review, plugin
# commands ...), asked from a CLI started without a prompt (no turn, no transcript), cached per folder for 1 hour; no MCP servers are started for it.
# They go to Claude as typed (type 'skill': inserted by the menu, sent as the message), like in the terminal.
edit("server/modules/commands/commands.routes.ts",
     ('import express from "express";\n',
      'import express from "express";\n'
      'import { query as claudeQuery } from "@anthropic-ai/claude-agent-sdk";\n\n'
      'import { resolveClaudeCodeExecutablePath } from "../../shared/claude-cli-path.js";\n'),
     ("/**\n * Built-in commands that are always available\n */",
      "const claudeCommandCache = new Map();\n"
      "// The list is asked for in the background: a request answers at once with what is known ('loading' while the\n"
      "// Claude Code CLI starts, 'error' for a minute after a failure) so the built-in and custom commands never wait.\n"
      "const FRESH_CHAT = /^(clear|new|reset)$/;\n"
      "function claudeCliCommands(cwd, refresh = false) {\n"
      "  const hit = claudeCommandCache.get(cwd);\n"
      "  if (hit && !refresh && Date.now() - hit.at < (hit.failed ? 60_000 : 3_600_000)) return hit;\n"
      "  const entry = { at: Date.now(), done: null, failed: false };\n"
      "  claudeCommandCache.set(cwd, entry);\n"
      "  void (async () => {\n"
      "    const idle = { async *[Symbol.asyncIterator]() { await new Promise(() => {}); } };\n"
      "    const q = claudeQuery({ prompt: idle, options: { cwd, env: { ...globalThis.process.env }, strictMcpConfig: true, mcpServers: {},\n"
      "      pathToClaudeCodeExecutable: resolveClaudeCodeExecutablePath(globalThis.process.env.CLAUDE_CLI_PATH) } });\n"
      "    try {\n"
      "      const cmds = await Promise.race([q.supportedCommands(),\n"
      "        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 20_000))]);\n"
      "      // /clear, /new and /reset all start a fresh chat here (the web UI handles them): one entry, in plain words\n"
      "      const fresh = cmds.filter((c) => FRESH_CHAT.test(c.name));\n"
      "      const keep = (fresh.find((c) => c.name === 'new') || fresh[0])?.name;\n"
      "      entry.done = cmds.filter((c) => /^[\\w:.-]+$/.test(c.name) && (!FRESH_CHAT.test(c.name) || c.name === keep)).map((c) => ({\n"
      "        name: `/${c.name}`,\n"
      "        description: FRESH_CHAT.test(c.name) ? 'Start a fresh chat (the current one is kept in the sidebar)'\n"
      "          : [c.description, c.argumentHint].filter(Boolean).join(' '),\n"
      "        namespace: 'claude', type: 'skill', metadata: { type: 'claude', argumentHint: c.argumentHint } }));\n"
      "    } catch (error) {\n"
      "      console.error('Claude Code commands:', error.message);\n"
      "      entry.failed = true;\n"
      "    } finally {\n"
      "      q.close();\n"
      "    }\n"
      "  })();\n"
      "  return entry;\n"
      "}\n\n"
      "/**\n * Built-in commands that are always available\n */"),
     ("    const { projectPath } = req.body;\n    const allCommands = [...builtInCommands];\n",
      "    const { projectPath, refresh } = req.body;\n    const allCommands = [...builtInCommands];\n"),
     ("      builtIn: builtInCommands,\n      custom: customCommands,\n",
      "      builtIn: builtInCommands,\n      custom: customCommands,\n"
      "      ...(() => {\n"
      "        const entry = projectPath ? claudeCliCommands(projectPath, refresh === true) : null;\n"
      "        return { claude: entry?.done || [], claudeStatus: !entry || entry.done ? 'ready' : entry.failed ? 'error' : 'loading' };\n"
      "      })(),\n"))
edit("src/shared/api.ts",
     ("    list: (projectPath: string | undefined) => post('/api/commands/list', { projectPath }),",
      "    list: (projectPath: string | undefined, refresh?: boolean) => post('/api/commands/list', { projectPath, refresh }),"))
edit("src/shared/hooks/useProjectSlashCommands.ts",
     ("        const allCommands: SlashCommand[] = [\n"
      "          ...((data.builtIn || []) as SlashCommand[]).map((command) => ({\n"
      "            ...command,\n"
      "            type: 'built-in',\n"
      "          })),\n",
      "        const known = new Set([...(data.builtIn || []), ...skillCommands, ...(data.custom || [])]\n"
      "          .map((command: SlashCommand) => command.name));\n"
      "        const allCommands: SlashCommand[] = [\n"
      "          ...((data.builtIn || []) as SlashCommand[]).map((command) => ({\n"
      "            ...command,\n"
      "            type: 'built-in',\n"
      "          })),\n"
      "          ...((data.claude || []) as SlashCommand[]).filter((command) => !known.has(command.name)),\n"))
# Claude Code's own commands load in the background (the server answers at once with 'loading'): ask again every 1.5 s
# (at most 8 times) and tell the menu how it stands, so it shows "Loading..." / "unavailable" + Retry, not an empty gap.
edit("src/shared/hooks/useProjectSlashCommands.ts",
     ("    let cancelled = false;\n\n    const fetchCommands = async () => {\n",
      "    let cancelled = false;\n    let pollTimer: number | undefined;\n    let polls = 0;\n\n    const fetchCommands = async (refresh = false) => {\n"),
     ("        const response = await api.commands.list(workspacePath || selectedProject.path);",
      "        const response = await api.commands.list(workspacePath || selectedProject.path, refresh);"),
     ("        if (!cancelled) {\n          setCommands(allCommands);\n          setIsLoading(false);\n        }",
      "        if (!cancelled) {\n          setCommands(allCommands);\n          setIsLoading(false);\n"
      "          const claudeStatus = data.claudeStatus || 'ready';\n"
      "          window.dispatchEvent(new CustomEvent('paas-claude-commands', { detail: claudeStatus }));\n"
      "          window.clearTimeout(pollTimer);\n"
      "          if (claudeStatus === 'loading' && polls++ < 8) pollTimer = window.setTimeout(() => void fetchCommands(), 1500);\n"
      "        }"),
     ("    fetchCommands();\n    return () => {\n      cancelled = true;\n    };",
      "    const retry = () => { polls = 0; window.dispatchEvent(new CustomEvent('paas-claude-commands', { detail: 'loading' })); void fetchCommands(true); };\n"
      "    window.addEventListener('paas-claude-retry', retry);\n"
      "    fetchCommands();\n    return () => {\n      cancelled = true;\n      window.clearTimeout(pollTimer);\n      window.removeEventListener('paas-claude-retry', retry);\n    };"))
edit("src/modules/chat/composer/CommandMenu.tsx",
     ("import { useEffect, useRef } from 'react';\n", "import { useEffect, useRef, useState } from 'react';\n"),
     ("  const menuPosition = getMenuPosition(position);\n",
      "  const menuPosition = getMenuPosition(position);\n"
      "  const [claudeStatus, setClaudeStatus] = useState('ready');\n"
      "  useEffect(() => {\n"
      "    const onStatus = (event: Event) => setClaudeStatus(String((event as CustomEvent).detail || 'ready'));\n"
      "    window.addEventListener('paas-claude-commands', onStatus);\n"
      "    return () => window.removeEventListener('paas-claude-commands', onStatus);\n"
      "  }, []);\n"),
     ("      ))}\n    </div>\n  );\n}",
      "      ))}\n"
      "      {claudeStatus === 'loading' && (\n"
      "        <div aria-live=\"polite\" className=\"px-2.5 py-2 text-[12px] text-muted-foreground\">Loading Claude Code commands…</div>\n"
      "      )}\n"
      "      {claudeStatus === 'error' && (\n"
      "        <div className=\"flex items-center justify-between gap-2 px-2.5 py-2 text-[12px] text-muted-foreground\">\n"
      "          <span>Claude Code commands unavailable</span>\n"
      "          <button type=\"button\" className=\"min-h-[32px] rounded-md border border-border px-2.5 text-foreground hover:bg-accent\"\n"
      "            onMouseDown={(event) => event.preventDefault()}\n"
      "            onClick={() => window.dispatchEvent(new CustomEvent('paas-claude-retry'))}>Retry</button>\n"
      "        </div>\n"
      "      )}\n"
      "    </div>\n  );\n}"))
edit("src/modules/chat/composer/CommandMenu.tsx",
     ("  builtin: 'Built-in Commands',\n", "  builtin: 'Built-in Commands',\n  claude: 'Claude Code',\n"),
     ("  builtin: Terminal,\n", "  builtin: Terminal,\n  claude: Terminal,\n"),
     ("  builtin: 'border-sky-200", "  claude: 'border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-400/20 dark:bg-violet-400/10 dark:text-violet-200',\n  builtin: 'border-sky-200"),
     ("    ? ['frequent', 'builtin', 'skill', 'project', 'user', 'other']\n    : ['builtin', 'skill', 'project', 'user', 'other'];",
      "    ? ['frequent', 'builtin', 'claude', 'skill', 'project', 'user', 'other']\n    : ['builtin', 'claude', 'skill', 'project', 'user', 'other'];"))

# --- a queued message goes about 2 s after its turn ends, not on the next 30 s poll (scheduled messages keep 30 s)
edit("server/modules/scheduled-messages/services/scheduled-message-dispatcher.service.ts",
     ("let dispatchInFlight = false;\n",
      "let dispatchInFlight = false;\nlet queuedTimer: ReturnType<typeof setInterval> | null = null;\n"),
     ("  pollTimer = setInterval(poll, POLL_INTERVAL_MS);\n",
      "  pollTimer = setInterval(poll, POLL_INTERVAL_MS);\n"
      "  queuedTimer = setInterval(() => {\n"
      "    if (dispatchInFlight) return;\n"
      "    dispatchInFlight = true;\n"
      "    void dispatchQueuedMessages(runtime)\n"
      "      .catch((error: unknown) => console.error('[QueuedMessages] Dispatch failed', { error: String(error) }))\n"
      "      .finally(() => { dispatchInFlight = false; });\n"
      "  }, 2_000);\n"
      "  queuedTimer.unref?.();\n"),
     ("export function closeScheduledMessageDispatcher(): void {\n",
      "export function closeScheduledMessageDispatcher(): void {\n"
      "  if (queuedTimer) {\n    clearInterval(queuedTimer);\n    queuedTimer = null;\n  }\n"))

# --- live text: the reply appears as Claude writes it (SDK partial messages), not only when a whole block is done.
# The client already buffers stream_delta / stream_end and swaps in the final text; subagents' text stays out, and the
# pieces stay in a run's replay buffer only until their block ends (a page reloaded mid-reply gets the whole block;
# afterwards the final text stands in for them), so a long turn cannot push real events out of it.
edit("server/modules/providers/list/claude/claude-runtime.provider.js",
     ("  sdkOptions.tools = { type: 'preset', preset: 'claude_code' };\n",
      "  sdkOptions.tools = { type: 'preset', preset: 'claude_code' };\n  sdkOptions.includePartialMessages = true;\n"),
     ("      // Transform and normalize message via adapter\n      const transformedMessage = transformMessage(message);",
      "      if (message.type === 'stream_event') {\n"
      "        const ev = message.event || {};\n"
      "        const liveSid = capturedSessionId || sessionId || null;\n"
      "        if (message.parent_tool_use_id) continue;\n"
      "        if (ev.type === 'content_block_delta' && ev.delta?.type === 'text_delta' && ev.delta.text) {\n"
      "          ws.send(createNormalizedMessage({ kind: 'stream_delta', content: ev.delta.text, sessionId: liveSid, provider: 'claude' }));\n"
      "        } else if (ev.type === 'content_block_stop') {\n"
      "          ws.send(createNormalizedMessage({ kind: 'stream_end', sessionId: liveSid, provider: 'claude' }));\n"
      "        }\n"
      "        continue;\n"
      "      }\n\n"
      "      // Transform and normalize message via adapter\n      const transformedMessage = transformMessage(message);"))
edit("server/modules/websocket/services/chat-run-registry.service.ts",
     ("  run.events.push(outbound);\n",
      "  if (message.kind === 'stream_end') run.events = run.events.filter((event) => event.kind !== 'stream_delta');\n"
      "  run.events.push(outbound);\n"))

# --- Browser tab: /preview/<port>/... and /preview/~/... (overlay server/modules/paas/preview.routes.ts), mounted before
# the body parsers so form posts reach the app untouched; signing in (any API call) also sets the preview cookie
edit("server/index.ts",
     ("import { paasRoutes } from './modules/paas/download.routes.js';",
      "import { paasRoutes } from './modules/paas/download.routes.js';\nimport { paasPreview } from './modules/paas/preview.routes.js';"),
     ("app.use(express.json({", "app.use('/preview', paasPreview);\napp.use(express.json({"))
edit("server/modules/auth/auth.middleware.ts",
     ("import { userDb, appConfigDb } from '../database/index.js';",
      "import { userDb, appConfigDb } from '../database/index.js';\nimport { previewCookie } from '../paas/preview.routes.js';"),
     ("    req.user = user;\n    next();\n  } catch (error) {",
      "    req.user = user;\n    previewCookie(req, res, user.id);\n    next();\n  } catch (error) {"))

# plugin tabs in a fixed order (a folder listing on the VM's disk has none): by name, Help always the last tab
edit("src/modules/project-workspace/WorkspaceTabs.tsx",
     ("  const pluginTabs: PluginTab[] = plugins\n    .filter((p) => p.enabled)\n",
      "  const pluginTabs: PluginTab[] = plugins\n    .filter((p) => p.enabled)\n"
      "    .sort((a, b) => Number(a.name === 'paas-help') - Number(b.name === 'paas-help') || a.name.localeCompare(b.name))\n"))

# a chat busy in a terminal: count from when this reply started (statusUpdatedAt, set when it turned busy), not from
# when that claude process started days ago ("Running in the Claude CLI… 9093m")
edit("server/modules/providers/services/claude-cli-liveness.service.ts",
     ("  const startedAt = typeof record.startedAt === 'number' ? record.startedAt : Date.now();",
      "  const startedAt = typeof record.statusUpdatedAt === 'number' ? record.statusUpdatedAt\n"
      "    : typeof record.startedAt === 'number' ? record.startedAt : Date.now();"))

# /clear, /new, /reset: a fresh chat in the same project, like the New chat button (sent to Claude, /clear made a new
# session holding only the text "/clear"). The chat it leaves stays in the sidebar (nothing is deleted behind the
# user's back) and a status line says so.
edit("src/modules/project-workspace/context/ProjectsStateContext.tsx",
     ("export function useProjectCommandState(): ProjectCommandState {",
      "/** The same as useProjectCommandState, or null outside the workspace (the chat composer in tests). */\n"
      "export function useOptionalProjectCommandState(): ProjectCommandState | null {\n"
      "  return useContext(ProjectCommandContext);\n}\n\n"
      "export function useProjectCommandState(): ProjectCommandState {"))
edit("src/modules/chat/hooks/useChatComposerState.ts",
     ("import { useSlashCommands } from '@/modules/chat/hooks/useSlashCommands';",
      "import { useSlashCommands } from '@/modules/chat/hooks/useSlashCommands';\n"
      "import { useOptionalProjectCommandState } from '@/modules/project-workspace/context/ProjectsStateContext';"),
     ("}: UseChatComposerStateArgs) {\n  const { t } = useTranslation('chat');\n",
      "}: UseChatComposerStateArgs) {\n  const { t } = useTranslation('chat');\n  const paasProjectCommands = useOptionalProjectCommandState();\n"
      "  // /clear, /new, /reset: a fresh chat in the same project; the chat it leaves stays in the sidebar\n"
      "  const paasNewChat = (project: Project) => {\n"
      "    setTimeout(() => {   // after this submit settles\n"
      "      paasProjectCommands?.handleNewSession(project);\n"
      "      setTimeout(() => paasNotice('Started a new chat. The previous one is still in the sidebar.'), 300);\n"
      "    }, 0);\n"
      "  };\n"),
     ("      if (!command || !selectedProject) {\n        return;\n      }\n\n      try {\n        const effectiveInput = rawInput ?? input;\n",
      "      if (!command || !selectedProject) {\n        return;\n      }\n"
      "      if (/^\\/(clear|new|reset)$/.test(command.name) && paasProjectCommands) {   // picked from the / menu\n"
      "        paasNewChat(selectedProject);\n"
      "        setInput('');\n"
      "        inputValueRef.current = '';\n"
      "        return;\n"
      "      }\n\n      try {\n        const effectiveInput = rawInput ?? input;\n"),
     ("        const matchedCommand =\n          slashCommands.find((cmd: SlashCommand) => cmd.name === commandName) ||",
      "        if (/^\\/(clear|new|reset)$/.test(commandName) && paasProjectCommands && selectedProject) {\n"
      "          paasNewChat(selectedProject);\n"
      "          setInput('');\n"
      "          inputValueRef.current = '';\n"
      "          resetCommandMenuState();\n"
      "          return;\n"
      "        }\n"
      "        const matchedCommand =\n          slashCommands.find((cmd: SlashCommand) => cmd.name === commandName) ||"))

# images in MCP tool results (Chrome DevTools screenshots): the 40 000-character cap cut the base64 mid-string, so the
# result stopped parsing and the chat showed raw JSON. Keep the text and up to 4 images of up to 1.5 MB each whole (a
# larger one becomes a note), and draw them under the text.
edit("server/shared/message-unification.ts",
     ("function capToolResult(message: NormalizedMessage): void {",
      "const MAX_KEPT_IMAGES = 4;\n"
      "const MAX_IMAGE_DATA = 1_500_000;\n\n"
      "/** An MCP result (text and image blocks) with its images kept whole and its text capped; null for anything else. */\n"
      "function capMcpBlocks(value: unknown): unknown[] | null {\n"
      "  let blocks: unknown = value;\n"
      "  if (typeof value === 'string') {\n"
      "    if (!value.startsWith('[') || !value.includes('\"image\"')) return null;\n"
      "    try { blocks = JSON.parse(value); } catch { return null; }\n"
      "  }\n"
      "  if (!Array.isArray(blocks) || !blocks.some((b) => readObjectRecord(b)?.type === 'image')) return null;\n"
      "  let kept = 0;\n"
      "  return blocks.map((b) => {\n"
      "    const block = readObjectRecord(b);\n"
      "    if (block?.type === 'text' && typeof block.text === 'string') return { type: 'text', text: truncateOutput(block.text) };\n"
      "    const data = readObjectRecord(block?.source)?.data ?? block?.data;\n"
      "    if (block?.type === 'image' && typeof data === 'string' && data.length <= MAX_IMAGE_DATA && kept < MAX_KEPT_IMAGES) {\n"
      "      kept += 1;\n"
      "      return block;\n"
      "    }\n"
      "    return { type: 'text', text: '[image left out: too large]' };\n"
      "  });\n"
      "}\n\n"
      "function capToolResult(message: NormalizedMessage): void {"),
     ("  if (typeof result.content === 'string') {\n    result.content = truncateOutput(result.content);\n  }\n",
      "  const mcpBlocks = capMcpBlocks(result.content);\n"
      "  if (mcpBlocks) {\n"
      "    result.content = JSON.stringify(mcpBlocks);\n"
      "  } else if (typeof result.content === 'string') {\n    result.content = truncateOutput(result.content);\n  }\n"))
edit("src/modules/chat/tools/configs/toolConfigs.ts",
     ("        return {\n          content: String(content),\n          format: 'plain'\n        };\n      }\n    }\n  }\n};",
      "        // images an MCP tool returned (Chrome DevTools screenshots): drawn under the text\n"
      "        const raw = result?.content;\n"
      "        let blocks: any = raw;\n"
      "        if (typeof raw === 'string' && raw.startsWith('[')) { try { blocks = JSON.parse(raw); } catch { blocks = null; } }\n"
      "        const images = Array.isArray(blocks)\n"
      "          ? blocks.filter((p: any) => p?.type === 'image' && (p.source?.data || p.data))\n"
      "              .map((p: any) => `data:${p.source?.media_type || p.mimeType || 'image/png'};base64,${p.source?.data || p.data}`)\n"
      "          : [];\n"
      "        return {\n          content: images.length ? String(content).replace(/^\\[Image: source: [^\\]]*\\]\\s*$/gm, '').trim() : String(content),\n"
      "          format: 'plain',\n          images\n        };\n      }\n    }\n  }\n};"))
edit("src/modules/chat/tools/ToolRenderer.tsx",
     ("          <TextContent\n            content={contentProps.content || ''}\n            format={contentProps.format || 'plain'}\n          />",
      "          <TextContent\n            content={contentProps.content || ''}\n            format={contentProps.format || 'plain'}\n            images={contentProps.images}\n          />"))
edit("src/modules/chat/tools/ContentRenderers/TextContent.tsx",
     ("  format?: 'plain' | 'json' | 'code';\n  className?: string;\n};",
      "  format?: 'plain' | 'json' | 'code';\n  className?: string;\n  images?: string[];\n};"),
     ("  format = 'plain',\n  className = ''\n}) => {",
      "  format = 'plain',\n  className = '',\n  images = []\n}) => {\n"
      "  if (images.length && format === 'plain') {\n"
      "    return (\n"
      "      <div className={`mt-1 space-y-2 ${className}`}>\n"
      "        {content && <div className=\"whitespace-pre-wrap text-sm text-foreground\">{content}</div>}\n"
      "        {images.map((src, i) => (\n"
      "          <a key={i} href={src} target=\"_blank\" rel=\"noreferrer\" title=\"Open full size\"\n"
      "            className=\"block min-h-[120px] animate-pulse rounded-lg bg-muted\" style={{ aspectRatio: '16/10' }}>\n"
      "            <img src={src} alt={`Screenshot ${i + 1} of ${images.length} from the tool`} loading=\"lazy\"\n"
      "              onLoad={(event) => { const box = event.currentTarget.parentElement; if (box) { box.style.aspectRatio = ''; box.classList.remove('animate-pulse', 'bg-muted', 'min-h-[120px]'); } }}\n"
      "              className=\"max-h-[480px] max-w-full rounded-lg border border-border object-contain\" />\n"
      "          </a>\n"
      "        ))}\n"
      "      </div>\n"
      "    );\n"
      "  }\n"))

# --- "Report ready": card under a finished reply that names a file, a notification when the tab is hidden, a 'new' dot
# on the Reports tab, and the notification switch in quick settings (overlay paasReportReady.ts)
edit("src/modules/chat/transcript/MessageComponent.tsx",
     ("import { MemoryCitations } from '@/modules/chat/transcript/MemoryCitations';\n",
      "import { MemoryCitations } from '@/modules/chat/transcript/MemoryCitations';\n"
      "import { PaasReportReady } from '@/modules/chat/transcript/paasReportReady';\n"),
     ("            {/* Outside the branches on purpose: a provider can cite memory on a\n",
      "            {message.type === 'assistant' && !message.isToolUse && !message.isThinking && !isExporting && (\n"
      "              <PaasReportReady content={formattedMessageContent} isStreaming={Boolean(message.isStreaming)} />\n"
      "            )}\n\n"
      "            {/* Outside the branches on purpose: a provider can cite memory on a\n"))
edit("src/modules/project-workspace/WorkspaceTabs.tsx",
     ("import { usePlugins,PluginIcon } from '@/modules/plugins';\n",
      "import { usePlugins,PluginIcon } from '@/modules/plugins';\nimport { PaasNewDot } from '@/modules/chat/transcript/paasReportReady';\n"),
     ("                  {displayLabel}\n                </span>\n              </Pill>",
      "                  {displayLabel}\n                </span>\n                <PaasNewDot tabId={tab.id} active={isActive} />\n              </Pill>"))
edit("src/modules/quick-settings-panel/QuickSettingsContent.tsx",
     ("import QuickSettingsSection from '@/modules/quick-settings-panel/QuickSettingsSection';\n",
      "import QuickSettingsSection from '@/modules/quick-settings-panel/QuickSettingsSection';\nimport { PaasNotifySwitch } from '@/modules/chat/transcript/paasReportReady';\n"),
     ("      <QuickSettingsSection title={t('quickSettings.sections.inputSettings')}>\n",
      "      <PaasNotifySwitch />\n\n      <QuickSettingsSection title={t('quickSettings.sections.inputSettings')}>\n"))
