import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'
import { Fragment, useMemo, useState, type KeyboardEvent, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { SkeletonTableRows } from './SkeletonRows'

export type SortDirection = 'asc' | 'desc'

export interface Column<T> {
  id: string
  header: ReactNode
  cell: (row: T, index: number) => ReactNode
  /** Comparator for ascending order; makes the header sortable. See `sortBy`. */
  sort?: (a: T, b: T) => number
  align?: 'left' | 'right' | 'center'
  /** CSS width for the column, e.g. "8rem" or "12%". */
  width?: string
  /** Render this cell as `<th scope="row">` (use for the identifying column). */
  rowHeader?: boolean
  className?: string
  headerClassName?: string
}

export interface DataTableProps<T> {
  columns: Column<T>[]
  rows: T[] | undefined
  getRowId: (row: T) => string
  /** Describes the table for screen readers (visually hidden unless `showCaption`). */
  caption: string
  showCaption?: boolean
  /** Renders skeleton rows under the real header (no spinner, no layout shift). */
  loading?: boolean
  skeletonRows?: number
  /** Shown in a full-width row when there are no rows. */
  empty?: ReactNode
  initialSort?: { id: string; direction: SortDirection }
  /** Makes rows focusable (Tab) and clickable; Enter / Space activate. */
  onRowClick?: (row: T) => void
  /** Accessible name for the row action, e.g. (row) => `Open lineage for ${row.code}`. */
  rowActionLabel?: (row: T) => string
  selectedRowId?: string | null
  rowClassName?: (row: T) => string | undefined
  /** Content rendered as a full-width row directly after a row (e.g. an in-place expansion). */
  renderAfterRow?: (row: T) => ReactNode
  /** Constrain height and scroll inside; the header stays sticky within the box. */
  maxHeight?: string
  /** Extra rows at the end of tbody (e.g. totals) — pass `<tr>` elements. */
  footer?: ReactNode
  className?: string
}

const ALIGN = { left: 'text-left', right: 'text-right', center: 'text-center' } as const

/**
 * Dense (36 px) semantic table with sticky header and optional sorting.
 * Sorting is stable: equal rows keep their incoming order.
 */
export function DataTable<T>({
  columns,
  rows,
  getRowId,
  caption,
  showCaption = false,
  loading = false,
  skeletonRows = 8,
  empty,
  initialSort,
  onRowClick,
  rowActionLabel,
  selectedRowId,
  rowClassName,
  renderAfterRow,
  maxHeight,
  footer,
  className,
}: DataTableProps<T>) {
  const [sort, setSort] = useState(initialSort ?? null)

  const sorted = useMemo(() => {
    if (!rows) return []
    const col = sort ? columns.find((c) => c.id === sort.id) : undefined
    if (!sort || !col?.sort) return rows
    const cmp = col.sort
    const dir = sort.direction === 'asc' ? 1 : -1
    return rows
      .map((row, i) => ({ row, i }))
      .sort((a, b) => cmp(a.row, b.row) * dir || a.i - b.i)
      .map((x) => x.row)
  }, [rows, columns, sort])

  const toggleSort = (id: string) => {
    setSort((prev) =>
      prev?.id === id
        ? { id, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { id, direction: 'asc' },
    )
  }

  const onRowKey = (e: KeyboardEvent<HTMLTableRowElement>, row: T) => {
    if (!onRowClick || e.target !== e.currentTarget) return
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onRowClick(row)
    }
  }

  return (
    <div
      className={cn(
        'relative w-full rounded-sm border border-rule bg-surface',
        // Scroll inside the box (both axes) so wide tables never push the page sideways and the
        // sticky header stays pinned at every width; short tables never reach the cap.
        'overflow-auto',
        !maxHeight && 'max-h-[80dvh]',
        className,
      )}
      style={maxHeight ? { maxHeight } : undefined}
    >
      <table className="w-full border-collapse text-sm">
        <caption className={showCaption ? 'px-3 py-2 text-left text-ink-muted' : 'sr-only'}>
          {caption}
        </caption>
        <colgroup>
          {columns.map((c) => (
            <col key={c.id} style={c.width ? { width: c.width } : undefined} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {columns.map((c) => {
              const active = sort?.id === c.id
              const ariaSort = active
                ? sort.direction === 'asc'
                  ? 'ascending'
                  : 'descending'
                : undefined
              return (
                <th
                  key={c.id}
                  scope="col"
                  aria-sort={c.sort ? (ariaSort ?? 'none') : undefined}
                  className={cn(
                    'sticky top-0 z-10 h-9 border-b border-rule bg-band px-3 font-medium whitespace-nowrap text-ink-muted',
                    ALIGN[c.align ?? 'left'],
                    c.headerClassName,
                  )}
                >
                  {c.sort ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(c.id)}
                      className={cn(
                        'inline-flex items-center gap-1 rounded-sm hover:text-ink',
                        c.align === 'right' && 'flex-row-reverse',
                        active && 'text-ink',
                      )}
                    >
                      {c.header}
                      {active ? (
                        sort.direction === 'asc' ? (
                          <ArrowUp className="size-3.5" aria-hidden />
                        ) : (
                          <ArrowDown className="size-3.5" aria-hidden />
                        )
                      ) : (
                        <ChevronsUpDown className="size-3.5 opacity-50" aria-hidden />
                      )}
                    </button>
                  ) : (
                    c.header
                  )}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <SkeletonTableRows rows={skeletonRows} columns={columns.length} />
          ) : sorted.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-3 py-6">
                {empty ?? <span className="text-ink-muted">Nothing to show.</span>}
              </td>
            </tr>
          ) : (
            sorted.map((row, index) => {
              const id = getRowId(row)
              const selected = selectedRowId != null && selectedRowId === id
              const after = renderAfterRow?.(row)
              return (
                <Fragment key={id}>
                  <tr
                    data-row-id={id}
                    tabIndex={onRowClick ? 0 : undefined}
                    aria-selected={onRowClick ? selected : undefined}
                    aria-label={onRowClick && rowActionLabel ? rowActionLabel(row) : undefined}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    onKeyDown={onRowClick ? (e) => onRowKey(e, row) : undefined}
                    className={cn(
                      'h-9 border-b border-rule last:border-b-0',
                      onRowClick && 'cursor-pointer hover:bg-band focus-visible:-outline-offset-2',
                      selected && 'bg-act-tint hover:bg-act-tint',
                      rowClassName?.(row),
                    )}
                  >
                    {columns.map((c) => {
                      const Cell = c.rowHeader ? 'th' : 'td'
                      return (
                        <Cell
                          key={c.id}
                          scope={c.rowHeader ? 'row' : undefined}
                          className={cn(
                            'px-3 py-1.5 align-middle font-normal',
                            ALIGN[c.align ?? 'left'],
                            c.className,
                          )}
                        >
                          {c.cell(row, index)}
                        </Cell>
                      )
                    })}
                  </tr>
                  {after ? (
                    <tr className="border-b border-rule">
                      <td colSpan={columns.length} className="p-0">
                        {after}
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              )
            })
          )}
          {!loading && sorted.length > 0 ? footer : null}
        </tbody>
      </table>
    </div>
  )
}
