import { formatMoney, isNegative, isZero } from '@/lib/money'
import { cn } from '@/lib/utils'

export interface MoneyProps {
  /** Decimal string from the API, e.g. "-2075000.00". Null/undefined renders an em dash. */
  value: string | null | undefined
  /** Prefix positive values with "+" (use for deltas). */
  signed?: boolean
  /** "auto" colours negatives red; "none" keeps ink (e.g. credit-normal balances). */
  tone?: 'auto' | 'none'
  /** Show 0.00 muted so non-zero amounts stand out. Default true. */
  dimZero?: boolean
  className?: string
}

/**
 * An amount: IBM Plex Mono, tabular figures, two decimals, thousands separators, leading minus.
 * Inline element; right-align it with the containing cell (`text-right`).
 */
export function Money({
  value,
  signed = false,
  tone = 'auto',
  dimZero = true,
  className,
}: MoneyProps) {
  if (value == null || value === '') {
    return (
      <span className={cn('num text-ink-muted', className)}>
        <span aria-hidden>—</span>
        <span className="sr-only">no amount</span>
      </span>
    )
  }
  return (
    <span
      className={cn(
        'num',
        tone === 'auto' && isNegative(value) && 'text-ledger-red',
        dimZero && isZero(value) && 'text-ink-muted',
        className,
      )}
    >
      {formatMoney(value, { signed })}
    </span>
  )
}
