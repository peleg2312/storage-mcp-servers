// Peleg As A Service (replaces upstream's TokenUsageSummary): the composer's context button shows how full Claude's
// working memory for this chat is - a ring that fills and turns amber / red, "Memory 34%" - instead of a bare token
// count; the tooltip says what it means and what to do. A click opens the details (/cost).
import { memo } from 'react';
import { formatTokens, LEVEL_STYLE, readContextMeter } from '@/modules/chat/composer/paasContextMeter';

type TokenUsageSummaryProps = {
  usage: Record<string, unknown> | null;
  onClick?: () => void;
};

function Ring({ percent, stroke }: { percent: number; stroke: string }) {
  const r = 7;
  const c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 18 18" className="h-[18px] w-[18px] -rotate-90" aria-hidden="true">
      <circle cx="9" cy="9" r={r} fill="none" strokeWidth="2.5" className="stroke-muted-foreground/20" />
      <circle cx="9" cy="9" r={r} fill="none" strokeWidth="2.5" strokeLinecap="round" className={stroke}
        strokeDasharray={`${(Math.max(percent, 3) / 100) * c} ${c}`} />
    </svg>
  );
}

function TokenUsageSummary({ usage, onClick }: TokenUsageSummaryProps) {
  const m = readContextMeter(usage);
  const style = LEVEL_STYLE[m.level];
  const detail = m.used
    ? `${formatTokens(m.used)} tokens${m.total ? ` of ${formatTokens(m.total)}` : ''} (about ${m.pages} page${m.pages === 1 ? '' : 's'} of text)`
    : '';
  const title = `Claude's memory for this chat: ${m.headline}. ${m.advice}${detail ? `\n${detail}` : ''}\nClick for details.`;

  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border/70 bg-background/70 px-2 text-xs text-muted-foreground shadow-sm transition-colors hover:border-primary/25 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:gap-2 sm:px-2.5"
      title={title}
      aria-label={`Chat memory ${m.headline}. Show details`}
    >
      <Ring percent={m.percent ?? (m.used ? 100 : 0)} stroke={style.stroke} />
      <span className="hidden text-muted-foreground/80 sm:inline">Memory</span>
      <span className={`font-medium ${m.level === 'empty' ? 'text-muted-foreground' : style.text}`}>
        {m.level === 'empty' ? 'empty' : m.percent !== null ? `${m.percent}%` : formatTokens(m.used)}
      </span>
    </button>
  );
}

/** Memoized: the composer re-renders on every keystroke and this row only moves when a turn ends. */
export default memo(TokenUsageSummary);
