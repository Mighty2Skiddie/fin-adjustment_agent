import type { PostedLine } from '@/api/types'
import { sumDecimals } from './decimal'

export interface CoaRoot {
  key: string
  label: string
}

/**
 * COA roots by the first digit of the account code. Unmapped lines always go to the last
 * group, whatever their first digit: they must never sit inside a COA subtotal (assumption A6).
 */
export const COA_ROOTS: readonly CoaRoot[] = [
  { key: '1', label: 'Assets' },
  { key: '2', label: 'Liabilities' },
  { key: '3', label: 'Equity' },
  { key: '4', label: 'Revenue' },
  { key: '5', label: 'Cost of goods sold' },
  { key: '6', label: 'Operating expenses' },
  { key: '7', label: 'Non-operating' },
  { key: '8', label: 'Income tax' },
  { key: '9', label: 'Unmapped' },
]

export const UNMAPPED_ROOT = '9'

export function rootKeyOf(line: Pick<PostedLine, 'account_code' | 'mapped'>): string {
  if (!line.mapped) return UNMAPPED_ROOT
  const first = line.account_code.charAt(0)
  return COA_ROOTS.some((r) => r.key === first) ? first : UNMAPPED_ROOT
}

export interface Subtotal {
  debit: string
  credit: string
  net: string
}

export function subtotal(lines: readonly PostedLine[]): Subtotal {
  return {
    debit: sumDecimals(lines.map((l) => l.debit)),
    credit: sumDecimals(lines.map((l) => l.credit)),
    net: sumDecimals(lines.map((l) => l.net)),
  }
}

export interface LedgerGroup extends CoaRoot {
  lines: PostedLine[]
  totals: Subtotal
}

/** Lines grouped by COA root in chart order; empty roots are left out. */
export function groupByRoot(lines: readonly PostedLine[]): LedgerGroup[] {
  return COA_ROOTS.map((root) => {
    const inRoot = lines
      .filter((l) => rootKeyOf(l) === root.key)
      .sort((a, b) => a.account_code.localeCompare(b.account_code))
    return { ...root, lines: inRoot, totals: subtotal(inRoot) }
  }).filter((g) => g.lines.length > 0)
}
