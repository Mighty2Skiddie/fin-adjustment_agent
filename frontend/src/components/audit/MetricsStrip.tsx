import type { RunMetrics } from '@/api/types'
import { SectionHeading, StatStrip, type Stat } from '@/components'
import { formatCount, formatMs, formatPct } from '@/lib/money'

const pct = (v: string | undefined) => (v == null ? '—' : formatPct(v))
const count = (v: number | undefined) => (v == null ? '—' : formatCount(v))

/** Rates arrive as decimal strings ("0.6000"); they are shifted to percentages, not parsed. */
export function MetricsStrip({ metrics }: { metrics: RunMetrics | undefined }) {
  const m = metrics ?? {}
  const fallback = m.guardrail_fallback_rate
  const stats: Stat[] = [
    { label: 'Auto-accept rate', value: pct(m.auto_accept_rate) },
    { label: 'Quarantine rate', value: pct(m.quarantine_rate) },
    { label: 'Reject rate', value: pct(m.reject_rate) },
    {
      label: 'Guardrail fallback rate',
      value: pct(fallback),
      tone: fallback != null && /[1-9]/.test(fallback) ? 'amber' : 'default',
    },
    { label: 'LLM calls', value: count(m.llm_calls) },
    { label: 'Cassette hit rate', value: pct(m.cassette_hit_rate) },
    {
      label: 'p50 LLM latency',
      value: m.p50_latency_ms == null ? '—' : formatMs(m.p50_latency_ms),
    },
  ]
  const providerFallbacks = m.provider_fallbacks
  const langfuse = m.langfuse

  return (
    <section aria-labelledby="metrics-heading" className="flex flex-col">
      <SectionHeading id="metrics-heading">Metrics</SectionHeading>
      <StatStrip stats={stats} loading={!metrics} />
      {metrics && (providerFallbacks != null || langfuse) ? (
        <p className="pt-2 text-xs text-ink-muted">
          {providerFallbacks != null ? (
            <>
              Provider fallbacks <span className="num">{formatCount(providerFallbacks)}</span>.{' '}
            </>
          ) : null}
          {typeof langfuse === 'string' ? <>Langfuse: {langfuse}.</> : null}
        </p>
      ) : null}
    </section>
  )
}
