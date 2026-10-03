import type { ReactNode } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export interface Stat {
  label: string
  /** Pre-formatted value (use <Money/>, formatPct, formatCount). */
  value: ReactNode
  /** Small note under the label, e.g. "brief listed 10". */
  note?: ReactNode
  tone?: 'default' | 'red' | 'green' | 'amber'
}

const TONE = {
  default: 'text-ink',
  red: 'text-ledger-red',
  green: 'text-ledger-green',
  amber: 'text-ledger-amber-ink',
} as const

/**
 * A row of headline numbers with labels beneath (Health header, Ledger totals, Audit metrics).
 * Rendered as a description list so each value is tied to its label.
 */
export function StatStrip({
  stats,
  loading = false,
  className,
}: {
  stats: Stat[]
  loading?: boolean
  className?: string
}) {
  return (
    <dl
      className={cn(
        'grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-rule bg-rule sm:grid-cols-[repeat(auto-fit,minmax(10rem,1fr))]',
        className,
      )}
    >
      {stats.map((s) => (
        <div key={s.label} className="flex flex-col-reverse gap-1 bg-surface px-4 py-3">
          <dt className="text-sm text-ink-muted">
            {s.label}
            {s.note ? <span className="block text-xs">{s.note}</span> : null}
          </dt>
          <dd className={cn('num text-2xl font-medium', TONE[s.tone ?? 'default'])}>
            {loading ? <Skeleton className="h-8 w-24" aria-hidden /> : s.value}
          </dd>
        </div>
      ))}
    </dl>
  )
}
