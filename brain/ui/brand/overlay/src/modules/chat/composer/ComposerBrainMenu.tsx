import { memo, useCallback, useState, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { Brain, MessageCircle } from 'lucide-react';

import { useComposerMenuAnchor } from '@/modules/chat/hooks/useComposerMenuAnchor';
import { ComposerMenuHeading, ComposerMenuItem, ComposerMenuSurface } from '@/modules/chat/composer/ComposerMenuPrimitives';

/**
 * Brain on / off, a chip next to the model in the message box. On (default): the storage brain, its tools, library
 * and notes. Off: a plain chat for simple questions, no tools, no library, ~35k fewer tokens and no MCP start-up.
 * The server reads `brain` from the message options (claude-runtime.provider: plain prompt, no tools, no MCP).
 * Remembered in the browser; a plain session can be switched back on at any message.
 */
const KEY = 'paas-brain';
const EVENT = 'paas-brain';

const read = (): boolean => { try { return localStorage.getItem(KEY) !== 'off'; } catch { return true; } };

/** The current setting, read at send time. */
export function brainOn(): boolean { return read(); }

export function setBrain(on: boolean): void {
  try { localStorage.setItem(KEY, on ? 'on' : 'off'); } catch { /* storage may be blocked */ }
  window.dispatchEvent(new Event(EVENT));
}

const subscribe = (cb: () => void) => {
  window.addEventListener(EVENT, cb);
  window.addEventListener('storage', cb);
  return () => { window.removeEventListener(EVENT, cb); window.removeEventListener('storage', cb); };
};

export function useBrain(): boolean { return useSyncExternalStore(subscribe, read, () => true); }

const ON = {
  icon: Brain,
  label: 'Brain',
  trigger: 'border-border/60 bg-muted/50 text-muted-foreground hover:bg-muted',
  title: 'Brain on: storage tools, docs library and notes. Click to switch to a plain chat.',
};
const OFF = {
  icon: MessageCircle,
  label: 'Plain chat',
  trigger: 'border-amber-300/60 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-600/40 dark:bg-amber-900/15 dark:text-amber-300 dark:hover:bg-amber-900/25',
  title: 'Brain off: a plain chat, no tools or library. Click to switch the brain on.',
};

function ComposerBrainMenu() {
  const on = useBrain();
  const [isOpen, setIsOpen] = useState(false);
  const close = useCallback(() => setIsOpen(false), []);
  const { triggerRef, menuRef, anchor, updateAnchor } = useComposerMenuAnchor(isOpen, close, 22 * 16);
  const active = on ? ON : OFF;
  const Icon = active.icon;
  const heading = 'What should the next message use?';
  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => { updateAnchor(); setIsOpen((current) => !current); }}
        className={`flex h-8 shrink-0 items-center justify-center gap-1.5 rounded-lg border px-2 text-xs font-medium transition-colors ${active.trigger}`}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={`${active.label}: ${heading}`}
        title={active.title}
      >
        <Icon className="h-4 w-4 shrink-0" />
        <span className="hidden sm:inline">{active.label}</span>
      </button>
      {isOpen && anchor && createPortal(
        <ComposerMenuSurface anchor={anchor} menuRef={menuRef} ariaLabel={heading}>
          <ComposerMenuHeading>{heading}</ComposerMenuHeading>
          <ComposerMenuItem
            icon={<Brain className="h-4 w-4" />}
            label="Brain on"
            description="Storage tools, the docs library, notes and skills. Slower to start, answers from your systems."
            isSelected={on}
            onSelect={() => { setBrain(true); setIsOpen(false); }}
          />
          <ComposerMenuItem
            icon={<MessageCircle className="h-4 w-4" />}
            label="Plain chat"
            description="No tools, no library: quick answers to general questions. Storage and vendor questions are sent back to the brain."
            isSelected={!on}
            onSelect={() => { setBrain(false); setIsOpen(false); }}
            className="text-amber-700 dark:text-amber-300"
          />
        </ComposerMenuSurface>,
        document.body,
      )}
    </>
  );
}

export default memo(ComposerBrainMenu);
