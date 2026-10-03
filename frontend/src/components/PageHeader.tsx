import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface PageHeaderProps {
  /** The page's h1, sentence case. */
  title: string
  /** One or two plain sentences on what this page is for. */
  description?: ReactNode
  /** Right-aligned actions (buttons, links). Wraps under the title on narrow screens. */
  actions?: ReactNode
  /** Small line under the description (e.g. keyboard hints, filters). */
  children?: ReactNode
  className?: string
}

export function PageHeader({ title, description, actions, children, className }: PageHeaderProps) {
  return (
    <header className={cn('flex flex-col gap-3 pb-5', className)}>
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="flex min-w-0 flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
          {description ? <div className="max-w-prose text-ink-muted">{description}</div> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {children}
    </header>
  )
}

/** A section heading inside a page (h2, 18 px). */
export function SectionHeading({
  children,
  id,
  aside,
  className,
}: {
  children: ReactNode
  id?: string
  aside?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-wrap items-baseline justify-between gap-2 pb-2', className)}>
      <h2 id={id} className="text-lg font-semibold text-ink">
        {children}
      </h2>
      {aside ? <div className="text-sm text-ink-muted">{aside}</div> : null}
    </div>
  )
}
