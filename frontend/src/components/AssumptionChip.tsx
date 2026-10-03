import { Link } from 'react-router-dom'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { assumptionAnchor, assumptionText } from '@/lib/assumptions'
import { cn } from '@/lib/utils'

/**
 * Amber "assumption" chip. Hover or focus shows the assumption text; clicking opens it in the
 * register on /about#assumption-<id>.
 */
export function AssumptionChip({ id, className }: { id: string; className?: string }) {
  const text = assumptionText(id)
  const label = `Assumption ${id}${text ? `: ${text}` : ''}`
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Link
            to={`/about#${assumptionAnchor(id)}`}
            aria-label={label}
            className={cn(
              'inline-flex h-5 shrink-0 items-center gap-1 rounded-sm border border-ledger-amber/60 bg-ledger-amber-tint px-1.5 text-xs leading-none font-medium whitespace-nowrap text-ledger-amber-ink no-underline hover:border-ledger-amber',
              className,
            )}
          />
        }
      >
        assumption <span className="font-mono">{id}</span>
      </TooltipTrigger>
      <TooltipContent className="max-w-sm text-left leading-snug">
        <span>
          <span className="font-mono font-medium">{id}</span>{' '}
          {text ?? 'See the assumptions register.'}
        </span>
      </TooltipContent>
    </Tooltip>
  )
}
