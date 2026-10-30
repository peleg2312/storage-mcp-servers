import { useEffect, useState } from 'react';

const EVENT = 'paas-notice';

/** Shows a short status line above the composer (no pop-up). Call from anywhere: paasNotice('...'). */
export function paasNotice(text: string): void {
  window.dispatchEvent(new CustomEvent(EVENT, { detail: text }));
}

/** The status line itself, mounted once in the composer: read out politely by screen readers, gone after 8 s. */
export default function PaasNotice() {
  const [text, setText] = useState('');
  useEffect(() => {
    let timer: number | undefined;
    const show = (event: Event) => {
      setText(String((event as CustomEvent).detail || ''));
      window.clearTimeout(timer);
      timer = window.setTimeout(() => setText(''), 8000);
    };
    window.addEventListener(EVENT, show);
    return () => { window.removeEventListener(EVENT, show); window.clearTimeout(timer); };
  }, []);
  return (
    <div role="status" aria-live="polite" className={text ? 'mx-auto mb-2 max-w-[54.25rem] rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground' : 'sr-only'}>
      {text}
    </div>
  );
}
