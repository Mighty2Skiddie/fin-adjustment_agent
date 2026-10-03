import {
  BookOpen,
  FlaskConical,
  Info,
  ListChecks,
  ScrollText,
  Stethoscope,
  type LucideIcon,
} from 'lucide-react'
import { Suspense } from 'react'
import { NavLink, Outlet, useParams } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { RunTopBar } from './RunTopBar'
import { SkeletonRows } from './SkeletonRows'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

function navItems(runId: string): NavItem[] {
  const base = `/runs/${encodeURIComponent(runId)}`
  return [
    { to: `${base}/health`, label: 'Health', icon: Stethoscope },
    { to: `${base}/queue`, label: 'Queue', icon: ListChecks },
    { to: `${base}/ledger`, label: 'Ledger', icon: BookOpen },
    { to: `${base}/audit`, label: 'Audit', icon: ScrollText },
    { to: `${base}/evals`, label: 'Evals', icon: FlaskConical },
    { to: '/about', label: 'About', icon: Info },
  ]
}

function RailLink({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        cn(
          'flex flex-col items-center justify-center gap-1 rounded-sm px-1 py-2 text-xs leading-none text-ink-muted hover:bg-band hover:text-ink',
          'max-md:flex-row max-md:gap-1.5 max-md:px-2.5',
          isActive && 'bg-act-tint text-act hover:bg-act-tint hover:text-act',
        )
      }
    >
      <Icon className="size-[18px] shrink-0" aria-hidden strokeWidth={1.75} />
      <span>{item.label}</span>
    </NavLink>
  )
}

/**
 * Page frame: a 56 px left rail (a top bar on narrow screens), the run context bar on run
 * pages, and left-aligned content capped at 1280 px.
 */
export function AppShell() {
  const { runId } = useParams<{ runId: string }>()
  const items = navItems(runId ?? 'latest')
  return (
    <div className="min-h-dvh bg-paper text-ink md:grid md:grid-cols-[3.5rem_minmax(0,1fr)]">
      <a
        href="#main"
        className="sr-only z-50 rounded-sm bg-act px-3 py-2 text-act-ink focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Skip to content
      </a>
      {/* The rail column stretches to the page height (so full-page captures keep it) while the
          nav inside stays pinned to the viewport. */}
      <div
        className={cn(
          'z-40 border-rule bg-surface',
          'md:border-r',
          'max-md:sticky max-md:top-0 max-md:border-b',
        )}
      >
        <nav aria-label="Primary" className="md:sticky md:top-0 md:flex md:h-dvh md:flex-col">
          <div
            className="hidden h-11 items-center justify-center border-b border-rule font-mono text-xs font-medium text-ink md:flex"
            title="fin-adjustments-agent"
            aria-hidden
          >
            FA
          </div>
          <ul className="flex gap-0.5 p-1 max-md:overflow-x-auto md:flex-col md:gap-1 md:py-2">
            {items.map((item) => (
              <li key={item.label} className="shrink-0">
                <RailLink item={item} />
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <div className="min-w-0">
        {runId ? <RunTopBar /> : null}
        <main id="main" tabIndex={-1} className="max-w-[1280px] px-4 py-6 outline-none md:px-6">
          {/* Pages are code-split; the fallback keeps the table-shaped skeleton, not a spinner. */}
          <Suspense fallback={<SkeletonRows label="Loading page" />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}
