import { Skeleton } from '@/components/ui/skeleton'

const WIDTHS = ['w-3/4', 'w-1/2', 'w-2/3', 'w-5/6', 'w-2/5']

/** Static placeholder rows inside a `<tbody>` (36 px, same as real rows: no layout shift). */
export function SkeletonTableRows({ rows = 8, columns }: { rows?: number; columns: number }) {
  return (
    <>
      {Array.from({ length: rows }, (_, r) => (
        <tr key={r} className="h-9 border-b border-rule last:border-b-0" aria-hidden>
          {Array.from({ length: columns }, (_, c) => (
            <td key={c} className="px-3 py-1.5">
              <Skeleton className={`h-3.5 ${WIDTHS[(r + c) % WIDTHS.length]}`} />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

/**
 * Loading placeholder for a table-shaped region outside a DataTable. Announces "Loading" to
 * screen readers once; the bars themselves are hidden from assistive tech.
 */
export function SkeletonRows({
  rows = 8,
  columns = 5,
  label = 'Loading',
}: {
  rows?: number
  columns?: number
  label?: string
}) {
  return (
    <div role="status" className="w-full rounded-sm border border-rule bg-surface">
      <span className="sr-only">{label}</span>
      <table className="w-full" aria-hidden>
        <tbody>
          <tr className="h-9 border-b border-rule bg-band">
            {Array.from({ length: columns }, (_, c) => (
              <td key={c} className="px-3">
                <Skeleton className="h-3 w-16 bg-rule" />
              </td>
            ))}
          </tr>
          <SkeletonTableRows rows={rows} columns={columns} />
        </tbody>
      </table>
    </div>
  )
}

/** A few text-line placeholders (e.g. for an explanation or a markdown document). */
export function SkeletonLines({ lines = 4 }: { lines?: number }) {
  return (
    <div role="status" className="flex flex-col gap-2.5">
      <span className="sr-only">Loading</span>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} aria-hidden className={`h-3.5 ${WIDTHS[i % WIDTHS.length]}`} />
      ))}
    </div>
  )
}
