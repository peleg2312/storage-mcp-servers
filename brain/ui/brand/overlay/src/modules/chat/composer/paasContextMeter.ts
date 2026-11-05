// Peleg As A Service: the session's context ("Claude's working memory for this chat") in words a person can act on.
// A token count alone means nothing to most people: this turns it into how full the memory is (a percent and a level),
// about how much text that is (pages), and what to do when it fills up.

export type ContextLevel = 'empty' | 'ok' | 'filling' | 'full' | 'unknown';

export type ContextMeter = {
  used: number;            // tokens the conversation holds now (what the last request carried)
  total: number;           // the model's window, 0 when not known
  percent: number | null;  // 0-100, null when the window is not known (or smaller than what is used)
  level: ContextLevel;
  pages: number;           // about how many pages of text the used tokens are
  headline: string;        // "34% full", "Almost full", ...
  advice: string;          // one sentence: what it means and what to do
};

// ~650 tokens is about one printed page (~500 English words; Hebrew takes more tokens per word, so fewer pages)
const TOKENS_PER_PAGE = 650;

const num = (v: unknown) => {
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? n : 0;
};

export function readContextMeter(usage: Record<string, unknown> | null | undefined): ContextMeter {
  const breakdown = usage?.breakdown && typeof usage.breakdown === 'object' ? (usage.breakdown as Record<string, unknown>) : null;
  const input = num(usage?.inputTokens ?? breakdown?.input);
  const output = num(usage?.outputTokens ?? breakdown?.output);
  const used = num(usage?.used) || input + output;
  const total = num(usage?.total ?? usage?.contextWindow);
  const percent = total > 0 && used <= total ? Math.min(100, Math.round((used / total) * 100)) : null;
  const pages = Math.max(used > 0 ? 1 : 0, Math.round(used / TOKENS_PER_PAGE));

  if (!used) {
    return { used, total, percent: total ? 0 : null, level: 'empty', pages: 0, headline: 'Empty',
      advice: 'Nothing in this chat yet. It fills as you talk, read files and run tools.' };
  }
  if (percent === null) {
    return { used, total, percent, level: 'unknown', pages, headline: `${formatTokens(used)} used`,
      advice: `About ${pages} page${pages === 1 ? '' : 's'} of text in Claude's memory for this chat.` };
  }
  if (percent < 50) {
    return { used, total, percent, level: 'ok', pages, headline: `${percent}% full`,
      advice: 'Plenty of room. Keep going.' };
  }
  if (percent < 80) {
    return { used, total, percent, level: 'filling', pages, headline: `${percent}% full`,
      advice: 'Getting full. For a new topic, start a new chat: answers stay sharper and faster.' };
  }
  return { used, total, percent, level: 'full', pages, headline: `${percent}% full`,
    advice: 'Almost full. Claude will soon summarize the older part of this chat by itself and may lose details. '
      + 'Type /compact to do it now, or start a new chat (notes and reports are kept).' };
}

export function formatTokens(value: number) {
  if (!Number.isFinite(value) || value <= 0) return '0';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value >= 10_000_000 ? 0 : 1)}M`;
  if (value >= 10_000) return `${Math.round(value / 1_000)}K`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return Math.round(value).toLocaleString();
}

// Tailwind classes per level: the ring / bar colour and the text colour
export const LEVEL_STYLE: Record<ContextLevel, { bar: string; text: string; stroke: string }> = {
  empty: { bar: 'bg-muted-foreground/30', text: 'text-muted-foreground', stroke: 'stroke-muted-foreground/40' },
  ok: { bar: 'bg-emerald-500', text: 'text-emerald-600 dark:text-emerald-400', stroke: 'stroke-emerald-500' },
  filling: { bar: 'bg-amber-500', text: 'text-amber-600 dark:text-amber-400', stroke: 'stroke-amber-500' },
  full: { bar: 'bg-red-500', text: 'text-red-600 dark:text-red-400', stroke: 'stroke-red-500' },
  unknown: { bar: 'bg-primary', text: 'text-foreground', stroke: 'stroke-primary' },
};
