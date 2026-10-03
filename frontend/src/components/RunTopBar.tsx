import type { ReactNode } from 'react'
import { useRun, useRunId } from '@/api/queries'
import { Skeleton } from '@/components/ui/skeleton'
import { fxPolicyLabel, llmModeLabel } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Chip } from './Chip'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-ink-muted">{label}</dt>
      <dd className="text-ink">{children}</dd>
    </div>
  )
}

/**
 * Run context on every run page: id, period, FX policy in effect, LLM mode and the system
 * decision counts (accepted · quarantined · rejected).
 */
export function RunTopBar({ className }: { className?: string }) {
  const { runId, notFound } = useRunId()
  const run = useRun(runId)
  if (notFound) return null
  const m = run.data
  return (
    <section
      aria-label="Run details"
      className={cn(
        'flex min-h-11 flex-wrap items-center gap-x-6 gap-y-1 border-b border-rule px-4 py-2 text-sm md:px-6',
        className,
      )}
    >
      {!m ? (
        run.isError ? (
          <span className="text-ledger-red">Run details unavailable.</span>
        ) : (
          <Skeleton className="h-4 w-96 max-w-full" aria-hidden />
        )
      ) : (
        <dl className="flex flex-wrap items-center gap-x-6 gap-y-1">
          <Field label="Run">
            <span className="inline-flex items-center gap-2">
              <span className="font-mono font-medium" title={m.run_id}>
                {m.run_id}
              </span>
              {m.latest ? (
                <Chip tone="muted" variant="outline">
                  latest
                </Chip>
              ) : null}
              {m.status !== 'OK' ? (
                <Chip tone="red">{m.status.toLowerCase().replace(/_/g, ' ')}</Chip>
              ) : null}
            </span>
          </Field>
          <Field label="Period">
            <span className="font-mono">{m.period ?? '—'}</span>
          </Field>
          <Field label="FX">
            <span title={m.fx_policy ?? undefined}>{fxPolicyLabel(m.fx_policy)}</span>
          </Field>
          <Field label="LLM">{llmModeLabel(m.llm_mode)}</Field>
          <Field label="Decisions">
            <span
              className="num"
              title={`${m.counts.accepted} accepted · ${m.counts.quarantined} quarantined · ${m.counts.rejected} rejected (system)`}
            >
              <span className="sr-only">
                {m.counts.accepted} accepted, {m.counts.quarantined} quarantined,{' '}
                {m.counts.rejected} rejected
              </span>
              <span aria-hidden>
                <span className="text-ledger-green">{m.counts.accepted}</span>
                <span className="text-ink-muted"> · </span>
                <span className="text-ledger-amber-ink">{m.counts.quarantined}</span>
                <span className="text-ink-muted"> · </span>
                <span className="text-ledger-red">{m.counts.rejected}</span>
              </span>
            </span>
          </Field>
        </dl>
      )}
    </section>
  )
}
