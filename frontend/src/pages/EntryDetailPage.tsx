import { ArrowLeft } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { useEntry, useRun, useTrace } from '@/api/queries'
import type { EntryDetail, HumanAction } from '@/api/types'
import {
  DecisionChip,
  EmptyState,
  ErrorState,
  KeyboardHints,
  PageHeader,
  RunGate,
  SectionHeading,
  SkeletonLines,
  SkeletonRows,
} from '@/components'
import { EntryPanel } from '@/components/entry/EntryPanel'
import { LineagePreview } from '@/components/entry/LineagePreview'
import { TraceTimeline } from '@/components/entry/TraceTimeline'
import { buttonVariants } from '@/components/ui/button'
import { useHotkeys } from '@/hooks/useHotkeys'
import { canDecide } from '@/lib/entry'
import { effectiveStateLabel, formatDate } from '@/lib/format'

function BackToQueue({ runId, jeId }: { runId: string; jeId?: string }) {
  const search = jeId ? `?open=${encodeURIComponent(jeId)}` : ''
  return (
    <Link
      to={`/runs/${encodeURIComponent(runId)}/queue${search}`}
      className={buttonVariants({ variant: 'outline', size: 'sm' })}
    >
      <ArrowLeft aria-hidden />
      Back to review queue
    </Link>
  )
}

function TraceSection({ runId, jeId }: { runId: string; jeId: string }) {
  const trace = useTrace(runId, jeId)
  const { hash } = useLocation()
  const ref = useRef<HTMLElement>(null)
  const scrolled = useRef(false)

  useEffect(() => {
    if (hash === '#trace' && trace.data && !scrolled.current) {
      scrolled.current = true
      ref.current?.scrollIntoView({ block: 'start' })
    }
  }, [hash, trace.data])

  return (
    <section ref={ref} id="trace" aria-labelledby="trace-heading" className="scroll-mt-4">
      <SectionHeading id="trace-heading" aside="Every step the pipeline took for this entry, in order">
        Trace
      </SectionHeading>
      {trace.isPending ? (
        <SkeletonRows rows={8} columns={3} label="Loading trace" />
      ) : trace.error ? (
        <ErrorState
          error={trace.error}
          onRetry={() => void trace.refetch()}
          title="Couldn't load the trace"
        />
      ) : trace.data.length === 0 ? (
        <EmptyState
          title="No trace events were recorded for this entry."
          description="Re-run the pipeline with tracing enabled to see each step."
        />
      ) : (
        <TraceTimeline events={trace.data} runId={runId} jeId={jeId} />
      )}
    </section>
  )
}

function EntryHeader({ entry }: { entry: EntryDetail }) {
  return (
    <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
      <div className="flex items-center gap-2">
        <dt className="text-ink-muted">Decision</dt>
        <dd className="flex items-center gap-2">
          <DecisionChip decision={entry.effective_decision} />
          {entry.human_decision ? (
            <span className="text-ink-muted">
              (system: <DecisionChip decision={entry.decision} />)
            </span>
          ) : null}
        </dd>
      </div>
      <div className="flex min-w-0 items-baseline gap-2">
        <dt className="text-ink-muted">State</dt>
        <dd className="min-w-0 [overflow-wrap:anywhere]">{effectiveStateLabel(entry.effective_state)}</dd>
      </div>
      <div className="flex items-baseline gap-2">
        <dt className="text-ink-muted">Date</dt>
        <dd className="num">{formatDate(entry.entry.date)}</dd>
      </div>
      <div className="flex items-baseline gap-2">
        <dt className="text-ink-muted">Source</dt>
        <dd>{entry.entry.source}</dd>
      </div>
      <div className="flex items-baseline gap-2">
        <dt className="text-ink-muted">Version</dt>
        <dd className="num">{entry.entry.version}</dd>
      </div>
      <div className="flex items-baseline gap-2">
        <dt className="text-ink-muted">Trace id</dt>
        <dd className="num">{entry.trace_id}</dd>
      </div>
    </dl>
  )
}

function EntryContent({ runId, jeId }: { runId: string; jeId: string }) {
  const entry = useEntry(runId, jeId)
  const run = useRun(runId)
  const [formAction, setFormAction] = useState<HumanAction | null>(null)
  const data = entry.data
  const decidable = !!data && canDecide(data)

  const open = (event: KeyboardEvent, action: HumanAction) => {
    if (!data) return
    event.preventDefault()
    if (!decidable) {
      toast.info(
        data.human_decision
          ? `${jeId} already has a reviewer decision.`
          : data.decision === 'REJECTED'
            ? "Rejected entries can't be approved. Edit the entry and resubmit as a new version."
            : 'Posted automatically — all checks passed.',
      )
      return
    }
    setFormAction(action)
  }

  useHotkeys(
    {
      a: (e) => open(e, 'APPROVED'),
      r: (e) => open(e, 'REJECTED'),
      Escape: () => setFormAction(null),
    },
    !!data,
  )

  if (entry.isPending) {
    return (
      <>
        <PageHeader title={jeId} actions={<BackToQueue runId={runId} jeId={jeId} />} />
        <div className="flex flex-col gap-6">
          <SkeletonLines lines={3} />
          <SkeletonRows rows={4} columns={4} label="Loading entry" />
        </div>
      </>
    )
  }
  if (entry.error) {
    const notFound = entry.error.status === 404
    return (
      <>
        <PageHeader title={jeId} actions={<BackToQueue runId={runId} />} />
        <ErrorState
          error={entry.error}
          onRetry={notFound ? undefined : () => void entry.refetch()}
          title={notFound ? 'Entry not found in this run' : "Couldn't load the entry"}
          action={notFound ? <BackToQueue runId={runId} /> : undefined}
        />
      </>
    )
  }

  const e = entry.data
  return (
    <>
      <PageHeader
        title={`${e.entry.id} · ${e.entry.description}`}
        actions={<BackToQueue runId={runId} jeId={jeId} />}
      >
        <EntryHeader entry={e} />
        {decidable ? (
          <KeyboardHints
            hints={[
              { keys: ['a'], label: 'approve' },
              { keys: ['r'], label: 'reject' },
              { keys: ['Esc'], label: 'close form' },
            ]}
          />
        ) : null}
      </PageHeader>
      <div className="flex flex-col gap-10">
        <article
          aria-label={`${e.entry.id} working paper`}
          className="rounded-sm border border-rule bg-surface p-4 sm:p-5"
        >
          <EntryPanel
            runId={runId}
            entry={e}
            llmMode={run.data?.llm_mode}
            formAction={formAction}
            onFormActionChange={setFormAction}
          />
        </article>
        {e.lineage_preview.length > 0 || e.human_decisions.length > 0 ? (
          <LineagePreview runId={runId} entry={e} />
        ) : null}
        <TraceSection runId={runId} jeId={jeId} />
      </div>
    </>
  )
}

export default function EntryDetailPage() {
  const { jeId } = useParams<{ jeId: string }>()
  return (
    <RunGate>
      {(runId) =>
        jeId ? (
          <EntryContent key={`${runId}/${jeId}`} runId={runId} jeId={jeId} />
        ) : (
          <EmptyState title="No entry selected." />
        )
      }
    </RunGate>
  )
}
