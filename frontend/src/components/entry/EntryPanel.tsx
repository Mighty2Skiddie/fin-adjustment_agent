import type { ReactNode } from 'react'
import type { EntryView, HumanAction } from '@/api/types'
import { cn } from '@/lib/utils'
import { DecisionPanel } from './DecisionPanel'
import { EntryLines } from './EntryLines'
import { ExplanationCard } from './ExplanationCard'
import { FindingList } from './FindingList'
import { FixCandidates } from './FixCandidates'
import { ImpactPreview } from './ImpactPreview'

function Column({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn('flex min-w-0 flex-col gap-2', className)} aria-label={title}>
      <h2 className="text-xs font-medium tracking-wide text-ink-muted uppercase">{title}</h2>
      {children}
    </section>
  )
}

export interface EntryPanelProps {
  runId: string
  entry: EntryView
  /** Run LLM mode for the explanation source chip. */
  llmMode?: string
  /** Link for "View trace"; omit on the detail page where the trace is below. */
  traceHref?: string
  /** Controlled decision form (bind `a` / `r`); omit for uncontrolled. */
  formAction?: HumanAction | null
  onFormActionChange?: (action: HumanAction | null) => void
  className?: string
}

/**
 * The unfolded working paper for one entry: lines · findings · explanation · fix candidates
 * (four columns on wide screens, stacked on narrow), then impact preview and the action bar.
 * Used by the Review Queue's in-place expansion and the entry detail page.
 */
export function EntryPanel({
  runId,
  entry,
  llmMode,
  traceHref,
  formAction,
  onFormActionChange,
  className,
}: EntryPanelProps) {
  return (
    <div className={cn('flex flex-col gap-5', className)}>
      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1.2fr)_minmax(0,1.2fr)_minmax(0,1.15fr)] xl:gap-5">
        <Column title="Lines">
          <EntryLines result={entry} />
        </Column>
        <Column title={`Findings (${entry.findings.length})`}>
          <FindingList findings={entry.findings} />
        </Column>
        <Column title="Explanation">
          <ExplanationCard result={entry} llmMode={llmMode} traceHref={traceHref} />
        </Column>
        <Column title="Fix candidates">
          <FixCandidates
            candidates={entry.fix_candidates}
            needsHumanInput={entry.needs_human_input}
          />
        </Column>
      </div>
      <Column title="Impact preview">
        <ImpactPreview impact={entry.impact} />
      </Column>
      <DecisionPanel
        runId={runId}
        entry={entry}
        formAction={formAction}
        onFormActionChange={onFormActionChange}
      />
    </div>
  )
}
