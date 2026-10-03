import { Link } from 'react-router-dom'
import type { EntryResult } from '@/api/types'
import { parseExplanation } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Chip } from '../Chip'

function explanationParts(result: EntryResult) {
  const d = result.explanation_detail
  if (d && typeof d.summary === 'string' && d.summary) {
    return {
      summary: d.summary,
      details: Array.isArray(d.details) ? d.details.filter((x) => typeof x === 'string') : [],
      nextStep: typeof d.next_step === 'string' ? d.next_step : null,
    }
  }
  return parseExplanation(result.explanation)
}

function SourceChip({ result, llmMode }: { result: EntryResult; llmMode?: string }) {
  if (result.explanation_source === 'llm') {
    const parts = ['LLM', result.explanation_model, llmMode].filter(Boolean)
    return (
      <Chip tone="muted" variant="outline" className="font-mono">
        {parts.join(' · ')}
      </Chip>
    )
  }
  if (result.explanation_source === 'template') {
    return (
      <Chip tone="amber" variant="outline">
        template fallback
      </Chip>
    )
  }
  return null
}

export interface ExplanationCardProps {
  result: EntryResult
  /** Run LLM mode ("cassette" | "live" | "off"), shown in the source chip. */
  llmMode?: string
  /** Link to the entry's trace, e.g. `/runs/<id>/entries/<je>#trace`. Omit to hide. */
  traceHref?: string
  className?: string
}

/** Summary (18 px), supporting bullets, the next step, and where the words came from. */
export function ExplanationCard({ result, llmMode, traceHref, className }: ExplanationCardProps) {
  const { summary, details, nextStep } = explanationParts(result)
  if (!summary) {
    return (
      <div className={cn('flex flex-col gap-2', className)}>
        <p className="text-sm text-ink-muted">
          {result.decision === 'ACCEPTED'
            ? 'No explanation needed — every blocking check passed.'
            : 'No explanation was produced for this entry.'}
        </p>
        {traceHref ? (
          <Link to={traceHref} className="text-sm text-act underline-offset-4 hover:underline">
            View trace
          </Link>
        ) : null}
      </div>
    )
  }
  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <p className="text-lg leading-snug text-ink">{summary}</p>
      {details.length > 0 ? (
        <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm marker:text-ink-muted">
          {details.map((d, i) => (
            <li key={i}>{d}</li>
          ))}
        </ul>
      ) : null}
      {nextStep ? (
        <p className="text-sm">
          <span className="font-medium">Next step: </span>
          {nextStep}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-3 border-t border-rule pt-2">
        <SourceChip result={result} llmMode={llmMode} />
        {traceHref ? (
          <Link to={traceHref} className="text-sm text-act underline-offset-4 hover:underline">
            View trace
          </Link>
        ) : null}
      </div>
    </div>
  )
}
