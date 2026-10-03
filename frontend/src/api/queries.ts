import {
  QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { ApiError, apiGet, apiGetText, apiPost, seg } from './client'
import type {
  AuditEvent,
  DecisionRequest,
  DecisionResponse,
  EntryDetail,
  EntryView,
  EvalReport,
  HealthResponse,
  LineageResponse,
  Manifest,
  PostedTb,
  RunSummary,
  TraceEvent,
} from './types'

/* ----------------------------------------------------------- query client */

/** Retry only transient failures (network / 5xx); a 4xx will not fix itself. */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && (error.status === 0 || error.status >= 500)) {
    return failureCount < 2
  }
  return false
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, staleTime: 30_000, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  })
}

/* ------------------------------------------------------------- query keys */

export const queryKeys = {
  runs: () => ['runs'] as const,
  run: (runId: string) => ['run', runId] as const,
  health: (runId: string) => ['run', runId, 'health'] as const,
  entries: (runId: string) => ['run', runId, 'entries'] as const,
  entry: (runId: string, jeId: string) => ['run', runId, 'entry', jeId] as const,
  postedTb: (runId: string) => ['run', runId, 'posted-tb'] as const,
  lineageAll: (runId: string) => ['run', runId, 'lineage'] as const,
  lineage: (runId: string, account: string) => ['run', runId, 'lineage', account] as const,
  traceAll: (runId: string) => ['run', runId, 'trace'] as const,
  trace: (runId: string, jeId: string) => ['run', runId, 'trace', jeId] as const,
  auditLog: (runId: string) => ['run', runId, 'audit-log'] as const,
  evals: (runId: string) => ['run', runId, 'evals'] as const,
  architectureDoc: () => ['docs', 'architecture'] as const,
}

/* --------------------------------------------------------------- run id */

export interface RunIdState {
  /** The concrete run id (never "latest"); undefined while resolving or when not found. */
  runId: string | undefined
  /** What the URL said: a run id or "latest". */
  routeRunId: string
  isLoading: boolean
  /** True when the URL names a run the server does not have. */
  notFound: boolean
  /** The latest run id, for "open the latest run" links. */
  latestRunId: string | undefined
  error: ApiError | null
  refetch: () => void
}

/**
 * Resolves the `:runId` route param. "latest" maps to the run flagged `latest` by GET /api/runs
 * (or the first item), so every cache key and mutation uses a concrete id.
 */
export function useRunId(): RunIdState {
  const { runId: param } = useParams<{ runId: string }>()
  const routeRunId = param ?? 'latest'
  const runs = useRuns()
  const list = runs.data
  const latest = list?.find((r) => r.latest)?.run_id ?? list?.[0]?.run_id
  let runId: string | undefined
  let notFound = false
  if (list) {
    if (routeRunId === 'latest') {
      runId = latest
      notFound = latest === undefined
    } else if (list.some((r) => r.run_id === routeRunId)) {
      runId = routeRunId
    } else {
      notFound = true
    }
  }
  return {
    runId,
    routeRunId,
    isLoading: runs.isPending,
    notFound,
    latestRunId: latest,
    error: runs.error,
    refetch: () => void runs.refetch(),
  }
}

/* ---------------------------------------------------------------- queries */

type Q<T> = UseQueryResult<T, ApiError>

export function useRuns(): Q<RunSummary[]> {
  return useQuery<RunSummary[], ApiError>({
    queryKey: queryKeys.runs(),
    queryFn: ({ signal }) => apiGet<RunSummary[]>('/runs', signal),
  })
}

export function useRun(runId: string | undefined): Q<Manifest> {
  return useQuery<Manifest, ApiError>({
    queryKey: queryKeys.run(runId ?? ''),
    queryFn: ({ signal }) => apiGet<Manifest>(`/runs/${seg(runId ?? '')}`, signal),
    enabled: !!runId,
  })
}

export function useHealth(runId: string | undefined): Q<HealthResponse> {
  return useQuery<HealthResponse, ApiError>({
    queryKey: queryKeys.health(runId ?? ''),
    queryFn: ({ signal }) => apiGet<HealthResponse>(`/runs/${seg(runId ?? '')}/health`, signal),
    enabled: !!runId,
  })
}

export function useEntries(runId: string | undefined): Q<EntryView[]> {
  return useQuery<EntryView[], ApiError>({
    queryKey: queryKeys.entries(runId ?? ''),
    queryFn: ({ signal }) => apiGet<EntryView[]>(`/runs/${seg(runId ?? '')}/entries`, signal),
    enabled: !!runId,
  })
}

export function useEntry(runId: string | undefined, jeId: string | undefined): Q<EntryDetail> {
  return useQuery<EntryDetail, ApiError>({
    queryKey: queryKeys.entry(runId ?? '', jeId ?? ''),
    queryFn: ({ signal }) =>
      apiGet<EntryDetail>(`/runs/${seg(runId ?? '')}/entries/${seg(jeId ?? '')}`, signal),
    enabled: !!runId && !!jeId,
  })
}

export function usePostedTb(runId: string | undefined): Q<PostedTb> {
  return useQuery<PostedTb, ApiError>({
    queryKey: queryKeys.postedTb(runId ?? ''),
    queryFn: ({ signal }) => apiGet<PostedTb>(`/runs/${seg(runId ?? '')}/posted-tb`, signal),
    enabled: !!runId,
  })
}

export function useLineage(
  runId: string | undefined,
  account: string | null | undefined,
): Q<LineageResponse> {
  return useQuery<LineageResponse, ApiError>({
    queryKey: queryKeys.lineage(runId ?? '', account ?? ''),
    queryFn: ({ signal }) =>
      apiGet<LineageResponse>(`/runs/${seg(runId ?? '')}/lineage/${seg(account ?? '')}`, signal),
    enabled: !!runId && !!account,
  })
}

export function useTrace(runId: string | undefined, jeId: string | undefined): Q<TraceEvent[]> {
  return useQuery<TraceEvent[], ApiError>({
    queryKey: queryKeys.trace(runId ?? '', jeId ?? ''),
    queryFn: ({ signal }) =>
      apiGet<TraceEvent[]>(`/runs/${seg(runId ?? '')}/trace/${seg(jeId ?? '')}`, signal),
    enabled: !!runId && !!jeId,
  })
}

export function useAuditLog(runId: string | undefined): Q<AuditEvent[]> {
  return useQuery<AuditEvent[], ApiError>({
    queryKey: queryKeys.auditLog(runId ?? ''),
    queryFn: ({ signal }) => apiGet<AuditEvent[]>(`/runs/${seg(runId ?? '')}/audit-log`, signal),
    enabled: !!runId,
  })
}

/** 404 with code `evals_missing` means `finagent eval` has not run: show the empty state. */
export function useEvals(runId: string | undefined): Q<EvalReport> {
  return useQuery<EvalReport, ApiError>({
    queryKey: queryKeys.evals(runId ?? ''),
    queryFn: ({ signal }) => apiGet<EvalReport>(`/runs/${seg(runId ?? '')}/evals`, signal),
    enabled: !!runId,
  })
}

/** ARCHITECTURE.md as markdown text. */
export function useArchitectureDoc(): Q<string> {
  return useQuery<string, ApiError>({
    queryKey: queryKeys.architectureDoc(),
    queryFn: ({ signal }) => apiGetText('/docs/architecture', signal),
    staleTime: Infinity,
  })
}

/* --------------------------------------------------------------- mutation */

export interface DecisionVariables extends DecisionRequest {
  jeId: string
}

/**
 * Records a reviewer decision. No optimistic update: the UI shows the server-confirmed state
 * only, so on success we invalidate every view the decision changes and let them refetch.
 * Errors are ApiErrors (400 rejected/accepted/short reason, 409 already decided).
 */
export function useDecision(runId: string | undefined) {
  const qc = useQueryClient()
  return useMutation<DecisionResponse, ApiError, DecisionVariables>({
    mutationFn: ({ jeId, action, actor, reason }) => {
      if (!runId) {
        return Promise.reject(new ApiError(0, 'no_run', 'The run is still loading. Try again.'))
      }
      return apiPost<DecisionResponse>(`/runs/${seg(runId)}/entries/${seg(jeId)}/decision`, {
        action,
        actor,
        reason,
      })
    },
    onError: (error) => {
      // Hook-level so it fires even when the refetch below unmounts the form that sent it.
      if (error.status === 409) toast.error(error.messageForUser)
    },
    onSettled: async (_data, error, { jeId }) => {
      // A 409 means someone else decided first: refetch so the page shows the server state.
      if (!runId || (error && error.status !== 409)) return
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.entries(runId) }),
        qc.invalidateQueries({ queryKey: queryKeys.entry(runId, jeId) }),
        qc.invalidateQueries({ queryKey: queryKeys.postedTb(runId) }),
        qc.invalidateQueries({ queryKey: queryKeys.lineageAll(runId) }),
        qc.invalidateQueries({ queryKey: queryKeys.auditLog(runId) }),
        qc.invalidateQueries({ queryKey: queryKeys.traceAll(runId) }),
      ])
    },
  })
}
