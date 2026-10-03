import { CircleCheck, OctagonX } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { EvalEntry } from '@/api/types'
import { DataTable, type Column } from '@/components/DataTable'
import { DecisionChip } from '@/components/DecisionChip'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { humanize } from '@/lib/format'
import { sortBy } from '@/lib/sort'
import { cn } from '@/lib/utils'
import { entryDiff } from './evalDiff'

interface Row {
  e: EvalEntry
  diff: ReturnType<typeof entryDiff>
  failed: boolean
}

function RuleIds({ ids }: { ids: readonly string[] }) {
  if (ids.length === 0) return <span className="text-ink-muted">none</span>
  return <span className="num text-xs whitespace-normal">{ids.join(', ')}</span>
}

/** Marks a cell that differs from the expectation: tint, outline, icon and a spoken note. */
function Diff({ differs, children }: { differs: boolean; children: ReactNode }) {
  if (!differs) return <>{children}</>
  return (
    <span className="inline-flex items-center gap-1 rounded-sm bg-ledger-red-tint px-1 py-0.5 outline outline-1 outline-ledger-red/50">
      <OctagonX className="size-3.5 shrink-0 text-ledger-red" aria-hidden />
      {children}
      <span className="sr-only"> (differs from expected)</span>
    </span>
  )
}

function columns(runId: string): Column<Row>[] {
  return [
    {
      id: 'id',
      header: 'Case',
      rowHeader: true,
      sort: sortBy.string((r: Row) => r.e.id),
      cell: ({ e }) =>
        e.source === 'golden' ? (
          <Link
            to={`/runs/${encodeURIComponent(runId)}/entries/${encodeURIComponent(e.id)}`}
            className="num font-medium text-act underline"
          >
            {e.id}
          </Link>
        ) : (
          <span className="num font-medium">{e.id}</span>
        ),
    },
    {
      id: 'source',
      header: 'Set',
      sort: sortBy.string((r: Row) => r.e.source),
      cell: ({ e }) => (
        <span className="whitespace-nowrap text-ink-muted">
          {e.source} · {humanize(e.category).toLowerCase()}
        </span>
      ),
    },
    { id: 'exp_decision', header: 'Expected', cell: ({ e }) => <DecisionChip decision={e.expected_decision} /> },
    {
      id: 'act_decision',
      header: 'Actual',
      cell: ({ e, diff }) => (
        <Diff differs={diff.decision}>
          <DecisionChip decision={e.actual_decision} />
        </Diff>
      ),
    },
    { id: 'exp_rules', header: 'Expected rules', cell: ({ e }) => <RuleIds ids={e.expected_rule_ids} /> },
    {
      id: 'act_rules',
      header: 'Actual rules',
      cell: ({ e, diff }) => (
        <Diff differs={diff.rules}>
          <RuleIds ids={e.actual_rule_ids} />
        </Diff>
      ),
    },
    {
      id: 'llm',
      header: 'Reviewer findings (expected → actual)',
      cell: ({ e, diff }) => (
        <span className="inline-flex flex-wrap items-center gap-1">
          <RuleIds ids={e.expected_llm_rule_ids} />
          <span className="text-ink-muted" aria-label="then actual">
            →
          </span>
          <Diff differs={diff.llm}>
            <RuleIds ids={e.actual_llm_rule_ids} />
          </Diff>
          {e.llm_extra_allowed.length > 0 ? (
            <span className="text-xs text-ink-muted">(allowed: {e.llm_extra_allowed.join(', ')})</span>
          ) : null}
        </span>
      ),
    },
    {
      id: 'explanation',
      header: 'Explanation',
      sort: sortBy.string((r: Row) => r.e.explanation_source),
      cell: ({ e }) => <span className="text-ink-muted">{e.explanation_source}</span>,
    },
    {
      id: 'match',
      header: 'Result',
      sort: sortBy.number((r: Row) => (r.failed ? 0 : 1)),
      cell: ({ failed }) =>
        failed ? (
          <span className="inline-flex items-center gap-1 font-medium text-ledger-red">
            <OctagonX className="size-4" aria-hidden /> mismatch
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-ledger-green">
            <CircleCheck className="size-4" aria-hidden /> match
          </span>
        ),
    },
  ]
}

type Filter = 'all' | 'mismatch'

/** Expected vs actual per case; cells that differ are marked so a reviewer sees why a case failed. */
export function EvalEntriesTable({ runId, entries }: { runId: string; entries: EvalEntry[] }) {
  const [filter, setFilter] = useState<Filter>('all')
  const rows = useMemo<Row[]>(
    () =>
      entries.map((e) => {
        const diff = entryDiff(e)
        return { e, diff, failed: !e.match || diff.decision || diff.rules || diff.llm }
      }),
    [entries],
  )
  const failedCount = rows.filter((r) => r.failed).length
  const shown = filter === 'mismatch' ? rows.filter((r) => r.failed) : rows
  const cols = useMemo(() => columns(runId), [runId])

  return (
    <div className="flex flex-col gap-3">
      <ToggleGroup
        aria-label="Filter cases"
        variant="outline"
        size="sm"
        spacing={0}
        value={[filter]}
        onValueChange={(v) => {
          const next = v[0]
          if (next === 'all' || next === 'mismatch') setFilter(next)
        }}
      >
        <ToggleGroupItem className="aria-pressed:bg-act-tint aria-pressed:text-act data-[pressed]:bg-act-tint data-[pressed]:text-act" value="all">All cases ({rows.length})</ToggleGroupItem>
        <ToggleGroupItem className="aria-pressed:bg-act-tint aria-pressed:text-act data-[pressed]:bg-act-tint data-[pressed]:text-act" value="mismatch">Mismatches only ({failedCount})</ToggleGroupItem>
      </ToggleGroup>
      <DataTable
        columns={cols}
        rows={shown}
        getRowId={(r) => r.e.id}
        caption="Expected versus actual decision and findings for each evaluation case"
        rowClassName={(r) => cn(r.failed && 'bg-ledger-red-tint/40')}
        empty={<span className="text-ink-muted">No mismatches — every case matches its expectation.</span>}
      />
    </div>
  )
}
