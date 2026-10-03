import { FileQuestion } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useRunId } from '@/api/queries'
import { buttonVariants } from '@/components/ui/button'
import { useSamePageOnRun } from '@/hooks/useSamePageOnRun'
import { SkeletonRows } from './SkeletonRows'
import { EmptyState, ErrorState } from './States'

function RunNotFound({ routeRunId }: { routeRunId: string }) {
  const latestHref = useSamePageOnRun('latest')
  return (
    <EmptyState
      icon={<FileQuestion />}
      title={`Run ${routeRunId} was not found`}
      description="It may have been created on another machine or removed from output/runs. Open the latest run instead."
      action={
        <Link to={latestHref} className={buttonVariants({ size: 'sm' })}>
          Open the latest run
        </Link>
      }
    />
  )
}

/**
 * Resolves the `:runId` route param (incl. "latest") before rendering a page. Handles the
 * loading, error and unknown-run states so pages only deal with a concrete run id.
 *
 *   <RunGate>{(runId) => <QueueContent runId={runId} />}</RunGate>
 */
export function RunGate({ children }: { children: (runId: string) => ReactNode }) {
  const { runId, routeRunId, isLoading, notFound, error, refetch } = useRunId()
  if (isLoading) return <SkeletonRows rows={6} columns={5} label="Loading run" />
  if (error) return <ErrorState error={error} onRetry={refetch} title="Couldn't load the runs" />
  if (notFound || !runId) {
    if (routeRunId === 'latest') {
      return (
        <EmptyState
          title="No runs yet"
          description={
            <>
              Run <code>uv run finagent run</code>, or start the server with{' '}
              <code>uv run finagent serve</code>, which creates one automatically.
            </>
          }
        />
      )
    }
    return <RunNotFound routeRunId={routeRunId} />
  }
  return <>{children(runId)}</>
}
