import { ChevronRight, ExternalLink } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { EntryView, HumanAction } from '@/api/types'
import { DataTable, type Column } from '@/components/DataTable'
import { DecisionChip } from '@/components/DecisionChip'
import { Money } from '@/components/Money'
import { SeverityChip } from '@/components/SeverityChip'
import { effectiveStateLabel, formatDate, formatTimestamp } from '@/lib/format'
import { sortBy } from '@/lib/sort'
import { decisionLabel } from '@/lib/status'
import { cn } from '@/lib/utils'
import { EntryPanel } from './EntryPanel'
import { panelId, totalDebits, worstFinding } from './queueModel'

export interface FormTarget {
  jeId: string
  action: HumanAction
}

export interface QueueTableProps {
  runId: string
  rows: EntryView[] | undefined
  loading: boolean
  empty: ReactNode
  llmMode?: string
  expanded: ReadonlySet<string>
  activeId: string | null
  form: FormTarget | null
  onToggle: (jeId: string) => void
  onFormChange: (target: FormTarget | null) => void
  /** Visible width of the table box; keeps the expansion on screen when the table scrolls sideways. */
  panelWidth?: number
}

function columns(expanded: ReadonlySet<string>, onToggle: (id: string) => void): Column<EntryView>[] {
  return [
    {
      id: 'id',
      header: 'JE',
      width: '6.5rem',
      rowHeader: true,
      sort: sortBy.string((e) => e.entry.id),
      cell: (e) => (
        <span className="font-mono font-medium whitespace-nowrap">
          {e.entry.id}
          {e.entry.version > 1 ? (
            <span className="ml-1 text-xs text-ink-muted">v{e.entry.version}</span>
          ) : null}
        </span>
      ),
    },
    {
      id: 'description',
      header: 'Description',
      cell: (e) => <span className="line-clamp-2 break-words">{e.entry.description}</span>,
    },
    {
      id: 'date',
      header: 'Date',
      width: '7rem',
      sort: sortBy.string((e) => e.entry.date),
      className: 'max-md:hidden',
      headerClassName: 'max-md:hidden',
      cell: (e) => <span className="num">{formatDate(e.entry.date)}</span>,
    },
    {
      id: 'total',
      header: 'Total debits',
      width: '9.5rem',
      align: 'right',
      sort: sortBy.decimal(totalDebits),
      cell: (e) => <Money value={totalDebits(e)} />,
    },
    {
      id: 'decision',
      header: 'Decision',
      width: '9rem',
      cell: (e) => (
        <span className="flex flex-col items-start gap-0.5">
          <DecisionChip decision={e.effective_decision} />
          {e.human_decision ? (
            <span className="text-xs text-ink-muted">System: {decisionLabel(e.decision).toLowerCase()}</span>
          ) : null}
        </span>
      ),
    },
    {
      id: 'findings',
      header: 'Findings',
      width: '8rem',
      sort: sortBy.number((e) => e.findings.length),
      cell: (e) => {
        const worst = worstFinding(e)
        return (
          <span className="inline-flex items-center gap-2">
            <span className="num w-4 text-right">{e.findings.length}</span>
            {worst ? <SeverityChip severity={worst.severity} className="max-sm:hidden" /> : null}
          </span>
        )
      },
    },
    {
      id: 'state',
      header: 'Effective state',
      width: '10rem',
      className: 'max-md:hidden',
      headerClassName: 'max-md:hidden',
      cell: (e) =>
        e.human_decision ? (
          <span title={formatTimestamp(e.human_decision.ts)} className="[overflow-wrap:anywhere]">
            {effectiveStateLabel(e.effective_state)}
          </span>
        ) : (
          <span className="text-ink-muted">{effectiveStateLabel(e.effective_state)}</span>
        ),
    },
    {
      id: 'expand',
      header: <span className="sr-only">Expand</span>,
      width: '3rem',
      align: 'right',
      cell: (e) => {
        const open = expanded.has(e.entry.id)
        return (
          <button
            type="button"
            aria-expanded={open}
            aria-controls={open ? panelId(e.entry.id) : undefined}
            aria-label={`${open ? 'Collapse' : 'Expand'} ${e.entry.id}`}
            onClick={(ev) => {
              ev.stopPropagation()
              onToggle(e.entry.id)
            }}
            className="inline-flex size-7 items-center justify-center rounded-sm text-ink-muted hover:bg-band hover:text-ink"
          >
            <ChevronRight
              aria-hidden
              className={cn('size-4 transition-transform duration-150', open && 'rotate-90')}
            />
          </button>
        )
      },
    },
  ]
}

function ExpandedEntry({
  runId,
  entry,
  llmMode,
  form,
  onFormChange,
  width,
}: {
  runId: string
  entry: EntryView
  llmMode?: string
  form: FormTarget | null
  onFormChange: (target: FormTarget | null) => void
  width?: number
}) {
  const jeId = entry.entry.id
  const detailHref = `/runs/${encodeURIComponent(runId)}/entries/${encodeURIComponent(jeId)}`
  return (
    <div
      id={panelId(jeId)}
      role="region"
      aria-label={`${jeId} working paper`}
      style={width ? { width } : undefined}
      className="sticky left-0 animate-in border-l-2 border-act bg-paper px-4 py-4 duration-150 fade-in-0 slide-in-from-top-1 sm:px-5"
    >
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm text-ink-muted">
          <span className="font-mono text-ink">{jeId}</span> · {entry.entry.source} · version{' '}
          <span className="num">{entry.entry.version}</span>
        </p>
        <Link
          to={detailHref}
          className="inline-flex items-center gap-1 text-sm text-act underline-offset-4 hover:underline"
        >
          Open entry page
          <ExternalLink className="size-3.5" aria-hidden />
        </Link>
      </div>
      <EntryPanel
        runId={runId}
        entry={entry}
        llmMode={llmMode}
        traceHref={`${detailHref}#trace`}
        formAction={form?.jeId === jeId ? form.action : null}
        onFormActionChange={(action) => onFormChange(action ? { jeId, action } : null)}
      />
    </div>
  )
}

/** The queue: dense rows that unfold in place into the entry's working paper. */
export function QueueTable({
  runId,
  rows,
  loading,
  empty,
  llmMode,
  expanded,
  activeId,
  form,
  onToggle,
  onFormChange,
  panelWidth,
}: QueueTableProps) {
  return (
    <DataTable
      caption="Journal entries in this run, needs review first. Select a row to expand it."
      columns={columns(expanded, onToggle)}
      rows={rows}
      getRowId={(e) => e.entry.id}
      loading={loading}
      skeletonRows={10}
      empty={empty}
      onRowClick={(e) => onToggle(e.entry.id)}
      selectedRowId={activeId}
      rowClassName={(e) => (expanded.has(e.entry.id) ? 'border-b-0' : undefined)}
      renderAfterRow={(e) =>
        expanded.has(e.entry.id) ? (
          <ExpandedEntry
            runId={runId}
            entry={e}
            llmMode={llmMode}
            form={form}
            onFormChange={onFormChange}
            width={panelWidth}
          />
        ) : null
      }
    />
  )
}
