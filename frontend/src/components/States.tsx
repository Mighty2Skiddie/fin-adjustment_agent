import { Inbox, OctagonX, RotateCw } from 'lucide-react'
import type { ReactNode } from 'react'
import { toDisplayError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface EmptyStateProps {
  title: string
  description?: ReactNode
  action?: ReactNode
  icon?: ReactNode
  className?: string
}

/** Nothing to show — say why, and what to do next if anything. */
export function EmptyState({ title, description, action, icon, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-start gap-2 rounded-sm border border-dashed border-rule px-5 py-6',
        className,
      )}
    >
      <div className="flex items-center gap-2 text-ink">
        <span className="text-ink-muted [&>svg]:size-4" aria-hidden>
          {icon ?? <Inbox />}
        </span>
        <p className="font-medium">{title}</p>
      </div>
      {description ? <div className="max-w-prose text-sm text-ink-muted">{description}</div> : null}
      {action ? <div className="pt-1">{action}</div> : null}
    </div>
  )
}

export interface ErrorStateProps {
  /** Anything thrown; ApiErrors show the server's message_for_user verbatim. */
  error: unknown
  onRetry?: () => void
  /** Short headline, e.g. "Couldn't load the review queue". */
  title?: string
  /** Extra actions (e.g. a link to the latest run). */
  action?: ReactNode
  className?: string
}

/** What happened (server's words) and what to do (retry). */
export function ErrorState({
  error,
  onRetry,
  title = "Couldn't load this",
  action,
  className,
}: ErrorStateProps) {
  const err = toDisplayError(error)
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-start gap-2 rounded-sm border border-ledger-red/40 bg-ledger-red-tint px-5 py-4',
        className,
      )}
    >
      <div className="flex items-center gap-2 font-medium text-ledger-red">
        <OctagonX className="size-4" aria-hidden />
        {title}
      </div>
      <p className="max-w-prose text-ink">{err.messageForUser}</p>
      {err.status > 0 ? (
        <p className="text-xs text-ink-muted">
          Error <span className="font-mono">{err.code}</span> · HTTP{' '}
          <span className="font-mono">{err.status}</span>
        </p>
      ) : null}
      {onRetry || action ? (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {onRetry ? (
            <Button variant="outline" size="sm" onClick={onRetry}>
              <RotateCw aria-hidden />
              Retry
            </Button>
          ) : null}
          {action}
        </div>
      ) : null}
    </div>
  )
}
