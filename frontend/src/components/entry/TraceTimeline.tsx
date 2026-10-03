import { Download } from 'lucide-react'
import { useMemo } from 'react'
import type { TraceEvent } from '@/api/types'
import { Button } from '@/components/ui/button'
import { JsonToggle } from '@/components/JsonToggle'
import { humanize } from '@/lib/format'
import { formatMs } from '@/lib/money'
import { cn } from '@/lib/utils'
import { PassBatchRow, TraceEventRow, TraceTime } from './TraceEventRow'
import { buildTimeline, summarizeTrace, toJsonl, type NodeSpan } from './traceModel'

function NodeSpanItem({ span }: { span: NodeSpan }) {
  const ts = span.enter?.ts ?? span.exit?.ts
  return (
    <li className="relative pb-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-rule/70 bg-band px-3 py-1.5">
        {ts ? <TraceTime ts={ts} /> : null}
        <span className="text-sm font-medium">
          {humanize(span.node)}
          {span.iteration !== undefined ? (
            <span className="font-normal text-ink-muted">
              {' '}
              · iteration <span className="num">{span.iteration}</span>
            </span>
          ) : null}
        </span>
        <span className="font-mono text-xs text-ink-muted">node {span.node}</span>
        <span className="ml-auto num text-xs">
          {span.durationMs != null ? (
            formatMs(span.durationMs)
          ) : (
            <span className="text-ledger-amber-ink">no exit recorded</span>
          )}
        </span>
      </div>
      {span.children.length > 0 ? (
        <ol className="ml-4 border-l border-rule" aria-label={`Events in ${humanize(span.node)}`}>
          {span.children.map((c, i) =>
            c.kind === 'passes' ? (
              <PassBatchRow key={i} events={c.events} />
            ) : (
              <TraceEventRow key={i} event={c.event} />
            ),
          )}
        </ol>
      ) : (
        <p className="ml-4 border-l border-rule py-2 pl-5 text-xs text-ink-muted">
          No events inside this step.
        </p>
      )}
      {span.enter || span.exit ? (
        <div className="ml-4 pl-5">
          <JsonToggle
            data={[span.enter, span.exit].filter(Boolean)}
            label="enter / exit JSON"
            maxHeight="12rem"
          />
        </div>
      ) : null}
    </li>
  )
}

/** Builds the JSONL file on demand so nothing lingers in memory between downloads. */
function downloadJsonl(events: TraceEvent[], filename: string) {
  const url = URL.createObjectURL(new Blob([toJsonl(events)], { type: 'application/x-ndjson' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}

export interface TraceTimelineProps {
  events: TraceEvent[]
  runId: string
  jeId: string
  className?: string
}

/**
 * Every step the graph took for one entry, in order: node spans (enter → exit, with duration)
 * containing rule results (passes batched), LLM calls, guardrail verdicts and decisions.
 */
export function TraceTimeline({ events, runId, jeId, className }: TraceTimelineProps) {
  const items = useMemo(() => buildTimeline(events), [events])
  const summary = useMemo(() => summarizeTrace(events), [events])

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <dl className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
          {(
            [
              ['Events', String(summary.events)],
              ['Rules run', `${summary.rules} (${summary.rulesPassed} passed)`],
              ['LLM calls', `${summary.llmCalls} (${summary.cassetteHits} from cassette)`],
              ['Guardrail failures', String(summary.guardrailFailures)],
              ['Time in steps', formatMs(summary.nodeTimeMs)],
            ] as const
          ).map(([k, v]) => (
            <div key={k} className="flex items-baseline gap-1.5">
              <dt className="text-ink-muted">{k}</dt>
              <dd className="num">{v}</dd>
            </div>
          ))}
        </dl>
        <Button
          variant="outline"
          size="sm"
          onClick={() => downloadJsonl(events, `trace-${runId}-${jeId}.jsonl`)}
        >
          <Download aria-hidden />
          Download trace (JSONL)
        </Button>
      </div>
      <ol className="flex flex-col gap-1 rounded-sm border border-rule bg-surface py-2" aria-label="Trace events">
        {items.map((item, i) =>
          item.kind === 'node' ? (
            <NodeSpanItem key={i} span={item} />
          ) : (
            <li key={i} className="ml-4 border-l border-rule">
              <ol>
                <TraceEventRow event={item.event} />
              </ol>
            </li>
          ),
        )}
      </ol>
    </div>
  )
}
