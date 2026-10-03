import { cn } from '@/lib/utils'
import { Chip } from './Chip'

export interface AccountCodeProps {
  code: string
  /** Account name, shown after the code in sans. */
  name?: string | null
  /** Code is not in the chart of accounts: red code plus a "not in COA" tag. */
  orphan?: boolean
  /** Tag for unmapped ledger lines (e.g. 9999). */
  unmapped?: boolean
  className?: string
}

export function AccountCode({
  code,
  name,
  orphan = false,
  unmapped = false,
  className,
}: AccountCodeProps) {
  return (
    <span className={cn('inline-flex min-w-0 items-baseline gap-2', className)}>
      <span className={cn('num font-medium', orphan && 'text-ledger-red')}>{code}</span>
      {name ? <span className="min-w-0 truncate">{name}</span> : null}
      {orphan ? (
        <Chip tone="red" variant="outline" className="self-center">
          not in COA
        </Chip>
      ) : null}
      {unmapped && !orphan ? (
        <Chip tone="amber" variant="outline" className="self-center">
          unmapped
        </Chip>
      ) : null}
    </span>
  )
}
