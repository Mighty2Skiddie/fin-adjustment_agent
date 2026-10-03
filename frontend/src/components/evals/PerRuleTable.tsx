import type { RulePrecisionRecall } from '@/api/types'
import { DataTable, type Column } from '@/components/DataTable'
import { decimalEquals } from '@/components/ledger/decimal'
import { formatPct } from '@/lib/money'
import { sortBy } from '@/lib/sort'
import { cn } from '@/lib/utils'

interface Row extends RulePrecisionRecall {
  rule: string
}

function Ratio({ value }: { value: string }) {
  const perfect = decimalEquals(value, '1')
  return (
    <span className={cn('num', !perfect && 'font-medium text-ledger-red')}>
      {formatPct(value)}
      {!perfect ? <span className="sr-only"> (below 100%)</span> : null}
    </span>
  )
}

function Count({ n, bad }: { n: number; bad?: boolean }) {
  return <span className={cn('num', bad && n > 0 ? 'font-medium text-ledger-red' : n === 0 && 'text-ink-muted')}>{n}</span>
}

const COLUMNS: Column<Row>[] = [
  {
    id: 'rule',
    header: 'Rule',
    rowHeader: true,
    sort: sortBy.string((r: Row) => r.rule),
    cell: (r) => <span className="num font-medium">{r.rule}</span>,
  },
  { id: 'tp', header: 'True pos.', align: 'right', sort: sortBy.number((r: Row) => r.tp), cell: (r) => <Count n={r.tp} /> },
  { id: 'fp', header: 'False pos.', align: 'right', sort: sortBy.number((r: Row) => r.fp), cell: (r) => <Count n={r.fp} bad /> },
  { id: 'fn', header: 'False neg.', align: 'right', sort: sortBy.number((r: Row) => r.fn), cell: (r) => <Count n={r.fn} bad /> },
  {
    id: 'precision',
    header: 'Precision',
    align: 'right',
    sort: sortBy.decimal((r: Row) => r.precision),
    cell: (r) => <Ratio value={r.precision} />,
  },
  {
    id: 'recall',
    header: 'Recall',
    align: 'right',
    sort: sortBy.decimal((r: Row) => r.recall),
    cell: (r) => <Ratio value={r.recall} />,
  },
]

/** Defect-detection precision and recall per deterministic rule. */
export function PerRuleTable({ perRule }: { perRule: Record<string, RulePrecisionRecall> }) {
  const rows: Row[] = Object.entries(perRule).map(([rule, v]) => ({ rule, ...v }))
  return (
    <DataTable
      columns={COLUMNS}
      rows={rows}
      getRowId={(r) => r.rule}
      caption="Precision and recall per rule across golden and synthetic cases"
      initialSort={{ id: 'rule', direction: 'asc' }}
      empty={<span className="text-ink-muted">No rule results in this report.</span>}
    />
  )
}
