import { ArrowRight, CircleCheck } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useHealth } from '@/api/queries'
import type { HealthFileSummary, HealthFinding, HealthResponse } from '@/api/types'
import { EmptyState, ErrorState, PageHeader, RunGate, SkeletonRows } from '@/components'
import { FileFindingsTable, FxPolicyPanel, HealthSummary } from '@/components/health'
import { buttonVariants } from '@/components/ui/button'
import { seg } from '@/api/client'

interface FileGroup {
  file: HealthFileSummary
  findings: HealthFinding[]
}

/** Groups in the server's file order; any file the summary omits is appended, never dropped. */
function groupByFile(data: HealthResponse): FileGroup[] {
  const groups: FileGroup[] = data.files.map((file) => ({
    file,
    findings: data.by_file[file.file] ?? data.findings.filter((f) => f.file === file.file),
  }))
  const known = new Set(data.files.map((f) => f.file))
  for (const f of data.findings) {
    if (known.has(f.file)) continue
    known.add(f.file)
    const findings = data.findings.filter((x) => x.file === f.file)
    groups.push({
      file: {
        file: f.file,
        label: f.file,
        listed_in_brief: 0,
        found: findings.length,
      },
      findings,
    })
  }
  return groups
}

function ContinueLink({ routeRunId }: { routeRunId: string }) {
  return (
    <Link to={`/runs/${seg(routeRunId)}/queue`} className={buttonVariants()}>
      Continue to review queue
      <ArrowRight aria-hidden />
    </Link>
  )
}

function HealthContent({ runId }: { runId: string }) {
  const { runId: routeRunId = runId } = useParams()
  const health = useHealth(runId)

  if (health.isError) {
    return (
      <ErrorState
        title="Couldn't load the data health audit"
        error={health.error}
        onRetry={() => void health.refetch()}
      />
    )
  }

  const data = health.data
  const groups = data ? groupByFile(data) : []

  return (
    <div className="flex flex-col gap-6">
      <HealthSummary data={data} />

      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_25rem]">
        <div className="flex min-w-0 flex-col gap-8">
          {!data ? (
            <SkeletonRows rows={6} columns={5} label="Loading defects" />
          ) : data.findings.length === 0 ? (
            <EmptyState
              icon={<CircleCheck />}
              title="No data defects found"
              description="The audit checked every input file and found nothing to report. The review queue is next."
            />
          ) : (
            groups.map((g) => (
              <FileFindingsTable key={g.file.file} file={g.file} findings={g.findings} />
            ))
          )}
        </div>

        <aside className="flex flex-col gap-4 xl:sticky xl:top-4">
          <FxPolicyPanel
            variants={data?.fx_variants}
            fxPolicy={data?.fx_policy}
            materiality={data?.materiality_tolerance}
            loading={!data}
          />
        </aside>
      </div>

      <div className="flex flex-wrap items-center gap-3 border-t border-rule pt-5">
        <ContinueLink routeRunId={routeRunId} />
        <p className="text-sm text-ink-muted">
          Defects are reported, never corrected in the input files.
        </p>
      </div>
    </div>
  )
}

export default function HealthPage() {
  const { runId = 'latest' } = useParams()
  return (
    <>
      <PageHeader
        title="Data health"
        description="Every defect the audit found in the input files, including those the brief does not list, with the evidence and the policy applied to each."
        actions={<ContinueLink routeRunId={runId} />}
      />
      <RunGate>{(id) => <HealthContent runId={id} />}</RunGate>
    </>
  )
}
