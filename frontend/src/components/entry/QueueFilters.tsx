import { cn } from '@/lib/utils'
import { QUEUE_FILTERS, type QueueFilter } from './queueModel'

const ACTIVE_TONE: Record<QueueFilter, string> = {
  all: 'border-ink bg-ink text-paper',
  review: 'border-ledger-amber bg-ledger-amber-tint text-ledger-amber-ink',
  rejected: 'border-ledger-red bg-ledger-red-tint text-ledger-red',
  accepted: 'border-ledger-green bg-ledger-green-tint text-ledger-green',
}

export interface QueueFiltersProps {
  value: QueueFilter
  counts: Record<QueueFilter, number> | undefined
  onChange: (filter: QueueFilter) => void
  className?: string
}

/** All · Needs review · Rejected · Accepted, with counts by effective decision. */
export function QueueFilters({ value, counts, onChange, className }: QueueFiltersProps) {
  return (
    <div role="group" aria-label="Filter entries" className={cn('flex flex-wrap gap-1.5', className)}>
      {QUEUE_FILTERS.map((f) => {
        const active = f.id === value
        return (
          <button
            key={f.id}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(f.id)}
            className={cn(
              'inline-flex h-7 items-center gap-1.5 rounded-sm border px-2.5 text-sm font-medium transition-colors duration-100 focus-visible:outline-[var(--focus)]',
              active ? ACTIVE_TONE[f.id] : 'border-rule bg-surface text-ink hover:bg-band',
            )}
          >
            {f.label}
            <span className={cn('num text-xs', !active && 'text-ink-muted')}>
              {counts ? counts[f.id] : '–'}
            </span>
          </button>
        )
      })}
    </div>
  )
}
