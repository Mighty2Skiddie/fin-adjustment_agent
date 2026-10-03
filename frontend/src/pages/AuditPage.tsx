import { Download } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { useAuditLog, useRun } from '@/api/queries'
import { ErrorState, PageHeader, RunGate, SectionHeading } from '@/components'
import { AuditLogTable, downloadJsonl, ManifestPanel, MetricsStrip } from '@/components/audit'
import { Button } from '@/components/ui/button'
import { formatCount } from '@/lib/money'

function AuditLogSection({ runId, routeRunId }: { runId: string; routeRunId: string }) {
  const log = useAuditLog(runId)
  const events = log.data
  return (
    <section aria-labelledby="audit-log-heading" className="flex flex-col">
      <SectionHeading
        id="audit-log-heading"
        aside={
          <span className="flex flex-wrap items-center gap-3">
            {events ? (
              <span>
                <span className="num text-ink">{formatCount(events.length)}</span> events
              </span>
            ) : null}
            <Button
              variant="outline"
              size="sm"
              disabled={!events || events.length === 0}
              onClick={() => events && downloadJsonl(events, `audit-log-${runId}.jsonl`)}
            >
              <Download aria-hidden />
              Download audit log (JSONL)
            </Button>
          </span>
        }
      >
        Audit log
      </SectionHeading>
      {log.isError ? (
        <ErrorState
          title="Couldn't load the audit log"
          error={log.error}
          onRetry={() => void log.refetch()}
        />
      ) : (
        <AuditLogTable events={events} routeRunId={routeRunId} loading={log.isPending} />
      )}
    </section>
  )
}

function AuditContent({ runId, routeRunId }: { runId: string; routeRunId: string }) {
  const run = useRun(runId)
  return (
    <div className="flex flex-col gap-8">
      {run.isError ? (
        <ErrorState
          title="Couldn't load the run manifest"
          error={run.error}
          onRetry={() => void run.refetch()}
        />
      ) : (
        <>
          <ManifestPanel manifest={run.data} />
          <MetricsStrip metrics={run.data?.metrics} />
        </>
      )}
      <AuditLogSection runId={runId} routeRunId={routeRunId} />
    </div>
  )
}

export default function AuditPage() {
  const { runId: routeRunId = 'latest' } = useParams()
  return (
    <>
      <PageHeader
        title="Audit"
        description="What produced this run, how it performed, and every decision recorded against it, system and human."
      />
      <RunGate>{(runId) => <AuditContent runId={runId} routeRunId={routeRunId} />}</RunGate>
    </>
  )
}
