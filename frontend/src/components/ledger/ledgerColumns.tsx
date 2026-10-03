import type { LineageKind, PostedLine } from '@/api/types'
import type { Column } from '@/components/DataTable'
import { Money } from '@/components/Money'
import { sortBy } from '@/lib/sort'
import { MappedCell } from './MappedCell'

const KIND_NOUN: Record<LineageKind, [string, string]> = {
  TB_ROW: ['TB row', 'TB rows'],
  FX: ['FX rate', 'FX rates'],
  JE: ['JE line', 'JE lines'],
  HUMAN: ['human decision', 'human decisions'],
  TRANSLATION_DIFF: ['translation difference', 'translation differences'],
}

/** "1 TB row, 1 FX rate, 2 JE lines" — what the sources count is made of. */
export function sourcesSummary(line: PostedLine): string {
  const counts = new Map<LineageKind, number>()
  for (const ref of line.lineage) counts.set(ref.kind, (counts.get(ref.kind) ?? 0) + 1)
  return [...counts.entries()]
    .map(([kind, n]) => {
      const [one, many] = KIND_NOUN[kind] ?? [kind, kind]
      return `${n} ${n === 1 ? one : many}`
    })
    .join(', ')
}

export const LEDGER_COLUMNS: Column<PostedLine>[] = [
  {
    id: 'code',
    header: 'Account',
    rowHeader: true,
    width: '6.5rem',
    sort: sortBy.string((l: PostedLine) => l.account_code),
    cell: (l) => <span className="num font-medium">{l.account_code}</span>,
  },
  {
    id: 'name',
    header: 'Name',
    sort: sortBy.string((l: PostedLine) => l.account_name),
    cell: (l) => <span className="block min-w-[10rem]">{l.account_name}</span>,
  },
  {
    id: 'debit',
    header: 'Debit',
    align: 'right',
    width: '10rem',
    sort: sortBy.decimal((l: PostedLine) => l.debit),
    cell: (l) => <Money value={l.debit} />,
  },
  {
    id: 'credit',
    header: 'Credit',
    align: 'right',
    width: '10rem',
    sort: sortBy.decimal((l: PostedLine) => l.credit),
    cell: (l) => <Money value={l.credit} />,
  },
  {
    id: 'net',
    header: 'Net (Dr − Cr)',
    align: 'right',
    width: '10.5rem',
    sort: sortBy.decimal((l: PostedLine) => l.net),
    cell: (l) => <Money value={l.net} />,
  },
  {
    id: 'mapped',
    header: 'Mapped',
    width: '7rem',
    sort: sortBy.string((l: PostedLine) => (l.mapped ? '1' : '0')),
    cell: (l) => <MappedCell mapped={l.mapped} />,
  },
  {
    id: 'sources',
    header: 'Sources',
    align: 'right',
    width: '5.5rem',
    sort: sortBy.number((l: PostedLine) => l.lineage.length),
    cell: (l) => (
      <span className="num" title={sourcesSummary(l)}>
        {l.lineage.length}
        <span className="sr-only"> ({sourcesSummary(l)})</span>
      </span>
    ),
  },
]

export function lineageLabel(l: PostedLine): string {
  return `Open lineage for ${l.account_code} ${l.account_name}`
}
