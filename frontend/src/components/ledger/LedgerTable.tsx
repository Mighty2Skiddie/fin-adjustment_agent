import { Search } from 'lucide-react'
import { useId, useMemo, useState } from 'react'
import type { PostedLine, PostedTbTotals } from '@/api/types'
import { DataTable } from '@/components/DataTable'
import { EmptyState } from '@/components/States'
import { Money } from '@/components/Money'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { groupByRoot, subtotal, type Subtotal } from './coaRoots'
import { GroupedLedgerTable } from './GroupedLedgerTable'
import { LEDGER_COLUMNS, lineageLabel } from './ledgerColumns'

export type LedgerGrouping = 'flat' | 'root'

function matches(line: PostedLine, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return line.account_code.toLowerCase().startsWith(q) || line.account_name.toLowerCase().includes(q)
}

function FlatTotalsRow({ label, totals }: { label: string; totals: Subtotal }) {
  return (
    <tr className="h-9 border-t-2 border-rule bg-band font-medium">
      <th scope="row" colSpan={2} className="px-3 py-1.5 text-left font-medium">
        {label}
      </th>
      <td className="px-3 py-1.5 text-right">
        <Money value={totals.debit} />
      </td>
      <td className="px-3 py-1.5 text-right">
        <Money value={totals.credit} />
      </td>
      <td className="px-3 py-1.5 text-right">
        <Money value={totals.net} />
      </td>
      <td colSpan={2} />
    </tr>
  )
}

export interface LedgerTableProps {
  lines: PostedLine[]
  totals: PostedTbTotals
  grouping: LedgerGrouping
  onGroupingChange: (g: LedgerGrouping) => void
  selectedCode: string | null
  onSelect: (line: PostedLine) => void
}

/** Toolbar (search, grouping) and the ledger table in either layout. */
export function LedgerTable({
  lines,
  totals,
  grouping,
  onGroupingChange,
  selectedCode,
  onSelect,
}: LedgerTableProps) {
  const [query, setQuery] = useState('')
  const searchId = useId()
  const filtered = useMemo(() => lines.filter((l) => matches(l, query)), [lines, query])
  const isFiltered = filtered.length !== lines.length

  // Unfiltered: the server's totals (the figures the invariants were checked on).
  // Filtered: an exact client-side sum of the visible lines.
  const shownTotals: Subtotal = isFiltered
    ? subtotal(filtered)
    : { debit: totals.debit, credit: totals.credit, net: totals.imbalance }
  const totalLabel = isFiltered
    ? `Total of ${filtered.length} shown ${filtered.length === 1 ? 'line' : 'lines'}`
    : 'Total, all lines'

  return (
    <section aria-labelledby="ledger-lines-heading" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 id="ledger-lines-heading" className="text-lg font-semibold text-ink">
          Ledger lines
          <span className="ml-2 text-sm font-normal text-ink-muted" aria-live="polite">
            {isFiltered ? `${filtered.length} of ${lines.length}` : `${lines.length} accounts`}
          </span>
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <label htmlFor={searchId} className="sr-only">
              Search by account code or name
            </label>
            <Search
              className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-ink-muted"
              aria-hidden
            />
            <Input
              id={searchId}
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Code or name"
              className="h-8 w-56 pl-8"
              autoComplete="off"
            />
          </div>
          <ToggleGroup
            aria-label="Group lines"
            variant="outline"
            size="sm"
            spacing={0}
            value={[grouping]}
            onValueChange={(v) => {
              const next = v[0]
              if (next === 'flat' || next === 'root') onGroupingChange(next)
            }}
          >
            <ToggleGroupItem className="aria-pressed:bg-act-tint aria-pressed:text-act data-[pressed]:bg-act-tint data-[pressed]:text-act" value="flat" aria-label="Flat list">
              Flat
            </ToggleGroupItem>
            <ToggleGroupItem className="aria-pressed:bg-act-tint aria-pressed:text-act data-[pressed]:bg-act-tint data-[pressed]:text-act" value="root" aria-label="Group by COA root">
              By COA root
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title={`No account matches "${query.trim()}"`}
          description="Search matches the start of an account code or any part of its name."
        />
      ) : grouping === 'root' ? (
        <GroupedLedgerTable
          groups={groupByRoot(filtered)}
          grandTotal={shownTotals}
          grandTotalLabel={totalLabel}
          selectedCode={selectedCode}
          onSelect={onSelect}
        />
      ) : (
        <DataTable
          columns={LEDGER_COLUMNS}
          rows={filtered}
          getRowId={(l) => l.account_code}
          caption="Adjusted trial balance, one line per account. Select a line to open its lineage."
          initialSort={{ id: 'code', direction: 'asc' }}
          onRowClick={onSelect}
          rowActionLabel={lineageLabel}
          selectedRowId={selectedCode}
          footer={<FlatTotalsRow label={totalLabel} totals={shownTotals} />}
        />
      )}
    </section>
  )
}
