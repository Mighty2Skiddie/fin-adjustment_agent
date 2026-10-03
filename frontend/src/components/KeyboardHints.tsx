import { Fragment } from 'react'
import { cn } from '@/lib/utils'

export interface KeyboardHint {
  /** Keys pressed together or as alternatives, e.g. ["j", "k"]. */
  keys: string[]
  label: string
}

export function Kbd({ children }: { children: string }) {
  return (
    <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded-sm border border-rule bg-surface px-1 font-mono text-xs leading-none text-ink shadow-[0_1px_0_var(--rule)]">
      {children}
    </kbd>
  )
}

/** A quiet line of shortcuts, e.g. "j / k move · Enter expand · a approve · r reject". */
export function KeyboardHints({ hints, className }: { hints: KeyboardHint[]; className?: string }) {
  return (
    <p
      className={cn('flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted', className)}
    >
      <span className="sr-only">Keyboard shortcuts:</span>
      {hints.map((h) => (
        <span key={h.label} className="inline-flex items-center gap-1">
          {h.keys.map((k, i) => (
            <Fragment key={k}>
              {i > 0 ? <span aria-hidden>/</span> : null}
              <Kbd>{k}</Kbd>
            </Fragment>
          ))}
          <span className="ml-0.5">{h.label}</span>
        </span>
      ))}
    </p>
  )
}
