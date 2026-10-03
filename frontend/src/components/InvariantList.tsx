import { CircleCheck, OctagonX } from 'lucide-react'
import { invariantLabel } from '@/lib/status'
import { cn } from '@/lib/utils'

/** Green / red ticks for run or ledger invariants. Pass/fail is spelled out, not only coloured. */
export function InvariantList({
  invariants,
  className,
}: {
  invariants: Record<string, boolean>
  className?: string
}) {
  return (
    <ul className={cn('flex flex-col gap-1.5', className)}>
      {Object.entries(invariants).map(([key, ok]) => (
        <li key={key} className="flex items-start gap-2 text-sm">
          {ok ? (
            <CircleCheck className="mt-px size-4 shrink-0 text-ledger-green" aria-hidden />
          ) : (
            <OctagonX className="mt-px size-4 shrink-0 text-ledger-red" aria-hidden />
          )}
          <span className={ok ? 'text-ink' : 'font-medium text-ledger-red'}>
            {invariantLabel(key)}
            <span className="sr-only">{ok ? ': holds' : ': fails'}</span>
          </span>
          <span className="ml-auto pl-3 font-mono text-xs text-ink-muted">{key}</span>
        </li>
      ))}
    </ul>
  )
}
