import { ArrowRight } from 'lucide-react'
import { useMemo, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { seg } from '@/api/client'
import type { AuditEvent, Decision } from '@/api/types'
import { DataTable, DecisionChip, sortBy, type Column } from '@/components'
import { formatTimestamp, humanize, llmModeLabel } from '@/lib/format'
import { formatCount } from '@/lib/money'

const EVENT_LABELS: Record<string, string> = {
  'run.created': 'Run created',
  'decision.system': 'System decision',
  'decision.human': 'Reviewer decision',
  'post.completed': 'Posted to ledger',
}

const DECISIONS: ReadonlySet<string> = new Set(['ACCEPTED', 'QUARANTINED', 'REJECTED'])

function isDecision(v: unknown): v is Decision {
  return typeof v === 'string' && DECISIONS.has(v)
}

function Muted({ children }: { children: ReactNode }) {
  return <span className="text-ink-muted">{children}</span>
}

function actorOf(e: AuditEvent): string | null {
  if (e.actor) return e.actor
  if (e.event === 'decision.system' || e.event === 'run.created' || e.event === 'post.completed')
    return 'system'
  return null
}

/** The reviewer's reason when there is one; otherwise what the system recorded with the event. */
function ReasonCell({ e }: { e: AuditEvent }) {
  if (e.reason) return <span className="[overflow-wrap:anywhere]">{e.reason}</span>
  if (e.event === 'decision.system') {
    const rules = e.rule_ids ?? []
    if (!rules.length) return <Muted>No rule findings</Muted>
    return (
      <Muted>
        Rules <span className="font-mono text-ink">{Array.from(new Set(rules)).join(', ')}</span>
      </Muted>
    )
  }
  if (e.event === 'post.completed' && typeof e.lines === 'number') {
    return (
      <Muted>
        <span className="num">{formatCount(e.lines)}</span> ledger lines written
      </Muted>
    )
  }
  if (e.event === 'run.created') {
    return (
      <Muted>
        {e.llm_mode ? `LLM mode: ${llmModeLabel(e.llm_mode).toLowerCase()}` : null}
        {e.llm_mode && e.status ? ' · ' : null}
        {e.status ? (
          <>
            status <span className="font-mono">{e.status}</span>
          </>
        ) : null}
      </Muted>
    )
  }
  return <Muted>—</Muted>
}

function Transition({ e }: { e: AuditEvent }) {
  const before = isDecision(e.before) ? e.before : null
  const after = isDecision(e.after) ? e.after : null
  if (!before && !after) return <Muted>—</Muted>
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      {before ? <DecisionChip decision={before} /> : null}
      {before && after ? (
        <>
          <ArrowRight className="size-3.5 text-ink-muted" aria-hidden />
          <span className="sr-only">to</span>
        </>
      ) : null}
      {after ? <DecisionChip decision={after} /> : null}
    </span>
  )
}

export function AuditLogTable({
  events,
  routeRunId,
  loading,
}: {
  events: AuditEvent[] | undefined
  routeRunId: string
  loading: boolean
}) {
  // Events can share a timestamp, event name and entry; their position in the log is unique.
  const order = useMemo(() => new Map((events ?? []).map((e, i) => [e, i])), [events])

  const columns: Column<AuditEvent>[] = [
    {
      id: 'ts',
      header: 'Time (UTC)',
      width: '11.5rem',
      className: 'align-top whitespace-nowrap',
      sort: sortBy.string((e) => e.ts),
      cell: (e) => (
        <time dateTime={e.ts} className="num text-xs">
          {formatTimestamp(e.ts).replace(' UTC', '')}
        </time>
      ),
    },
    {
      id: 'event',
      header: 'Event',
      width: '11rem',
      rowHeader: true,
      className: 'align-top text-left',
      sort: sortBy.string((e) => e.event),
      cell: (e) => (
        <span className="flex flex-col">
          <span className="text-ink">{EVENT_LABELS[e.event] ?? humanize(e.event)}</span>
          <span className="font-mono text-xs text-ink-muted">{e.event}</span>
        </span>
      ),
    },
    {
      id: 'entry',
      header: 'Entry',
      width: '6.5rem',
      className: 'align-top whitespace-nowrap',
      sort: sortBy.string((e) => e.entry_id ?? ''),
      cell: (e) =>
        e.entry_id ? (
          <Link
            to={`/runs/${seg(routeRunId)}/entries/${seg(e.entry_id)}`}
            className="font-mono text-act underline-offset-2 hover:underline"
          >
            {e.entry_id}
          </Link>
        ) : (
          <Muted>—</Muted>
        ),
    },
    {
      id: 'actor',
      header: 'Actor',
      width: '8rem',
      className: 'align-top',
      sort: sortBy.string((e) => actorOf(e) ?? ''),
      cell: (e) => {
        const actor = actorOf(e)
        if (!actor) return <Muted>—</Muted>
        return actor === 'system' ? <Muted>System</Muted> : <span className="[overflow-wrap:anywhere]">{actor}</span>
      },
    },
    {
      id: 'transition',
      header: (
        <>
          Before → after<span className="sr-only"> (decision)</span>
        </>
      ),
      width: '15rem',
      className: 'align-top',
      cell: (e) => <Transition e={e} />,
    },
    {
      id: 'reason',
      header: 'Reason',
      className: 'align-top',
      cell: (e) => <ReasonCell e={e} />,
    },
  ]

  return (
    <DataTable
      columns={columns}
      rows={events}
      loading={loading}
      skeletonRows={8}
      getRowId={(e) => String(order.get(e) ?? `${e.ts}|${e.event}|${e.entry_id ?? ''}`)}
      caption="Audit log: every system and reviewer event for this run, oldest first"
      empty={<Muted>No events have been recorded for this run.</Muted>}
    />
  )
}
