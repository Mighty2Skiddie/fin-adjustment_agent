import { FlaskConical } from 'lucide-react'
import { useEvals } from '@/api/queries'
import {
  EmptyState,
  ErrorState,
  JsonToggle,
  PageHeader,
  RunGate,
  SectionHeading,
  SkeletonRows,
} from '@/components'
import {
  EvalEntriesTable,
  EvalGateBanner,
  EvalProblems,
  EvalSummaryTable,
  PerRuleTable,
  entryDiff,
} from '@/components/evals'

function EvalsContent({ runId }: { runId: string }) {
  const q = useEvals(runId)

  if (q.isPending) {
    return (
      <div className="flex flex-col gap-6">
        <SkeletonRows rows={3} columns={1} label="Loading the evaluation report" />
        <SkeletonRows rows={10} columns={3} label="Loading the evaluation report" />
      </div>
    )
  }
  if (q.isError) {
    if (q.error.code === 'evals_missing' || q.error.status === 404) {
      return (
        <EmptyState
          icon={<FlaskConical />}
          title="No evaluation report for this run yet"
          description={
            <>
              Run <code className="rounded-sm bg-band px-1">finagent eval</code> (
              <code className="rounded-sm bg-band px-1">uv run finagent eval</code>) to score this run against
              the golden decisions, then reload this page.
            </>
          }
        />
      )
    }
    return (
      <ErrorState error={q.error} onRetry={() => void q.refetch()} title="Couldn't load the evaluation report" />
    )
  }

  const report = q.data
  const mismatches = report.entries.filter((e) => {
    const d = entryDiff(e)
    return !e.match || d.decision || d.rules || d.llm
  }).length

  return (
    <div className="flex flex-col gap-8">
      <EvalGateBanner report={report} mismatches={mismatches} />

      <section aria-labelledby="evals-summary" className="max-w-4xl">
        <SectionHeading id="evals-summary">Summary</SectionHeading>
        <EvalSummaryTable summary={report.summary} />
      </section>

      <section aria-labelledby="evals-rules" className="max-w-4xl">
        <SectionHeading id="evals-rules" aside="defect detection across golden and synthetic cases">
          Precision and recall per rule
        </SectionHeading>
        <PerRuleTable perRule={report.per_rule} />
      </section>

      <section aria-labelledby="evals-entries">
        <SectionHeading id="evals-entries" aside="differing cells are outlined in red">
          Expected vs actual, per case
        </SectionHeading>
        <EvalEntriesTable runId={runId} entries={report.entries} />
      </section>

      <section aria-labelledby="evals-problems" className="flex flex-col gap-3">
        <SectionHeading id="evals-problems">Guardrail checks on LLM output</SectionHeading>
        <EvalProblems report={report} />
        <JsonToggle data={report} label="full report JSON" />
      </section>
    </div>
  )
}

export default function EvalsPage() {
  return (
    <>
      <PageHeader
        title="Evaluation"
        description="How this run scores against the golden decisions and synthetic cases. The gate must pass before a build ships."
      />
      <RunGate>{(runId) => <EvalsContent runId={runId} />}</RunGate>
    </>
  )
}
