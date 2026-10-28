"""Chat fixes on top of the branding (run by brand.py with its edit()): follow the transcript while it streams,
thinking starts collapsed, "Send now" on a queued message, and Claude Code's own slash commands in the / menu."""

# --- auto-scroll: follow a message that grows in place (streamed text, tool output), not only new rows; and only
# a scroll UP stops following (a fast stream used to leave the view >50 px short, which counted as "scrolled up")
edit("src/modules/chat/hooks/useChatSessionState.ts",
     ("    const nearBottom = isNearBottom();\n    setIsUserScrolledUp(!nearBottom);\n",
      "    const nearBottom = isNearBottom();\n"
      "    if (nearBottom || container.scrollTop < scrollPositionRef.current.top - 1) setIsUserScrolledUp(!nearBottom);\n"),
     ("  const wasChatActiveRef = useRef(isActive);\n",
      "  const hasChatRows = chatMessages.length > 0;\n"
      "  useEffect(() => {\n"
      "    const container = scrollContainerRef.current;\n"
      "    if (!isActive || !container || typeof MutationObserver === 'undefined') return;\n"
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
      "    observer.observe(container, { childList: true, subtree: true, characterData: true });\n"
      "    return () => { observer.disconnect(); if (frame) cancelAnimationFrame(frame); };\n"
      "  }, [isActive, hasChatRows, scrollToBottom]);\n\n"
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
