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
      "  const sendNowRef = useRef<QueuedDraft | null>(null);\n"
      "  const sendQueuedDraftNow = useCallback(() => {\n"
      "    if (!queuedDraft) return;\n"
      "    if (queuedDraftSessionRef.current) clearQueuedMessage(queuedDraftSessionRef.current);\n"
      "    sendNowRef.current = queuedDraft;\n"
      "    setQueuedDraft(null);\n"
      "    handleAbortSession();\n"
      "  }, [handleAbortSession, queuedDraft]);\n"
      "  useEffect(() => {\n"
      "    if (isLoading || !sendNowRef.current) return;\n"
      "    const draft = sendNowRef.current;\n"
      "    sendNowRef.current = null;\n"
      "    void handleSubmitRef.current?.(createFakeSubmitEvent(), draft);\n"
      "  }, [isLoading, queuedDraft]);\n\n"
      "  const handleGrantToolPermission = useCallback("),
     ("    deleteQueuedDraft,\n", "    deleteQueuedDraft,\n    sendQueuedDraftNow,\n"))
edit("src/modules/chat/ChatInterface.tsx",
     ("    deleteQueuedDraft,\n", "    deleteQueuedDraft,\n    sendQueuedDraftNow,\n"),
     ("          onDeleteQueuedDraft={deleteQueuedDraft}",
      "          onDeleteQueuedDraft={deleteQueuedDraft}\n          onSendQueuedDraftNow={sendQueuedDraftNow}"))
edit("src/modules/chat/composer/ChatComposer.tsx",
     ("  onDeleteQueuedDraft: () => void;", "  onDeleteQueuedDraft: () => void;\n  onSendQueuedDraftNow: () => void;"),
     ("  onDeleteQueuedDraft,\n", "  onDeleteQueuedDraft,\n  onSendQueuedDraftNow,\n"),
     ("          onDelete={onDeleteQueuedDraft}", "          onDelete={onDeleteQueuedDraft}\n          onSendNow={onSendQueuedDraftNow}"))
edit("src/modules/chat/composer/QueuedMessageCard.tsx",
     ("  onDelete: () => void;\n};", "  onDelete: () => void;\n  onSendNow?: () => void;\n};"),
     ("  onDelete,\n}: QueuedMessageCardProps)", "  onDelete,\n  onSendNow,\n}: QueuedMessageCardProps)"),
     ("        <div className=\"flex shrink-0 items-center gap-0.5\">\n",
      "        <div className=\"flex shrink-0 items-center gap-0.5\">\n"
      "          {onSendNow && (\n"
      "            <button\n"
      "              type=\"button\"\n"
      "              onClick={onSendNow}\n"
      "              title=\"Stop the running turn and send this now\"\n"
      "              className=\"mr-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/20\"\n"
      "            >\n"
      "              Send now\n"
      "            </button>\n"
      "          )}\n"))

# --- slash commands: everything Claude Code offers in that folder (/compact, /context, /init, /review, plugin
# commands ...), asked from a CLI started without a prompt (no turn, no transcript), cached per folder for 5 minutes.
# They go to Claude as typed (type 'skill': inserted by the menu, sent as the message), like in the terminal.
edit("server/modules/commands/commands.routes.ts",
     ('import express from "express";\n',
      'import express from "express";\n'
      'import { query as claudeQuery } from "@anthropic-ai/claude-agent-sdk";\n\n'
      'import { resolveClaudeCodeExecutablePath } from "../../shared/claude-cli-path.js";\n'),
     ("/**\n * Built-in commands that are always available\n */",
      "const claudeCommandCache = new Map();\n"
      "function claudeCliCommands(cwd) {\n"
      "  const hit = claudeCommandCache.get(cwd);\n"
      "  if (hit && Date.now() - hit.at < 300_000) return hit.list;\n"
      "  const list = (async () => {\n"
      "    const idle = { async *[Symbol.asyncIterator]() { await new Promise(() => {}); } };\n"
      "    const q = claudeQuery({ prompt: idle, options: { cwd, env: { ...globalThis.process.env },\n"
      "      pathToClaudeCodeExecutable: resolveClaudeCodeExecutablePath(globalThis.process.env.CLAUDE_CLI_PATH) } });\n"
      "    try {\n"
      "      const cmds = await Promise.race([q.supportedCommands(),\n"
      "        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 20_000))]);\n"
      "      return cmds.filter((c) => /^[\\w:.-]+$/.test(c.name)).map((c) => ({\n"
      "        name: `/${c.name}`, description: [c.description, c.argumentHint].filter(Boolean).join(' '),\n"
      "        namespace: 'claude', type: 'skill', metadata: { type: 'claude', argumentHint: c.argumentHint } }));\n"
      "    } catch (error) {\n"
      "      console.error('Claude Code commands:', error.message);\n"
      "      claudeCommandCache.delete(cwd);\n"
      "      return [];\n"
      "    } finally {\n"
      "      q.close();\n"
      "    }\n"
      "  })();\n"
      "  claudeCommandCache.set(cwd, { at: Date.now(), list });\n"
      "  return list;\n"
      "}\n\n"
      "/**\n * Built-in commands that are always available\n */"),
     ("      builtIn: builtInCommands,\n      custom: customCommands,\n",
      "      builtIn: builtInCommands,\n      custom: customCommands,\n"
      "      claude: projectPath ? await claudeCliCommands(projectPath) : [],\n"))
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
