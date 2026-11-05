// Peleg As A Service: the composer's context counter never shows "0" because a model streamed its usage late.
// Run on a branded checkout (brand.py applied):
//   cp brain/ui/brand/tests/paas-context-budget.test.ts <checkout>/server/modules/providers/tests/
//   npx tsx --tsconfig server/tsconfig.json --test server/modules/providers/tests/paas-context-budget.test.ts
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { ClaudeSessionsProvider } from '@/modules/providers/list/claude/claude-sessions.provider.js';
import { CLAUDE_PREDEFINED_MODELS } from '@/modules/providers/list/claude/claude-models.provider.js';
import { queryClaudeSDK } from '@/modules/providers/list/claude/claude-runtime.provider.js';
import type { NormalizedMessage, ProviderRuntimeContext } from '@/shared/types.js';

type Emitted = Record<string, unknown>;

async function runScripted(appSessionId: string, stream: Emitted[]): Promise<NormalizedMessage[]> {
  const cwd = await mkdtemp(path.join(os.tmpdir(), 'paas-context-budget-'));
  const sent: NormalizedMessage[] = [];
  const writer = { send: (message: NormalizedMessage) => { sent.push(message); }, userId: null };
  const sessions = new ClaudeSessionsProvider({ getLiveRunStartTime: () => null });
  const context: ProviderRuntimeContext = {
    resolveProviderSessionId: () => null,
    resolveResumeModel: async () => undefined,
    getProviderModels: async () => CLAUDE_PREDEFINED_MODELS as never,
    normalizeMessage: (raw, sessionId) => sessions.normalizeMessage(raw, sessionId),
    isProviderInstalled: async () => true,
    createQuery: ({ prompt }) => {
      void (async () => { for await (const _message of prompt) { /* read */ } })();
      const iterator = (async function* () { yield* stream; })();
      return Object.assign(iterator, { interrupt: async () => {} }) as never;
    },
  };
  try {
    await queryClaudeSDK('hello', { sessionId: appSessionId, cwd }, writer as never, context);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
  return sent;
}

const budgets = (sent: NormalizedMessage[]) => sent
  .filter((m) => m.kind === 'status' && m.text === 'token_budget')
  .map((m) => m.tokenBudget as { used: number; total: number });

const zero = { input_tokens: 0, cache_read_input_tokens: 0, cache_creation_input_tokens: 0, output_tokens: 0 };
const real = { input_tokens: 12, cache_read_input_tokens: 40_000, cache_creation_input_tokens: 2_000, output_tokens: 500 };
const assistant = (id: string, usage: Emitted) => ({
  type: 'assistant', session_id: id, parent_tool_use_id: null,
  message: { role: 'assistant', model: 'glm-5.3-flash', content: [{ type: 'text', text: 'ok' }], usage },
});

test('assistant messages that stream all-zero usage (a model behind a proxy) never send a 0 reading', async () => {
  const id = 'native-glm';
  const sent = await runScripted('app-glm', [
    { type: 'system', subtype: 'init', session_id: id },
    assistant(id, zero),
    assistant(id, zero),
    { type: 'result', subtype: 'success', session_id: id, result: 'ok', duration_ms: 1, num_turns: 1, usage: real },
  ]);
  const b = budgets(sent);
  assert.ok(b.length > 0, 'a reading is sent');
  assert.ok(b.every((x) => x.used > 0), `no zero reading: ${JSON.stringify(b)}`);
  assert.equal(b.at(-1)!.used, 42_512, 'the turn result stands in for the missing per-message usage');
});

test('a normal stream still reports the last request, not the zero ones', async () => {
  const id = 'native-claude';
  const sent = await runScripted('app-claude', [
    { type: 'system', subtype: 'init', session_id: id },
    assistant(id, zero),
    assistant(id, real),
    { type: 'result', subtype: 'success', session_id: id, result: 'ok', duration_ms: 1, num_turns: 1, usage: real },
  ]);
  const b = budgets(sent);
  assert.deepEqual(b.map((x) => x.used), [42_512]);
});
