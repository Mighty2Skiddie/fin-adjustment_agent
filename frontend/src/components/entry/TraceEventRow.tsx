import type { ReactNode } from 'react'
import { isTraceEvent, type RuleResultEvent, type TraceEvent } from '@/api/types'
import { Chip } from '@/components/Chip'
import { DecisionChip } from '@/components/DecisionChip'
import { JsonToggle } from '@/components/JsonToggle'
import { SeverityChip } from '@/components/SeverityChip'
import { formatTimestamp, humanize } from '@/lib/format'
import { formatCount, formatMs } from '@/lib/money'
import { cn } from '@/lib/utils'

/** "2026-10-01T15:34:06Z" -> "15:34:06" (full UTC timestamp in the title). */
export function TraceTime({ ts }: { ts: string }) {
  const time = /T(\d{2}:\d{2}:\d{2})/.exec(ts)?.[1] ?? ts
  return (
    <time dateTime={ts} title={formatTimestamp(ts)} className="num text-xs text-ink-muted">
      {time}
    </time>
  )
}

function Meta({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
      {items.map(([k, v]) => (
        <div key={k} className="flex items-baseline gap-1">
          <dt className="text-ink-muted">{k}</dt>
          <dd className="num text-ink">{v}</dd>
        </div>
      ))}
    </dl>
  )
}

function Title({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="font-mono text-xs text-ink-muted">{label}</span>
      {children}
    </div>
  )
}

function roleLabel(role: string) {
  return humanize(role).toLowerCase()
}

/** The readable body of one event; the raw JSON sits beneath it. */
function EventBody({ event }: { event: TraceEvent }) {
  if (isTraceEvent(event, 'entry.start')) {
    return (
      <Title label="entry.start">
        <span className="text-sm">Entry started</span>
        <span className="num text-xs text-ink-muted">trace {event.trace_id}</span>
      </Title>
    )
  }
  if (isTraceEvent(event, 'rule.result')) {
    return (
      <Title label="rule.result">
        <span className="font-mono text-sm font-medium">{event.rule_id}</span>
        <SeverityChip severity={event.severity} />
        {typeof event.duration_ms === 'number' ? (
          <span className="num text-xs text-ink-muted">{formatMs(event.duration_ms)}</span>
        ) : null}
        {event.produced_by && event.produced_by !== 'rule' ? (
          <Chip tone="act" variant="outline">
            {event.produced_by}
          </Chip>
        ) : null}
      </Title>
    )
  }
  if (isTraceEvent(event, 'llm.call')) {
    return (
      <div className="flex flex-col gap-1">
        <Title label="llm.call">
          <span className="text-sm font-medium">{roleLabel(event.role)}</span>
          {event.cassette_hit === true ? (
            <Chip tone="green" variant="outline">
              cassette hit
            </Chip>
          ) : event.cassette_hit === false ? (
            <Chip tone="amber" variant="outline">
              cassette miss
            </Chip>
          ) : null}
        </Title>
        <Meta
          items={[
            ['model', event.model],
            ['provider', event.provider],
            ['mode', event.mode],
            ['latency', formatMs(event.latency_ms)],
            [
              'tokens in / out (est.)',
              `${event.input_tokens != null ? formatCount(event.input_tokens) : '—'} / ${
                event.output_tokens != null ? formatCount(event.output_tokens) : '—'
              }`,
            ],
            ['prompt', event.prompt_hash],
          ]}
        />
      </div>
    )
  }
  if (isTraceEvent(event, 'guardrail.result')) {
    return (
      <div className="flex flex-col gap-1">
        <Title label="guardrail.result">
          <span className="text-sm">
            {roleLabel(event.role)} · attempt <span className="num">{event.attempt}</span>
          </span>
          <Chip tone={event.passed ? 'green' : 'red'} variant="outline">
            {event.passed ? 'passed' : 'failed'}
          </Chip>
        </Title>
        {event.violations.length > 0 ? (
          <ul className="list-disc pl-5 text-sm text-ledger-red">
            {event.violations.map((v, i) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        ) : null}
      </div>
    )
  }
  if (isTraceEvent(event, 'llm.role')) {
    const items: [string, ReactNode][] = [
      ['source', event.source],
      ['attempts', String(event.attempts)],
    ]
    if (event.model) items.push(['model', event.model])
    if (event.consistent !== undefined) items.push(['consistent', event.consistent ? 'yes' : 'no'])
    if (event.added_finding) items.push(['added finding', event.added_finding])
    if (event.candidates !== undefined) items.push(['candidates', String(event.candidates)])
    return (
      <div className="flex flex-col gap-1">
        <Title label="llm.role">
          <span className="text-sm font-medium">{roleLabel(event.role)} finished</span>
          {event.guardrail_fallback ? (
            <Chip tone="amber" variant="outline">
              guardrail fallback
            </Chip>
          ) : null}
          {event.cassette_miss ? (
            <Chip tone="amber" variant="outline">
              cassette miss
            </Chip>
          ) : null}
        </Title>
        <Meta items={items} />
      </div>
    )
  }
  if (isTraceEvent(event, 'decision')) {
    return (
      <Title label="decision">
        <DecisionChip decision={event.decision} />
        <span className="text-sm">by {event.by}</span>
      </Title>
    )
  }
  if (isTraceEvent(event, 'fix.revalidated')) {
    return (
      <div className="flex flex-col gap-1">
        <Title label="fix.revalidated">
          <span className="text-sm font-medium">{event.label}</span>
          <Chip tone={event.resolves ? 'green' : 'red'} variant="outline">
            {event.resolves ? 'resolves' : 'does not resolve'}
          </Chip>
        </Title>
        {event.rule_ids.length > 0 ? (
          <Meta items={[['rules raised on re-check', event.rule_ids.join(', ')]]} />
        ) : null}
      </div>
    )
  }
  if (isTraceEvent(event, 'decision.human')) {
    return (
      <div className="flex flex-col gap-1">
        <Title label="decision.human">
          <Chip tone={event.action === 'APPROVED' ? 'green' : 'red'}>
            {event.action === 'APPROVED' ? 'Approved' : 'Rejected'}
          </Chip>
          <span className="min-w-0 text-sm [overflow-wrap:anywhere]">by {event.actor}</span>
        </Title>
        <p className="text-sm [overflow-wrap:anywhere]">“{event.reason}”</p>
      </div>
    )
  }
  return (
    <Title label={event.event}>
      <span className="text-sm text-ink-muted">Event recorded</span>
    </Title>
  )
}

function markerTone(event: TraceEvent): string {
  if (isTraceEvent(event, 'rule.result')) {
    if (event.severity === 'BLOCK') return 'bg-ledger-red'
    if (event.severity === 'ESCALATE' || event.severity === 'WARN') return 'bg-ledger-amber'
    return 'bg-rule'
  }
  if (isTraceEvent(event, 'guardrail.result')) return event.passed ? 'bg-ledger-green' : 'bg-ledger-red'
  if (isTraceEvent(event, 'decision') || isTraceEvent(event, 'decision.human')) return 'bg-act'
  if (isTraceEvent(event, 'llm.call') || isTraceEvent(event, 'llm.role')) return 'bg-act/60'
  return 'bg-ink-muted'
}

/** A list item on the timeline rail: marker, time, readable body, raw JSON. */
export function TraceEventRow({ event }: { event: TraceEvent }) {
  return (
    <li className="relative flex flex-col gap-1 py-2 pl-5">
      <span
        aria-hidden
        className={cn('absolute top-3.5 left-[-4.5px] size-2 rounded-full', markerTone(event))}
      />
      <div className="flex flex-wrap items-start gap-x-3 gap-y-1">
        <TraceTime ts={event.ts} />
        <div className="min-w-0 flex-1">
          <EventBody event={event} />
        </div>
      </div>
      <JsonToggle data={event} label="raw JSON" maxHeight="16rem" className="gap-1" />
    </li>
  )
}

/** Consecutive passing rules collapsed into one compact row. */
export function PassBatchRow({ events }: { events: RuleResultEvent[] }) {
  const total = events.reduce((sum, e) => sum + (e.duration_ms ?? 0), 0)
  const first = events[0]
  return (
    <li className="relative flex flex-col gap-1 py-2 pl-5">
      <span
        aria-hidden
        className="absolute top-3.5 left-[-4.5px] size-2 rounded-full bg-ledger-green"
      />
      <div className="flex flex-wrap items-start gap-x-3 gap-y-1">
        {first ? <TraceTime ts={first.ts} /> : null}
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-ink-muted">rule.result</span>
          <SeverityChip severity="PASS" />
          <span className="text-sm">
            <span className="num">{events.length}</span> {events.length === 1 ? 'rule' : 'rules'}{' '}
            passed
          </span>
          <span className="font-mono text-xs break-all text-ink-muted">
            {events.map((e) => e.rule_id).join(' · ')}
          </span>
          <span className="num text-xs text-ink-muted">{formatMs(total)}</span>
        </div>
      </div>
      <JsonToggle data={events} label="raw JSON" maxHeight="16rem" className="gap-1" />
    </li>
  )
}
