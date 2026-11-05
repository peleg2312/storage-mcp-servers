// Peleg As A Service: the details behind the composer's "Memory" button (the /cost modal), in plain words - how full
// Claude's memory for this chat is, what fills it, and what to do about it. Replaces upstream's token table.
import type { CostCommandData } from '@/shared/types';
import { formatTokens, LEVEL_STYLE, readContextMeter } from '@/modules/chat/composer/paasContextMeter';

const pagesOf = (tokens: number) => Math.max(tokens > 0 ? 1 : 0, Math.round(tokens / 650));
const plural = (n: number, w: string) => `${n.toLocaleString()} ${w}${n === 1 ? '' : 's'}`;

export default function PaasContextCard({ data, providerLabel }: { data: CostCommandData; providerLabel?: string }) {
  const input = Number(data.tokenBreakdown?.input ?? 0) || 0;
  const output = Number(data.tokenBreakdown?.output ?? 0) || 0;
  const m = readContextMeter({ used: data.tokenUsage?.used, total: data.tokenUsage?.total, inputTokens: input, outputTokens: output });
  const style = LEVEL_STYLE[m.level];
  const rows = [
    { label: 'What Claude read', hint: 'your messages, files, tool results, rules and notes', tokens: input },
    { label: 'What Claude wrote', hint: 'its answers and the commands it ran', tokens: output },
  ].filter((r) => r.tokens > 0);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border/70 bg-background/75 p-5">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-sm font-medium text-muted-foreground">Claude&apos;s memory for this chat</p>
          <p className={`text-2xl font-semibold ${style.text}`}>{m.headline}</p>
        </div>
        {m.percent !== null && (
          <div className="mt-3 h-3 w-full overflow-hidden rounded-full bg-muted">
            <div className={`h-full rounded-full ${style.bar} transition-all`} style={{ width: `${Math.max(m.percent, 2)}%` }} />
          </div>
        )}
        <p className="mt-3 text-sm text-foreground">{m.advice}</p>
        {m.used > 0 && (
          <p className="mt-1 text-xs text-muted-foreground">
            {formatTokens(m.used)} tokens{m.total ? ` of ${formatTokens(m.total)}` : ''}, about {plural(m.pages, 'page')} of text
          </p>
        )}
      </div>

      {rows.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-border/70 bg-background/75">
          {rows.map((r) => (
            <div key={r.label} className="flex items-center justify-between gap-4 border-b border-border/60 px-4 py-3 last:border-b-0">
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground">{r.label}</p>
                <p className="text-xs text-muted-foreground">{r.hint}</p>
              </div>
              <p className="shrink-0 text-sm text-foreground">
                ~{plural(pagesOf(r.tokens), 'page')} <span className="text-xs text-muted-foreground">({formatTokens(r.tokens)} tokens)</span>
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-2xl border border-border/70 bg-muted/20 p-4">
        <p className="text-sm font-medium text-foreground">When it fills up</p>
        <ul className="mt-2 space-y-1.5 text-sm text-muted-foreground">
          <li><span className="font-mono text-foreground">/compact</span>: Claude summarizes this chat and keeps going with more room.</li>
          <li><span className="font-medium text-foreground">New chat</span>: starts empty. Your notes, reports and the team&apos;s knowledge stay.</li>
          <li>Ask for summaries and filtered results instead of whole logs or long lists: they fill it fastest.</li>
        </ul>
        <p className="mt-3 text-xs text-muted-foreground">
          A token is a piece of a word (an English word is about 1.3 tokens, a Hebrew word 2-3). Model: {data.model || 'unknown'}
          {providerLabel ? ` (${providerLabel})` : ''}.
        </p>
      </div>
    </div>
  );
}
