import { CircleCheck } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState, type FocusEvent, type RefObject } from 'react'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { useEntries, useRun } from '@/api/queries'
import type { EntryView, HumanAction } from '@/api/types'
import { EmptyState, ErrorState, KeyboardHints, PageHeader, RunGate } from '@/components'
import { QueueFilters } from '@/components/entry/QueueFilters'
import { QueueTable, type FormTarget } from '@/components/entry/QueueTable'
import {
  autoAcceptedCount,
  filterCounts,
  matchesFilter,
  parseQueueFilter,
  queueOrder,
  type QueueFilter,
} from '@/components/entry/queueModel'
import { Button } from '@/components/ui/button'
import { useHotkeys } from '@/hooks/useHotkeys'
import { canDecide } from '@/lib/entry'

const HINTS = [
  { keys: ['j', 'k'], label: 'next / previous entry' },
  { keys: ['Enter'], label: 'expand' },
  { keys: ['a'], label: 'approve' },
  { keys: ['r'], label: 'reject' },
  { keys: ['Esc'], label: 'close' },
]

function notDecidableMessage(entry: EntryView): string {
  if (entry.human_decision) return `${entry.entry.id} already has a reviewer decision.`
  if (entry.decision === 'REJECTED') {
    return "Rejected entries can't be approved. Edit the entry and resubmit as a new version."
  }
  return 'Posted automatically — all checks passed.'
}

function EmptyForFilter({
  filter,
  autoAccepted,
  onShowAll,
}: {
  filter: QueueFilter
  autoAccepted: number
  onShowAll: () => void
}) {
  const showAll = (
    <Button variant="outline" size="sm" onClick={onShowAll}>
      Show all entries
    </Button>
  )
  if (filter === 'review') {
    return (
      <EmptyState
        icon={<CircleCheck />}
        title={`No entries need review — ${autoAccepted} accepted automatically.`}
        action={showAll}
      />
    )
  }
  if (filter === 'rejected') return <EmptyState title="No rejected entries." action={showAll} />
  if (filter === 'accepted') return <EmptyState title="No accepted entries yet." action={showAll} />
  return (
    <EmptyState
      title="This run has no journal entries."
      description="The adjustments batch was empty, so there is nothing to review."
    />
  )
}

/** Inner width of the table box (minus its 1px borders), tracked as the layout changes. */
function useInnerWidth(ref: RefObject<HTMLDivElement | null>): number | undefined {
  const [width, setWidth] = useState<number | undefined>(undefined)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setWidth(Math.max(0, Math.floor(entry.contentRect.width) - 2))
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [ref])
  return width
}

function QueueContent({ runId }: { runId: string }) {
  const entries = useEntries(runId)
  const run = useRun(runId)
  const [params, setParams] = useSearchParams()
  const filter = parseQueueFilter(params.get('filter'))
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(
    () => new Set((params.get('open') ?? '').split(',').filter(Boolean)),
  )
  const [activeId, setActiveId] = useState<string | null>(() => params.get('open')?.split(',')[0] ?? null)
  const [form, setForm] = useState<FormTarget | null>(null)
  const tableRef = useRef<HTMLDivElement>(null)
  const panelWidth = useInnerWidth(tableRef)

  const all = entries.data
  const rows = useMemo(
    () => (all ? queueOrder(all.filter((e) => matchesFilter(e, filter))) : undefined),
    [all, filter],
  )
  const counts = useMemo(() => (all ? filterCounts(all) : undefined), [all])
  const byId = useMemo(() => new Map((all ?? []).map((e) => [e.entry.id, e])), [all])

  const syncOpenParam = useCallback(
    (next: ReadonlySet<string>) => {
      setParams(
        (prev) => {
          const p = new URLSearchParams(prev)
          if (next.size > 0) p.set('open', [...next].join(','))
          else p.delete('open')
          return p
        },
        { replace: true },
      )
    },
    [setParams],
  )

  const setExpandedAndSync = (next: ReadonlySet<string>) => {
    setExpanded(next)
    syncOpenParam(next)
  }

  const toggle = (jeId: string) => {
    const next = new Set(expanded)
    if (next.has(jeId)) {
      next.delete(jeId)
      if (form?.jeId === jeId) setForm(null)
    } else next.add(jeId)
    setActiveId(jeId)
    setExpandedAndSync(next)
  }

  const changeFilter = (f: QueueFilter) => {
    const keep = new Set([...expanded].filter((id) => {
      const e = byId.get(id)
      return e ? matchesFilter(e, f) : false
    }))
    if (form && !keep.has(form.jeId)) setForm(null)
    setExpanded(keep)
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev)
        if (f === 'all') p.delete('filter')
        else p.set('filter', f)
        if (keep.size > 0) p.set('open', [...keep].join(','))
        else p.delete('open')
        return p
      },
      { replace: true },
    )
  }

  const rowElements = () =>
    Array.from(tableRef.current?.querySelectorAll<HTMLTableRowElement>('tbody tr[data-row-id]') ?? [])

  const focusRow = (row: HTMLTableRowElement | undefined) => {
    if (!row) return
    row.focus()
    row.scrollIntoView({ block: 'nearest' })
    setActiveId(row.dataset.rowId ?? null)
  }

  const move = (delta: 1 | -1) => {
    const list = rowElements()
    if (list.length === 0) return
    const idx = list.findIndex((r) => r.dataset.rowId === activeId)
    const nextIdx = idx < 0 ? (delta === 1 ? 0 : list.length - 1) : Math.min(list.length - 1, Math.max(0, idx + delta))
    focusRow(list[nextIdx])
  }

  const openForm = (event: KeyboardEvent, action: HumanAction) => {
    const entry = activeId ? byId.get(activeId) : undefined
    if (!entry) return
    event.preventDefault()
    if (!canDecide(entry)) {
      toast.info(notDecidableMessage(entry), { description: entry.entry.id })
      return
    }
    if (!expanded.has(entry.entry.id)) setExpandedAndSync(new Set(expanded).add(entry.entry.id))
    setForm({ jeId: entry.entry.id, action })
  }

  useHotkeys(
    {
      j: (e) => {
        e.preventDefault()
        move(1)
      },
      k: (e) => {
        e.preventDefault()
        move(-1)
      },
      a: (e) => openForm(e, 'APPROVED'),
      r: (e) => openForm(e, 'REJECTED'),
      Escape: () => {
        if (form) {
          setForm(null)
          return
        }
        if (activeId && expanded.has(activeId)) {
          toggle(activeId)
          focusRow(rowElements().find((r) => r.dataset.rowId === activeId))
        }
      },
    },
    !!all,
  )

  const onFocusCapture = (e: FocusEvent<HTMLDivElement>) => {
    const row = (e.target as HTMLElement).closest<HTMLTableRowElement>('tr[data-row-id]')
    if (row?.dataset.rowId) setActiveId(row.dataset.rowId)
  }

  if (entries.error) {
    return (
      <ErrorState
        error={entries.error}
        onRetry={() => void entries.refetch()}
        title="Couldn't load the review queue"
      />
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <QueueFilters value={filter} counts={counts} onChange={changeFilter} />
        <KeyboardHints hints={HINTS} className="max-md:hidden" />
      </div>
      <div ref={tableRef} onFocusCapture={onFocusCapture}>
        <QueueTable
          runId={runId}
          rows={rows}
          loading={entries.isPending}
          empty={
            <EmptyForFilter
              filter={filter}
              autoAccepted={all ? autoAcceptedCount(all) : 0}
              onShowAll={() => changeFilter('all')}
            />
          }
          llmMode={run.data?.llm_mode}
          expanded={expanded}
          activeId={activeId}
          form={form}
          onToggle={toggle}
          onFormChange={setForm}
          panelWidth={panelWidth}
        />
      </div>
      <p className="text-xs text-ink-muted">
        Decisions are recorded against the run and never change the system result. Only
        quarantined entries can be approved; approval posts the entry as submitted.
      </p>
    </div>
  )
}

export default function QueuePage() {
  return (
    <>
      <PageHeader
        title="Review queue"
        description="Every journal entry in the batch with the system's decision. Expand an entry to see its lines, findings, explanation and proposed fixes, then approve or reject the ones held for review."
      />
      <RunGate>{(runId) => <QueueContent key={runId} runId={runId} />}</RunGate>
    </>
  )
}
