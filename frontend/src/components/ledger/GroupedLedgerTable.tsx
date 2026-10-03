import type { KeyboardEvent, ReactNode } from 'react'
import type { PostedLine } from '@/api/types'
import { AssumptionChip } from '@/components/AssumptionChip'
import { Money } from '@/components/Money'
import { cn } from '@/lib/utils'
import { UNMAPPED_ROOT, type LedgerGroup, type Subtotal } from './coaRoots'
import { LEDGER_COLUMNS, lineageLabel } from './ledgerColumns'

const ALIGN = { left: 'text-left', right: 'text-right', center: 'text-center' } as const
const COLS = LEDGER_COLUMNS.length

function TotalsRow({ label, totals, strong }: { label: ReactNode; totals: Subtotal; strong?: boolean }) {
  return (
    <tr className={cn('h-9 border-b border-rule bg-band/60', strong && 'border-t-2 bg-band font-medium')}>
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
      <td colSpan={COLS - 5} />
    </tr>
  )
}

export interface GroupedLedgerTableProps {
  groups: LedgerGroup[]
  grandTotal: Subtotal
  grandTotalLabel: string
  selectedCode: string | null
  onSelect: (line: PostedLine) => void
}

/**
 * Ledger lines under COA root headings with an exact subtotal per root. One <tbody> per root
 * so assistive technology announces the group; unmapped lines sit in their own group and are
 * never added into a COA subtotal.
 */
export function GroupedLedgerTable({
  groups,
  grandTotal,
  grandTotalLabel,
  selectedCode,
  onSelect,
}: GroupedLedgerTableProps) {
  const onKey = (e: KeyboardEvent<HTMLTableRowElement>, line: PostedLine) => {
    if (e.target !== e.currentTarget) return
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onSelect(line)
    }
  }

  return (
    <div className="relative w-full rounded-sm border border-rule bg-surface max-md:overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Adjusted trial balance grouped by COA root, with subtotals</caption>
        <colgroup>
          {LEDGER_COLUMNS.map((c) => (
            <col key={c.id} style={c.width ? { width: c.width } : undefined} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {LEDGER_COLUMNS.map((c) => (
              <th
                key={c.id}
                scope="col"
                className={cn(
                  'sticky top-0 z-10 h-9 border-b border-rule bg-band px-3 font-medium whitespace-nowrap text-ink-muted',
                  ALIGN[c.align ?? 'left'],
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        {groups.map((g) => (
          <tbody key={g.key} aria-labelledby={`ledger-root-${g.key}`}>
            <tr className="border-b border-rule">
              <th
                id={`ledger-root-${g.key}`}
                scope="rowgroup"
                colSpan={COLS}
                className="bg-paper px-3 pt-4 pb-1.5 text-left font-semibold text-ink"
              >
                <span className="inline-flex flex-wrap items-center gap-2">
                  <span className="num text-ink-muted">{g.key}</span>
                  {g.label}
                  <span className="text-xs font-normal text-ink-muted">
                    {g.lines.length} {g.lines.length === 1 ? 'line' : 'lines'}
                  </span>
                  {g.key === UNMAPPED_ROOT ? (
                    <>
                      <span className="text-xs font-normal text-ink-muted">
                        kept out of COA subtotals
                      </span>
                      <AssumptionChip id="A6" />
                    </>
                  ) : null}
                </span>
              </th>
            </tr>
            {g.lines.map((line, i) => {
              const selected = selectedCode === line.account_code
              return (
                <tr
                  key={line.account_code}
                  data-row-id={line.account_code}
                  tabIndex={0}
                  aria-selected={selected}
                  aria-label={lineageLabel(line)}
                  onClick={() => onSelect(line)}
                  onKeyDown={(e) => onKey(e, line)}
                  className={cn(
                    'h-9 cursor-pointer border-b border-rule hover:bg-band focus-visible:-outline-offset-2',
                    selected && 'bg-act-tint hover:bg-act-tint',
                  )}
                >
                  {LEDGER_COLUMNS.map((c) => {
                    const Cell = c.rowHeader ? 'th' : 'td'
                    return (
                      <Cell
                        key={c.id}
                        scope={c.rowHeader ? 'row' : undefined}
                        className={cn('px-3 py-1.5 align-middle font-normal', ALIGN[c.align ?? 'left'])}
                      >
                        {c.cell(line, i)}
                      </Cell>
                    )
                  })}
                </tr>
              )
            })}
            <TotalsRow label={`Subtotal · ${g.label.toLowerCase()}`} totals={g.totals} />
          </tbody>
        ))}
        <tbody>
          <TotalsRow label={grandTotalLabel} totals={grandTotal} strong />
        </tbody>
      </table>
    </div>
  )
}
